from fastapi import FastAPI
# from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.logger import init_logger
from app.core.config import settings
from app.api.websocket import router as ws_router
from app.dashboard import dashboard_router

# Initialize logging
init_logger()

app = FastAPI(
    title="Smart Trash Server",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# JSON health check chuyển sang "/health"
@app.get("/health", include_in_schema=False)
async def health_check():
    return {"message": "Smart Trash Server is running"}

# Serve static SPA từ thư mục build (giả sử bạn build front-end vào app/static)
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(ws_router)
app.include_router(dashboard_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)