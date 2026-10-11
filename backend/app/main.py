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
    camera_router,
    vehicles_router,
    college_vehicles_router,
    auth_router,
    users_router,
)

from backend.app.api.websocket import manager
from backend.app.services.camera_service import CameraService
from backend.app.services.college_vehicle_service import CollegeVehicleService
from backend.app.services.user_service import UserService
from backend.app.core.security import decode_token, is_token_revoked

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
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(recognition_router, prefix=api_prefix)
    app.include_router(cameras_router, prefix=api_prefix)
    app.include_router(camera_router, prefix=api_prefix)
    app.include_router(vehicles_router, prefix=api_prefix)
    app.include_router(college_vehicles_router, prefix=api_prefix)



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Authenticate WebSocket connection via short-lived JWT token query param or cookie
    token = websocket.query_params.get("token") or websocket.cookies.get("access_token")
    if not token:
        logger.warning("WebSocket rejection: missing authentication token.")
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        logger.warning("WebSocket rejection: invalid or expired token.")
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        logger.warning("WebSocket rejection: revoked token.")
        await websocket.close(code=1008, reason="Revoked token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008, reason="Invalid user subject")
        return

    with SessionLocal() as db:
        user_svc = UserService(db)
        user = user_svc.get_by_id(int(user_id)) if str(user_id).isdigit() else None
        if not user or not user.is_active:
            logger.warning(f"WebSocket rejection: user {user_id} inactive or non-existent.")
            await websocket.close(code=1008, reason="User account is inactive or not found")
            return

    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open and accept optional client heartbeat/ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                try:
                    import json
                    msg = json.loads(data)
                    if isinstance(msg, dict) and msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except Exception:
                    pass
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
