# scripts/test.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Quiet
& "$PSScriptRoot/../venv310/Scripts/Activate.ps1"

Write-Host "Running tests..."
pytest --maxfail=1 --disable-warnings -q
