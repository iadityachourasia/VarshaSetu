$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$frontend = Join-Path $root 'frontend-v2'
$python = Join-Path $root '.venv\Scripts\python.exe'
$node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
$runtime = Join-Path $PSScriptRoot '.runtime'
$statePath = Join-Path $runtime 'owned-processes.json'
foreach ($path in @($frontend, (Join-Path $root 'backend'), (Join-Path $root 'data\manifests\phase2c'), (Join-Path $frontend '.next\BUILD_ID'))) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Required project/build artifact missing: $path" }
}
if (-not (Test-Path -LiteralPath $python)) { throw 'Project Python environment missing; restore .venv before launch' }
if (-not $node) { throw 'Node.js is unavailable in PATH' }
$existing = @()
if (Test-Path -LiteralPath $statePath) { $existing = @(Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json) }
$owned = [System.Collections.Generic.List[object]]::new()
foreach ($record in $existing) {
  $process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
  if ($process -and [math]::Abs(($process.StartTime.ToUniversalTime() - ([datetime]$record.started_utc).ToUniversalTime()).TotalSeconds) -lt 1) { $owned.Add($record) }
}
function Health([string]$url) {
  try { return (Invoke-WebRequest $url -TimeoutSec 5).StatusCode -eq 200 } catch { return $false }
}
function PortOccupied([int]$port) {
  return $null -ne (Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}
function StartOwned([string]$name, [string]$file, [string[]]$arguments, [string]$workingDirectory) {
  $process = Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $workingDirectory -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime "$name.stdout.log") -RedirectStandardError (Join-Path $runtime "$name.stderr.log")
  $owned.Add([pscustomobject]@{ name = $name; pid = $process.Id; started_utc = $process.StartTime.ToUniversalTime().ToString('o'); executable = (Resolve-Path -LiteralPath $file).Path })
  $owned | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
}
function WaitHealthy([string]$url, [int]$seconds) {
  $end = (Get-Date).AddSeconds($seconds)
  while ((Get-Date) -lt $end) { if (Health $url) { return }; Start-Sleep -Milliseconds 500 }
  throw "Service failed to become healthy: $url. Inspect logs under $runtime"
}
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
if (-not (Health 'http://127.0.0.1:8000/api/science/status')) {
  if (PortOccupied 8000) { throw 'Port 8000 is occupied by an unverified service; no process was stopped' }
  StartOwned 'backend' $python @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000') $root
  WaitHealthy 'http://127.0.0.1:8000/api/science/status' 90
} else { Write-Host 'Reusing existing healthy scientific API; shutdown affects it only if launcher-owned' }
& (Join-Path $PSScriptRoot 'preflight-demo.ps1') -SkipFrontend
if (-not $?) { throw 'Scientific preflight failed; production frontend was not started' }
if (-not (Health 'http://127.0.0.1:3200')) {
  if (PortOccupied 3200) { throw 'Port 3200 is occupied by an unverified service; no process was stopped' }
  StartOwned 'frontend' $node @('node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3200') $frontend
  WaitHealthy 'http://127.0.0.1:3200' 90
} else { Write-Host 'Reusing existing healthy frontend; shutdown affects it only if launcher-owned' }
& (Join-Path $PSScriptRoot 'preflight-demo.ps1')
if (-not $?) { throw 'Final demo preflight failed; inspect logs and repair before recording' }
Write-Host 'VarshaSetu historical prototype ready at http://127.0.0.1:3200'
