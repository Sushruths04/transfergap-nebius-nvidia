import argparse
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

from .adapters import validate_plan
from .hosted import call_model, plan_messages, video_messages
from .metrics import paired_gap, summarize


def read_episodes(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def doctor():
    report = {"packages": {n: importlib.util.find_spec(n) is not None for n in ("torch", "mujoco", "cv2")},
              "configured": {n: bool(os.environ.get(n)) for n in (
                  "NEBIUS_API_KEY", "NEMOTRON_MODEL", "COSMOS_BASE_URL", "COSMOS_MODEL", "COSMOS_API_KEY")}}
    binary = shutil.which("nvidia-smi")
    if binary:
        try:
            result = subprocess.run([binary, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                                    capture_output=True, text=True, timeout=10)
            report["gpu"] = result.stdout.strip() if result.returncode == 0 else "NVIDIA driver unavailable"
        except subprocess.TimeoutExpired:
            report["gpu"] = "nvidia-smi timed out"
    else:
        report["gpu"] = "nvidia-smi not installed"
    return report


def main():
    parser = argparse.ArgumentParser(description="TransferGap evaluation and hosted-call tools")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("episodes")
    evaluate.add_argument("--allow-fixtures", action="store_true")
    compare = commands.add_parser("compare")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--allow-fixtures", action="store_true")
    for name in ("plan", "review-video"):
        child = commands.add_parser(name)
        child.add_argument("--goal", required=True)
        child.add_argument("--receipt", required=True)
        if name == "plan":
            child.add_argument("--robot", required=True)
            child.add_argument("--skills", nargs="+", default=["reach", "grasp", "lift", "place", "release"])
        else:
            child.add_argument("video")
    diag = commands.add_parser("diagnose", help="failure trace -> menu correction (rule baseline + Nemotron 3 "
                               "Super) -> paired evaluation on DEV seeds only")
    source = diag.add_mutually_exclusive_group()
    source.add_argument("--trace", help="prebuilt failure trace JSON (schema transfergap.failure_trace/v1)")
    source.add_argument("--dev-episodes", help="dev oracle-substitution JSONL (default runs/gap_budget/dev.jsonl "
                        "if present, else simulated)")
    diag.add_argument("--llm", choices=["auto", "off", "required"], default="auto",
                      help="auto: call Nemotron only if NEBIUS_API_KEY is set")
    diag.add_argument("--model", help="override model id (default nvidia/nemotron-3-super-120b-a12b)")
    diag.add_argument("--seeds-limit", type=int, help="use only the first N dev seeds")
    diag.add_argument("--no-apply", action="store_true", help="diagnose only; skip the dev evaluation")
    diag.add_argument("--out-dir", help="run directory (default runs/diagnose/<utc>-<pid>)")
    diag.add_argument("--procs", type=int)
    critic = commands.add_parser("critic", help="Cosmos-Reason2 as a measured critic of rollout clips "
                                 "(render dev clips -> query self-hosted vLLM -> score vs simulator labels)")
    critic.add_argument("action", choices=["render", "run", "score", "tuning"])
    critic.add_argument("--split", default="dev", choices=["dev", "tuning", "v2"],
                        help="seed split: dev 0-59 (v1), tuning 2000-2019, v2 2020-2079 (confirmatory)")
    critic.add_argument("--cameras", nargs="+", default=["v1"], help="camera configs to render (v1 close close_top)")
    critic.add_argument("--static-controls", type=int, default=0, help="add N static negative-control clips")
    critic.add_argument("--prompt", default="v1", choices=["v1", "obs"])
    critic.add_argument("--camera", default="v1", choices=["v1", "close", "close_top"])
    critic.add_argument("--frozen-v2", action="store_true", help="use the committed FROZEN_V2 prompt and camera")
    critic.add_argument("--tags", nargs="+", help="tuning: prediction sets to compare")
    critic.add_argument("--version", default="v1", help="score: title/version written to the summary")
    critic.add_argument("--run-dir", help="clips, labels, receipts (default runs/cosmos_critic_v1)")
    critic.add_argument("--results-dir", help="score output (default results/cosmos_critic_v1)")
    critic.add_argument("--n-per-class", type=int, default=40)
    critic.add_argument("--procs", type=int)
    critic.add_argument("--base-url", default=os.environ.get("COSMOS_BASE_URL", "http://127.0.0.1:8000/v1"))
    critic.add_argument("--model", default=os.environ.get("COSMOS_MODEL", "nvidia/Cosmos-Reason2-8B"))
    critic.add_argument("--workers", type=int, default=4)
    critic.add_argument("--limit", type=int, help="only the first N clips (smoke test)")
    critic.add_argument("--tag", default="scored", help="receipt/prediction set name")
    critic.add_argument("--smoke", action="store_true", help="allow an uncommitted prompt (never for scoring)")
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "evaluate":
            result = summarize(read_episodes(args.episodes), args.allow_fixtures)
        elif args.command == "compare":
            left, right = read_episodes(args.left), read_episodes(args.right)
            # Validate each side on its own; a legitimate self-comparison sanity check
            # (the same file on both sides) must not be rejected as duplicate data.
            summarize(left, args.allow_fixtures)
            summarize(right, args.allow_fixtures)
            result = paired_gap(left, right)
            result["contains_fixtures"] = any(ep["source"] == "fixture" for ep in left + right)
        elif args.command == "plan":
            result = call_model("nemotron", plan_messages(args.goal, args.robot, args.skills), args.receipt)
            # A successful inference call and an accepted plan are distinct auditable
            # outcomes. Record both in the same receipt rather than letting a validation
            # failure crash past an already-written "succeeded" receipt with no note that
            # the plan itself was rejected.
            try:
                result["validated_plan"] = validate_plan(json.loads(result["content"]), args.skills)
                result["validated"] = True
            except (json.JSONDecodeError, ValueError) as exc:
                result["validated"] = False
                result["validation_error"] = str(exc)
            finally:
                Path(args.receipt).write_text(
                    json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        elif args.command == "diagnose":
            from .diagnose import run_loop
            result = run_loop(trace_path=args.trace, dev_episodes=args.dev_episodes, llm=args.llm,
                              model=args.model, seeds_limit=args.seeds_limit, apply=not args.no_apply,
                              out_dir=args.out_dir, procs=args.procs)
        elif args.command == "critic":
            from . import critic as cr
            if args.action == "render":
                result = cr.render(args.n_per_class, args.run_dir, args.procs, split=args.split,
                                   cameras=args.cameras, static_controls=args.static_controls)
            elif args.action == "run":
                result = cr.run(args.base_url, model=args.model, out_dir=args.run_dir, workers=args.workers,
                                limit=args.limit, api_key=os.environ.get("COSMOS_API_KEY") or None, tag=args.tag,
                                require_frozen=not args.smoke, prompt=args.prompt, camera=args.camera,
                                frozen_v2=args.frozen_v2)
            elif args.action == "tuning":
                if not (args.run_dir and args.results_dir and args.tags):
                    raise ValueError("tuning needs --run-dir, --results-dir and --tags")
                result = {k: v["results"]["stage"]["accuracy"] for k, v in
                          cr.tuning_report(args.run_dir, args.results_dir, args.tags)["configs"].items()}
            else:
                result = cr.write_results(args.run_dir, args.results_dir, args.tag, args.version)["results"]
        else:
            result = call_model("cosmos", video_messages(args.video, args.goal), args.receipt)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
