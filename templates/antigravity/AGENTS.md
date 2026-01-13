
# AGENTS.md (agent instructions)

This file is the **agent-facing** entrypoint. Keep it accurate.
(See also AI_PLAYBOOK.md for the full ruleset.)

## Setup commands
- Detect stack: `python scripts/stack_detect.py` (or `powershell -File scripts/stack_detect.ps1`)
- Install deps: `<fill based on detected stack>`
- Start dev server: `<fill>`
- Run tests: `<fill>`
- Lint/format: `<fill>`

## Operating rules
- Make small, reversible changes; include tests.
- Do **deny-by-default** authorization and object-level checks.
- Never commit secrets; never log secrets/tokens/PII.
- Prefer managed services and simple architectures unless scaling triggers demand more.

## Files to read first
- AI_PLAYBOOK.md
- README.md
- ARCHITECTURE.md
- AUTH_MODEL.md
- SECURITY_CHECKLIST.md
- THREAT_MODEL.md
- SLO.md
- OBSERVABILITY.md
- SUPERPOWERS.md (if using superpowers workflow)
- RESOURCES.md
- TEST_MATRIX.md
- SCRIPTS_GUIDE.md (if scripts/automation)
- docs/decisions/* (latest)

## Output format (always)
- Assumptions
- Patch plan
- Diffs
- Tests
- Commands
- Risks + rollback
