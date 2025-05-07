from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import base64, cv2, numpy as np

from app.core.logger import init_logger
from app.core.config import settings
from app.api.websocket import router as ws_router
from app.dashboard import dashboard_router
from app.services.inference import predict, get_waste_category

templates = Jinja2Templates(directory="app/templates")

# Initialize logging
init_logger()

app = FastAPI(
    title="Smart Trash Server",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health", include_in_schema=False)
async def health_check():
    return {"message": "Smart Trash Server is running"}

# Nhận ảnh từ client, decode và chạy model
@app.post("/upload")
async def upload_image(req: Request):
    payload = await req.json()
    img_b64 = payload.get("image")
    if not img_b64 or not img_b64.startswith("data:image"):
        return {"error": "Invalid image"}, 400

    # decode base64 -> numpy array -> BGR image
    header, data = img_b64.split(",", 1)
    img_bytes = base64.b64decode(data)
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    # chạy inference
    boxes, probs = predict(img, force=True)
    waste_type, specific, conf = get_waste_category(boxes, probs)

    return {
        "waste_type": waste_type,
        "specific_waste": specific,
        "confidence": conf
    }

# Serve static files (JS/CSS) và trang index/dashboard qua Jinja
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 1) WebSocket-only router (chỉ đường dẫn ws/*)
app.include_router(ws_router, prefix="/ws")


# 2) Dashboard: HTML tại /dashboard và API tại /api
app.include_router(dashboard_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)