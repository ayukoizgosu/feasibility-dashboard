
# SLOs (Small app)

## Why
SLOs are the contract for reliability and the basis for alerting (burn-rate).

## Core user journeys
1) <journey> (e.g., "login")
2) <journey> (e.g., "create booking")
3) <journey> (e.g., "checkout")

## SLIs
- Availability: successful requests / total requests (exclude 4xx unless auth service itself)
- Latency: p95 / p99 for key endpoints
- Freshness (if applicable): lag for async pipelines

## SLO targets (example)
- Availability: 99.9% / 30 days
- Latency: p95 < 500ms for <critical endpoints>
- Error rate: < 0.1% 5xx over 30d

## Error budget policy
- If burn rate > threshold: freeze risky deploys, focus on reliability.
- If budget healthy: ship features.

## Alerting (burn-rate)
Define burn-rate windows (fast + slow) and page only when both violate.
See OBSERVABILITY.md for implementation.
