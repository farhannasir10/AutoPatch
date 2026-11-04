# Local stand-in for GitHub Actions: run the Next cart Jest suite,
# then POST the failure log to AutoPatch's CI webhook.

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
$sample = Join-Path $root "samples\nextjs-cart"
$api = if ($env:AUTOPATCH_URL) { $env:AUTOPATCH_URL.TrimEnd("/") } else { "http://127.0.0.1:8000" }

Write-Host "==> npm test in samples/nextjs-cart"
Push-Location $sample
try {
  if (-not (Test-Path "node_modules")) {
    npm install --no-fund --no-audit | Out-Host
  }
  $logFile = Join-Path $env:TEMP "autopatch-jest.log"
  npm test 2>&1 | Tee-Object -FilePath $logFile
  $code = $LASTEXITCODE
} finally {
  Pop-Location
}

if ($code -eq 0) {
  Write-Host "Tests already green — nothing for AutoPatch to do."
  exit 0
}

$log = Get-Content -Raw $logFile
$body = @{
  fixture_id = "nextjs_pricing"
  error_log  = $log
  repo       = $env:GITHUB_REPOSITORY
  branch     = "local"
  commit_sha = "local-sim"
} | ConvertTo-Json

Write-Host "==> POST $api/api/ci/failures"
$resp = Invoke-RestMethod -Method Post -Uri "$api/api/ci/failures" -ContentType "application/json" -Body $body
$resp | ConvertTo-Json -Depth 6
Write-Host "Open http://localhost:3000 and approve the run when HITL appears."
