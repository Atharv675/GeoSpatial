# Validate GeoSentinel deployment after docker compose up
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$FrontendUrl = "http://localhost:5173",
    [switch]$SkipFrontend
)

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$args = @("$root\scripts\validate_deployment.py", "--base-url", $BaseUrl)
if ($SkipFrontend) {
    $args += "--skip-frontend"
} else {
    $args += "--frontend-url", $FrontendUrl
}

& $python @args
exit $LASTEXITCODE
