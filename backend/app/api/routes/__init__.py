from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.recognition import router as recognition_router
from backend.app.api.routes.cameras import router as cameras_router, camera_router
from backend.app.api.routes.vehicles import router as vehicles_router
from backend.app.api.routes.college_vehicles import router as college_vehicles_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.users import router as users_router

__all__ = [
    "health_router",
    "recognition_router",
    "cameras_router",
    "camera_router",
    "vehicles_router",
    "college_vehicles_router",
    "auth_router",
    "users_router",
]

