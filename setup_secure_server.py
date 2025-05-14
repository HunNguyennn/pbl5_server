import os
import subprocess
import sys
import platform
import socket

def check_mkcert_installed():
    """Kiểm tra xem mkcert đã được cài đặt chưa"""
    try:
        subprocess.run(["mkcert", "-version"], capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False

def install_mkcert():
    """Hướng dẫn cài đặt mkcert"""
    system = platform.system()
    print("mkcert chưa được cài đặt. Vui lòng cài đặt mkcert trước:")
    
    if system == "Windows":
        print("Windows: chạy 'choco install mkcert' (cần Chocolatey)")
        print("Hoặc tải mkcert từ https://github.com/FiloSottile/mkcert/releases")
    elif system == "Darwin":  # macOS
        print("macOS: chạy 'brew install mkcert' (cần Homebrew)")
    elif system == "Linux":
        print("Linux (Ubuntu/Debian): chạy 'sudo apt install mkcert'")
        print("Linux (Fedora): chạy 'sudo dnf install mkcert'")
    
    print("\nSau khi cài đặt, chạy lại script này.")
    sys.exit(1)

def generate_certificates():
    """Tạo SSL certificates bằng mkcert"""
    # Tạo thư mục certs nếu chưa tồn tại
    os.makedirs("certs", exist_ok=True)
    
    # Cài đặt CA root
    subprocess.run(["mkcert", "-install"])
    
    # Lấy hostname và IP local
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        print("Không thể lấy địa chỉ IP local, sử dụng 127.0.0.1 thay thế")
        local_ip = "127.0.0.1"
    
    # Tạo certificates
    print(f"Tạo certificates cho localhost, {hostname}, {local_ip}, và *.local...")
    subprocess.run([
        "mkcert",
        "-key-file", "certs/key.pem",
        "-cert-file", "certs/cert.pem",
        "localhost", 
        "127.0.0.1",
        local_ip,
        hostname,
        "*.local"
    ])
    
    print(f"Certificates đã được tạo tại thư mục 'certs/'")
    return "certs/cert.pem", "certs/key.pem"

def update_config_file():
    """Cập nhật file .env để sử dụng HTTPS"""
    env_content = ""
    try:
        with open(".env", "r") as f:
            env_content = f.read()
    except FileNotFoundError:
        print("Không tìm thấy file .env, tạo file mới")
        env_content = "HOST=127.0.0.1\nPORT=8000\n"
    
    # Thay đổi HOST thành 0.0.0.0
    if "HOST=127.0.0.1" in env_content:
        env_content = env_content.replace("HOST=127.0.0.1", "HOST=0.0.0.0")
        
    # Thêm các biến SSL nếu chưa có
    if "SSL_CERT_FILE" not in env_content:
        env_content += "\nSSL_CERT_FILE=certs/cert.pem"
    if "SSL_KEY_FILE" not in env_content:
        env_content += "\nSSL_KEY_FILE=certs/key.pem"
    if "USE_HTTPS" not in env_content:
        env_content += "\nUSE_HTTPS=true"
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("File .env đã được cập nhật với cấu hình HTTPS")

def update_main_file():
    """Cập nhật file main.py để sử dụng SSL và mDNS"""
    try:
        with open("app/main.py", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("Không tìm thấy file app/main.py, vui lòng kiểm tra đường dẫn")
        return
    
    # Tìm phần if __name__ == "__main__":
    if "if __name__ == \"__main__\":" in content:
        # Kiểm tra xem đã có mã cho SSL chưa
        if "ssl_keyfile" not in content:
            # Tìm vị trí của khối lệnh uvicorn.run
            run_index = content.find("uvicorn.run")
            end_index = content.find(")", run_index)
            
            if run_index != -1 and end_index != -1:
                # Lấy dòng gọi uvicorn
                run_line = content[run_index:end_index+1]
                
                # Tạo dòng mới với SSL
                new_run_line = (
                    "uvicorn.run(\"app.main:app\", host=host, port=port, "
                    "ssl_keyfile=settings.SSL_KEY_FILE if use_https else None, "
                    "ssl_certfile=settings.SSL_CERT_FILE if use_https else None, "
                    "reload=True)"
                )
                
                # Thay thế dòng cũ bằng dòng mới
                content = content.replace(run_line, new_run_line)
                
                with open("app/main.py", "w") as f:
                    f.write(content)
                
                print("File main.py đã được cập nhật để sử dụng SSL")
            else:
                print("Không thể tìm thấy chỗ để cập nhật file main.py")
        else:
            print("File main.py đã có cấu hình SSL, không cần cập nhật")
    else:
        print("Không tìm thấy phần 'if __name__ == \"__main__\":' trong file main.py")

def update_config_settings():
    """Cập nhật file config.py để thêm các cài đặt SSL"""
    config_file = "app/core/config.py"
    try:
        with open(config_file, "r") as f:
            content = f.read()
        
        # Kiểm tra xem đã có các biến SSL chưa
        if "SSL_CERT_FILE" not in content:
            # Tìm class Settings
            if "class Settings" in content:
                # Tìm vị trí cuối cùng của class Settings
                class_start = content.find("class Settings")
                class_end = content.find("settings =", class_start)
                
                if class_start != -1 and class_end != -1:
                    # Lấy nội dung của class
                    class_content = content[class_start:class_end]
                    
                    # Thêm các biến SSL
                    ssl_settings = """
    USE_HTTPS: bool = bool(os.getenv("USE_HTTPS", "false").lower() == "true")
    SSL_CERT_FILE: str = os.getenv("SSL_CERT_FILE", "certs/cert.pem")
    SSL_KEY_FILE: str = os.getenv("SSL_KEY_FILE", "certs/key.pem")
"""
                    # Thêm vào cuối class
                    updated_class = class_content + ssl_settings
                    
                    # Cập nhật file
                    content = content.replace(class_content, updated_class)
                    
                    with open(config_file, "w") as f:
                        f.write(content)
                    
                    print("File config.py đã được cập nhật với các biến SSL")
                else:
                    print("Không thể tìm thấy vị trí để cập nhật trong class Settings")
            else:
                print("Không tìm thấy class Settings trong file config.py")
        else:
            print("File config.py đã có các biến SSL, không cần cập nhật")
    except FileNotFoundError:
        print(f"Không tìm thấy file {config_file}")

def create_mdns_service():
    """Tạo file để khởi tạo mDNS service"""
    mdns_file = "app/core/mdns_service.py"
    
    mdns_content = """# app/core/mdns_service.py
from zeroconf import ServiceInfo, Zeroconf
import socket
import time
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class MDNSService:
    def __init__(self):
        self.zeroconf = None
        self.info = None
        self.hostname = socket.gethostname()
        
        try:
            # Lấy địa chỉ IP local
            self.local_ip = socket.gethostbyname(self.hostname)
        except socket.gaierror:
            logger.warning("Không thể lấy địa chỉ IP local, sử dụng 127.0.0.1")
            self.local_ip = "127.0.0.1"
    
    def register_service(self):
        # Đăng ký service mDNS
        try:
            port = settings.PORT
            
            # Khởi tạo service info
            self.info = ServiceInfo(
                "_http._tcp.local.",
                "SmartTrash._http._tcp.local.",
                addresses=[socket.inet_aton(self.local_ip)],
                port=port,
                properties={
                    "path": "/ws",
                    "https": "true" if settings.USE_HTTPS else "false"
                }
            )
            
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.info)
            
            logger.info(f"Đã đăng ký dịch vụ mDNS: SmartTrash._http._tcp.local. tại {self.local_ip}:{port}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi đăng ký service mDNS: {e}")
            return False
    
    def unregister_service(self):
        # Hủy đăng ký service khi tắt server
        if self.zeroconf and self.info:
            try:
                self.zeroconf.unregister_service(self.info)
                self.zeroconf.close()
                logger.info("Đã hủy đăng ký dịch vụ mDNS")
            except Exception as e:
                logger.error(f"Lỗi khi hủy đăng ký service mDNS: {e}")

# Singleton instance
mdns_service = MDNSService()
"""

    # Tạo file
    os.makedirs(os.path.dirname(mdns_file), exist_ok=True)
    with open(mdns_file, "w") as f:
        f.write(mdns_content)
    
    print(f"Đã tạo file {mdns_file}")

def update_main_for_mdns():
    """Cập nhật file main.py để sử dụng mDNS"""
    try:
        with open("app/main.py", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("Không tìm thấy file app/main.py, vui lòng kiểm tra đường dẫn")
        return
    
    # Kiểm tra xem đã import mDNS chưa
    if "mdns_service" not in content:
        # Tìm vị trí import
        import_section_end = content.find("app = FastAPI(")
        
        if import_section_end != -1:
            # Thêm import vào đầu file
            import_mdns = "from app.core.mdns_service import mdns_service\n"
            content = content[:import_section_end] + import_mdns + content[import_section_end:]
            
            # Tìm if __name__ == "__main__":
            main_section = content.find("if __name__ == \"__main__\":")
            
            if main_section != -1:
                # Tìm vị trí trước khi gọi uvicorn.run
                run_index = content.find("uvicorn.run", main_section)
                
                if run_index != -1:
                    # Thêm đăng ký mDNS
                    mdns_register = "\n    # Đăng ký service mDNS\n    mdns_service.register_service()\n\n"
                    content = content[:run_index] + mdns_register + content[run_index:]
                    
                    with open("app/main.py", "w") as f:
                        f.write(content)
                    
                    print("File main.py đã được cập nhật để sử dụng mDNS")
                else:
                    print("Không thể tìm vị trí để thêm đăng ký mDNS")
            else:
                print("Không tìm thấy phần 'if __name__ == \"__main__\":' trong file main.py")
        else:
            print("Không thể tìm vị trí để thêm import mDNS")
    else:
        print("File main.py đã có cấu hình mDNS, không cần cập nhật")

def create_raspberry_client():
    """Tạo file client mẫu cho Raspberry Pi"""
    client_file = "raspberry_client.py"
    
    client_content = """#!/usr/bin/env python3
# raspberry_client.py - Client WebSocket cho Raspberry Pi
import asyncio
import websockets
import json
import socket
import time
import ssl
import logging
import platform
from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RaspberryClient")

# Cấu hình mặc định
DEFAULT_SERVER = "localhost:8000"
ws_url = f"ws://{DEFAULT_SERVER}/ws"
use_ssl = False

def on_service_state_change(zeroconf, service_type, name, state_change):
    # Callback khi phát hiện service thông qua mDNS
    global ws_url, use_ssl
    
    if state_change is ServiceStateChange.Added and "SmartTrash" in name:
        info = zeroconf.get_service_info(service_type, name)
        if info:
            try:
                addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
                if addresses:
                    ip = addresses[0]
                    port = info.port
                    use_ssl = info.properties.get(b'https', b'false').decode('utf-8').lower() == 'true'
                    
                    protocol = "wss" if use_ssl else "ws"
                    ws_url = f"{protocol}://{ip}:{port}/ws"
                    
                    logger.info(f"Tìm thấy server SmartTrash: {ws_url}")
                    return True
            except Exception as e:
                logger.error(f"Lỗi khi xử lý service info: {e}")
    
    return False

def discover_server():
    # Tìm kiếm server SmartTrash thông qua mDNS
    logger.info("Bắt đầu tìm kiếm server SmartTrash...")
    zeroconf = Zeroconf()
    browser = ServiceBrowser(zeroconf, "_http._tcp.local.", handlers=[on_service_state_change])
    
    # Đợi tối đa 10 giây để tìm server
    for _ in range(10):
        time.sleep(1)
        if ws_url != f"ws://{DEFAULT_SERVER}/ws":
            # Đã tìm thấy server
            break
    
    zeroconf.close()
    logger.info(f"Kết thúc tìm kiếm. Sử dụng server: {ws_url}")

async def connect_websocket():
    # Kết nối tới WebSocket server
    while True:
        try:
            logger.info(f"Đang kết nối tới {ws_url}...")
            
            # Cấu hình SSL nếu cần
            ssl_context = None
            if use_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            async with websockets.connect(ws_url, ssl=ssl_context) as websocket:
                logger.info("Đã kết nối thành công!")
                
                # Gửi ping mỗi 30 giây để giữ kết nối
                ping_task = asyncio.create_task(send_ping(websocket))
                
                # Nhận dữ liệu
                while True:
                    try:
                        message = await websocket.recv()
                        await process_message(message)
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("Kết nối bị đóng")
                        break
                
                # Hủy task ping khi kết nối đóng
                ping_task.cancel()
                
        except Exception as e:
            logger.error(f"Lỗi kết nối: {e}")
        
        # Đợi 5 giây rồi thử kết nối lại
        logger.info("Đợi 5 giây và thử kết nối lại...")
        await asyncio.sleep(5)

async def send_ping(websocket):
    # Gửi ping định kỳ để giữ kết nối
    while True:
        try:
            await websocket.send("ping")
            logger.debug("Đã gửi ping")
        except Exception as e:
            logger.error(f"Lỗi khi gửi ping: {e}")
            break
        
        await asyncio.sleep(30)

async def process_message(message):
    # Xử lý dữ liệu nhận được từ server
    try:
        data = json.loads(message)
        logger.info(f"Nhận được dữ liệu: {data}")
        
        # Thêm code xử lý dữ liệu tại đây
        # Ví dụ: Kiểm tra nếu có bản ghi mới, xử lý và hiển thị kết quả
        
    except json.JSONDecodeError:
        if message != "pong":  # Bỏ qua pong từ server
            logger.warning(f"Không thể phân tích dữ liệu JSON: {message}")

async def send_detection(image_data, metadata=None):
    # Gửi ảnh phát hiện lên server
    try:
        async with websockets.connect(ws_url) as websocket:
            data = {
                "type": "detection",
                "image": image_data,
                "metadata": metadata or {}
            }
            await websocket.send(json.dumps(data))
            logger.info("Đã gửi dữ liệu phát hiện lên server")
    except Exception as e:
        logger.error(f"Lỗi khi gửi dữ liệu phát hiện: {e}")

async def main():
    # Hàm chính
    # Tìm server trước khi kết nối
    discover_server()
    
    # Kết nối tới WebSocket server
    await connect_websocket()

if __name__ == "__main__":
    try:
        # Đặt event loop policy cho Windows nếu cần
        if platform.system().lower() == "windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Chạy main
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Đã dừng ứng dụng")
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {e}")
"""

    with open(client_file, "w") as f:
        f.write(client_content)
    
    print(f"Đã tạo file client mẫu: {client_file}")

def create_requirements():
    """Tạo hoặc cập nhật file requirements.txt"""
    try:
        with open("requirements.txt", "r") as f:
            requirements = f.read()
    except FileNotFoundError:
        requirements = ""
    
    # Thêm các thư viện cần thiết nếu chưa có
    new_packages = ["zeroconf", "websockets"]
    for package in new_packages:
        if package not in requirements:
            requirements += f"\n{package}"
    
    with open("requirements.txt", "w") as f:
        f.write(requirements.strip() + "\n")
    
    print("Đã cập nhật file requirements.txt")

if __name__ == "__main__":
    # Kiểm tra mkcert
    if not check_mkcert_installed():
        install_mkcert()
    
    # Tạo certificates
    cert_file, key_file = generate_certificates()
    
    # Cập nhật các file cấu hình
    update_config_file()
    update_config_settings()
    update_main_file()
    
    # Thiết lập mDNS
    create_mdns_service()
    update_main_for_mdns()
    
    # Tạo client mẫu cho Raspberry Pi
    create_raspberry_client()
    
    # Cập nhật requirements
    create_requirements()
    
    print("\n=== Thiết lập hoàn tất ===")
    print("1. Chạy lại server để áp dụng các thay đổi:")
    print("   cd server && venv310/Scripts/Activate.ps1 && python -m app.main")
    print("\n2. Sao chép file 'raspberry_client.py' sang Raspberry Pi và cài đặt các gói phụ thuộc:")
    print("   pip install zeroconf websockets")
    print("\n3. Chạy client trên Raspberry Pi:")
    print("   python raspberry_client.py") 