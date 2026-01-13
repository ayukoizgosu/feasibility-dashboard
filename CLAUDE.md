# Claude Operating Notes

## Repo overview
- Purpose: TODO
- Key directories: TODO

## Workflow
- Plan -> approve -> execute. Keep diffs small and scoped.
- Verification is mandatory. Use the tasks below or update them.

## Superpowers (optional)
If Superpowers is installed, use:
- /superpowers:brainstorm -> capture design in docs/decisions/NNNN-*.md or ARCHITECTURE.md.
- /superpowers:write-plan -> include files, tests, and rollback.
- /superpowers:execute-plan -> execute in small batches and verify.
See SUPERPOWERS.md for install and workflow mapping.

## Commands (update as you wire the repo)
- Unit tests: TODO
- Integration tests: TODO
- Lint: TODO
- Typecheck: TODO
- E2E: TODO

## Usage logging
- Log model, input tokens, output tokens, and estimated cost to `.claude\logs\usage.jsonl`.
- Use `scripts\log-usage.ps1` or `/log-usage`.
- Update `.claude\usage-rates.json` with per-1k prices for your models.

## Specialist agents
- security-reviewer, perf-reviewer, db-migration-reviewer, bug-triage, docs-updater, release-checker.
- Use them for focused review passes and checklists.

## Conventions
- Naming: TODO
- Error handling: TODO
- Logging: TODO

## Footguns
- TODO: Add "do not" rules when mistakes repeat.
