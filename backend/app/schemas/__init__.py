from backend.app.schemas.recognition import (
    RecognitionBase,
    RecognitionCreate,
    RecognitionResponse,
    RecognitionEventBase,
    RecognitionEventCreate,
    RecognitionEventResponse,
    RecognitionEventDetail,
    RecognitionStats,
    CategoryStats,
    DashboardSummary,
)
from backend.app.schemas.camera import (
    CameraBase,
    CameraCreate,
    CameraUpdate,
    CameraResponse,
)
from backend.app.schemas.college_vehicle import (
    CollegeVehicleBase,
    CollegeVehicleCreate,
    CollegeVehicleUpdate,
    CollegeVehicleResponse,
)

__all__ = [
    "RecognitionBase",
    "RecognitionCreate",
    "RecognitionResponse",
    "RecognitionEventBase",
    "RecognitionEventCreate",
    "RecognitionEventResponse",
    "RecognitionEventDetail",
    "RecognitionStats",
    "CategoryStats",
    "DashboardSummary",
    "CameraBase",
    "CameraCreate",
    "CameraUpdate",
    "CameraResponse",
    "CollegeVehicleBase",
    "CollegeVehicleCreate",
    "CollegeVehicleUpdate",
    "CollegeVehicleResponse",
]
