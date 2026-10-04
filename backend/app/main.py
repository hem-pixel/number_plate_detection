from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.database.connection import engine, SessionLocal
from backend.app.database.base import Base
from backend.app.api.routes import (
    health_router,
    recognition_router,
    cameras_router,
    vehicles_router,
    college_vehicles_router,
)
from backend.app.api.websocket import manager
from backend.app.services.camera_service import CameraService
from backend.app.services.college_vehicle_service import CollegeVehicleService

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Number Plate Recognition Backend...")
    # Ensure storage directories exist
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.VEHICLES_DIR.mkdir(parents=True, exist_ok=True)
    settings.PLATES_DIR.mkdir(parents=True, exist_ok=True)

    # Verify database connectivity and seed default records idempotently
    try:
        with SessionLocal() as db:
            cam_service = CameraService(db)
            cam_service.seed_default_camera()
            college_service = CollegeVehicleService(db)
            college_service.seed_default_college_vehicles()
        logger.info("Database connection verified; default camera and college fleet initialized.")
    except Exception as e:
        logger.error(f"Critical error connecting to database on startup: {e}")
        raise

    yield
    logger.info("Shutting down Number Plate Recognition Backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for local vehicle and plate images
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")

# Include API Routers (Mount on both /api/v1 and /api for full compatibility)
for api_prefix in [settings.API_V1_STR, "/api"]:
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(recognition_router, prefix=api_prefix)
    app.include_router(cameras_router, prefix=api_prefix)
    app.include_router(vehicles_router, prefix=api_prefix)
    app.include_router(college_vehicles_router, prefix=api_prefix)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open and accept optional client heartbeat/ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "docs": "http://localhost:8000/docs",
        "api_v1": f"http://localhost:8000{settings.API_V1_STR}",
        "status": "online",
    }
