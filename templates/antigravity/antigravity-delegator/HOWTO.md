
# Drop-in real wrappers for your delegator

## What this pack does
- Adds `bin/gemini` and `bin/codex` shims (so your existing PATH-prepend logic picks them up).
- Shims call `gemini_cli.py` / `codex_cli.py`, which:
  - run the real CLIs (or `npx @google/gemini-cli` as fallback for Gemini)
  - append per-call telemetry to `tools/ai/call-log.ndjson`
  - update `usage.json` (keeps your current `{used,limit}` schema; adds optional `calls`)

## Setup
1) Copy the contents of this zip into your delegator repo root.
2) Ensure Python 3 is available.
3) Install CLIs:
   - Codex: `npm i -g @openai/codex`
   - Gemini: `npm i -g @google/gemini-cli`
4) Run your existing `test_delegator.py`.

## Notes
- Codex usage: wrapper best-effort parses `$CODEX_HOME/sessions/.../rollout-*.jsonl` if present; otherwise estimates from output.
- Gemini usage: counts calls + rough output token estimate (Gemini CLI doesn't consistently expose token usage).
