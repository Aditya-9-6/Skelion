# Verify Skelion platform
# Runs sanity check, starts API, and checks health endpoint
Write-Host "Running sanity check..."
uv run python "C:/Users/adity/.gemini/antigravity/brain/5b2cce19-829f-47e8-a475-c50d0b5847f8/sanity_check.py"

Write-Host "Starting FastAPI server..."
Start-Process -NoNewWindow -FilePath "uv" -ArgumentList "run", "uvicorn", "skelion_agent.control_plane:app", "--port", "8002"
Start-Sleep -Seconds 5

Write-Host "Checking health endpoint..."
try {
    $resp = Invoke-RestMethod -Uri http://127.0.0.1:8002/health -ErrorAction Stop
    Write-Host "Health check succeeded: $($resp | ConvertTo-Json)"
} catch {
    Write-Error "Health check failed: $_"
}
Write-Host "Verification complete."
