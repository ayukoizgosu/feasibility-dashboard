
# Auth Model

## AuthN (how identity is established)
- Method: <session cookie | JWT | OAuth | magic link>
- Token/session lifetime: <e.g., 15m access, 7d refresh>
- Revocation: <yes/no + how>
- MFA: <optional/required>

## AuthZ (who can do what)
### Tenancy
- Single-tenant / Multi-tenant (Org/Workspace)
- Tenant boundary key: <org_id | account_id>

### Roles
| Role | Description | Typical permissions |
|---|---|---|
| owner | | |
| admin | | |
| member | | |
| viewer | | |

### Permission matrix (actions x resources)
Define actions precisely and enforce server-side.

| Resource | Action | Allowed roles | Object-level rule |
|---|---|---|---|
| project | read | | must belong to org |
| project | write | | must belong to org and have role |
| user | read | | self or admin |
| user | write | | self or admin |

## Object-level authorization invariants (copy into tests)
- Any endpoint that takes an ID must verify **tenant + ownership/membership**.
- Never trust client-supplied `role`, `org_id`, `user_id` as authority.
- Default deny unless explicitly allowed.

## Implementation notes
- Centralize auth middleware.
- Prefer ABAC: `actor`, `resource`, `action`, `context` -> allow/deny.
