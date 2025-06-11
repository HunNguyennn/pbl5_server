# Tạo file dashboard.py để quản lý giao diện web
from fastapi import FastAPI, WebSocket, Request, APIRouter, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json, datetime, sqlite3, os
import hashlib
from starlette.middleware.sessions import SessionMiddleware
from functools import wraps

# Tạo router riêng cho dashboard
dashboard_router = APIRouter()

# Khởi tạo templates
templates = Jinja2Templates(directory="app/templates")

# Khởi tạo database nếu chưa có
def init_database():
    """
    Khởi tạo cơ sở dữ liệu nếu chưa tồn tại
    """
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    
    # Tạo bảng waste_records để lưu thông tin về các lần phát hiện rác (không lưu ảnh)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS waste_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        waste_type TEXT NOT NULL,
        specific_waste TEXT NOT NULL,
        confidence REAL NOT NULL,
        timestamp DATETIME DEFAULT (datetime('now', '+7 hours'))
    )
    ''')
    
    # Tạo bảng sensor_data để lưu thông tin từ cảm biến khoảng cách
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        distance REAL NOT NULL,
        timestamp DATETIME DEFAULT (datetime('now', '+7 hours'))
    )
    ''')
    
    # Tạo bảng waste_detections để lưu chi tiết về các lần phát hiện cùng với hình ảnh
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS waste_detections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        waste_type TEXT NOT NULL,
        specific_waste TEXT NOT NULL,
        confidence REAL NOT NULL,
        processing_time REAL NOT NULL,
        object_count INTEGER NOT NULL,
        orig_image TEXT,
        result_image TEXT,
        timestamp DATETIME DEFAULT (datetime('now', '+7 hours'))
    )
    ''')
    
    # Tạo bảng users để quản lý tài khoản và phân quyền
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'admin'))
    )
    ''')
    
    conn.commit()
    conn.close()

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

# Lưu chi tiết phát hiện rác vào database
def save_waste_detection(waste_type, specific_waste, confidence, processing_time, object_count, orig_image, result_image):
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO waste_detections (waste_type, specific_waste, confidence, processing_time, object_count, orig_image, result_image) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (waste_type, specific_waste, confidence, processing_time, object_count, orig_image, result_image)
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

# Lưu người dùng mới
def create_user(username, password_hash, role='user'):
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role)
    )
    conn.commit()
    conn.close()

# Tạo tài khoản admin mặc định khi khởi động
def create_admin_account():
    from hashlib import sha256
    if not get_user_by_username("admin123"):
        create_user("admin123", sha256("admin123".encode()).hexdigest(), role="admin")

# Lấy thông tin người dùng theo username
def get_user_by_username(username):
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

# Xác thực người dùng
def verify_user(username, password_hash):
    user = get_user_by_username(username)
    if user and user[2] == password_hash:
        return user
    return None

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

# Hàm băm mật khẩu
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Decorator kiểm tra đăng nhập
def login_required(role=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = request.session.get("user")
            if not user:
                return RedirectResponse(url="/login", status_code=302)
            if role and user.get("role") != role:
                return RedirectResponse(url="/dashboard", status_code=302)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Route cho dashboard
@dashboard_router.get("/dashboard", response_class=HTMLResponse)
@login_required()
async def dashboard(request: Request):
    stats = get_waste_statistics()
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "stats": stats}
    )

# Route cho trang history
@dashboard_router.get("/dashboard/history", response_class=HTMLResponse)
@login_required()
async def detection_history(request: Request):
    return templates.TemplateResponse(
        "detection_history.html", 
        {"request": request}
    )

# Route cho trang đăng nhập
@dashboard_router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@dashboard_router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    user = verify_user(username, hash_password(password))
    if user:
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        request.session["user"] = {"id": user[0], "username": user[1], "role": user[3]}
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Sai tên đăng nhập hoặc mật khẩu!"})

# Route cho trang đăng ký
@dashboard_router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@dashboard_router.post("/register", response_class=HTMLResponse)
async def register_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if get_user_by_username(username):
        return templates.TemplateResponse("register.html", {"request": request, "error": "Tên đăng nhập đã tồn tại!"})
    create_user(username, hash_password(password), role="user")
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return response

# Route cho đăng xuất
@dashboard_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

# Các API endpoint đã được chuyển sang app/api/stats.py

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

# Broadcast update tới các client
async def broadcast_update(data):
    for connection in connections:
        try:
            await connection.send_json(data)
        except Exception:
            connections.remove(connection)

# Tạo tài khoản admin mặc định khi khởi động
create_admin_account()
