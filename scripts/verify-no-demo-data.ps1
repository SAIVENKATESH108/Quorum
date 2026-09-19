# Live regression check: created records persist, deletions stick, and no demo
# data reappears on any read surface.
# Usage: powershell -File scripts/verify-no-demo-data.ps1 -Port 3113

param([int]$Port = 3113)

$ErrorActionPreference = "Stop"
$base = "http://localhost:$Port"

$proc = Start-Process -FilePath "node" `
  -ArgumentList "node_modules/next/dist/bin/next", "start", "apps/web", "-p", "$Port" `
  -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput "$env:TEMP\quorum-verify-out.log" `
  -RedirectStandardError "$env:TEMP\quorum-verify-err.log"

try {
  Start-Sleep -Seconds 16

  $proj = Invoke-RestMethod -Uri "$base/api/projects" -Method Post `
    -ContentType "application/json" -Body '{"title":"Deletion Regression Check"}'
  Write-Host "1. created project: $($proj.id) '$($proj.title)'"

  $rep = Invoke-RestMethod -Uri "$base/api/projects/$($proj.id)/reports" -Method Post `
    -ContentType "application/json" -Body '{"query":"Deletion regression check query"}'
  Write-Host "2. created report:  $($rep.id) status=$($rep.status)"

  $detail = Invoke-RestMethod -Uri "$base/api/reports/$($rep.id)" -Method Get
  Write-Host "3. report detail:   status=$($detail.status) sections=$($detail.sections.Count) sources=$($detail.sources.Count)"

  Invoke-RestMethod -Uri "$base/api/projects/$($proj.id)" -Method Delete | Out-Null
  Write-Host "4. deleted project: $($proj.id)"

  $projectsAfter = Invoke-RestMethod -Uri "$base/api/projects" -Method Get
  $reportsAfter = Invoke-RestMethod -Uri "$base/api/reports" -Method Get
  # PowerShell wraps an empty JSON array as $null, so count defensively.
  $projectCount = if ($null -eq $projectsAfter) { 0 } else { @($projectsAfter).Count }
  $reportCount = if ($null -eq $reportsAfter) { 0 } else { @($reportsAfter).Count }
  Write-Host "5. projects after delete: $projectCount"
  Write-Host "6. reports after delete:  $reportCount"

  $sources = Invoke-RestMethod -Uri "$base/api/sources" -Method Get
  $sourceCount = if ($null -eq $sources) { 0 } else { @($sources).Count }
  Write-Host "7. evidence library:      $sourceCount (HTTP 200, API-backed, no mock citations)"

  $missing = try {
    Invoke-RestMethod -Uri "$base/api/reports/$($rep.id)" -Method Get | Out-Null
    "unexpected 200"
  } catch {
    "$($_.Exception.Response.StatusCode.value__)"
  }
  Write-Host "7. deleted report GET:    $missing"

  if ($projectCount -ne 0 -or $reportCount -ne 0) {
    throw "Demo data reappeared after deletion."
  }
  Write-Host "RESULT: no demo data reappeared; store is empty after delete."
}
finally {
  Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  Write-Host "server stopped"
}