import base64
import json
import cv2
import numpy as np
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.inference import predict, draw_boxes, labels, waste_categories, get_waste_category
from app.dashboard import save_waste_record, save_sensor_data, broadcast_update
from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Store Raspberry Pi connection
raspberry_connection: WebSocket = None

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global raspberry_connection
    try:
        client_type = await websocket.receive_text()
        if client_type == "raspberry":
            raspberry_connection = websocket
            logging.info("[+] Raspberry Pi client connected")
            while True:
                data = await websocket.receive_text()
                # Image data
                if data.startswith("data:image"):
                    header, encoded = data.split(",", 1)
                    img_bytes = base64.b64decode(encoded)
                    img_np = np.frombuffer(img_bytes, dtype=np.uint8)
                    img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

                    boxes, class_probs = predict(img)
                    waste_type, specific, conf = get_waste_category(boxes, class_probs)
                    img_out = draw_boxes(img.copy(), boxes, class_probs, waste_type)

                    cv2.imshow("Camera", img_out)
                    cv2.waitKey(1)

                    if waste_type and conf > settings.CONF_THRESHOLD:
                        # Không gửi phản hồi về Pi nữa
                        save_waste_record(waste_type, specific, float(conf))
                        await broadcast_update({
                            "type": "waste_detection",
                            "waste_type": waste_type,
                            "specific_waste": specific,
                            "confidence": float(conf)
                        })
                # Nhận JSON detection từ Pi và lưu vào database
                elif data.startswith("{"):
                    try:
                        detection = json.loads(data)
                        # Nếu có đủ các trường cần thiết thì lưu vào database
                        if all(k in detection for k in ["waste_type", "waste_class", "max_conf", "processing_time", "num_detections", "img_b64_orig", "img_b64_result"]):
                            from app.dashboard import save_waste_detection
                            save_waste_detection(
                                detection["waste_type"],
                                detection["waste_class"],
                                detection["max_conf"],
                                detection["processing_time"],
                                detection["num_detections"],
                                detection["img_b64_orig"],
                                detection["img_b64_result"]
                            )
                            await broadcast_update({
                                "type": "waste_detection",
                                "waste_type": detection["waste_type"],
                                "specific_waste": detection["waste_class"],
                                "confidence": float(detection["max_conf"])
                            })
                        else:
                            # Xử lý như sensor data cũ
                            sensor = detection
                            dist = sensor.get("distance")
                            if dist is not None:
                                save_sensor_data(dist)
                                await broadcast_update({"type": "sensor_data", "distance": dist})
                    except json.JSONDecodeError:
                        logging.error("Invalid JSON from Raspberry Pi: %s", data)
        else:
            logging.info("[+] Browser client connected")
            while True:
                msg = await websocket.receive_text()
                try:
                    cmd = json.loads(msg).get("command")
                    if cmd == "manual_control" and raspberry_connection:
                        await raspberry_connection.send_text(msg)
                except json.JSONDecodeError:
                    logging.warning("Invalid JSON from browser: %s", msg)
    except WebSocketDisconnect:
        logging.info("Client disconnected")
        raspberry_connection = None
        cv2.destroyAllWindows()
    except Exception as e:
        logging.error("WebSocket error: %s", e)
        raspberry_connection = None
        cv2.destroyAllWindows()