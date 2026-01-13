Review schema/data migrations for safety.

Inputs:
- $ARGUMENTS: optional focus area or file paths.

Context (run first):
! git status
! git diff --stat
! git diff

Steps:
1) Identify migration and schema changes.
2) Check backward compatibility, locking risks, defaults, indexes, and backfills.
3) Recommend a safe rollout and rollback plan.
