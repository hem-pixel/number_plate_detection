from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.schemas.camera import CameraCreate, CameraResponse
from backend.app.services.camera_service import CameraService

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("", response_model=List[CameraResponse])
def get_cameras(db: Session = Depends(get_db)):
    service = CameraService(db)
    return service.get_cameras()


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(camera_in: CameraCreate, db: Session = Depends(get_db)):
    service = CameraService(db)
    existing = service.get_camera_by_code(camera_in.camera_code)
    if existing:
        raise HTTPException(status_code=400, detail="Camera code already exists")
    return service.create_camera(camera_in)
