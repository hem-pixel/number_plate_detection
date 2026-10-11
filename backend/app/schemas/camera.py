from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CameraBase(BaseModel):
    camera_code: str = Field(..., examples=["CAM-01"])
    camera_name: str = Field(..., examples=["Main Gate Camera"])
    location: Optional[str] = Field(None, examples=["Main Entry Gate"])
    source_type: str = Field("WEBCAM", examples=["WEBCAM"])
    source: str = Field("0", examples=["0"])
    status: str = Field("ACTIVE", examples=["ACTIVE"])


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    camera_name: Optional[str] = None
    location: Optional[str] = None
    source_type: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None


class CameraResponse(CameraBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SingleCameraConfig(BaseModel):
    camera_id: str = Field("GATE_CAMERA_01", examples=["GATE_CAMERA_01"])
    camera_name: str = Field("Main Gate Virtual Line Camera", examples=["Main Gate Virtual Line Camera"])
    frame_width: int = Field(640, examples=[640])
    frame_height: int = Field(480, examples=[480])
    line_position_percent: float = Field(50.0, ge=5.0, le=95.0, examples=[50.0])
    line_position_y: float = Field(240.0, examples=[240.0])
    line_dead_zone: int = Field(20, examples=[20])
    min_track_age: int = Field(5, examples=[5])
    min_vertical_movement: int = Field(15, examples=[15])
    event_cooldown_seconds: float = Field(5.0, examples=[5.0])
    enabled: bool = Field(True, examples=[True])


class SingleCameraConfigUpdate(BaseModel):
    camera_name: Optional[str] = None
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    line_position_percent: Optional[float] = Field(None, ge=5.0, le=95.0)
    line_dead_zone: Optional[int] = None
    min_track_age: Optional[int] = None
    min_vertical_movement: Optional[int] = None
    event_cooldown_seconds: Optional[float] = None
    enabled: Optional[bool] = None

