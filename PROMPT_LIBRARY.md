
# Prompt Library (copy/paste into Antigravity agent tasks)

## 1) Small-App Blueprint (architecture)
**Goal:** fastest secure path for a small business app.
Output:
- components + data flows + trust boundaries
- assumptions (RPS, data sensitivity, budget ceiling)
- decisions: security/reliability/cost/ops/perf
- threat list + mitigations
- rollout + rollback
- cost drivers + kill switches

Prompt:
"""
Design a Small-App Blueprint for this repo. Prefer a monolith + managed services. 
Include trust boundaries, auth model implications, SLO targets, and an incremental rollout plan.
"""

## 2) “Ship-ready” DevOps (minimal ops)
Prompt:
"""
Propose minimal CI/CD for this repo:
- lint/test/build
- secret scan + SAST
- SBOM generation
- deploy + rollback
Provide exact files/commands to add.
"""

## 3) Scaling triggers (no premature microservices)
Prompt:
"""
Define scaling triggers (metrics thresholds) and the next step at each trigger.
Start with cheap wins: caching, pagination, indexes, async jobs, rate limits.
"""

## 4) Observability baseline (vendor-neutral)
Prompt:
"""
Add an observability baseline:
- structured logs
- trace propagation
- key metrics
- SLO + burn-rate alerts
Provide implementation steps for the detected stack.
"""

## 5) Security regression suite
Prompt:
"""
Create security regression tests for:
- unauthenticated access (401)
- unauthorized access (403)
- cross-tenant IDOR attempts
- injection probes where applicable
Include a test runner command and CI hook.
"""
