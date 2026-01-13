
# Architecture (1-page)

> Keep this file short. The point is to remove ambiguity for humans + AI.

## Overview
- Product: <what this app does>
- Primary users: <who>
- Data sensitivity: <low/med/high> (PII? payments? health?)

## Components
- Client: <web/mobile/cli> (where auth token lives?)
- API: <framework/runtime>
- Background jobs: <queues/cron>
- Data: <db>, <object storage>, <cache>
- 3rd-party: <payments/email/maps/etc>

## Automation (if this repo is a script or job)
- Trigger: <manual/cron/webhook/CI>
- Inputs: <files/args/db>
- Outputs: <files/db/notifications>
- Side effects: <writes/deletes>
- Rollback/compensation: <how to undo>

## Trust boundaries
- Internet → Edge (CDN/WAF) → App
- App → DB
- App → 3rd party
- Admin functions

## Data flows (high-level)
1) <flow>
2) <flow>

## Deployment
- Cloud: <AWS/GCP/Other>
- Runtime: <containers/serverless/vm>
- Environments: local / dev / stage / prod

## Scalability assumptions
- Typical RPS: <#>
- Peak RPS: <#>
- Largest tables/objects: <#>
- Latency target: <p95 ms>

## “Keep it simple” constraints
- Prefer a monolith until clear scaling triggers.
- Prefer managed services to reduce ops.
