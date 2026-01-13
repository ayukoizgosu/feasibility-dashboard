# Superpowers integration

Use this file when you want the Superpowers workflow and skills in this repo.

## Install

### Claude Code
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
/help

### Codex CLI
Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md

### OpenCode
Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.opencode/INSTALL.md

## Workflow mapping (this repo)
1) Brainstorm: /superpowers:brainstorm -> design doc in docs/decisions/NNNN-*.md or ARCHITECTURE.md.
2) Plan: /superpowers:write-plan -> include file list, tests, rollback; save as TODO.md.
3) Execute: /superpowers:execute-plan -> small batches; run tests or tasks after each batch.
4) Review: use .claude/commands/security-review.md and perf-review.md as needed.
5) Finish: run full verification and update docs.

## Guardrails
- Output format from AGENTS.md and AI_PLAYBOOK.md still applies.
- Keep diffs small and reversible.
- Deny-by-default auth and object-level checks.
- Never log secrets or PII.
