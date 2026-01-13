Security review of recent changes.

Inputs:
- $ARGUMENTS: optional focus area or file paths.

Context (run first):
! git status
! git diff --stat
! git diff

Steps:
1) Review changes for auth/authz gaps, injection risks, secrets, unsafe deserialization, SSRF, etc.
2) Report issues with severity and file references.
3) Recommend minimal fixes or tests.
