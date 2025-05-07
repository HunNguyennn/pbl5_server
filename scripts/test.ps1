# scripts/test.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& "$PSScriptRoot/../venv310/Scripts/Activate.ps1"
$env:PYTHONPATH = "$PSScriptRoot\.." 

Write-Host "Running tests..."
pytest --maxfail=1 --disable-warnings -q
