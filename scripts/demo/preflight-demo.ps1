param([switch]$SkipFrontend)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$manifest = Join-Path $root 'data\manifests\phase2c\artifact_manifest.json'
$sidecar = Join-Path $root 'data\manifests\phase2c\artifact_manifest.sha256'
$primary = '20190802T000000Z_day3_24h'
$api = 'http://127.0.0.1:8000/api/science'
$frontend = 'http://127.0.0.1:3200'
$failures = [System.Collections.Generic.List[string]]::new()
function Check([string]$name, [scriptblock]$action) {
  try { & $action; Write-Host "PASS $name" }
  catch { $failures.Add("$name`: $($_.Exception.Message)"); Write-Host "FAIL $name`: $($_.Exception.Message)" }
}
Check 'Frozen Phase 2C manifest sidecar' {
  if (-not (Test-Path -LiteralPath $manifest) -or -not (Test-Path -LiteralPath $sidecar)) { throw 'Manifest or sidecar missing' }
  $actual = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
  $expected = (Get-Content -LiteralPath $sidecar -Raw).Trim().ToLowerInvariant()
  if ($actual -ne $expected) { throw 'Manifest SHA-256 differs from frozen sidecar' }
}
Check 'Scientific readiness' {
  $status = Invoke-RestMethod "$api/status" -TimeoutSec 30
  if ($status.readiness_state -ne 'prototype_scientific_ready' -or $status.operational_ready -ne $false) { throw 'Unexpected readiness state' }
  if ($status.provenance.artifact_manifest_sha256 -ne (Get-Content -LiteralPath $sidecar -Raw).Trim()) { throw 'API manifest digest mismatch' }
}
Check 'Official primary demo case' {
  $catalogue = Invoke-RestMethod "$api/demo-cases" -TimeoutSec 30
  if ($primary -notin @($catalogue.cases | ForEach-Object case_id)) { throw 'Primary case absent from official catalogue' }
  $detail = Invoke-RestMethod "$api/cases/$primary" -TimeoutSec 30
  if ($detail.case_id -ne $primary) { throw 'Case detail mismatch' }
}
foreach ($entry in @(
  @('Model comparison', '/model-comparison'),
  @('Rainfall fields', "/cases/$primary/rainfall"),
  @('Regime probabilities', "/cases/$primary/regime"),
  @('Extreme probabilities', "/cases/$primary/probabilities"),
  @('FSS', "/cases/$primary/fss"),
  @('District products', "/cases/$primary/districts"),
  @('District geometry', '/geometry/districts'),
  @('2019 verification', '/verification')
)) {
  $name, $path = $entry
  Check $name { $response = Invoke-WebRequest "$api$path" -TimeoutSec 45; if ($response.StatusCode -ne 200) { throw "HTTP $($response.StatusCode)" } }
}
if (-not $SkipFrontend) {
  Check 'Production frontend' { $response = Invoke-WebRequest $frontend -TimeoutSec 30; if ($response.StatusCode -ne 200 -or $response.Content -notmatch 'VarshaSetu') { throw 'Frontend not healthy' } }
  Check 'Frontend API proxy' { $response = Invoke-RestMethod "$frontend/api/science/status" -TimeoutSec 30; if ($response.readiness_state -ne 'prototype_scientific_ready') { throw 'Proxy mismatch' } }
}
$online = $false
try {
  $style = Invoke-RestMethod 'https://tiles.openfreemap.org/styles/dark' -TimeoutSec 8
  $online = $null -ne $style.sources
} catch { Write-Host "WARN Online OpenFreeMap unavailable: $($_.Exception.Message)" }
Write-Host "Online geography: $(if ($online) { 'AVAILABLE' } else { 'UNAVAILABLE — local district fallback remains usable' })"
if ($failures.Count) { Write-Host "Preflight failed: $($failures.Count) local scientific/demo check(s)"; exit 1 }
Write-Host 'Local scientific demo preflight PASS'
