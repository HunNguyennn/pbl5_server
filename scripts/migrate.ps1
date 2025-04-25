# scripts/migrate.ps1
Write-Host "Initializing database..."

# Kích hoạt venv
& "$PSScriptRoot/../venv310/Scripts/Activate.ps1"

# Chạy đoạn script Python
python -Command @"
from app.dashboard import init_database
init_database()
"@

Write-Host "Database initialized."