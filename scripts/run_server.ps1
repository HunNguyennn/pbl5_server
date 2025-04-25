# Kích hoạt virtual environment nếu có
$venvPath = ".\venv310\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    . $venvPath
}

# Load biến môi trường từ .env
$envFile = ".env"
if (Test-Path $envFile) {
    Get-Content $envFile |
        Where-Object { $_ -and ($_ -notmatch '^#') } |
        ForEach-Object {
            $parts = $_ -split '=', 2
            if ($parts.Length -eq 2) {
                $name = $parts[0].Trim()
                $value = $parts[1].Trim()
                [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
}

# Chạy FastAPI server bằng uvicorn
$serverHost = $env:HOST
$serverPort = $env:PORT

if (-not $serverHost) { $serverHost = "0.0.0.0" }
if (-not $serverPort) { $serverPort = "8000" }

uvicorn app.main:app --host $serverHost --port $serverPort --reload
