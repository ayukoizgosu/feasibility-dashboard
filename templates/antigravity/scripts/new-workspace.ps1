[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$TargetPath,

  [string]$WorkspaceName,

  [switch]$SkipFrameworkDoc,

  [switch]$Force
)

$ErrorActionPreference = "Stop"

function Resolve-TargetPath {
  param([string]$Path)

  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }

  $combined = Join-Path -Path (Get-Location) -ChildPath $Path
  return [System.IO.Path]::GetFullPath($combined)
}

$TemplateRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$TargetPath = Resolve-TargetPath -Path $TargetPath

if (Test-Path -LiteralPath $TargetPath) {
  $items = @(Get-ChildItem -LiteralPath $TargetPath -Force)
  if ($items.Count -gt 0 -and -not $Force) {
    throw "Target path exists and is not empty. Use -Force to overwrite."
  }
} else {
  New-Item -ItemType Directory -Force -Path $TargetPath | Out-Null
}

if (-not $WorkspaceName -or $WorkspaceName.Trim().Length -eq 0) {
  $WorkspaceName = Split-Path -Leaf $TargetPath
}

$copyPaths = @(
  "CLAUDE.md",
  "SUPERPOWERS.md",
  ".claude\settings.json",
  ".claude\usage-rates.json",
  ".claude\commands\commit-push-pr.md",
  ".claude\commands\test.md",
  ".claude\commands\lint-fix.md",
  ".claude\commands\repro.md",
  ".claude\commands\new-workspace.md",
  ".claude\commands\log-usage.md",
  ".claude\commands\security-review.md",
  ".claude\commands\perf-review.md",
  ".claude\commands\db-migration-review.md",
  ".claude\commands\bug-triage.md",
  ".claude\commands\docs-update.md",
  ".claude\commands\release-check.md",
  ".claude\agents\code-simplifier.md",
  ".claude\agents\verify-app.md",
  ".claude\agents\security-reviewer.md",
  ".claude\agents\perf-reviewer.md",
  ".claude\agents\db-migration-reviewer.md",
  ".claude\agents\bug-triage.md",
  ".claude\agents\docs-updater.md",
  ".claude\agents\release-checker.md",
  ".vscode\tasks.json",
  ".vscode\launch.json",
  "scripts\new-workspace.ps1",
  "scripts\log-usage.ps1"
)

if (-not $SkipFrameworkDoc) {
  $copyPaths += "boris-claude-code-vscode-framework.md"
}

foreach ($rel in $copyPaths) {
  $src = Join-Path -Path $TemplateRoot -ChildPath $rel
  $dst = Join-Path -Path $TargetPath -ChildPath $rel

  if (-not (Test-Path -LiteralPath $src)) {
    throw "Template file not found: $rel"
  }

  $dstDir = Split-Path -Parent $dst
  if (-not (Test-Path -LiteralPath $dstDir)) {
    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
  }

  Copy-Item -LiteralPath $src -Destination $dst -Force
}

$workspaceFile = Join-Path -Path $TargetPath -ChildPath ($WorkspaceName + ".code-workspace")
if ((Test-Path -LiteralPath $workspaceFile) -and -not $Force) {
  throw "Workspace file already exists. Use -Force to overwrite."
}

$workspaceJson = @"
{
  "folders": [
    {
      "path": "."
    }
  ],
  "settings": {}
}
"@

$workspaceJson | Set-Content -LiteralPath $workspaceFile -Encoding ASCII

Write-Host "Workspace created at: $TargetPath"
Write-Host "Workspace file: $workspaceFile"
Write-Host "Next: open with VS Code and fill in TODOs in CLAUDE.md, .vscode\tasks.json, and .claude\usage-rates.json."
