
# Budgets & Limits (edit these)

Set these to match your actual provider quotas.

## Providers
- Codex CLI (ChatGPT plan): enforce a session cap (tokens or tasks) and check `/status` periodically.
- Gemini CLI: enforce requests/min + requests/day based on your entitlement.
- OpenRouter :free: enforce RPM + daily caps.

## Suggested default caps (starter)
- Strong model: max 20 calls/day
- Cheap model: max 200 calls/day
- Research: max 50 web-backed queries/day

## Logging
- Append-only NDJSON at tools/ai/call-log.ndjson with fields:
  ts, tool, model, task_class, input_tokens_est, output_tokens_est, cost_est, status
