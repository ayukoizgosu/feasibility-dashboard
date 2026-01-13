# Usage accounting (best-effort)

## Update usage.json
```bash
python tools/ai/poll_usage.py
```

## Notes
- Codex CLI: this script only finds token counts if Codex session logging is enabled and the log schema includes token fields.
- Gemini CLI: append entries to `tools/ai/call-log.ndjson` from your delegator wrapper (recommended).
