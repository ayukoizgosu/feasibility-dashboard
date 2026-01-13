
# Observability

## Signals
- Logs: structured JSON; include trace_id/span_id when available.
- Metrics: request count, latency histograms, error ratios, saturation.
- Traces: spans for inbound requests + DB + external calls.

## OpenTelemetry conventions
- Service name: <app-name>
- Resource attrs: deployment.environment, service.version, cloud.provider

## Golden signals (minimum dashboards)
- Latency (p50/p95/p99)
- Traffic (RPS)
- Errors (5xx rate, dependency errors)
- Saturation (CPU/memory/DB connections/queue depth)

## SLO-based alerting
- Use burn-rate alerting (fast window + slow window).
- Each alert must have a runbook in RUNBOOKS/.

## Runbooks
RUNBOOKS/
- api-high-error-rate.md
- api-high-latency.md
- db-connection-exhaustion.md
- queue-backlog.md
