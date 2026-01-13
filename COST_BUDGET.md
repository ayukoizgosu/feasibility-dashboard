
# Cost budget

## Monthly ceiling
- Target: $<amount>/month
- Hard stop: $<amount>/month

## Primary cost drivers
- Compute: <service>
- Database: <service>
- Egress: <service>
- Observability: <vendor>

## Guardrails / kill switches
- Rate limits on expensive endpoints
- Background jobs concurrency caps
- Feature flags to disable cost-heavy features
- Budget alerts in cloud billing

## Review cadence
- Weekly: top 5 spenders
- Monthly: re-size resources, remove unused deps
