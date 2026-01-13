# Scripts and Automation Guide

Use this file when the repo is a script, CLI tool, or scheduled job.

## Defaults (required)
- Dry-run for any write/delete/side effect.
- Idempotent behavior on retries and re-runs.
- Config precedence: CLI args > env vars > config file > defaults.
- Validate inputs at boundaries; fail fast with clear errors.
- Structured logs; never log secrets or PII.
- Exit codes: 0 success, 1 failure, 2 validation, 3 transient.
- Timeouts and cancellation for long-running operations.
- Retry/backoff with jitter for transient failures; cap attempts.
- Rate limit external APIs.
- Concurrency control (lock file or job runner).
- Checkpoint/resume for large batch jobs.

## Safety rails
- Add a max-scope guard (date range, item limit, allowlist).
- Record a run_id and write an audit log of side effects.
- Document rollback or compensating actions.

## Testing (minimum)
- Dry-run asserts no writes.
- Idempotency on repeated run.
- Failure/retry path for a transient error.
- Rollback or restore path for data changes.
