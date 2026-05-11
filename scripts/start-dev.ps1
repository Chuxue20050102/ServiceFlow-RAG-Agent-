$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend_fastapi"
$frontend = Join-Path $root "frontend_vue"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Backend virtual environment not found. Create it first:"
    Write-Host "  cd $backend"
    Write-Host "  py -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path (Join-Path $backend ".env"))) {
    Write-Host "Missing backend_fastapi\.env. Copy backend_fastapi\.env.example and fill your API settings."
    exit 1
}

if (-not (Test-Path (Join-Path $frontend ".env.local"))) {
    Copy-Item -LiteralPath (Join-Path $frontend ".env.example") -Destination (Join-Path $frontend ".env.local")
    Write-Host "Created frontend_vue\.env.local from .env.example."
}

docker compose -f (Join-Path $root "docker-compose.yml") up -d serviceflow-mysql

Start-Process -WindowStyle Hidden -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010" -WorkingDirectory $backend
Start-Process -WindowStyle Hidden -FilePath "npm.cmd" -ArgumentList "run", "dev", "--", "--host", "0.0.0.0" -WorkingDirectory $frontend

Write-Host "ServiceFlow dev services are starting."
Write-Host "Backend:  http://127.0.0.1:8010/health"
Write-Host "Frontend: http://127.0.0.1:5173"
