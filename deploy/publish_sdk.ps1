# deploy/publish_sdk.ps1 - Automated SDK Package & Publish Tool
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Skelion Official SDK Packaging & Publish   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Package Node.js SDK
Write-Host "`n[1/2] Verifying Node.js SDK (@skelion/node)..." -ForegroundColor Yellow
Push-Location "src/sdk/node"
if (Test-Path "package.json") {
    Write-Host "  ✓ Found package.json" -ForegroundColor Green
    Write-Host "  Running npm pack (dry-run)..."
    npm pack --dry-run
    Write-Host "  Ready to publish: npm publish --access public" -ForegroundColor Magenta
}
Pop-Location

# 2. Package Python SDK
Write-Host "`n[2/2] Verifying Python SDK (skelion)..." -ForegroundColor Yellow
Push-Location "src/sdk/python"
if (Test-Path "pyproject.toml") {
    Write-Host "  ✓ Found pyproject.toml" -ForegroundColor Green
    Write-Host "  Building wheel and sdist with pip/build..."
    & python -m build --sdist --wheel .
    Write-Host "  Ready to publish: twine upload dist/*" -ForegroundColor Magenta
}
Pop-Location

Write-Host "`n=============================================" -ForegroundColor Green
Write-Host "  SDK Packaging Verification Completed!      " -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
