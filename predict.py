import tensorflow as tf
import cv2
import numpy as np
import time

# Đường dẫn tới model .tflite
MODEL_PATH = 'yolov8n_dynamic.tflite'

# Nhãn phân loại rác
labels = {
    0: 'bananapeel',
    1: 'bottlescans',
    2: 'eggsell',
    3: 'paper',
    4: 'plasticbag'
}

# Phân loại rác thành hữu cơ và vô cơ
waste_categories = {
    'bananapeel': 'huu_co',  # Vỏ chuối - rác hữu cơ
    'bottlescans': 'vo_co',  # Chai lon - rác vô cơ
    'eggsell': 'huu_co',     # Vỏ trứng - rác hữu cơ
    'paper': 'vo_co',        # Giấy - rác vô cơ
    'plasticbag': 'vo_co'    # Túi nhựa - rác vô cơ
}

# Biến toàn cục để theo dõi thời gian dự đoán
last_prediction_time = time.time()
prediction_interval = 1.0  # Thời gian giữa các lần dự đoán (giây)

# Load model .tflite
try:
    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    # Lấy thông tin đầu vào và đầu ra
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    print(f"Model loaded successfully. Input shape: {input_details[0]['shape']}")
    print(f"Output details: {output_details[0]['shape']}")
except Exception as e:
    print(f"Error loading model: {e}")
    # Tạo một interpreter giả nếu không thể tải model (để tránh crash khi chạy ứng dụng)
    class DummyInterpreter:
        def set_tensor(self, *args): pass
        def invoke(self): pass
        def get_tensor(self, *args): return np.zeros((1, 20, 85))
    
    interpreter = DummyInterpreter()
    input_details = [{'index': 0, 'shape': [1, 640, 640, 3]}]
    output_details = [{'index': 0, 'shape': [1, 20, 85]}]
    print("Using dummy interpreter due to model loading failure")

# Hàm chuẩn hóa ảnh
def preprocess_image(image):
    # Resize ảnh về kích thước 640x640
    image_resized = cv2.resize(image, (640, 640))
    # Chuyển đổi sang float32 và normalize [0, 1]
    image_normalized = image_resized.astype(np.float32) / 255.0
    # Thêm batch dimension (1, 640, 640, 3)
    image_input = np.expand_dims(image_normalized, axis=0)
    return image_input

# Hàm chạy dự đoán
def predict(image, force=False):
    global last_prediction_time
    
    # Kiểm tra khoảng thời gian giữa các lần dự đoán (để tránh dự đoán quá thường xuyên)
    current_time = time.time()
    if not force and (current_time - last_prediction_time) < prediction_interval:
        # Trả về kết quả rỗng nếu chưa đến thời gian dự đoán tiếp theo
        return np.array([]), np.array([[]])
    
    # Cập nhật thời gian dự đoán gần nhất
    last_prediction_time = current_time
    
    try:
        # Chuẩn bị ảnh đầu vào
        image_input = preprocess_image(image)
        
        # Thực hiện dự đoán
        interpreter.set_tensor(input_details[0]['index'], image_input)
        interpreter.invoke()

        # Lấy kết quả đầu ra (bounding box và class scores)
        output_data = interpreter.get_tensor(output_details[0]['index'])

        # Thông tin về bounding boxes và các lớp
        boxes = output_data[0][:, :4]  # Lấy tọa độ bounding box
        class_probs = output_data[0][:, 4:]  # Lấy xác suất phân loại
        
        return boxes, class_probs
    except Exception as e:
        print(f"Prediction error: {e}")
        return np.array([]), np.array([[]])

# Hàm lọc các dự đoán có độ tin cậy cao
def filter_predictions(boxes, class_probs, conf_threshold=0.5):
    filtered_boxes = []
    filtered_probs = []
    filtered_classes = []
    
    for i, probs in enumerate(class_probs):
        class_id = np.argmax(probs)
        conf = probs[class_id]
        
        if conf > conf_threshold:
            filtered_boxes.append(boxes[i])
            filtered_probs.append(conf)
            filtered_classes.append(class_id)
    
    return np.array(filtered_boxes), np.array(filtered_probs), np.array(filtered_classes)

# Hàm vẽ bounding box lên ảnh và hiển thị kết quả phân loại
def draw_boxes(image, boxes, class_probs, current_waste_type=None, conf_threshold=0.5):
    result_image = image.copy()
    
    # Vẽ thông tin phân loại chung ở góc trên cùng bên trái
    if current_waste_type:
        waste_type_text = "HỮU CƠ" if current_waste_type == "huu_co" else "VÔ CƠ"
        cv2.putText(result_image, f"PHAN LOAI: {waste_type_text}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    for i, box in enumerate(boxes):
        # Xác suất của mỗi lớp
        class_id = np.argmax(class_probs[i])  # Lớp có xác suất cao nhất
        prob = class_probs[i][class_id]  # Xác suất của lớp đó

        if prob > conf_threshold:  # Chỉ vẽ nếu xác suất cao hơn ngưỡng
            # Chuyển tọa độ bounding box từ 640x640 về kích thước gốc
            h, w, _ = image.shape
            x1, y1, x2, y2 = box * np.array([w, h, w, h])

            # Kiểm tra nếu class_id có trong labels
            if class_id in labels:
                specific_waste = labels[class_id]
                waste_type = waste_categories.get(specific_waste, "unknown")
                
                # Chọn màu dựa trên loại rác
                color = (0, 255, 0) if waste_type == "huu_co" else (0, 0, 255)  # xanh lá cho hữu cơ, đỏ cho vô cơ
                
                # Vẽ bounding box
                cv2.rectangle(result_image, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                
                # Hiển thị nhãn và xác suất
                category_text = "HỮU CƠ" if waste_type == "huu_co" else "VÔ CƠ"
                label_text = f"{specific_waste} - {category_text} ({prob:.2f})"
                cv2.putText(result_image, label_text, 
                            (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            else:
                label = 'Unknown'  # Nếu class_id không hợp lệ, gán nhãn 'Unknown'
                cv2.rectangle(result_image, (int(x1), int(y1)), (int(x2), int(y2)), (128, 128, 128), 2)
                cv2.putText(result_image, f"{label} ({prob:.2f})", (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 2)

    return result_image

# Chỉ chạy đoạn mã này khi gọi trực tiếp (để kiểm tra model)
if __name__ == "__main__":
    # Mở webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Không thể mở webcam. Kiểm tra kết nối camera.")
    else:
        print("Đã kết nối với webcam thành công.")
        
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Không thể đọc frame từ webcam.")
                break

            # Dự đoán với model (force=True để đảm bảo luôn dự đoán khi chạy file này)
            boxes, class_probs = predict(frame, force=True)
            
            # Xác định loại rác phát hiện được
            waste_type = None
            specific_waste = None
            max_conf = 0
            
            for i, probs in enumerate(class_probs):
                class_id = np.argmax(probs)
                conf = probs[class_id]
                
                if conf > 0.5 and class_id in labels and conf > max_conf:
                    max_conf = conf
                    specific_waste = labels[class_id]
                    waste_type = waste_categories.get(specific_waste, "unknown")
            
            # Hiển thị thông tin phân loại
            if waste_type:
                print(f"Phát hiện: {specific_waste} - {waste_type} ({max_conf:.2f})")
            
            # Vẽ bounding box lên hình
            frame_with_boxes = draw_boxes(frame, boxes, class_probs, waste_type)

            # Hiển thị webcam với bounding boxes
            cv2.imshow("Waste Detection", frame_with_boxes)

            # Nếu nhấn 'q' thì thoát
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print(f"Error in main loop: {e}")
    finally:
        # Giải phóng tài nguyên
        cap.release()
        cv2.destroyAllWindows()
        print("Test completed.")