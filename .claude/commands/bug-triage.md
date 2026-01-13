Triage a bug report into a repro and fix plan.

Inputs:
- $ARGUMENTS: bug report or issue description.

Context (run first):
! git status

Steps:
1) Turn the report into deterministic reproduction steps.
2) Find the smallest failing test or add a minimal repro.
3) Identify root cause and propose a minimal fix.
4) Provide verification steps.
