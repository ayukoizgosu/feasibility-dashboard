Release readiness check.

Inputs:
- $ARGUMENTS: optional focus area or file paths.

Context (run first):
! git status
! git diff --stat

Steps:
1) Verify version bump, changelog, and release notes if applicable.
2) Ensure verification commands are defined and run.
3) Call out missing steps or release risks.
