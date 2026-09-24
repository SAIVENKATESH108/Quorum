# Reproduction & Verification Script for Stage 3 Data Persistence
# Tests that projects and reports survive a complete server restart / redeploy.

param([int]$Port = 3114)

$ErrorActionPreference = "Stop"
$base = "http://localhost:$Port"

Write-Host "--- Stage 3 Data Persistence Verification ---"
Write-Host "1. Starting Next.js Web Server (Deploy 1)..."
$proc1 = Start-Process -FilePath "node" `
  -ArgumentList "node_modules/next/dist/bin/next", "start", "apps/web", "-p", "$Port" `
  -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput "$env:TEMP\quorum-persist-out1.log" `
  -RedirectStandardError "$env:TEMP\quorum-persist-err1.log"

try {
  Start-Sleep -Seconds 10

  Write-Host "2. Creating project and report in Deploy 1..."
  $proj = Invoke-RestMethod -Uri "$base/api/projects" -Method Post `
    -ContentType "application/json" -Body '{"title":"Persistent Quantum DAG Domain"}'
  Write-Host "   Created Project: $($proj.id) '$($proj.title)'"

  $rep = Invoke-RestMethod -Uri "$base/api/projects/$($proj.id)/reports" -Method Post `
    -ContentType "application/json" -Body '{"query":"BFT Consensus Persistence Bounds"}'
  Write-Host "   Created Report:  $($rep.id) query='$($rep.query)'"

  # Verify immediate read
  $detail = Invoke-RestMethod -Uri "$base/api/reports/$($rep.id)" -Method Get
  Write-Host "   Confirmed in Deploy 1: status=$($detail.status)"

} finally {
  Write-Host "3. Simulating Redeploy: Stopping Server 1 (killing process)..."
  Stop-Process -Id $proc1.Id -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

Write-Host "4. Starting Next.js Web Server (Deploy 2 / Redeployed Instance)..."
$proc2 = Start-Process -FilePath "node" `
  -ArgumentList "node_modules/next/dist/bin/next", "start", "apps/web", "-p", "$Port" `
  -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput "$env:TEMP\quorum-persist-out2.log" `
  -RedirectStandardError "$env:TEMP\quorum-persist-err2.log"

try {
  Start-Sleep -Seconds 10

  Write-Host "5. Checking if project and report survived the redeploy..."
  $projAfter = Invoke-RestMethod -Uri "$base/api/projects/$($proj.id)" -Method Get
  Write-Host "   Project after redeploy: $($projAfter.id) '$($projAfter.title)'"

  $repAfter = Invoke-RestMethod -Uri "$base/api/reports/$($rep.id)" -Method Get
  Write-Host "   Report after redeploy:  $($repAfter.id) query='$($repAfter.query)' status=$($repAfter.status)"

  if ($projAfter.id -ne $proj.id -or $repAfter.id -ne $rep.id) {
    throw "REGRESSION: Data was lost across redeploy!"
  }

  Write-Host "SUCCESS: Data survived the redeploy completely!"

  Write-Host "6. Cleaning up test data..."
  Invoke-RestMethod -Uri "$base/api/projects/$($proj.id)" -Method Delete | Out-Null
  Write-Host "   Test project deleted."

} finally {
  Stop-Process -Id $proc2.Id -Force -ErrorAction SilentlyContinue
  Write-Host "Server 2 stopped."
}
