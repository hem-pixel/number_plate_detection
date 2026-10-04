from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from ..database.base import Base


class CollegeVehicle(Base):
    __tablename__ = "college_vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    vehicle_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    vehicle_name: Mapped[str] = mapped_column(String(128), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(64), default="BUS", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)  # ACTIVE / INACTIVE
    current_status: Mapped[str] = mapped_column(String(32), default="OUTSIDE", nullable=False)  # INSIDE / OUTSIDE
    last_movement_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

