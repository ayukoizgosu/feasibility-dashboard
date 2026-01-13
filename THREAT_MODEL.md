
# Threat model (lightweight)

## Scope
- In-scope assets: <data, money, reputation, availability>
- Out of scope: <explicit>

## Attack surface
- Public endpoints:
  - <GET /...>
- Auth flows:
  - <login, callback, refresh>
- Webhooks:
  - <provider>
- Background jobs:
  - <cron/queue>
- Admin features:
  - <routes>

## Top abuse cases (prioritized)
1) **IDOR / broken access control**
   - Scenario: attacker guesses IDs and reads/updates other users' records
   - Mitigation: tenant-scoped queries + centralized authZ
   - Verification: negative tests for cross-tenant access

2) **Privilege escalation**
   - Scenario: client sets role/org_id and backend trusts it
   - Mitigation: derive authority from server-side identity + membership

3) **Token theft/replay**
   - Scenario: token stored insecurely or logged
   - Mitigation: httpOnly cookies or secure storage; redaction; short TTL

4) **Injection / SSRF**
   - Scenario: untrusted strings reach query/command/URL fetch
   - Mitigation: parameterized queries; allowlists; egress controls

5) **Data exfil via exports/backups**
   - Scenario: export endpoints unprotected or overly broad
   - Mitigation: least privilege; audit logs; rate limit; watermarks

## Security test plan
- 401/403 for unauthenticated/unauthorized
- Cross-tenant ID tests for every resource
- Injection probes where query-like endpoints exist

## Residual risk
- <fill>
