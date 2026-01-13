
# Heuristic stack detector (PowerShell)
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$hints = @()
if (Test-Path (Join-Path $root "package.json")) { $hints += "node" }
if (Get-ChildItem -Path $root -Recurse -Include *.ts,*.tsx -ErrorAction SilentlyContinue) { $hints += "typescript" }
if ((Test-Path (Join-Path $root "pyproject.toml")) -or (Test-Path (Join-Path $root "requirements.txt")) -or (Get-ChildItem -Path $root -Recurse -Include *.py -ErrorAction SilentlyContinue)) { $hints += "python" }
if ((Test-Path (Join-Path $root "go.mod")) -or (Get-ChildItem -Path $root -Recurse -Include *.go -ErrorAction SilentlyContinue)) { $hints += "go" }
if ((Test-Path (Join-Path $root "Cargo.toml")) -or (Get-ChildItem -Path $root -Recurse -Include *.rs -ErrorAction SilentlyContinue)) { $hints += "rust" }
if ((Test-Path (Join-Path $root "docker-compose.yml")) -or (Test-Path (Join-Path $root "Dockerfile"))) { $hints += "docker" }
if ((Test-Path (Join-Path $root "openapi.yaml")) -or (Test-Path (Join-Path $root "openapi.yml"))) { $hints += "openapi" }

$hints = $hints | Sort-Object -Unique
@{
  root = $root
  hints = $hints
} | ConvertTo-Json -Depth 4
