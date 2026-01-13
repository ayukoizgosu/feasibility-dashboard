[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$Model,

  [Parameter(Mandatory = $true)]
  [long]$InputTokens,

  [Parameter(Mandatory = $true)]
  [long]$OutputTokens,

  [string]$RatesPath,

  [string]$LogPath,

  [double]$InputCostPer1k,

  [double]$OutputCostPer1k,

  [double]$EstimatedCostUsd,

  [string]$Source,

  [string]$Note
)

$ErrorActionPreference = "Stop"

function Resolve-PathSafe {
  param([string]$PathValue)

  if (-not $PathValue) {
    return $null
  }

  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }

  $combined = Join-Path -Path (Get-Location) -ChildPath $PathValue
  return [System.IO.Path]::GetFullPath($combined)
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$defaultRatesPath = Join-Path -Path $scriptRoot -ChildPath "..\\.claude\\usage-rates.json"
$defaultLogPath = Join-Path -Path $scriptRoot -ChildPath "..\\.claude\\logs\\usage.jsonl"

if (-not $RatesPath) {
  $RatesPath = $defaultRatesPath
}
if (-not $LogPath) {
  $LogPath = $defaultLogPath
}

$RatesPath = Resolve-PathSafe -PathValue $RatesPath
$LogPath = Resolve-PathSafe -PathValue $LogPath

$ratesSource = "none"
$inputRate = $null
$outputRate = $null
$estimatedCost = $null

if ($PSBoundParameters.ContainsKey("EstimatedCostUsd")) {
  $estimatedCost = [double]$EstimatedCostUsd
  $ratesSource = "manual"
} else {
  if ($PSBoundParameters.ContainsKey("InputCostPer1k") -or $PSBoundParameters.ContainsKey("OutputCostPer1k")) {
    if (-not $PSBoundParameters.ContainsKey("InputCostPer1k")) {
      $InputCostPer1k = 0.0
    }
    if (-not $PSBoundParameters.ContainsKey("OutputCostPer1k")) {
      $OutputCostPer1k = 0.0
    }
    $inputRate = [double]$InputCostPer1k
    $outputRate = [double]$OutputCostPer1k
    $ratesSource = "override"
  } elseif ($RatesPath -and (Test-Path -LiteralPath $RatesPath)) {
    $ratesJson = Get-Content -LiteralPath $RatesPath -Raw | ConvertFrom-Json
    $modelRate = $ratesJson.models.PSObject.Properties |
      Where-Object { $_.Name -eq $Model } |
      Select-Object -First 1 -ExpandProperty Value

    if ($null -ne $modelRate) {
      $inputRate = [double]$modelRate.input
      $outputRate = [double]$modelRate.output
      $ratesSource = "rates_file"
    } else {
      $inputRate = 0.0
      $outputRate = 0.0
      $ratesSource = "missing_model"
    }
  } else {
    $inputRate = 0.0
    $outputRate = 0.0
    $ratesSource = "missing_rates_file"
  }

  $estimatedCost = [Math]::Round((($InputTokens / 1000) * $inputRate) + (($OutputTokens / 1000) * $outputRate), 6)
}

$totalTokens = $InputTokens + $OutputTokens

$entry = [ordered]@{
  timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
  model = $Model
  input_tokens = $InputTokens
  output_tokens = $OutputTokens
  total_tokens = $totalTokens
  input_cost_per_1k = $inputRate
  output_cost_per_1k = $outputRate
  estimated_cost_usd = $estimatedCost
  rates_source = $ratesSource
}

if ($Source) {
  $entry.source = $Source
}
if ($Note) {
  $entry.note = $Note
}

$logDir = Split-Path -Parent $LogPath
if (-not (Test-Path -LiteralPath $logDir)) {
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

$line = $entry | ConvertTo-Json -Compress
Add-Content -LiteralPath $LogPath -Value $line -Encoding ASCII

Write-Host "Logged usage to $LogPath"
Write-Host ("Model: {0} | input {1} | output {2} | cost {3} USD" -f $Model, $InputTokens, $OutputTokens, $estimatedCost)
