Run the verification tasks.

Context (run first):
! git status
! rg --files -g "tasks.json" -g "CLAUDE.md"

Steps:
1) If `tasks.json` exists, run: test:unit, test:integration, lint, typecheck, e2e.
2) Otherwise, use commands from `CLAUDE.md` or ask for missing ones and update it.
3) Summarize results and failures, if any.
