from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import base64, cv2, numpy as np, time
import logging
import os

from app.core.logger import init_logger
from app.core.config import settings
from app.api.websocket import router as ws_router
from app.dashboard import dashboard_router, save_waste_record, save_waste_detection, broadcast_update
from app.api.stats import router as stats_router
from app.services.inference import predict, get_waste_category, draw_boxes, labels, waste_categories

# Khởi tạo templates cho Jinja2
templates = Jinja2Templates(directory="app/templates")

# Initialize logging
init_logger()

# Đặt cấp độ ghi log theo cấu hình
logging.getLogger().setLevel(getattr(logging, settings.LOG_LEVEL))

# Tạo thư mục logs nếu chưa tồn tại
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Tạo thư mục để lưu ảnh debug (nếu cần)
debug_img_dir = "logs/debug_images"
if settings.SAVE_DEBUG_IMAGES and not os.path.exists(debug_img_dir):
    os.makedirs(debug_img_dir)

app = FastAPI(
    title="Smart Trash Server",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)


def enhance_image(image):
    """
    Nâng cao chất lượng hình ảnh để cải thiện việc phát hiện đối tượng
    """
    try:
        # 1. Tách các kênh màu
        h, w = image.shape[:2]
        logging.debug(f"Enhancing image of size {w}x{h}")
        
        # 2. Chuyển hình ảnh sang không gian màu LAB
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 3. Áp dụng CLAHE (Contrast Limited Adaptive Histogram Equalization) cho kênh L
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l)
        
        # 4. Merge các kênh lại và chuyển về BGR
        lab_clahe = cv2.merge((l_clahe, a, b))
        enhanced_img = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
        
        # 5. Áp dụng Gaussian blur để giảm nhiễu
        enhanced_img = cv2.GaussianBlur(enhanced_img, (3, 3), 0)
        
        # 6. Cân chỉnh độ sáng và độ tương phản
        # Áp dụng phương pháp alpha-beta: g(x,y) = alpha*f(x,y) + beta
        alpha = 1.1  # Tăng độ tương phản 
        beta = 5     # Tăng độ sáng
        enhanced_img = cv2.convertScaleAbs(enhanced_img, alpha=alpha, beta=beta)
        
        logging.debug("Image enhancement completed successfully")
        
        # Lưu ảnh gốc và ảnh đã được nâng cao nếu cần debug
        if settings.SAVE_DEBUG_IMAGES:
            timestamp = int(time.time())
            cv2.imwrite(f"{debug_img_dir}/original_{timestamp}.jpg", image)
            cv2.imwrite(f"{debug_img_dir}/enhanced_{timestamp}.jpg", enhanced_img)
            logging.debug(f"Debug images saved with timestamp {timestamp}")
            
        return enhanced_img
    except Exception as e:
        logging.error(f"Error during image enhancement: {e}")
        return image  # Trả về ảnh gốc nếu có lỗi


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Endpoint kiểm tra bằng JSON (chuyển từ root sang /api/status)
@app.get("/api/status", response_class=JSONResponse)
async def status():
    return {"message": "Smart Trash Server is running"}

# Endpoint health (không hiển thị trong schema)
@app.get("/health", include_in_schema=False)
async def health_check():
    return {"message": "Smart Trash Server is running"}

# Route để phát video từ camera - không còn cần thiết nữa nhưng giữ lại để tương thích ngược
@app.get("/video_feed")
async def video_feed():
    # Trả về một HTTP redirect về ảnh placeholder tĩnh
    return RedirectResponse(url="/static/images/camera_placeholder.jpg")

# Nhận ảnh từ client, decode và chạy model
@app.post("/detect")
async def upload_image(req: Request):
    try:
        logging.info("Nhận yêu cầu phân tích ảnh")
        payload = await req.json()
        img_b64 = payload.get("image")
        
        if not img_b64 or not img_b64.startswith("data:image"):
            logging.error("Định dạng ảnh không hợp lệ")
            return JSONResponse(content={"error": "Invalid image"}, status_code=400)

        try:
            # Lấy phần dữ liệu base64 (bỏ qua phần header)
            header, data = img_b64.split(",", 1)
            
            # Giải mã base64
            img_bytes = base64.b64decode(data)
            
            # Chuyển đổi thành numpy array
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            
            # Giải mã thành ảnh BGR (OpenCV format)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            
            if img is None or img.size == 0:
                logging.error("Không thể giải mã ảnh")
                return JSONResponse(content={"error": "Cannot decode image"}, status_code=400)
                
            logging.info(f"Ảnh đã được giải mã thành công: shape={img.shape}")
        except Exception as e:
            logging.error(f"Lỗi xử lý ảnh: {e}")
            return JSONResponse(content={"error": f"Image processing error: {str(e)}"}, status_code=400)

        # Đo thời gian xử lý
        start_time = time.time()
        
        # Nâng cao chất lượng hình ảnh
        img_enhanced = enhance_image(img)
        
        # Thực hiện dự đoán với mô hình trên ảnh đã nâng cao
        logging.info("Đang chạy mô hình dự đoán")
        boxes, probs = predict(img_enhanced, force=True)
        
        # Xác định loại rác chính
        waste_type, waste_class, max_conf = get_waste_category(boxes, probs)
        logging.info(f"Loại rác được phân loại: {waste_type}, lớp: {waste_class}, độ tin cậy: {max_conf:.4f}")
        
        # Tính toán số lượng đối tượng được phát hiện
        detections = []
        for i in range(len(boxes)):
            class_id = np.argmax(probs[i])
            confidence = float(probs[i][class_id])
            
            if confidence > settings.CONF_THRESHOLD:
                class_name = labels.get(class_id, "unknown")
                
                # Format box tương tự như Raspberry Pi
                x_center, y_center, width, height = boxes[i]
                x1 = float(x_center - width/2)
                y1 = float(y_center - height/2)
                
                detections.append({
                    "class": class_name,
                    "confidence": confidence,
                    "waste_type": waste_categories.get(class_name, "unknown"),
                    "bbox": [x1, y1, float(width), float(height)]
                })
        
        # Vẽ kết quả lên ảnh
        result_img = draw_boxes(img_enhanced, boxes, probs, current=waste_type)
        
        # Chuyển đổi ảnh kết quả thành base64
        _, buffer = cv2.imencode('.jpg', result_img)
        img_b64_result = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
        
        # Chuyển đổi ảnh gốc thành base64 (để lưu database)
        _, orig_buffer = cv2.imencode('.jpg', img)
        img_b64_orig = f"data:image/jpeg;base64,{base64.b64encode(orig_buffer).decode('utf-8')}"
        
        # Tính thời gian xử lý
        processing_time = time.time() - start_time
        
        # Lưu thông tin vào database nếu đã phát hiện rác
        if waste_type and waste_class != 'unknown' and max_conf > settings.CONF_THRESHOLD:
            # Lưu bản ghi vào bảng waste_records (cho thống kê tổng hợp)
            save_waste_record(waste_type, waste_class, max_conf)
            
            # Lưu chi tiết phát hiện với ảnh vào bảng waste_detections
            save_waste_detection(
                waste_type, 
                waste_class, 
                max_conf, 
                processing_time, 
                len(detections), 
                img_b64_orig, 
                img_b64_result
            )
            
            # Gửi thông báo cập nhật qua WebSocket
            await broadcast_update({
                "recent_records": [{
                    "waste_type": waste_type,
                    "specific_waste": waste_class,
                    "confidence": float(max_conf),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", 
                        time.localtime(time.time() + 7 * 3600))  # UTC+7 cho Việt Nam
                }],
                "stats_updated": True
            })
        
        # Trả về kết quả với format chính xác như Raspberry Pi
        return {
            "processing_time": processing_time,
            "object_count": len(detections),
            "detections": detections,
            "classification_result": {
                "waste_type": waste_type,
                "class": waste_class,
                "confidence": float(max_conf)
            },
            "image": img_b64_result
        }
    except Exception as e:
        logging.error(f"Lỗi xử lý: {e}")
        import traceback
        traceback_str = traceback.format_exc()
        logging.error(traceback_str)
        return JSONResponse(
            content={"error": str(e), "traceback": traceback_str}, 
            status_code=500
        )

# Serve static files (JS/CSS) và trang index/dashboard qua Jinja
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# WebSocket router
app.include_router(ws_router, prefix="/ws")

# API stats (đảm bảo prefix /api)
app.include_router(stats_router, prefix="/api")

# Dashboard: HTML tại /dashboard và các API nội bộ của dashboard
app.include_router(dashboard_router)

if __name__ == "__main__":
    import uvicorn
    # Đảm bảo chạy trên localhost để có secure context cho việc truy cập camera
    # host = settings.HOST if settings.HOST != "0.0.0.0" else "127.0.0.1"
    # print(f"Starting server on {host}:{settings.PORT}")
    # print(f"Secure context available: {'Yes (localhost)' if host == '127.0.0.1' else 'No'}")
    # uvicorn.run("app.main:app", host=host, port=settings.PORT, reload=True)
    host = settings.HOST 
    port = settings.PORT
    
    print(f"Starting server on {host}:{port}")
    
    # Chạy server thông thường
    uvicorn.run("app.main:app", 
                host=host, 
                port=port,
                reload=True)