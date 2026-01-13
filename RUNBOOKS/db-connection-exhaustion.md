## Symptoms
- DB connection pool exhausted

## Immediate actions
- Restart app workers (if safe)
- Reduce concurrency temporarily

## Diagnosis
- Long-running queries
- Leaked connections

## Remediation
- Fix pool usage
- Add timeouts
