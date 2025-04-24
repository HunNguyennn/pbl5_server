# Tạo file dashboard.py để quản lý giao diện web
from fastapi import FastAPI, WebSocket, Request, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, datetime, sqlite3, os

# Tạo router riêng cho dashboard
dashboard_router = APIRouter()

# Khởi tạo templates
templates = Jinja2Templates(directory="templates")

# Khởi tạo database nếu chưa có
def init_database():
    db_path = "waste_stats.db"
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE waste_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waste_type TEXT NOT NULL,
            specific_waste TEXT NOT NULL,
            confidence REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distance REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        conn.close()
        print("Database initialized")

# Tạo bảng dữ liệu
init_database()

# Lưu kết quả phân loại rác vào database
def save_waste_record(waste_type, specific_waste, confidence):
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO waste_records (waste_type, specific_waste, confidence) VALUES (?, ?, ?)",
        (waste_type, specific_waste, confidence)
    )
    conn.commit()
    conn.close()

# Lưu dữ liệu cảm biến
def save_sensor_data(distance):
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sensor_data (distance) VALUES (?)",
        (distance,)
    )
    conn.commit()
    conn.close()

# Lấy thống kê phân loại rác
def get_waste_statistics():
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    
    # Tổng số lượng theo loại
    cursor.execute('''
    SELECT waste_type, COUNT(*) as count 
    FROM waste_records
    GROUP BY waste_type
    ''')
    waste_counts = cursor.fetchall()
    
    # Thống kê theo ngày (7 ngày gần nhất)
    cursor.execute('''
    SELECT DATE(timestamp) as date, waste_type, COUNT(*) as count
    FROM waste_records
    WHERE timestamp >= DATE('now', '-7 days')
    GROUP BY DATE(timestamp), waste_type
    ORDER BY date
    ''')
    daily_stats = cursor.fetchall()
    
    # Chi tiết từng loại rác cụ thể
    cursor.execute('''
    SELECT specific_waste, COUNT(*) as count
    FROM waste_records
    GROUP BY specific_waste
    ORDER BY count DESC
    ''')
    specific_waste_stats = cursor.fetchall()
    
    conn.close()
    
    # Định dạng dữ liệu để trả về
    stats = {
        "waste_counts": {item[0]: item[1] for item in waste_counts},
        "daily_stats": {},
        "specific_waste": {item[0]: item[1] for item in specific_waste_stats}
    }
    
    # Xử lý dữ liệu theo ngày
    for date, waste_type, count in daily_stats:
        if date not in stats["daily_stats"]:
            stats["daily_stats"][date] = {}
        stats["daily_stats"][date][waste_type] = count
    
    return stats

# Route cho dashboard
@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = get_waste_statistics()
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "stats": stats}
    )

# API endpoint để lấy dữ liệu thống kê
@dashboard_router.get("/api/stats")
async def get_stats():
    return get_waste_statistics()

# API endpoint để lấy dữ liệu thời gian thực
@dashboard_router.get("/api/realtime")
async def get_realtime_data():
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    
    # Lấy 10 bản ghi mới nhất
    cursor.execute('''
    SELECT waste_type, specific_waste, confidence, timestamp
    FROM waste_records
    ORDER BY timestamp DESC
    LIMIT 10
    ''')
    recent_records = cursor.fetchall()
    
    # Lấy dữ liệu cảm biến mới nhất
    cursor.execute('''
    SELECT distance, timestamp
    FROM sensor_data
    ORDER BY timestamp DESC
    LIMIT 1
    ''')
    latest_sensor = cursor.fetchone()
    
    conn.close()
    
    return {
        "recent_records": [
            {
                "waste_type": r[0],
                "specific_waste": r[1], 
                "confidence": r[2],
                "timestamp": r[3]
            } for r in recent_records
        ],
        "sensor": {
            "distance": latest_sensor[0] if latest_sensor else None,
            "timestamp": latest_sensor[1] if latest_sensor else None
        }
    }

# Thêm endpoint reset thống kê vào dashboard.py
@dashboard_router.post("/api/stats/reset")
async def reset_stats():
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    
    # Xóa tất cả dữ liệu trong bảng waste_records
    cursor.execute("DELETE FROM waste_records")
    
    # Xóa tất cả dữ liệu trong bảng sensor_data
    cursor.execute("DELETE FROM sensor_data")
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Statistics reset successfully"}

# WebSocket cho dữ liệu theo thời gian thực
connections = []

@dashboard_router.websocket("/dashboard/ws")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    try:
        while True:
            # Chỉ chờ message keep-alive
            data = await websocket.receive_text()
    except Exception:
        connections.remove(websocket)

# Hàm để broadcast cập nhật đến tất cả kết nối dashboard
async def broadcast_update(data):
    for connection in connections:
        try:
            await connection.send_text(json.dumps(data))
        except Exception:
            # Nếu gửi lỗi, bỏ qua
            pass
