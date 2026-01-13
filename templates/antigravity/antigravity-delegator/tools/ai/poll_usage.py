#!/usr/bin/env python3
"""Best-effort local usage accounting for Codex CLI + Gemini CLI.

- Codex CLI: reads ~/.codex/log/ (or $CODEX_HOME/log/) and aggregates obvious usage fields if present.
- Gemini CLI: counts entries in tools/ai/call-log.ndjson if you append to it.

This is intentionally schema-tolerant: it won't break if the log format changes; it just reports what it can find.
"""
from __future__ import annotations
import os, json, time, sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
try:
    from tools.ai._shim_utils import repo_root
    ROOT = repo_root()
except Exception:
    ROOT = SCRIPT_ROOT
CALL_LOG = ROOT / "tools" / "ai" / "call-log.ndjson"
USAGE_JSON = ROOT / "usage.json"

def _read_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line: 
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue

def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))

def find_latest_session_logs(log_dir: Path):
    # Common patterns: session-*.jsonl (when session logging enabled)
    cand = sorted(log_dir.glob("session-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return cand[:10]

def summarize_codex():
    base = codex_home()
    log_dir = base / "log"
    if not log_dir.exists():
        return {"available": False, "reason": f"Missing {log_dir}"}

    sessions = find_latest_session_logs(log_dir)
    totals = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
    for s in sessions:
        for obj in _read_jsonl(s):
            totals["calls"] += 1
            # Be liberal about field names
            for k in ("input_tokens", "prompt_tokens", "in_tokens"):
                if isinstance(obj.get(k), int):
                    totals["input_tokens"] += obj[k]
                    break
            for k in ("output_tokens", "completion_tokens", "out_tokens"):
                if isinstance(obj.get(k), int):
                    totals["output_tokens"] += obj[k]
                    break
            # Some schemas may embed usage
            usage = obj.get("usage")
            if isinstance(usage, dict):
                for k, out_key in [("prompt_tokens","input_tokens"),("completion_tokens","output_tokens")]:
                    if isinstance(usage.get(k), int):
                        totals[out_key] += usage[k]
    return {"available": True, "log_dir": str(log_dir), "sessions_scanned": len(sessions), **totals}

def summarize_gemini():
    if not CALL_LOG.exists():
        return {"available": False, "reason": f"Missing {CALL_LOG}"}
    totals = {"calls": 0}
    for obj in _read_jsonl(CALL_LOG):
        if obj.get("tool") == "gemini":
            totals["calls"] += 1
    return {"available": True, **totals}

def main():
    out = {
        "ts": int(time.time()),
        "codex": summarize_codex(),
        "gemini": summarize_gemini(),
    }
    USAGE_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
