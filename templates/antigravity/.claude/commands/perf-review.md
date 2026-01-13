Performance review of recent changes.

Inputs:
- $ARGUMENTS: optional focus area or file paths.

Context (run first):
! git status
! git diff --stat
! git diff

Steps:
1) Identify potential hot paths, expensive loops, or blocking I/O.
2) Flag N+1 queries, redundant work, or excessive allocations.
3) Recommend minimal fixes or targeted tests/benchmarks.
