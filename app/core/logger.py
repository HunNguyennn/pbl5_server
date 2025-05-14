import logging
import os
import time
from logging.handlers import RotatingFileHandler
from app.core.config import settings

def init_logger():
    """Khởi tạo logger cho ứng dụng với định dạng và handlers phù hợp"""
    # Tạo thư mục logs nếu chưa tồn tại
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Tạo formatter với định dạng chi tiết
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
    )
    
    # Tạo file handler cho log file chính
    log_file = os.path.join(logs_dir, f"app_{time.strftime('%Y%m%d')}.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Tạo file handler riêng cho lỗi
    error_log_file = os.path.join(logs_dir, f"error_{time.strftime('%Y%m%d')}.log")
    error_file_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_file_handler.setFormatter(formatter)
    error_file_handler.setLevel(logging.ERROR)
    
    # Tạo console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Thiết lập root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Xóa handlers cũ nếu có
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    # Thêm handlers mới
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_file_handler)
    root_logger.addHandler(console_handler)
    
    # Ghi log khởi động
    logging.info("="*50)
    logging.info(f"Logger initialized with level: {settings.LOG_LEVEL}")
    logging.info(f"Main log file: {log_file}")
    logging.info(f"Error log file: {error_log_file}")
    logging.info("="*50)
    
    return root_logger