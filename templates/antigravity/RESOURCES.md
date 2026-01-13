# Resource inventory

Use this to drive object-level authorization and safe automation.

## Resource table
| Resource | Primary key | Tenant key | Owner key | PII? | Notes |
|---|---|---|---|---|---|
| <resource> | <id> | <org_id> | <user_id> | <yes/no> | <notes> |

## Authorization invariants
- Every read/write must filter by tenant + ownership.
- Scripts must not cross tenants without an explicit allowlist.
- Do not trust client-supplied role, user_id, or org_id.
