"""Cosmos as a MEASURED critic: Cosmos-Reason2 labels arm rollout clips, the simulator labels are ground truth.

  python -m transfergap critic render [--split dev|tuning|v2] [--cameras v1 close ...] [--static-controls N]
  python -m transfergap critic run [--prompt v1|obs] [--camera v1|close|close_top] [--tag T] [--frozen-v2]
  python -m transfergap critic score [--tag T]
  python -m transfergap critic tuning --run-dir runs/cosmos_critic_v2/tuning --tags ...

Labels come from metrics.score_episode on gap_budget_v2 rollouts (UR5e and UR10e). Seed splits never overlap:
v1 used dev seeds 0-59; v2 tunes on 2000-2019 and is scored on 2020-2079; held-out 1000-1059 never enter.
Stage label: "none" (success), "grasp" (no_lift: block never lifted >= min_lift_m), "place" (lifted, but not
released and settled at the goal). Prompts and cameras are frozen: a scored run refuses to start unless this file
is committed and unmodified, and every receipt records the prompt hash and the git commit.
"""
from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .hosted import NoRedirect
from .metrics import wilson_interval

ROOT = Path(__file__).resolve().parents[1]              # transfergap/ (project dir)
REPO = ROOT.parent
RUN_DIR = ROOT / "runs" / "cosmos_critic_v1"
RESULTS_DIR = ROOT / "results" / "cosmos_critic_v1"
DEFAULT_MODEL = "nvidia/Cosmos-Reason2-8B"
STAGES = ("none", "grasp", "place")
PROTOCOL = "gap_budget_v2"
ROBOTS = ("ur5e", "ur10e")             # both v2 arms: the place-only failure is rare per arm
SPLITS = {"dev": list(range(0, 60)),               # v1 (gap_budget dev seeds)
          "tuning": list(range(2000, 2020)),       # v2 exploratory tuning
          "v2": list(range(2020, 2080))}           # v2 confirmatory scoring
FORBIDDEN_SEEDS = set(range(1000, 1060))           # gap_budget held-out: never rendered here

# ---------------------------------------------------------------- frozen prompt (v1)
# Model-card settings (huggingface.co/nvidia/Cosmos-Reason2-8B and github.com/nvidia-cosmos/cosmos-reason2):
# fps=4, max_tokens >= 4096, the reasoning-format suffix appended to the user prompt, default system prompt,
# and the repository's reasoning sampling defaults (cosmos_reason2_utils SamplingOverrides, reasoning=True).
SYSTEM_PROMPT = "You are a helpful assistant."
REASONING_PROMPT = ("Answer the question using the following format:\n\n<think>\nYour reasoning.\n</think>\n\n"
                    "Write your final answer immediately after the </think> tag.")
CRITIC_PROMPT = (
    "The video shows a simulated robot arm, seen from a fixed third-person camera, attempting one task: pick up "
    "the small red block from the table, carry it to the green tray, release it so it rests inside the tray, "
    "and move the gripper away.\n"
    "Watch the whole clip and judge the outcome.\n"
    "(a) success: \"yes\" only if, at the end of the video, the red block has been released and is resting "
    "inside the green tray; otherwise \"no\".\n"
    "(b) failing_stage: exactly one of\n"
    "  \"none\"  - the task succeeded;\n"
    "  \"grasp\" - the gripper never lifted the block off the table (it missed, pushed or knocked the block, "
    "or lost it before lifting);\n"
    "  \"place\" - the block was lifted, but it did not end up released and resting inside the green tray.\n"
    "(c) rationale: one or two short sentences describing what you saw.\n"
    "Your final answer must be a single JSON object and nothing else, exactly of the form "
    "{\"success\": \"yes\" or \"no\", \"failing_stage\": \"none\" or \"grasp\" or \"place\", "
    "\"rationale\": \"...\"}."
)
USER_PROMPT = CRITIC_PROMPT + "\n\n" + REASONING_PROMPT
FPS = 4
SAMPLING = {"max_tokens": 4096, "temperature": 0.6, "top_p": 0.95, "top_k": 20, "repetition_penalty": 1.0,
            "presence_penalty": 0.0, "seed": 1234}
ANSWER_SCHEMA = {"type": "object", "additionalProperties": False,
                 "required": ["success", "failing_stage", "rationale"],
                 "properties": {"success": {"type": "string", "enum": ["yes", "no"]},
                                "failing_stage": {"type": "string", "enum": list(STAGES)},
                                "rationale": {"type": "string", "maxLength": 600}}}

# ---------------------------------------------------------------- v2: observational prompt (no task narration)
# The v1 critic answered "success" for every clip and its reasoning restated the task steps from the prompt.
# The observational prompt never states the intended task or its steps; it asks what is visible, and success /
# stage are derived from the answers in code (derive_from_observation).
OBS_PROMPT = (
    "The video shows a robot arm, a red cube and a green tray on a table.{views}\n"
    "Answer only from what is visible in the video.\n"
    "(a) cube_last_frame: where is the red cube in the last frame of the video? Exactly one of\n"
    "  \"table\"   - resting on the table surface, outside the green tray;\n"
    "  \"tray\"    - resting inside the green tray;\n"
    "  \"gripper\" - held by, or touching, the robot's gripper.\n"
    "(b) cube_left_table: at any time in the video, was the red cube lifted off the table into the air? "
    "\"yes\" or \"no\".\n"
    "(c) observations: one or two short sentences describing what happens to the red cube.\n"
    "Your final answer must be a single JSON object and nothing else, exactly of the form "
    "{{\"cube_last_frame\": \"table\" or \"tray\" or \"gripper\", \"cube_left_table\": \"yes\" or \"no\", "
    "\"observations\": \"...\"}}."
)
OBS_TWO_VIEWS = (" Each frame shows two views of the same moment side by side: on the left a front view, on the "
                 "right a top-down view.")
OBS_SCHEMA = {"type": "object", "additionalProperties": False,
              "required": ["cube_last_frame", "cube_left_table", "observations"],
              "properties": {"cube_last_frame": {"type": "string", "enum": ["table", "tray", "gripper"]},
                             "cube_left_table": {"type": "string", "enum": ["yes", "no"]},
                             "observations": {"type": "string", "maxLength": 600}}}
PROMPTS = ("v1", "obs")

# ---------------------------------------------------------------- cameras
# Free cameras close to the workspace (block start ~(0.45, -0.12), tray (0.45, 0.22)). At these settings a 4 cm
# block spans ~77 px (close, 640x480) and ~58 / ~57 px (close_top front / top views at 480x360), measured with
# segmentation rendering at the block start and in the tray.
CLOSE_FRONT = {"lookat": [0.45, 0.05, 0.11], "distance": 0.42, "azimuth": 180.0, "elevation": -18.0}
CLOSE_TOP = {"lookat": [0.45, 0.05, 0.0], "distance": 0.44, "azimuth": 180.0, "elevation": -89.0}
CAMERAS = {"v1": {"views": ["third_person"], "size": [480, 640]},
           "close": {"views": [CLOSE_FRONT], "size": [480, 640]},
           "close_top": {"views": [CLOSE_FRONT, CLOSE_TOP], "size": [360, 480]}}

# Chosen on the tuning split (seeds 2000-2019) BEFORE the confirmatory run; see
# results/cosmos_critic_v2/tuning_exploratory/. obs+close and obs+close_top tied (9/17 stage, 0/2 static controls
# called success); the single view is chosen because it is simpler and uses fewer video tokens.
FROZEN_V2 = {"prompt": "obs", "camera": "close"}
V2_STATIC_CONTROLS = 6    # negative controls added to the confirmatory set, reported separately


def user_prompt(prompt="v1", camera="v1"):
    if prompt == "v1":
        return USER_PROMPT
    if prompt == "obs":
        views = OBS_TWO_VIEWS if len(CAMERAS[camera]["views"]) > 1 else ""
        return OBS_PROMPT.format(views=views) + "\n\n" + REASONING_PROMPT
    raise ValueError(f"unknown prompt {prompt!r}")


def answer_schema(prompt="v1"):
    return ANSWER_SCHEMA if prompt == "v1" else OBS_SCHEMA


def prompt_sha256(prompt="v1", camera="v1"):
    if prompt == "v1" and camera == "v1":   # v1 hash, unchanged so the v1 receipts stay verifiable
        blob = {"system": SYSTEM_PROMPT, "user": USER_PROMPT, "fps": FPS, "sampling": SAMPLING,
                "schema": ANSWER_SCHEMA}
    else:
        blob = {"system": SYSTEM_PROMPT, "user": user_prompt(prompt, camera), "fps": FPS, "sampling": SAMPLING,
                "schema": answer_schema(prompt), "camera": CAMERAS[camera]}
    return hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    """Repo-relative path for anything written into a result file (never an absolute local path)."""
    p = Path(path).resolve()
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return p.name


# ---------------------------------------------------------------- labels

def stage_label(score):
    """metrics.score_episode result -> one of STAGES (first failing stage)."""
    if score["success"]:
        return "none"
    return "grasp" if "no_lift" in score["failure_reasons"] else "place"


def _assert_dev(seeds):
    from .diagnose import assert_dev_only
    return assert_dev_only(seeds)


def assert_split(seeds, split):
    seeds = [int(s) for s in seeds]
    if not seeds:
        raise ValueError("no seeds")
    if set(seeds) & FORBIDDEN_SEEDS:
        raise ValueError("held-out seeds 1000-1059 must never be used by the critic")
    if split == "dev":
        return _assert_dev(seeds)
    if not set(seeds) <= set(SPLITS[split]):
        raise ValueError(f"split {split!r} allows seeds {SPLITS[split][0]}-{SPLITS[split][-1]} only")
    return seeds


def _outcome_job(a):
    seed, cond, robot = a
    from .metrics import score_episode
    from .sim.errors_v2 import build_perturbation
    from .sim.rollout import run_episode
    pert, oracle = build_perturbation(seed, cond)
    ep = run_episode(seed, pert, label=cond, oracle=oracle, condition=cond, robot=robot)
    s = score_episode(ep)
    return {"seed": seed, "condition": cond, "robot": robot, "success": s["success"],
            "failure_reasons": s["failure_reasons"], "stage": stage_label(s), "elapsed_s": s["elapsed_s"]}


def _render_job(a):
    seed, cond, robot, path, camera = a[:5]
    from .metrics import score_episode
    from .sim.errors_v2 import build_perturbation
    from .sim.rollout import run_episode
    cam = CAMERAS[camera]
    pert, oracle = build_perturbation(seed, cond)
    ep = run_episode(seed, pert, video_path=path, label=cond, oracle=oracle, condition=cond, robot=robot,
                     cameras=cam["views"], size=tuple(cam["size"]))
    if not ep["video"]:
        raise RuntimeError("no working GL backend; cannot render clips")
    s = score_episode(ep)
    return {"success": s["success"], "failure_reasons": s["failure_reasons"], "stage": stage_label(s)}


STATIC_SECONDS = 4.5      # ~ median rollout clip length


def _static_job(a):
    """Negative control: the arm holds its home pose, nothing moves. Label: failure at grasp (no lift)."""
    seed, robot, path, camera = a
    import imageio.v2 as imageio
    import mujoco
    from .sim.rollout import make_camera, make_renderer, render_views
    from .sim.scene import Scene
    cam = CAMERAS[camera]
    scene = Scene(seed, robot)
    m, d = scene.model, scene.data
    renderer = make_renderer(scene, tuple(cam["size"]))
    if renderer is None:
        raise RuntimeError("no working GL backend; cannot render clips")
    cams = [make_camera(c) for c in cam["views"]]
    frames, every = [], round(1 / (25 * m.opt.timestep))
    z0 = scene.block_pos()[2]
    for i in range(round(STATIC_SECONDS / m.opt.timestep)):
        mujoco.mj_step(m, d)
        if i % every == 0:
            frames.append(render_views(renderer, d, cams))
    renderer.close()
    imageio.mimwrite(path, frames, fps=25)
    if scene.block_pos()[2] - z0 > 0.01:
        raise RuntimeError("static control: block moved")
    return {"success": False, "failure_reasons": ["no_lift", "not_released_and_settled_at_goal"], "stage": "grasp"}


def select_balanced(outcomes, n_per_class, rng_seed=0):
    """Up to n_per_class episodes per stage, deterministic shuffle. Within a class, distinct (robot, seed) pairs
    are taken first; a pair is reused (another condition = another error draw) only if the class runs short."""
    rng = random.Random(rng_seed)
    picked = []
    for stage in STAGES:
        cands = sorted((o for o in outcomes if o["stage"] == stage),
                       key=lambda o: (o.get("robot", ""), o["seed"], o["condition"]))
        rng.shuffle(cands)
        seen, first, rest = set(), [], []
        for o in cands:
            key = (o.get("robot"), o["seed"])
            (rest if key in seen else first).append(o)
            seen.add(key)
        picked += (first + rest)[:n_per_class]
    return picked


def render(n_per_class=40, out_dir=None, procs=None, split="dev", cameras=("v1",), static_controls=0):
    """Label every (robot, seed, condition) of the split, pick a balanced set, render it once per camera config.
    v1 (split dev, camera v1) writes the v1 layout (clips/, video, video_sha256)."""
    import multiprocessing as mp
    import os
    from .sim.errors_v2 import CONDITIONS
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    out_dir = Path(out_dir or RUN_DIR)
    seeds = assert_split(SPLITS[split], split)
    for c in cameras:
        if c not in CAMERAS:
            raise ValueError(f"unknown camera {c!r}")
    legacy = list(cameras) == ["v1"] and split == "dev"
    clipdir = {c: out_dir / ("clips" if legacy else f"clips_{c}") for c in cameras}
    for d in clipdir.values():
        d.mkdir(parents=True, exist_ok=True)
    procs = procs or min(20, mp.cpu_count() or 2)
    with mp.get_context("spawn").Pool(procs) as pool:
        outcomes = pool.map(_outcome_job, [(s, c, r) for r in ROBOTS for s in seeds for c in CONDITIONS],
                            chunksize=2)
        picked = select_balanced(outcomes, n_per_class)
        statics = [{"seed": seeds[i % len(seeds)], "robot": ROBOTS[i % len(ROBOTS)], "condition": "static_control",
                    "success": False, "failure_reasons": ["no_lift", "not_released_and_settled_at_goal"],
                    "stage": "grasp", "elapsed_s": STATIC_SECONDS} for i in range(static_controls)]
        # Opaque clip ids: the file name must not leak the condition or the outcome.
        order = sorted(picked + statics, key=lambda o: hashlib.sha256(
            f"{o['robot']}|{o['seed']}|{o['condition']}".encode()).hexdigest())
        for i, o in enumerate(order):
            o["clip_id"] = f"clip{i:03d}"
        rendered = {}
        for cam in cameras:
            jobs = [(o["seed"], o["condition"], o["robot"], str(clipdir[cam] / f"{o['clip_id']}.mp4"), cam)
                    for o in order]
            rollouts = pool.map(_render_job, [j for j in jobs if j[1] != "static_control"], chunksize=1)
            controls = pool.map(_static_job, [(j[0], j[2], j[3], j[4]) for j in jobs if j[1] == "static_control"])
            it_r, it_c = iter(rollouts), iter(controls)
            rendered[cam] = [next(it_c) if o["condition"] == "static_control" else next(it_r) for o in order]
    rows = []
    for k, o in enumerate(order):
        for cam in cameras:
            if rendered[cam][k]["stage"] != o["stage"]:
                raise RuntimeError(f"rendered rollout differs from label pass: {o['robot']} seed {o['seed']} "
                                   f"{o['condition']} ({cam})")
        row = {"clip_id": o["clip_id"], "seed": o["seed"], "condition": o["condition"], "protocol": PROTOCOL,
               "robot": o["robot"], "split": split, "success": o["success"], "stage": o["stage"],
               "failure_reasons": o["failure_reasons"], "elapsed_s": o["elapsed_s"]}
        paths = {cam: clipdir[cam] / f"{o['clip_id']}.mp4" for cam in cameras}
        if legacy:
            row.update(camera="third_person", video=str(paths["v1"].relative_to(out_dir)),
                       video_sha256=sha256_file(paths["v1"]))
        else:
            row.update(videos={c: str(p.relative_to(out_dir)) for c, p in paths.items()},
                       video_sha256={c: sha256_file(p) for c, p in paths.items()})
        rows.append(row)
    labels = out_dir / "labels.jsonl"
    labels.write_text("".join(json.dumps(r) + "\n" for r in rows))
    pool_counts = Counter(f"{o['robot']}:{o['stage']}" for o in outcomes)
    summary = {"labels": rel(labels), "split": split, "seeds": [seeds[0], seeds[-1]], "cameras": list(cameras),
               "n": len(rows), "per_stage": dict(Counter(r["stage"] for r in rows)),
               "static_controls": static_controls,
               "per_robot_stage": dict(Counter(f"{r['robot']}:{r['stage']}" for r in rows)),
               "distinct_robot_seed_pairs_per_stage": {
                   st: len({(r["robot"], r["seed"]) for r in rows if r["stage"] == st}) for st in STAGES},
               "candidate_pool_per_stage": dict(pool_counts), "candidate_pool_n": len(outcomes)}
    (out_dir / "render_summary.json").write_text(json.dumps(summary, indent=1))
    return summary


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------- request

def critic_messages(video_path, prompt="v1", camera="v1"):
    path = Path(video_path)
    if path.suffix.lower() != ".mp4" or not path.is_file():
        raise ValueError("Provide a local MP4 clip")
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("clip larger than 20 MiB")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "video_url", "video_url": {"url": "data:video/mp4;base64," + data}},
                {"type": "text", "text": user_prompt(prompt, camera)}]}]


def request_body(model, messages, guided=True, prompt="v1"):
    # vLLM 0.30 samples video frames in its media loader: per-request media_io_kwargs fps=4 gives 4 frames per
    # second of clip (checked: a 3.16 s clip -> 12 frames). The HF processor must not resample them again
    # (do_sample_frames=True on already-sampled frames is rejected); fps is kept for the frame timestamps.
    body = {"model": model, "messages": messages, **SAMPLING,
            "media_io_kwargs": {"video": {"fps": FPS, "num_frames": -1}},
            "mm_processor_kwargs": {"fps": FPS, "do_sample_frames": False}}
    if guided:
        body["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "critic_answer", "schema": answer_schema(prompt), "strict": True}}
    return body


def check_base_url(base):
    """Self-hosted vLLM over an SSH tunnel: plain HTTP is allowed only to a loopback host; otherwise HTTPS."""
    p = urllib.parse.urlparse(base)
    if not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError("base URL must be http(s)://host[:port]/v1 without credentials")
    if p.scheme == "http" and p.hostname in ("127.0.0.1", "localhost", "::1"):
        return p
    if p.scheme == "https":
        return p
    raise ValueError("plain HTTP is only allowed to a loopback host (use an SSH tunnel)")


def derive_from_observation(last, left_table):
    """Observational answers -> (success, failing_stage), using the simulator's stage definitions."""
    if last == "tray":
        return True, "none"
    return False, ("place" if left_table == "yes" else "grasp")


def _json_obj(content):
    if not isinstance(content, str):
        return None, "no text content"
    text = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.S)
    if fence:
        text = fence.group(1)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None, "not a single JSON object"
    if not isinstance(obj, dict):
        return None, "JSON is not an object"
    return obj, None


def parse_answer(content, prompt="v1"):
    """-> (answer dict, None) or (None, error). Strips a <think> block and an optional ```json fence.
    Every answer has success (bool), failing_stage and rationale; observational answers also keep the raw
    observations they were derived from."""
    obj, err = _json_obj(content)
    if obj is None:
        return None, err
    if prompt == "obs":
        last = str(obj.get("cube_last_frame", "")).strip().lower()
        left = str(obj.get("cube_left_table", "")).strip().lower()
        if last not in ("table", "tray", "gripper"):
            return None, "cube_last_frame not in the fixed list"
        if left not in ("yes", "no"):
            return None, "cube_left_table not yes/no"
        success, stage = derive_from_observation(last, left)
        obs = obj.get("observations", "")
        return {"success": success, "failing_stage": stage,
                "rationale": obs if isinstance(obs, str) else json.dumps(obs),
                "observed": {"cube_last_frame": last, "cube_left_table": left}}, None
    success = str(obj.get("success", "")).strip().lower()
    stage = str(obj.get("failing_stage", "")).strip().lower()
    if success not in ("yes", "no"):
        return None, "success not yes/no"
    if stage not in STAGES:
        return None, "failing_stage not in the fixed list"
    rationale = obj.get("rationale", "")
    return {"success": success == "yes", "failing_stage": stage,
            "rationale": rationale if isinstance(rationale, str) else json.dumps(rationale)}, None


def critique_clip(video_path, receipt_path, base_url, model=DEFAULT_MODEL, api_key=None, timeout=600,
                  guided=True, extra=None, prompt="v1", camera="v1"):
    """One request. Writes a receipt (never overwrites) and returns it; failures are recorded, not raised."""
    p = check_base_url(base_url)
    body = json.dumps(request_body(model, critic_messages(video_path, prompt, camera), guided, prompt),
                      allow_nan=False).encode()
    path = Path(receipt_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as fh:
        receipt = {"schema_version": 1, "kind": "cosmos_critic", "requested_model": model,
                   "endpoint_host": p.hostname, "created_at": datetime.now(timezone.utc).isoformat(),
                   "prompt_sha256": prompt_sha256(prompt, camera), "video_sha256": sha256_file(video_path),
                   "request_sha256": hashlib.sha256(body).hexdigest(), "fps": FPS, "sampling": SAMPLING,
                   "guided_json": guided, "status": "started", **(extra or {})}
        if (prompt, camera) != ("v1", "v1"):
            receipt.update(prompt=prompt, camera=camera)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        start = time.monotonic()
        try:
            req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body, headers=headers)
            with urllib.request.build_opener(NoRedirect).open(req, timeout=timeout) as resp:
                result = json.load(resp)
            choice = result["choices"][0]
            msg = choice["message"]
            content = msg.get("content")
            reasoning = msg.get("reasoning_content") or msg.get("reasoning")
            answer, err = parse_answer(content, prompt)
            receipt.update(status="succeeded", response_id=result.get("id"), returned_model=result.get("model"),
                           usage=result.get("usage"), finish_reason=choice.get("finish_reason"),
                           content=content, reasoning_content=reasoning, parsed=answer is not None,
                           answer=answer, parse_error=err)
        except Exception as exc:
            receipt.update(status="failed", error_type=type(exc).__name__, parsed=False, answer=None)
        finally:
            receipt["latency_s"] = time.monotonic() - start
            json.dump(receipt, fh, indent=2, allow_nan=False)
            fh.write("\n")
    return receipt


def _committed(path):
    rel_path = str(Path(path).resolve().relative_to(ROOT))
    if subprocess.run(["git", "ls-files", "--error-unmatch", rel_path], cwd=ROOT, capture_output=True).returncode:
        return False
    return not subprocess.check_output(["git", "status", "--porcelain", "--", rel_path], cwd=ROOT, text=True).strip()


def git_hash():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def run(base_url, labels=None, model=DEFAULT_MODEL, out_dir=None, workers=4, limit=None, api_key=None,
        tag="scored", require_frozen=True, guided=True, prompt="v1", camera="v1", frozen_v2=False):
    """One request per clip. Receipts go to <out_dir>/receipts_<tag>/; predictions to predictions_<tag>.jsonl.
    frozen_v2: use FROZEN_V2's prompt and camera (and require them to be set and committed)."""
    out_dir = Path(out_dir or RUN_DIR)
    labels = Path(labels or out_dir / "labels.jsonl")
    rows = read_jsonl(labels)
    split = rows[0].get("split", "dev")
    if any(r.get("split", "dev") != split for r in rows):
        raise ValueError("labels mix seed splits")
    assert_split([r["seed"] for r in rows], split)
    if frozen_v2:
        if not FROZEN_V2["prompt"] or not FROZEN_V2["camera"]:
            raise ValueError("FROZEN_V2 is not set; choose on the tuning split and commit first")
        if split != "v2":
            raise ValueError("the frozen v2 configuration is scored on the v2 split only")
        prompt, camera, require_frozen = FROZEN_V2["prompt"], FROZEN_V2["camera"], True
    if split == "v2" and not frozen_v2:
        raise ValueError("the v2 split is confirmatory: run it only with --frozen-v2")
    if prompt not in PROMPTS or camera not in CAMERAS:
        raise ValueError("unknown prompt or camera")
    if limit:
        rows = rows[:limit]
    if require_frozen and not _committed(Path(__file__)):
        raise ValueError("critic.py (the frozen prompt) must be committed and unmodified before a scored run")
    commit = git_hash()
    rdir = out_dir / f"receipts_{tag}"

    def one(r):
        if "videos" in r:
            video, sha = out_dir / r["videos"][camera], r["video_sha256"][camera]
        else:
            if camera != "v1":
                raise ValueError("v1 labels only have the v1 camera")
            video, sha = out_dir / r["video"], r["video_sha256"]
        if sha256_file(video) != sha:
            raise ValueError(f"{r['clip_id']}: clip hash differs from labels")
        rec = critique_clip(video, rdir / f"{r['clip_id']}.json", base_url, model, api_key, guided=guided,
                            extra={"clip_id": r["clip_id"], "git_commit": commit}, prompt=prompt, camera=camera)
        return {"clip_id": r["clip_id"], "status": rec["status"], "parsed": rec.get("parsed", False),
                "answer": rec.get("answer"), "latency_s": rec["latency_s"], "usage": rec.get("usage"),
                "response_id": rec.get("response_id"), "finish_reason": rec.get("finish_reason")}

    with ThreadPoolExecutor(max(1, workers)) as ex:
        preds = list(ex.map(one, rows))
    pred_path = out_dir / f"predictions_{tag}.jsonl"
    pred_path.write_text("".join(json.dumps(p) + "\n" for p in preds))
    manifest = {"model": model, "base_url_host": urllib.parse.urlparse(base_url).hostname, "git_commit": commit,
                "prompt_sha256": prompt_sha256(prompt, camera), "labels": rel(labels),
                "labels_sha256": sha256_file(labels), "n": len(preds), "workers": workers, "guided_json": guided,
                "finished_at": datetime.now(timezone.utc).isoformat()}
    if (prompt, camera) != ("v1", "v1"):
        manifest.update(prompt=prompt, camera=camera, split=split, frozen_v2=frozen_v2)
    (out_dir / f"manifest_{tag}.json").write_text(json.dumps(manifest, indent=1))
    return {"predictions": rel(pred_path), "n": len(preds), "parsed": sum(p["parsed"] for p in preds),
            "failed": sum(p["status"] != "succeeded" for p in preds)}


# ---------------------------------------------------------------- scoring

def confusion(truth, pred, classes):
    m = {t: {p: 0 for p in classes} for t in classes}
    for t, p in zip(truth, pred):
        m[t][p] += 1
    return m


def per_class(m, classes):
    out = {}
    for c in classes:
        tp = m[c][c]
        pred_c = sum(m[t][c] for t in classes)
        true_c = sum(m[c].values())
        out[c] = {"support": true_c, "predicted": pred_c,
                  "precision": tp / pred_c if pred_c else None, "recall": tp / true_c if true_c else None}
    return out


def _acc(k, n):
    return {"correct": k, "n": n, "accuracy": k / n if n else None, "wilson_95": wilson_interval(k, n) if n else None}


def score(labels, predictions):
    """Unparsed or failed answers count as wrong (class "unparsed" in the confusion matrix). Static negative
    controls (robot never moves) are reported separately and excluded from the main metrics."""
    truth = {r["clip_id"]: r for r in labels}
    preds = {p["clip_id"]: p for p in predictions}
    if len(truth) != len(labels) or len(preds) != len(predictions):
        raise ValueError("duplicate clip IDs in labels or predictions")
    if set(preds) != set(truth):
        raise ValueError(f"prediction/label clip IDs differ: missing={len(set(truth) - set(preds))}, "
                         f"extra={len(set(preds) - set(truth))}")
    controls = sorted(i for i in set(truth) & set(preds) if truth[i].get("condition") == "static_control")
    ids = sorted(i for i in set(truth) & set(preds) if truth[i].get("condition") != "static_control")
    if not ids:
        raise ValueError("no overlapping clips between labels and predictions")
    succ_cls, stage_cls = ["yes", "no", "unparsed"], list(STAGES) + ["unparsed"]
    t_s = ["yes" if truth[i]["success"] else "no" for i in ids]
    t_g = [truth[i]["stage"] for i in ids]

    def pred_of(i):
        a = preds[i].get("answer") if preds[i].get("parsed") else None
        return ("unparsed", "unparsed") if a is None else ("yes" if a["success"] else "no", a["failing_stage"])
    p_s, p_g = zip(*(pred_of(i) for i in ids))
    n = len(ids)
    res = {}
    for name, t, p, classes in (("success", t_s, p_s, succ_cls), ("stage", t_g, p_g, stage_cls)):
        k = sum(a == b for a, b in zip(t, p))
        maj, maj_n = Counter(t).most_common(1)[0]
        m = confusion(t, p, classes)
        res[name] = {"accuracy": _acc(k, n), "confusion": m,
                     "per_class": per_class(m, [c for c in classes if c != "unparsed"]),
                     "majority_baseline": {"class": maj, **_acc(maj_n, n)},
                     "uniform_chance": 1 / (len(classes) - 1)}
    consistent = sum((a == "yes") == (b == "none") for a, b in zip(p_s, p_g) if a != "unparsed")
    parsed = sum(a != "unparsed" for a in p_s)
    lat = sorted(preds[i]["latency_s"] for i in ids if preds[i].get("latency_s") is not None)
    toks = [preds[i]["usage"] for i in ids if preds[i].get("usage")]
    res["n"] = n
    res["parsed"] = parsed
    res["truncated"] = sum(preds[i].get("finish_reason") == "length" for i in ids)
    res["internal_consistency"] = {"success_yes_iff_stage_none": consistent, "of_parsed": parsed}
    res["latency_s"] = {"median": lat[len(lat) // 2], "max": lat[-1]} if lat else None
    if toks:
        res["tokens_mean"] = {k: sum(u.get(k, 0) for u in toks) / len(toks)
                              for k in ("prompt_tokens", "completion_tokens")}
    res["truth_per_stage"] = dict(Counter(t_g))
    if controls:
        cp = [pred_of(i) for i in controls]
        res["static_controls"] = {"n": len(controls), "said_success": sum(s == "yes" for s, _ in cp),
                                  "said_grasp": sum(g == "grasp" for _, g in cp),
                                  "unparsed": sum(s == "unparsed" for s, _ in cp)}
    obs = [preds[i]["answer"]["observed"] for i in ids
           if preds[i].get("parsed") and preds[i]["answer"].get("observed")]
    if obs:
        res["observed_answers"] = {"cube_last_frame": dict(Counter(o["cube_last_frame"] for o in obs)),
                                   "cube_left_table": dict(Counter(o["cube_left_table"] for o in obs))}
    return res


def plot_confusion(res, path, model=DEFAULT_MODEL):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, key, title in ((axs[0], "success", "Success (yes/no)"), (axs[1], "stage", "Failing stage")):
        m = res[key]["confusion"]
        rows = [c for c in m if sum(m[c].values())]
        cols = [c for c in next(iter(m.values())) if c != "unparsed" or any(m[r]["unparsed"] for r in rows)]
        grid = [[m[r][c] for c in cols] for r in rows]
        ax.imshow(grid, cmap="Blues")
        top = max(max(r) for r in grid) or 1
        for i, r in enumerate(grid):
            for j, v in enumerate(r):
                ax.text(j, i, str(v), ha="center", va="center", color="white" if v > top / 2 else "black")
        ax.set_xticks(range(len(cols)), cols)
        ax.set_yticks(range(len(rows)), rows)
        ax.set_xlabel(f"{model.split('/')[-1]} prediction")
        ax.set_ylabel("simulator label")
        a = res[key]["accuracy"]
        b = res[key]["majority_baseline"]
        ax.set_title(f"{title}: acc {100*a['accuracy']:.0f}% [{100*a['wilson_95'][0]:.0f}, "
                     f"{100*a['wilson_95'][1]:.0f}]\nmajority baseline {100*b['accuracy']:.0f}% (n={a['n']})",
                     fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _pct(a):
    return f"{100*a['accuracy']:.1f}% ({a['correct']}/{a['n']}), Wilson 95% [{100*a['wilson_95'][0]:.1f}, {100*a['wilson_95'][1]:.1f}]"


def _f(x):
    return "-" if x is None else f"{100*x:.0f}%"


def _metric_lines(res):
    s, g = res["success"], res["stage"]
    lines = [f"Parsed answers: {res['parsed']}/{res['n']} (unparsed count as wrong); truncated: {res['truncated']}.",
             "", "| task | Cosmos accuracy | majority-class baseline | uniform chance |", "|---|---|---|---|",
             f"| success yes/no | {_pct(s['accuracy'])} | {_pct(s['majority_baseline'])} ('{s['majority_baseline']['class']}') | {100*s['uniform_chance']:.0f}% |",
             f"| failing stage (none/grasp/place) | {_pct(g['accuracy'])} | {_pct(g['majority_baseline'])} ('{g['majority_baseline']['class']}') | {100*g['uniform_chance']:.0f}% |",
             "", "## Per-class precision / recall", "", "| task | class | support | predicted | precision | recall |",
             "|---|---|---|---|---|---|"]
    for key in ("success", "stage"):
        for c, v in res[key]["per_class"].items():
            lines.append(f"| {key} | {c} | {v['support']} | {v['predicted']} | {_f(v['precision'])} | {_f(v['recall'])} |")
    lines += ["", "## Confusion (rows = simulator, columns = Cosmos)", ""]
    for key in ("success", "stage"):
        m = res[key]["confusion"]
        cols = list(next(iter(m.values())))
        lines += [f"**{key}**", "", "| sim \\ cosmos | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
        lines += [f"| {r} | " + " | ".join(str(m[r][c]) for c in cols) + " |" for r in m if sum(m[r].values())]
        lines.append("")
    pred_dist = {c: v["predicted"] for c, v in g["per_class"].items()}
    lines.append(f"Predicted stage distribution: {pred_dist}.")
    if sum(1 for v in pred_dist.values() if v) == 1:
        only = next(c for c, v in pred_dist.items() if v)
        lines.append(f"**The critic gave the same answer ('{only}') for every clip: it does not discriminate "
                     "outcomes on this set, and its accuracy equals that class's share.**")
    if res.get("observed_answers"):
        lines.append(f"Raw observational answers: {res['observed_answers']}.")
    if res.get("static_controls"):
        sc = res["static_controls"]
        lines.append(f"Static negative controls (arm never moves; excluded from the metrics above): "
                     f"{sc['said_success']}/{sc['n']} answered success.")
    lines.append("")
    return lines


def write_results(run_dir=None, results_dir=None, tag="scored", version="v1"):
    run_dir, results_dir = Path(run_dir or RUN_DIR), Path(results_dir or RESULTS_DIR)
    labels = read_jsonl(run_dir / "labels.jsonl")
    preds = read_jsonl(run_dir / f"predictions_{tag}.jsonl")
    manifest = json.loads((run_dir / f"manifest_{tag}.json").read_text())
    res = score(labels, preds)
    model = manifest["model"]
    prompt, camera = manifest.get("prompt", "v1"), manifest.get("camera", "v1")
    split = manifest.get("split", "dev")
    seeds = f"{SPLITS[split][0]}-{SPLITS[split][-1]}"
    results_dir.mkdir(parents=True, exist_ok=True)
    cam_note = ("one fixed third-person camera, 640x480" if camera == "v1" else
                f"camera config '{camera}': {CAMERAS[camera]}")
    summary = {"kind": "cosmos_critic", "version": version,
               "what": f"{model.split('/')[-1]} as a video critic of UR5e/UR10e block-to-tray rollouts, scored "
                       "against simulator labels", "run": manifest, "protocol": PROTOCOL, "robots": list(ROBOTS),
               "seeds": f"{split} split, seeds {seeds}", "prompt": prompt, "camera": camera,
               "camera_config": CAMERAS[camera],
               "stages": {"none": "success", "grasp": "no_lift",
                          "place": "lifted but not released and settled at goal"},
               "fps": FPS, "sampling": SAMPLING, "results": res,
               "caveats": [f"simulator renders, not real video; {cam_note}",
                           "classes balanced by construction (sampled per stage), so accuracy is not the "
                           "deployment-mix accuracy",
                           "one sample per clip at temperature 0.6 (model-card reasoning defaults), seed 1234",
                           "the failing-stage definitions are ours; the model was not fine-tuned on them"]}
    if prompt == "obs":
        summary["caveats"].append("success and stage are derived in code from the observational answers "
                                  "(cube in tray -> success; else lifted -> place, not lifted -> grasp)")
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    (results_dir / "labels.jsonl").write_text("".join(json.dumps(r) + "\n" for r in labels))
    (results_dir / "predictions.jsonl").write_text("".join(json.dumps(p) + "\n" for p in preds))
    plot_confusion(res, results_dir / "confusion_matrix.png", model)
    lines = [f"# Cosmos critic {version}: {model.split('/')[-1]} vs simulator labels", "",
             f"Model `{model}` (self-hosted vLLM), prompt `{prompt}`, camera `{camera}`, prompt sha256 "
             f"`{manifest['prompt_sha256'][:16]}`, code commit `{manifest['git_commit'][:12]}`. Clips: {res['n']} "
             f"UR5e/UR10e block-to-tray rollouts (gap_budget_v2 conditions, {split} seeds {seeds}, balanced per "
             f"stage: {res['truth_per_stage']}). fps={FPS}, max_tokens={SAMPLING['max_tokens']}, "
             f"temperature={SAMPLING['temperature']}.", ""] + _metric_lines(res)
    lines += [f"Internal consistency (success=yes iff stage=none): {res['internal_consistency']['success_yes_iff_stage_none']}"
              f"/{res['internal_consistency']['of_parsed']}.",
              f"Latency per request (with {manifest['workers']} concurrent requests): median "
              f"{res['latency_s']['median']:.1f} s, max {res['latency_s']['max']:.1f} s." if res["latency_s"] else "",
              "", "![confusion](confusion_matrix.png)", "",
              "Serving: vLLM on one L40S, command in `serve_vllm.sh`; per-request `media_io_kwargs` "
              "{video: {fps: 4}} (vLLM samples the frames) with `do_sample_frames: false`. Receipts (response id, "
              "tokens, latency, reasoning, answer) per clip in `receipts/`.", "", "## Caveats", ""]
    lines += [f"- {c}" for c in summary["caveats"]]
    (results_dir / "summary.md").write_text("\n".join(lines) + "\n")
    return summary


def tuning_report(run_dir, results_dir, tags):
    """EXPLORATORY: one row per (prompt, camera) configuration run on the tuning split."""
    run_dir, results_dir = Path(run_dir), Path(results_dir)
    labels = read_jsonl(run_dir / "labels.jsonl")
    rows, out = [], {}
    for tag in tags:
        man = json.loads((run_dir / f"manifest_{tag}.json").read_text())
        res = score(labels, read_jsonl(run_dir / f"predictions_{tag}.jsonl"))
        out[tag] = {"model": man["model"], "prompt": man.get("prompt", "v1"), "camera": man.get("camera", "v1"),
                    "prompt_sha256": man["prompt_sha256"], "git_commit": man["git_commit"], "results": res}
        sc = res.get("static_controls") or {}
        pd = {c: v["predicted"] for c, v in res["stage"]["per_class"].items()}
        rows.append(f"| {tag} | {man['model'].split('/')[-1]} | {out[tag]['prompt']} | {out[tag]['camera']} | "
                    f"{_pct(res['success']['accuracy'])} | {_pct(res['stage']['accuracy'])} | {pd} | "
                    f"{sc.get('said_success', '-')}/{sc.get('n', '-')} |")
    results_dir.mkdir(parents=True, exist_ok=True)
    summary = {"kind": "cosmos_critic_tuning", "exploratory": True, "split": "tuning",
               "seeds": [SPLITS["tuning"][0], SPLITS["tuning"][-1]], "configs": out,
               "note": "EXPLORATORY: small tuning set used to choose one configuration; not a confirmatory result."}
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    (results_dir / "labels.jsonl").write_text("".join(json.dumps(r) + "\n" for r in labels))
    n = out[tags[0]]["results"]["n"]
    md = ["# Cosmos critic v2 tuning (EXPLORATORY)", "",
          f"Tuning split, seeds {SPLITS['tuning'][0]}-{SPLITS['tuning'][-1]} (disjoint from v1 dev 0-59, the v2 "
          f"scored split 2020-2079 and held-out 1000-1059). {n} rollout clips, balanced per stage "
          f"{out[tags[0]]['results']['truth_per_stage']}, plus static negative controls (arm never moves). "
          "Used only to choose one configuration; numbers here are not confirmatory and have wide intervals.", "",
          "| config | model | prompt | camera | success acc | stage acc | predicted stages | static controls said success |",
          "|---|---|---|---|---|---|---|---|"] + rows
    (results_dir / "summary.md").write_text("\n".join(md) + "\n")
    return summary
