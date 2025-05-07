import time
import numpy as np
import tensorflow as tf
import cv2
from app.core.config import settings

# Load labels and categories
labels = {0: 'AppleCore', 1: 'DryLeaves', 2: 'EggShell', 3: 'OrangePeel', 4: 'Paper', 5: 'PaperCup', 6: 'PlasticBag', 7: 'BananaPeel', 8: 'Cans', 9: 'PlasticBottle'}
waste_categories = {
    'AppleCore': 'huu_co', 'DryLeaves': 'huu_co', 'EggShell': 'huu_co',
    'OrangePeel': 'huu_co', 'Paper': 'vo_co', 'PaperCup': 'vo_co',
    'PlasticBag': 'vo_co', 'BananaPeel': 'huu_co', 'Cans': 'vo_co',
}

# Load TFLite model
_interpreter = tf.lite.Interpreter(model_path=settings.MODEL_PATH)
_interpreter.allocate_tensors()
_input_details = _interpreter.get_input_details()
_output_details = _interpreter.get_output_details()

_last_time = time.time()

def preprocess_image(img):
    img_r = cv2.resize(img, (640, 640))
    arr = img_r.astype(np.float32) / 255.0
    return np.expand_dims(arr, axis=0)


def predict(image, force=False):
    global _last_time
    now = time.time()
    if not force and (now - _last_time) < settings.PREDICTION_INTERVAL:
        return np.array([]), np.array([[]])
    _last_time = now

    inp = preprocess_image(image)
    _interpreter.set_tensor(_input_details[0]['index'], inp)
    _interpreter.invoke()
    out_raw = _interpreter.get_tensor(_output_details[0]['index'])
    # xác định số classes từ labels của bạn
    num_classes = len(labels)
    # mỗi detection có 4 box coords + num_classes scores
    num_outputs = num_classes + 4
    # reshape đầu ra vuông theo (n_detections, num_outputs)
    out = out_raw.reshape(-1, num_outputs)

    boxes, probs = out[:, :4], out[:, 4:]
    return boxes, probs


def get_waste_category(boxes, class_probs, conf_thr=None):
    # Nếu không có boxes hoặc class_probs trống => không phát hiện gì
    if boxes.size == 0 or class_probs.size == 0:
        return None, 'unknown', 0

    conf_thr = conf_thr or settings.CONF_THRESHOLD
    best_conf = 0
    waste, spec = None, 'unknown'
    for probs in class_probs:
        cid = np.argmax(probs)
        c = probs[cid]
        if c > best_conf and c > conf_thr:
            best_conf = c
            spec = labels[cid]
            waste = waste_categories.get(spec)
    return waste, spec, best_conf


def draw_boxes(image, boxes, class_probs, current=None, conf_thr=None):
    conf_thr = conf_thr or settings.CONF_THRESHOLD
    h, w, _ = image.shape
    if current:
        txt = 'HỮU CƠ' if current=='huu_co' else 'VÔ CƠ'
        cv2.putText(image, f'PHÂN LOẠI: {txt}', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),2)
    for i, b in enumerate(boxes):
        cid = np.argmax(class_probs[i]); c=class_probs[i][cid]
        if c>conf_thr:
            x1,y1,x2,y2 = (b * np.array([w,h,w,h])).astype(int)
            cat = labels.get(cid,'unknown')
            wt = waste_categories.get(cat,'unknown')
            color = (0,255,0) if wt=='huu_co' else (0,0,255)
            cv2.rectangle(image,(x1,y1),(x2,y2),color,2)
            cv2.putText(image,f"{cat} ({c:.2f})",(x1,y1-10),cv2.FONT_HERSHEY_SIMPLEX,0.5,color,2)
    return image