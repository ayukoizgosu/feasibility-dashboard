
from __future__ import annotations
import os, json, time, shutil
from pathlib import Path
from typing import Optional, Dict, Any

def repo_root() -> Path:
    # Prefer the workspace root when this delegator is vendored into a larger repo.
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "AI_PLAYBOOK.md").exists() or (parent / "AGENTS.md").exists():
            return parent
        if (parent / "tools" / "ai" / "BUDGETS.md").exists():
            return parent
    # Fallback: delegator root (tools/ai/_shim_utils.py -> tools -> antigravity-delegator)
    return here.parents[2]

def usage_file() -> Path:
    return repo_root() / "usage.json"

def call_log_file() -> Path:
    return repo_root() / "tools" / "ai" / "call-log.ndjson"

def load_usage() -> Dict[str, Any]:
    p = usage_file()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "gemini": {"used": 0, "limit": 100000, "calls": 0},
        "codex": {"used": 0, "limit": 100000, "calls": 0},
    }

def save_usage(d: Dict[str, Any]) -> None:
    p = usage_file()
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")

def append_call_log(obj: Dict[str, Any]) -> None:
    p = call_log_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def estimate_tokens_rough(text: str) -> int:
    # fallback only
    return max(1, len(text) // 4)

def find_executable(exe: str, exclude_dir: Optional[Path] = None) -> Optional[str]:
    # Search PATH, optionally skipping a directory (e.g., repo/bin to avoid recursion)
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep)
    cand = []
    for d in parts:
        if not d:
            continue
        dp = Path(d)
        if exclude_dir is not None and dp.resolve() == exclude_dir.resolve():
            continue
        cand.append(d)
    tmp_path = os.pathsep.join(cand)
    return shutil.which(exe, path=tmp_path)

def now_ts() -> int:
    return int(time.time())
