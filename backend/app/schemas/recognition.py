from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, model_validator, computed_field


class RecognitionBase(BaseModel):
    plate_number: str
    camera_id: str = "CAM-01"
    vehicle_category: Optional[str] = None  # Auto-detected if None
    movement_type: Optional[str] = None  # Auto-detected (ENTRY/EXIT) if None
    vehicle_name: Optional[str] = None


class RecognitionCreate(RecognitionBase):
    detected_at: Optional[datetime] = None
    yolo_confidence: float = Field(0.95, ge=0.0, le=1.0)
    ocr_confidence: float = Field(0.95, ge=0.0, le=1.0)
    vehicle_image_path: Optional[str] = None
    plate_image_path: Optional[str] = None
    frames_observed: int = 1
    status: str = "VERIFIED"

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map license_plate -> plate_number
            if "license_plate" in data and "plate_number" not in data:
                data["plate_number"] = data["license_plate"]
            # Map direction -> movement_type
            if "direction" in data and "movement_type" not in data:
                data["movement_type"] = data["direction"]
            # Map confidence -> yolo_confidence and ocr_confidence
            if "confidence" in data:
                conf = float(data["confidence"])
                if "yolo_confidence" not in data:
                    data["yolo_confidence"] = conf
                if "ocr_confidence" not in data:
                    data["ocr_confidence"] = conf
            if "camera_id" in data:
                data["camera_id"] = str(data["camera_id"])
            if "image_url" in data and "vehicle_image_path" not in data:
                data["vehicle_image_path"] = data["image_url"]
        return data


class RecognitionResponse(BaseModel):
    id: int
    plate_number: str
    college_vehicle_id: Optional[int] = None
    vehicle_category: str
    vehicle_name: Optional[str] = None
    movement_type: str
    current_status: str
    detected_at: datetime
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    yolo_confidence: float
    ocr_confidence: float
    vehicle_image_path: Optional[str] = None
    plate_image_path: Optional[str] = None
    camera_id: str
    frames_observed: int
    status: str
    created_at: datetime

    @computed_field
    @property
    def license_plate(self) -> str:
        return self.plate_number

    @computed_field
    @property
    def direction(self) -> str:
        return self.movement_type

    class Config:
        from_attributes = True


# Aliases for compatibility
RecognitionEventBase = RecognitionBase
RecognitionEventCreate = RecognitionCreate
RecognitionEventResponse = RecognitionResponse
RecognitionEventDetail = RecognitionResponse


class CategoryStats(BaseModel):
    total: int = 0
    inside: int = 0
    outside: int = 0


class DashboardSummary(BaseModel):
    college_vehicles: CategoryStats
    other_vehicles: CategoryStats
    total_events_today: int = 0
    today_entries: int = 0
    today_exits: int = 0
    other_vehicles_today: int = 0
    recent_college_movements: List[RecognitionResponse] = []
    recent_other_movements: List[RecognitionResponse] = []
    recent_movements: List[RecognitionResponse] = []


class RecognitionStats(BaseModel):
    total_vehicles: int
    today_vehicles: int
    active_cameras: int = 1
    last_recognized_plate: Optional[str] = None
