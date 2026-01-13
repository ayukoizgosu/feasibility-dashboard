Log token usage and estimated cost.

Inputs:
- $ARGUMENTS: -Model, -InputTokens, -OutputTokens, optional -Source/-Note or rate overrides.

Context (run first):
! powershell -NoProfile -ExecutionPolicy Bypass -File scripts\log-usage.ps1 -Model "MODEL" -InputTokens 0 -OutputTokens 0 -Source "task"

Steps:
1) Confirm model and token counts from the tool output.
2) If rates are missing, update .claude\usage-rates.json or pass -InputCostPer1k/-OutputCostPer1k.
3) Run the script and report the appended log line.
