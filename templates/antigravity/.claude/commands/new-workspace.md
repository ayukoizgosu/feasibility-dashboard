Bootstrap a new workspace from this template.

Inputs:
- $ARGUMENTS: target path, optional flags (-WorkspaceName, -SkipFrameworkDoc, -Force)

Context (run first):
! powershell -NoProfile -ExecutionPolicy Bypass -File scripts\new-workspace.ps1 -TargetPath "C:\path\MyProject"

Steps:
1) Confirm target path and workspace name.
2) Run the script with any needed flags.
3) Report created files and next steps.
4) If using Superpowers, open SUPERPOWERS.md and install the plugin.
