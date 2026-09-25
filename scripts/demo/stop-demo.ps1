$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.runtime'
$statePath = Join-Path $runtime 'owned-processes.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Host 'No launcher-owned demo processes recorded'; exit 0 }
$records = @(Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json)
$remaining = [System.Collections.Generic.List[object]]::new()
foreach ($record in $records) {
  $process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
  if (-not $process) { continue }
  $sameStart = [math]::Abs(($process.StartTime.ToUniversalTime() - ([datetime]$record.started_utc).ToUniversalTime()).TotalSeconds) -lt 1
  $sameExecutable = $record.executable -and $process.Path -eq $record.executable
  if (-not $sameStart -or -not $sameExecutable) { Write-Warning "PID $($record.pid) no longer matches the recorded demo process; leaving it untouched"; $remaining.Add($record); continue }
  & taskkill.exe /PID $record.pid /T /F | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Warning "Could not stop recorded PID $($record.pid); leaving its state for review"; $remaining.Add($record); continue }
  Write-Host "Stopped launcher-owned $($record.name) PID $($record.pid)"
}
if ($remaining.Count) { $remaining | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8 }
else { Remove-Item -LiteralPath $statePath }
