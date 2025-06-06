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

# Kiểm tra xem biến môi trường có SSL được kích hoạt không
# Mặc định là True - nghĩa là sử dụng localhost (secure context)
$useSSL = $env:USE_SSL -ne "False"
$serverHost = $env:HOST
$serverPort = $env:PORT

if (-not $serverHost) { $serverHost = "127.0.0.1" }
if (-not $serverPort) { $serverPort = "8000" }

# Hiển thị thông tin server sẽ chạy
Write-Host "Starting server with configuration:"
Write-Host "Host: $serverHost"
Write-Host "Port: $serverPort"
Write-Host "Secure context available: Yes (localhost)"

# Chạy FastAPI server bằng uvicorn
uvicorn app.main:app --host $serverHost --port $serverPort --reload
