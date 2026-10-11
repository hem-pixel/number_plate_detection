from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.schemas.camera import (
    CameraCreate,
    CameraResponse,
    SingleCameraConfig,
    SingleCameraConfigUpdate,
)
from backend.app.services.camera_service import CameraService
from backend.app.core.auth_deps import require_viewer_or_admin, require_admin
from backend.app.models.user import User

router = APIRouter(prefix="/cameras", tags=["Cameras"])
camera_router = APIRouter(prefix="/camera", tags=["Camera"])

# In-memory singleton configuration for Phase 3 Single Virtual Line Camera
_single_camera_config = SingleCameraConfig(
    camera_id="GATE_CAMERA_01",
    camera_name="Gate Camera 01 (Virtual Line)",
    frame_width=640,
    frame_height=480,
    line_position_percent=50.0,
    line_position_y=240.0,
    line_dead_zone=20,
    min_track_age=5,
    min_vertical_movement=15,
    event_cooldown_seconds=5.0,
    enabled=True,
)


def _get_config() -> SingleCameraConfig:
    global _single_camera_config
    # Ensure line_position_y is calculated dynamically
    calculated_y = float(_single_camera_config.frame_height) * (_single_camera_config.line_position_percent / 100.0)
    _single_camera_config.line_position_y = round(calculated_y, 2)
    return _single_camera_config


def _update_config(config_update: SingleCameraConfigUpdate) -> SingleCameraConfig:
    global _single_camera_config
    update_data = config_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            setattr(_single_camera_config, field, val)
    # Recalculate line_position_y dynamically
    calculated_y = float(_single_camera_config.frame_height) * (_single_camera_config.line_position_percent / 100.0)
    _single_camera_config.line_position_y = round(calculated_y, 2)
    return _single_camera_config


@router.get("/config", response_model=SingleCameraConfig)
def get_camera_config(current_user: User = Depends(require_viewer_or_admin)):
    return _get_config()


@router.put("/config", response_model=SingleCameraConfig)
def update_camera_config(
    config_in: SingleCameraConfigUpdate,
    current_user: User = Depends(require_admin),
):
    return _update_config(config_in)


@router.post("/line-config", response_model=SingleCameraConfig)
@router.put("/line-config", response_model=SingleCameraConfig)
def set_camera_line_config(
    payload: dict,
    current_user: User = Depends(require_admin),
):
    if "line_y_ratio" in payload:
        _single_camera_config.line_position_percent = float(payload["line_y_ratio"]) * 100.0
    elif "line_position_percent" in payload:
        _single_camera_config.line_position_percent = float(payload["line_position_percent"])
    return _get_config()


@camera_router.get("/config", response_model=SingleCameraConfig)
def get_single_camera_config(current_user: User = Depends(require_viewer_or_admin)):
    return _get_config()


@camera_router.put("/config", response_model=SingleCameraConfig)
def update_single_camera_config(
    config_in: SingleCameraConfigUpdate,
    current_user: User = Depends(require_admin),
):
    return _update_config(config_in)


@router.get("", response_model=List[CameraResponse])
def get_cameras(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_admin),
):
    service = CameraService(db)
    return service.get_cameras()


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(
    camera_in: CameraCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    service = CameraService(db)
    existing = service.get_camera_by_code(camera_in.camera_code)
    if existing:
        raise HTTPException(status_code=400, detail="Camera code already exists")
    return service.create_camera(camera_in)

