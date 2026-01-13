
# Secure development practices (SSDF-lite)

This is the small-team implementation of secure SDLC practices.

## Prepare
- Define security requirements (SECURITY_CHECKLIST.md)
- Threat model key flows (THREAT_MODEL.md)

## Protect
- Secrets management + scanning (Gitleaks)
- Dependency pinning + SBOM (Syft)

## Produce
- Code review + tests for every change
- SAST (Semgrep) for main branch
- Fix high-severity findings before release

## Respond
- Triage security issues within 24–72h based on severity
- Patch + release notes
- Post-incident review and regression tests
