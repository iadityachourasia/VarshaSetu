param([switch]$SkipFrontend)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$manifest = Join-Path $root 'data\manifests\phase2c\artifact_manifest.json'
$sidecar = Join-Path $root 'data\manifests\phase2c\artifact_manifest.sha256'
$primary = '20190802T000000Z_day3_24h'
# Phase 5B: Track-B (2025) official demo case, added alongside the existing
# Track-A (2019) checks below rather than replacing them -- both tracks are
# part of the official judge path now (docs/presentation/OFFICIAL_DEMO_CASES.md).
$operationalPrimary = '20250714_day2_24h'
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
Check 'Official primary demo case (Track A · 2019)' {
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
# Phase 5B: Track-B (2025 operational-era) official demo case and its
# principal endpoints. A SCIENCE_INTEGRITY_FAILURE (HTTP 503) here must
# fail this preflight, never be silently treated as an offline-map-style
# soft warning -- Check() already achieves that by adding it to $failures.
Check 'Official primary demo case (Track B · 2025)' {
  $detail = Invoke-RestMethod "$api/operational/2025/cases/$operationalPrimary" -TimeoutSec 30
  if ($detail.case_id -ne $operationalPrimary) { throw 'Operational case detail mismatch' }
  if (-not $detail.deterministic_source_eligible -or -not $detail.probability_source_eligible -or -not $detail.regime_source_eligible -or -not $detail.ensemble_source_eligible) { throw 'Official case is missing an expected data-source eligibility flag' }
}
foreach ($entry in @(
  @('Operational status', '/operational/status'),
  @('Operational deterministic metrics (2025)', '/operational/2025/metrics/deterministic'),
  @('Operational rainfall (M1)', "/operational/2025/cases/$operationalPrimary/rainfall?field=m1"),
  @('Operational regime', "/operational/2025/cases/$operationalPrimary/regime"),
  @('Operational probability (heavy)', "/operational/2025/cases/$operationalPrimary/probability/heavy"),
  @('Operational ensemble', "/operational/2025/cases/$operationalPrimary/ensemble")
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
# Phase 5B, section 25: the three-state decision this launcher exposes to
# its callers. Online tile availability alone never blocks -- the offline
# district fallback is a genuine, usable degraded mode, not a failure.
if ($failures.Count) {
  Write-Host "Preflight failed: $($failures.Count) local scientific/demo check(s)"
  Write-Host 'DEMO_PREFLIGHT_RESULT=BLOCKED'
  exit 1
}
if ($online) {
  Write-Host 'Local scientific demo preflight PASS'
  Write-Host 'DEMO_PREFLIGHT_RESULT=READY'
} else {
  Write-Host 'Local scientific demo preflight PASS (offline map fallback)'
  Write-Host 'DEMO_PREFLIGHT_RESULT=READY_WITH_OFFLINE_MAP'
}
