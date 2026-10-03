from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.models.camera import Camera
from backend.app.schemas.camera import CameraCreate, CameraUpdate


class CameraService:
    def __init__(self, db: Session):
        self.db = db

    def get_cameras(self) -> List[Camera]:
        return self.db.query(Camera).all()

    def get_camera_by_code(self, camera_code: str) -> Optional[Camera]:
        return self.db.query(Camera).filter(Camera.camera_code == camera_code).first()

    def create_camera(self, camera_in: CameraCreate) -> Camera:
        camera = Camera(
            camera_code=camera_in.camera_code,
            camera_name=camera_in.camera_name,
            location=camera_in.location,
            source_type=camera_in.source_type,
            source=camera_in.source,
            status=camera_in.status,
        )
        self.db.add(camera)
        self.db.commit()
        self.db.refresh(camera)
        return camera

    def seed_default_camera(self) -> Camera:
        default_cam = self.get_camera_by_code("CAM-01")
        if not default_cam:
            default_cam = Camera(
                camera_code="CAM-01",
                camera_name="Default Webcam",
                location="Main Gate",
                source_type="WEBCAM",
                source="0",
                status="ACTIVE",
            )
            self.db.add(default_cam)
            self.db.commit()
            self.db.refresh(default_cam)
        return default_cam
