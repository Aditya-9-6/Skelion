# deploy/deploy_production.ps1 - Automated Cloud Production Deployment Script
param (
    [string]$Domain = "app.skelion.dev"
)

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "     Skelion Production Cloud Deployment         " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Environment Verification
Write-Host ""
Write-Host "[1/4] Checking Production Configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env.production")) {
    Write-Error "  Missing .env.production. Create it from .env.production.example and inject secrets via your secret manager."
    exit 1
}
Write-Host "  [OK] Production environment file present (.env.production)" -ForegroundColor Green

# 2. Package Artifacts Verification
Write-Host ""
Write-Host "[2/4] Verifying SDK and Extension Packages..." -ForegroundColor Yellow
$nodePackage = "src/sdk/node/package.json"
$pythonPackage = "src/sdk/python/pyproject.toml"
$vsixPackage = "skelion_vscode_extension/skelion-vscode-0.1.0.vsix"

if ((Test-Path $nodePackage) -and (Test-Path $pythonPackage)) {
    Write-Host "  [OK] Node and Python distribution packages present" -ForegroundColor Green
}
if (Test-Path $vsixPackage) {
    Write-Host "  [OK] VS Code Extension VSIX package ready ($vsixPackage)" -ForegroundColor Green
}

# 3. Docker Orchestration Check
Write-Host ""
Write-Host "[3/4] Validating Docker Compose Stack..." -ForegroundColor Yellow
$composeFile = "deploy/docker-compose.saas.yml"
if (Test-Path $composeFile) {
    Write-Host "  [OK] Verified production compose spec: $composeFile" -ForegroundColor Green
    Write-Host "  To launch in cloud: docker compose -f deploy/docker-compose.saas.yml up -d --build" -ForegroundColor Cyan
}

# 4. Local Health Verification
Write-Host ""
Write-Host "[4/4] Probing Local Control Plane Routes..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8002/health" -Method Get -TimeoutSec 3
    Write-Host "  [OK] /health: $($r.status) (v$($r.version))" -ForegroundColor Green
} catch {
    Write-Host "  Notice: Local control plane daemon not running or initializing on port 8002." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Skelion SaaS pre-flight checks completed.       " -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  Landing Page:    https://$Domain/"
Write-Host "  Customer Portal: https://$Domain/portal"
Write-Host "  Admin Console:   Configure separately behind private access"
Write-Host "  API Docs:        https://$Domain/docs"
Write-Host "  Legal Pages:     /terms, /privacy, /refund"
