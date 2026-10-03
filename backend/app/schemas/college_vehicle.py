from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CollegeVehicleBase(BaseModel):
    vehicle_number: str = Field(..., description="Indian plate format, e.g. TN45BD7321")
    vehicle_name: str = Field(..., description="Descriptive name, e.g. College Bus 01")
    vehicle_type: str = Field("BUS", description="BUS, VAN, CAR, STAFF_BUS, etc.")
    status: str = Field("ACTIVE", description="ACTIVE or INACTIVE")


class CollegeVehicleCreate(CollegeVehicleBase):
    pass


class CollegeVehicleUpdate(BaseModel):
    vehicle_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    status: Optional[str] = None
    current_status: Optional[str] = None


class CollegeVehicleResponse(CollegeVehicleBase):
    id: int
    current_status: str
    last_movement_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
