from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import base64, json, cv2, numpy as np, uvicorn
from routers.dashboard import dashboard_router, save_waste_record, save_sensor_data, broadcast_update
from predict import predict, draw_boxes, labels, waste_categories


# Thêm router vào app
app = FastAPI()
app.include_router(dashboard_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Lưu trữ kết nối websocket từ Raspberry Pi
raspberry_connection = None

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global raspberry_connection
    
    try:
        client_type = await websocket.receive_text()  # Nhận loại client: "raspberry" hoặc "browser"
        
        if client_type == "raspberry":
            raspberry_connection = websocket
            print("[+] Raspberry Pi client connected")
            
            try:
                while True:
                    data = await websocket.receive_text()
                    # Kiểm tra nếu là dữ liệu hình ảnh
                    if data.startswith("data:image"):
                        header, encoded = data.split(",", 1)
                        img_bytes = base64.b64decode(encoded)
                        img_np = np.frombuffer(img_bytes, dtype=np.uint8)
                        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                        
                        # Thực hiện dự đoán phân loại rác
                        boxes, class_probs = predict(img)
                        
                        # Xác định loại rác (hữu cơ/vô cơ) dựa trên dự đoán
                        waste_type, specific_waste, confidence = get_waste_category(boxes, class_probs)
                        
                        # Vẽ bounding box lên hình ảnh và hiển thị kết quả phân loại
                        img_with_boxes = draw_boxes(img.copy(), boxes, class_probs, waste_type)
                        
                        # Hiển thị ảnh trên server để theo dõi
                        cv2.imshow("Raspberry Pi Camera", img_with_boxes)
                        cv2.waitKey(1)
                        
                        # Nếu phát hiện rác và có độ tin cậy cao, gửi lệnh điều khiển đến Raspberry Pi
                        if waste_type and confidence > 0.5:
                            servo_angle = 30 if waste_type == "huu_co" else 150  # 30 độ cho hữu cơ, 150 độ cho vô cơ
                            
                            await websocket.send_text(json.dumps({
                                "waste_type": waste_type,
                                "specific_waste": specific_waste,
                                "confidence": float(confidence),
                                "action": "move_servo",
                                "angle": servo_angle
                            }))
                            
                            # Lưu dữ liệu phân loại rác vào database
                            save_waste_record(waste_type, specific_waste, float(confidence))
                            
                            # Gửi cập nhật đến dashboard
                            await broadcast_update({
                                "type": "waste_detection",
                                "waste_type": waste_type,
                                "specific_waste": specific_waste,
                                "confidence": float(confidence)
                            })
                    
                    # Nhận dữ liệu cảm biến từ Raspberry Pi
                    elif data.startswith("{"):
                        try:
                            sensor_data = json.loads(data)
                            distance = sensor_data.get("distance")
                            
                            # Lưu dữ liệu cảm biến vào database
                            if distance is not None:
                                save_sensor_data(distance)
                                
                                # Xử lý thông tin từ cảm biến siêu âm
                                if distance < 10:  # Khi có vật thể gần cảm biến
                                    print(f"Có vật thể gần cảm biến: {distance} cm")
                                    
                                # Gửi cập nhật đến dashboard
                                await broadcast_update({
                                    "type": "sensor_data",
                                    "distance": distance
                                })
                        except json.JSONDecodeError:
                            print("Lỗi giải mã JSON từ dữ liệu cảm biến:", data)
            
            except WebSocketDisconnect:
                print("[-] Raspberry Pi Disconnected (WebSocketDisconnect)")
                raspberry_connection = None
                cv2.destroyAllWindows()
            except Exception as e:
                print(f"[-] Raspberry Pi Disconnected: {type(e).__name__} - {str(e)}")
                raspberry_connection = None
                cv2.destroyAllWindows()
        
        else:  # Browser client
            print("[+] Web browser client connected")
            try:
                while True:
                    # Nhận dữ liệu từ browser (nếu có)
                    data = await websocket.receive_text()
                    try:
                        json_data = json.loads(data)
                        command = json_data.get("command")
                        
                        # Xử lý các lệnh từ giao diện web
                        if command == "manual_control" and raspberry_connection:
                            # Gửi lệnh điều khiển thủ công từ web đến Raspberry Pi
                            await raspberry_connection.send_text(data)
                    except json.JSONDecodeError:
                        print("Dữ liệu không hợp lệ từ trình duyệt:", data)
            except WebSocketDisconnect:
                print("[-] Browser client disconnected (WebSocketDisconnect)")
            except Exception as e:
                print(f"[-] Browser client disconnected: {type(e).__name__} - {str(e)}")
    
    except Exception as e:
        print(f"Lỗi kết nối WebSocket: {type(e).__name__} - {str(e)}")



def get_waste_category(boxes, class_probs, conf_threshold=0.5):
    """Xác định loại rác (hữu cơ/vô cơ) dựa trên kết quả dự đoán có độ tin cậy cao nhất"""
    max_conf = 0
    detected_class = None
    waste_type = None
    specific_waste = "unknown"  # Đặt giá trị mặc định
    
    for i, probs in enumerate(class_probs):
        class_id = np.argmax(probs)
        conf = probs[class_id]
        
        if conf > max_conf and conf > conf_threshold:
            max_conf = conf
            specific_waste = labels.get(class_id, "unknown")
            waste_type = waste_categories.get(specific_waste, "unknown")
            detected_class = class_id
    
    return waste_type, specific_waste, max_conf

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)