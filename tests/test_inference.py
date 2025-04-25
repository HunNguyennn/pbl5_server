# tests/test_inference.py

import numpy as np
from app.services.inference import predict, get_waste_category
from app.services.inference import labels

def test_predict_dummy():
    # Tạo ảnh đen 640x640
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    boxes, probs = predict(img, force=True)
    # Kỳ vọng trả về array
    assert isinstance(boxes, np.ndarray)
    assert isinstance(probs, np.ndarray)
    # Kiểm tra shape cơ bản: mỗi prob là vector độ dài 81 (85-4)
    assert probs.ndim == 2
    assert probs.shape[1] == len(labels)

def test_get_waste_category_empty():
    # Đầu vào trống => không phát hiện gì
    waste_type, specific, conf = get_waste_category(np.array([]), np.array([[]]))
    assert waste_type is None
    assert specific == 'unknown'
    assert conf == 0
