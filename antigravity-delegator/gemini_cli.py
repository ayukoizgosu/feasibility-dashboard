
#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys, os, time
from pathlib import Path
from tools.ai._shim_utils import load_usage, save_usage, append_call_log, estimate_tokens_rough, find_executable, now_ts

def run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)

def resolve_gemini_path(bin_dir: Path) -> str | None:
    env_path = os.environ.get("GEMINI_CLI_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            return str(p)

    home = os.environ.get("GEMINI_HOME")
    if home:
        base = Path(home).expanduser()
        for name in ("gemini.cmd", "gemini.exe", "gemini"):
            cand = base / "bin" / name
            if cand.exists():
                return str(cand)
            cand = base / name
            if cand.exists():
                return str(cand)

    if os.name == "nt":
        for env in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            for name in ("gemini.cmd", "gemini.exe", "gemini"):
                cand = Path(base) / "npm" / name
                if cand.exists():
                    return str(cand)

    return find_executable("gemini", exclude_dir=bin_dir)

def env_allowed_mcp_server_names() -> list[str]:
    raw = os.environ.get("GEMINI_ALLOWED_MCP_SERVER_NAMES")
    if not raw:
        return []
    return [name.strip() for name in raw.split(",") if name.strip()]

def default_model() -> str | None:
    raw = os.environ.get("GEMINI_DEFAULT_MODEL")
    if raw is None:
        raw = os.environ.get("GEMINI_MODEL")
    if raw is None:
        return "flash"
    raw = raw.strip()
    if not raw or raw.lower() in ("none", "null", "off"):
        return None
    return raw

def main():
    parser = argparse.ArgumentParser(description="Gemini CLI wrapper (passthrough + usage tracking)")
    parser.add_argument("--force-npx", action="store_true", help="Use npx @google/gemini-cli even if gemini is installed")
    parser.add_argument("--timeout", type=int, default=0, help="Timeout seconds (0 = no timeout)")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Args to pass to gemini CLI")
    ns, unknown = parser.parse_known_args()

    # Avoid recursion if repo/bin is in PATH
    wrapper_root = Path(__file__).resolve().parent
    bin_dir = wrapper_root / "bin"
    gemini_path = None if ns.force_npx else resolve_gemini_path(bin_dir)

    if gemini_path is None:
        # Fallback: npx (requires node + network)
        cmd = ["npx", "@google/gemini-cli"]
    else:
        cmd = [gemini_path]

    passthrough = []
    passthrough.extend(unknown)
    passthrough.extend([a for a in ns.args if a != "--"])  # tolerate " -- " separator

    if not any(arg.startswith("--allowed-mcp-server-names") for arg in passthrough):
        allowed_mcp = env_allowed_mcp_server_names()
        if allowed_mcp:
            passthrough.extend(["--allowed-mcp-server-names", *allowed_mcp])

    cmd += passthrough

    # Inject default model if not specified
    if not any(arg.startswith(("-m", "--model")) for arg in cmd):
        model = default_model()
        if model:
            cmd.extend(["--model", model])

    usage = load_usage()
    usage.setdefault("gemini", {}).setdefault("calls", 0)

    print(f"DEBUG: Gemini CMD: {cmd}", file=sys.stderr)
    
    ok = False
    returncode = -1
    out_tok = 0
    dur_ms = 0
    
    start = time.time()
    try:
        try:
            cp = run(cmd, timeout=None if ns.timeout == 0 else ns.timeout)
            returncode = cp.returncode
            if cp.stdout:
                sys.stdout.write(cp.stdout)
            if cp.stderr:
                sys.stderr.write(cp.stderr)
            ok = (returncode == 0)
            out_tok = estimate_tokens_rough(cp.stdout or "")
            
            # Update usage only on success or partial success
            usage["gemini"]["calls"] = int(usage["gemini"].get("calls", 0)) + 1
            usage["gemini"]["used"] = int(usage["gemini"].get("used", 0)) + out_tok
            save_usage(usage)

        except FileNotFoundError:
            print("Gemini CLI not found. Install with: npm install -g @google/gemini-cli", file=sys.stderr)
            returncode = 127
        except subprocess.TimeoutExpired:
            print("Gemini CLI timed out", file=sys.stderr)
            returncode = 124
    finally:
        dur_ms = int((time.time() - start) * 1000)
        append_call_log({
            "ts": now_ts(),
            "tool": "gemini",
            "cmd": cmd,
            "ok": ok,
            "returncode": returncode,
            "duration_ms": dur_ms,
            "output_tokens_est": out_tok,
        })

    sys.exit(returncode)

if __name__ == "__main__":
    main()
