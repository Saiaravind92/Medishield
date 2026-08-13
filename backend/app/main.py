import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.routes import cases, websocket, report

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MediShield AI Multi-Agent Health Insurance Claims Ingestion & Processing Platform",
    version="1.0.0"
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static storage & dataset directories
app.mount("/storage", StaticFiles(directory=settings.STORAGE_DIR), name="storage")
if os.path.exists(settings.DATASET_DIR):
    app.mount("/dataset", StaticFiles(directory=settings.DATASET_DIR), name="dataset")

frontend_dir = os.path.join(settings.BASE_DIR, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Include Routers
app.include_router(cases.router, prefix=settings.API_V1_STR)
app.include_router(report.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router)

@app.get("/")
@app.get("/ui")
def serve_ui():
    ui_path = os.path.join(settings.BASE_DIR, "frontend", "index.html")
    if os.path.exists(ui_path):
        return FileResponse(ui_path)
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
