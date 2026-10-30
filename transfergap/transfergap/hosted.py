"""Explicit hosted calls with response receipts. No silent mock fallback."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def call_model(role, messages, output_path, model=None, max_tokens=1024, timeout=120):
    if role not in {"nemotron", "cosmos"}:
        raise ValueError("Unknown model role")
    prefix = role.upper()
    base = os.environ.get(f"{prefix}_BASE_URL", "https://api.tokenfactory.nebius.com/v1" if role == "nemotron" else "")
    model = model or os.environ.get(f"{prefix}_MODEL", "")
    key = os.environ.get("NEBIUS_API_KEY" if role == "nemotron" else "COSMOS_API_KEY", "")
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"Set {prefix}_BASE_URL to an HTTPS API base URL without embedded credentials")
    if not key or not model:
        raise ValueError(f"Set {prefix}_MODEL and its API key; no model or credentials are assumed")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the receipt before spending tokens. Never overwrite previous evidence.
    with path.open("x", encoding="utf-8") as receipt_file:
        body = json.dumps({"model": model, "messages": messages, "max_tokens": int(max_tokens)}, allow_nan=False).encode()
        receipt = {"schema_version": 1, "kind": "hosted_inference", "role": role,
                   "requested_model": model, "endpoint_host": parsed.hostname,
                   "created_at": datetime.now(timezone.utc).isoformat(),
                   "request_sha256": hashlib.sha256(body).hexdigest(), "status": "started"}
        start = time.monotonic()
        request = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
                result = json.load(response)
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Endpoint returned no text content")
            receipt.update(status="succeeded", response_id=result.get("id"),
                           returned_model=result.get("model"), usage=result.get("usage"),
                           finish_reason=result["choices"][0].get("finish_reason"),
                           content=content)
        except Exception as exc:
            receipt.update(status="failed", error_type=type(exc).__name__)
            # Do not persist raw error bodies or headers; they may contain credentials.
            raise RuntimeError(f"{role} request failed ({type(exc).__name__}); see receipt") from None
        finally:
            receipt["latency_s"] = time.monotonic() - start
            json.dump(receipt, receipt_file, indent=2, allow_nan=False)
            receipt_file.write("\n")
    return receipt


def plan_messages(goal, robot, skills):
    return [{"role": "system", "content": "Produce JSON with a steps array. Each step has skill and target strings. "
             "Use only the supplied robot skills. Propose task steps; do not invent coordinates or report execution success."},
            {"role": "user", "content": json.dumps({"goal": goal, "robot": robot, "allowed_skills": skills})}]


def video_messages(video_path, goal):
    path = Path(video_path)
    if path.suffix.lower() != ".mp4" or not path.is_file():
        raise ValueError("Provide a local MP4 clip")
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Use a short MP4 clip smaller than 20 MiB for this initial adapter")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return [{"role": "user", "content": [
        {"type": "video_url", "video_url": {"url": "data:video/mp4;base64," + data}},
        {"type": "text", "text": f"Task: {goal}. Describe visible action events with timestamps, "
         "object interactions, and any mismatch with the task. Mark uncertain observations. "
         "Return a concise JSON assessment. Do not assume occluded contacts or metric depth."}]}]
