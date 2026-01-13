# Antigravity Delegator

A hybrid agent workflow with two Builders: **Gemini CLI** and **Codex CLI**.

## Quick Start

1. Copy context files (`GEMINI.md`, `CODEX.md`) to your project root
2. Copy `quality_gate.py` to your project root  
3. Add `ARCHITECT_RULES.md` content to your Antigravity settings

## How It Works

```
User Request → Claude Plans → Gemini/Codex Writes → Quality Gate → Done
```

| Role | Tool | Purpose |
|------|------|---------|
| **Architect** | Claude Opus | Planning, reasoning, verification |
| **Builder 1** | Gemini CLI | General code generation |
| **Builder 2** | Codex CLI | Complex logic, backup |

## Local CLI configuration (optional)
- Codex CLI: set `CODEX_CLI_PATH` to the executable. If you use the VS Code extension, the binary is typically at `%USERPROFILE%\.antigravity\extensions\openai.chatgpt-<version>\bin\windows-x86_64\codex.exe`.
- Gemini CLI: set `GEMINI_CLI_PATH` (or `GEMINI_HOME`) if `gemini` is not on PATH.
- Gemini default model: set `GEMINI_DEFAULT_MODEL` (or `GEMINI_MODEL`) to override; default is `flash`. Use `none` to skip model injection.
- Gemini MCP allowlist: set `GEMINI_ALLOWED_MCP_SERVER_NAMES` (comma-separated) to limit MCP servers; use `none` to disable MCP if you hit `INVALID_ARGUMENT` errors.

## Files

| File | Description |
|------|-------------|
| `GEMINI.md` | Context file for Gemini CLI |
| `CODEX.md` | Context file for Codex CLI |
| `quality_gate.py` | Validates Builder output |
| `ARCHITECT_RULES.md` | Paste into Antigravity settings |
| `bin/` | Shim entrypoints (bat + sh) |
| `codex_cli.py` | Codex wrapper (passthrough + usage tracking) |
| `gemini_cli.py` | Gemini wrapper (passthrough + usage tracking) |
| `cli_impl/` | Compatibility shims that delegate to the wrappers |
