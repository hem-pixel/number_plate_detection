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
