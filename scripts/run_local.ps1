# Start GeoSentinel locally (Windows). Uses port 55000 for API (8000/8080 often blocked).
param(
    [int]$ApiPort = 55000,
    [int]$WebPort = 5173
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:PYTHONPATH = $Root
$env:DATA_ROOT = Join-Path $Root "data"
$env:REGISTRY_PATH = Join-Path $Root "data\registry"

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
$venvUvicorn = Join-Path $Root ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Create venv first: python -m venv .venv; pip install -r requirements\dev.txt"
    exit 1
}

Write-Host "Starting API on http://127.0.0.1:$ApiPort ..."
Start-Process -FilePath $venvUvicorn -ArgumentList @(
    "backend.main:app", "--host", "127.0.0.1", "--port", "$ApiPort"
) -WorkingDirectory $Root -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "Starting frontend on http://localhost:$WebPort (proxy -> API) ..."
$frontendDir = Join-Path $Root "frontend"
Start-Process -FilePath "cmd.exe" -ArgumentList @(
    "/c", "set VITE_API_PROXY=http://127.0.0.1:$ApiPort && npm run dev -- --host 0.0.0.0 --port $WebPort"
) -WorkingDirectory $frontendDir -WindowStyle Normal

Write-Host ""
Write-Host "Open dashboard: http://localhost:$WebPort"
Write-Host "API docs:       http://127.0.0.1:${ApiPort}/docs"
Write-Host "Validate:       .\.venv\Scripts\python.exe scripts\validate_deployment.py --base-url http://127.0.0.1:$ApiPort --frontend-url http://127.0.0.1:$WebPort"
