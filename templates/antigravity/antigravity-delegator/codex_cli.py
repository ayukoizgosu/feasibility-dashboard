
#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys, os, time, json, glob
from pathlib import Path
from tools.ai._shim_utils import load_usage, save_usage, append_call_log, estimate_tokens_rough, find_executable, now_ts

def run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)

def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))

def iter_recent_session_logs(since_epoch: float) -> list[Path]:
    base = codex_home() / "sessions"
    if not base.exists():
        return []
    # Scan recent day folders only by mtime (cheap)
    # We'll just glob all rollout logs and filter by mtime >= since_epoch
    logs = []
    for p in base.rglob("rollout-*.jsonl"):
        try:
            if p.stat().st_mtime >= since_epoch:
                logs.append(p)
        except Exception:
            continue
    logs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[:20]

def parse_tokens_from_jsonl(path: Path) -> tuple[int,int,int]:
    # returns (calls, input_tokens, output_tokens) if fields exist, else zeros
    calls = in_tok = out_tok = 0
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            calls += 1
            usage = obj.get("usage")
            if isinstance(usage, dict):
                pt = usage.get("prompt_tokens")
                ct = usage.get("completion_tokens")
                if isinstance(pt, int): in_tok += pt
                if isinstance(ct, int): out_tok += ct
            # Some events might use alternative keys
            for k, acc in [("prompt_tokens","in"),("completion_tokens","out"),("input_tokens","in"),("output_tokens","out")]:
                v = obj.get(k)
                if isinstance(v, int):
                    if acc == "in": in_tok += v
                    else: out_tok += v
    except Exception:
        pass
    return calls, in_tok, out_tok

def extension_subdirs() -> list[str]:
    if sys.platform.startswith("win"):
        return ["windows-x86_64", "windows-aarch64"]
    if sys.platform == "darwin":
        return ["macos-aarch64", "macos-x86_64"]
    return ["linux-x86_64", "linux-aarch64"]

def find_codex_in_extension(ext_root: Path) -> str | None:
    exe_name = "codex.exe" if os.name == "nt" else "codex"
    for subdir in extension_subdirs():
        cand = ext_root / "bin" / subdir / exe_name
        if cand.exists():
            return str(cand)
    return None

def resolve_codex_path(bin_dir: Path) -> str | None:
    env_path = os.environ.get("CODEX_CLI_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return str(p)

    ext_root = os.environ.get("CODEX_EXTENSION_ROOT")
    if ext_root:
        found = find_codex_in_extension(Path(ext_root).expanduser())
        if found:
            return found

    if os.name == "nt":
        user_home = Path.home()
        patterns = [
            user_home / ".antigravity" / "extensions" / "openai.chatgpt-*-universal" / "bin" / "windows-x86_64" / "codex.exe",
            user_home / ".antigravity" / "extensions" / "openai.chatgpt-*-universal" / "bin" / "windows-aarch64" / "codex.exe",
        ]
        for pattern in patterns:
            matches = glob.glob(str(pattern))
            if matches:
                return matches[0]

    return find_executable("codex", exclude_dir=bin_dir)

def main():
    parser = argparse.ArgumentParser(description="Codex CLI wrapper (passthrough + usage tracking)")
    parser.add_argument("--timeout", type=int, default=0, help="Timeout seconds (0 = no timeout)")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Args to pass to codex CLI")
    ns, unknown = parser.parse_known_args()

    wrapper_root = Path(__file__).resolve().parent
    bin_dir = wrapper_root / "bin"
    codex_path = resolve_codex_path(bin_dir)

    if codex_path is None:
        print("Codex CLI not found. Install with: npm i -g @openai/codex", file=sys.stderr)
        sys.exit(127)

    passthrough = []
    passthrough.extend(unknown)
    passthrough.extend([a for a in ns.args if a != "--"])
    cmd = [codex_path] + passthrough

    print(f"DEBUG: Codex CMD: {cmd}", file=sys.stderr)

    usage = load_usage()
    usage.setdefault("codex", {}).setdefault("calls", 0)

    start_epoch = time.time()
    start = time.time()
    
    ok = False
    returncode = -1
    calls = 0
    in_tok = 0
    out_tok = 0
    dur_ms = 0

    try:
        try:
            # Bypass TTY check by providing explicit empty stdin if not interactive
            cp = subprocess.run(
                cmd, 
                text=True, 
                capture_output=True, 
                timeout=None if ns.timeout == 0 else ns.timeout,
                input=""
            )
            returncode = cp.returncode

            if cp.stdout:
                sys.stdout.write(cp.stdout)
            if cp.stderr:
                sys.stderr.write(cp.stderr)

            ok = (returncode == 0)

            # Try to extract actual tokens from session logs created during this run
            for log in iter_recent_session_logs(start_epoch - 1):
                c, i, o = parse_tokens_from_jsonl(log)
                # Heuristic: pick the first log that has any tokens
                if (i + o) > 0:
                    calls, in_tok, out_tok = c, i, o
                    break

            # Fallback rough estimate from output if we couldn't parse any usage
            if (in_tok + out_tok) == 0:
                out_tok = estimate_tokens_rough(cp.stdout or "")

            usage["codex"]["calls"] = int(usage["codex"].get("calls", 0)) + 1
            usage["codex"]["used"] = int(usage["codex"].get("used", 0)) + int(in_tok + out_tok)
            save_usage(usage)

        except subprocess.TimeoutExpired:
            print("Codex CLI timed out", file=sys.stderr)
            returncode = 124

    finally:
        dur_ms = int((time.time() - start) * 1000)
        append_call_log({
            "ts": now_ts(),
            "tool": "codex",
            "cmd": cmd,
            "ok": ok,
            "returncode": returncode,
            "duration_ms": dur_ms,
            "calls_scanned": calls,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "codex_home": str(codex_home()),
        })

    sys.exit(returncode)

if __name__ == "__main__":
    main()
