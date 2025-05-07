# WebSocket Server – Local for Raspberry Pi

## Setup

Trước tiên phải vào folder của server:
cd server
```bash
python -m venv310 venv
venv\Scripts\activate
pip install -r requirements.txt
```

Trong file .env nhớ thay đổi cấu hình IP lại bằng ipconfig (cmd)

rồi chạy:
```bash
.\scripts\migrate.ps1
.\scripts\test.ps1
.\scripts\run_server.ps1

