# Test matrix

Keep this minimal and enforceable.

## App/API
| Test type | Purpose | Minimum |
|---|---|---|
| Unit | Business logic | Critical paths |
| Integration | DB/external calls | Key workflows |
| Security (negative) | AuthZ, IDOR, input validation | Each resource/endpoint |
| Smoke | Deploy verification | Health + 1 core flow |

## Scripts/automation
| Test type | Purpose | Minimum |
|---|---|---|
| Dry-run | No side effects | One representative run |
| Idempotency | Safe re-runs | Repeat same inputs |
| Failure/retry | Transient error handling | 1 simulated failure |
| Rollback | Recovery path | Documented + exercised |
