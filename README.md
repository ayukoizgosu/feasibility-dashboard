
# Project

## Quickstart
1) Copy `.env.example` -> `.env` and fill values.
2) Detect stack to fill commands:
   - `python scripts/stack_detect.py`
   - `powershell -File scripts/stack_detect.ps1`
3) Run the app:
   - TODO: add commands for your stack
4) Run tests:
   - TODO: add commands for your stack

## Template variants
### App or API
- Fill ARCHITECTURE.md, AUTH_MODEL.md, THREAT_MODEL.md, SECURITY_CHECKLIST.md.
- Define trust boundaries, data flows, and object-level authorization.
- Set SLO.md and OBSERVABILITY.md for user-facing services.

### Scripts or automation
- Fill SCRIPTS_GUIDE.md and RESOURCES.md before coding.
- Define dry-run, idempotency, scope limits, and rollback.
- Add the script-specific tests in TEST_MATRIX.md.

## AI-assisted development
See AI_PLAYBOOK.md. Agents must read repo docs before proposing changes.

## Superpowers workflow (optional)
Install Superpowers for your agent and use it to drive brainstorming, planning, and execution.
- Claude Code: /plugin marketplace add obra/superpowers-marketplace
  /plugin install superpowers@superpowers-marketplace
- Codex CLI: Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md
- OpenCode: Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md
See SUPERPOWERS.md for workflow mapping and repo guardrails.

## Security & reliability
- SECURITY_CHECKLIST.md
- THREAT_MODEL.md
- SLO.md
- OBSERVABILITY.md
- RESOURCES.md
- SCRIPTS_GUIDE.md
- TEST_MATRIX.md
