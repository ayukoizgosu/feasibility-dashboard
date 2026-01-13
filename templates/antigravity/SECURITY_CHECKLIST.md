
# Security checklist (small-team)

This is the deploy gate. Keep it short and enforceable.

## A) Access control (highest risk)
- [ ] Server-side access control only; **deny-by-default**.
- [ ] Object-level authorization checks for every `/:id` or `?id=` parameter.
- [ ] Admin-only routes protected and audited.
- [ ] CORS is minimal; no wildcard origins unless truly public.

## B) Auth/session/token
- [ ] Short-lived access tokens or server sessions.
- [ ] Refresh + rotation strategy documented (AUTH_MODEL.md).
- [ ] Logout/revocation behavior defined.
- [ ] CSRF mitigations if cookie-based auth.

## C) Injection / SSRF / file safety
- [ ] Parameterized queries (no string-built SQL).
- [ ] Strict input schemas at boundaries.
- [ ] Safe file upload rules (size/type/path traversal).
- [ ] SSRF protections for any URL-fetch feature.

## D) Secrets & crypto
- [ ] No secrets in repo. Gitleaks clean.
- [ ] Secrets stored in secret manager; rotated.
- [ ] TLS everywhere; HSTS if web.

## E) Supply chain
- [ ] Dependencies pinned; lockfiles committed.
- [ ] SBOM generated in CI/release.
- [ ] Renovate/Dependabot (optional) configured.

## F) Observability & ops
- [ ] Traces/metrics/logs correlation working in prod.
- [ ] SLOs defined; burn-rate alerts exist.
- [ ] Runbooks for paging alerts.

## G) Release safety
- [ ] Feature flag/rollback for risky changes.
- [ ] Backups for data stores; restore tested.

## Reference mappings
- OWASP ASVS: Use as detailed verification reference.
- NIST SSDF: Use as lifecycle practice reference.
