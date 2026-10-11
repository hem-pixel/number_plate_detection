from datetime import datetime
from typing import Optional, List
from enum import Enum
import re
from pydantic import BaseModel, Field, field_validator, ConfigDict, AliasChoices, computed_field


ALLOWED_VEHICLE_TYPES = ["BUS", "VAN", "CAR", "STAFF_VEHICLE", "OTHER"]


class VehicleTypeEnum(str, Enum):
    BUS = "BUS"
    VAN = "VAN"
    CAR = "CAR"
    STAFF_VEHICLE = "STAFF_VEHICLE"
    OTHER = "OTHER"


def normalize_plate(v: str) -> str:
    """Normalize vehicle plate number by removing spaces, dashes, and uppercasing."""
    if not v:
        return ""
    return v.upper().replace(" ", "").replace("-", "").strip()


class CollegeVehicleBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    vehicle_number: str = Field(
        ...,
        validation_alias=AliasChoices("vehicle_number", "registration_number"),
        description="Indian plate format, e.g. TN45BD7321"
    )
    vehicle_name: str = Field(..., description="Descriptive name, e.g. College Bus 01")
    vehicle_type: str = Field("BUS", description="BUS, VAN, CAR, STAFF_VEHICLE, OTHER")
    description: Optional[str] = Field(None, description="Optional vehicle details/notes")
    status: str = Field("ACTIVE", description="ACTIVE or INACTIVE")

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def validate_vehicle_type(cls, v: str) -> str:
        if isinstance(v, Enum):
            v = v.value
        clean = str(v).upper().strip()
        if clean not in ALLOWED_VEHICLE_TYPES:
            raise ValueError(f"Invalid vehicle type '{v}'. Allowed types: {', '.join(ALLOWED_VEHICLE_TYPES)}")
        return clean

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean = v.upper().strip()
        if clean not in ["ACTIVE", "INACTIVE"]:
            raise ValueError("Status must be either 'ACTIVE' or 'INACTIVE'")
        return clean

    @field_validator("vehicle_number", mode="before")
    @classmethod
    def validate_plate_number(cls, v: str) -> str:
        norm = normalize_plate(str(v))
        if not norm or len(norm) < 4 or len(norm) > 16:
            raise ValueError("Registration number must be between 4 and 16 alphanumeric characters.")
        # Match alphanumeric Indian vehicle registration plates
        if not re.match(r"^[A-Z0-9]+$", norm):
            raise ValueError("Registration number must contain only letters and digits.")
        return norm


class CollegeVehicleCreate(CollegeVehicleBase):
    pass


class CollegeVehicleUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    vehicle_number: Optional[str] = Field(None, validation_alias=AliasChoices("vehicle_number", "registration_number"))
    vehicle_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    current_status: Optional[str] = None

    @field_validator("vehicle_number")
    @classmethod
    def validate_plate_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        norm = v.upper().replace(" ", "").replace("-", "").strip()
        if not norm or len(norm) < 4 or len(norm) > 16:
            raise ValueError("Registration number must be between 4 and 16 alphanumeric characters.")
        if not re.match(r"^[A-Z0-9]+$", norm):
            raise ValueError("Registration number must contain only letters and digits.")
        return norm

    @field_validator("vehicle_type")
    @classmethod
    def validate_vehicle_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.upper().strip()
        if clean not in ALLOWED_VEHICLE_TYPES:
            raise ValueError(f"Invalid vehicle type '{v}'. Allowed types: {', '.join(ALLOWED_VEHICLE_TYPES)}")
        return clean

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.upper().strip()
        if clean not in ["ACTIVE", "INACTIVE"]:
            raise ValueError("Status must be either 'ACTIVE' or 'INACTIVE'")
        return clean

    @field_validator("current_status")
    @classmethod
    def validate_current_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.upper().strip()
        if clean not in ["INSIDE", "OUTSIDE"]:
            raise ValueError("Current status must be either 'INSIDE' or 'OUTSIDE'")
        return clean


class CollegeVehicleResponse(CollegeVehicleBase):
    id: int
    current_status: str
    last_movement_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def registration_number(self) -> str:
        return self.vehicle_number

    class Config:
        from_attributes = True


class CollegeVehicleHistoryResponse(BaseModel):
    vehicle: CollegeVehicleResponse
    total_entries: int = 0
    total_exits: int = 0
    history: List[dict] = []
