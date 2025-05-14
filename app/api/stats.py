from fastapi import APIRouter, HTTPException
import sqlite3
from typing import Dict, List, Any, Optional

router = APIRouter()

@router.get("/stats")
async def get_waste_statistics():
    """
    Lấy thống kê phân loại rác từ database
    """
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

@router.get("/sensor")
async def get_sensor_data():
    """
    Lấy dữ liệu cảm biến gần nhất
    """
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT distance, timestamp
    FROM sensor_data
    ORDER BY timestamp DESC
    LIMIT 10
    ''')
    sensor_data = cursor.fetchall()
    conn.close()
    
    return {
        "sensor_data": [
            {"distance": item[0], "timestamp": item[1]} 
            for item in sensor_data
        ]
    }

@router.get("/realtime")
async def get_realtime_data():
    """
    Lấy dữ liệu thời gian thực (10 bản ghi mới nhất + cảm biến gần nhất)
    """
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

@router.get("/detections")
async def get_detections(limit: int = 10, offset: int = 0, waste_type: Optional[str] = None):
    """
    Lấy lịch sử các lần phát hiện rác với hình ảnh kèm theo
    """
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    
    # Xây dựng truy vấn SQL với bộ lọc tùy chọn
    query = "SELECT id, waste_type, specific_waste, confidence, processing_time, object_count, result_image, timestamp FROM waste_detections"
    params = []
    
    if waste_type:
        query += " WHERE waste_type = ?"
        params.append(waste_type)
    
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    detections = cursor.fetchall()
    
    # Đếm tổng số bản ghi (để phân trang)
    count_query = "SELECT COUNT(*) FROM waste_detections"
    if waste_type:
        count_query += " WHERE waste_type = ?"
        cursor.execute(count_query, [waste_type])
    else:
        cursor.execute(count_query)
    
    total_count = cursor.fetchone()[0]
    conn.close()
    
    # Chuyển dữ liệu về định dạng phù hợp với frontend
    detection_list = []
    for d in detections:
        detection_list.append({
            "id": d[0],
            "waste_type": d[1],
            "specific_waste": d[2],
            "confidence": d[3],
            "processing_time": d[4],
            "object_count": d[5],
            "result_image": d[6],  # Giữ nguyên định dạng base64 đầy đủ
            "timestamp": d[7]
        })
    
    return {
        "success": True,
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "detections": detection_list
    }

@router.get("/detections/{detection_id}")
async def get_detection_detail(detection_id: int):
    """
    Lấy chi tiết một phát hiện rác theo ID
    """
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, waste_type, specific_waste, confidence, processing_time, object_count, orig_image, result_image, timestamp FROM waste_detections WHERE id = ?",
        [detection_id]
    )
    detection = cursor.fetchone()
    conn.close()
    
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    # Chuyển đổi dữ liệu về định dạng phù hợp với frontend
    result = {
        "success": True,
        "detection": {
            "id": detection[0],
            "waste_type": detection[1],
            "specific_waste": detection[2],
            "confidence": detection[3],
            "processing_time": detection[4],
            "object_count": detection[5],
            "orig_image": detection[6],  # Giữ nguyên định dạng base64 đầy đủ
            "result_image": detection[7],  # Giữ nguyên định dạng base64 đầy đủ
            "timestamp": detection[8]
        }
    }
    
    return result

@router.post("/reset")
async def reset_stats():
    """
    Reset tất cả thống kê và dữ liệu cảm biến
    """
    conn = sqlite3.connect("waste_stats.db")
    cursor = conn.cursor()
    
    # Xóa tất cả dữ liệu trong bảng waste_records
    cursor.execute("DELETE FROM waste_records")
    
    # Xóa tất cả dữ liệu trong bảng sensor_data
    cursor.execute("DELETE FROM sensor_data")
    
    # Xóa tất cả dữ liệu trong bảng waste_detections
    cursor.execute("DELETE FROM waste_detections")
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": "Statistics reset successfully"} 