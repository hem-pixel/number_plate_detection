from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from ..database.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    plate_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    vehicle_category: Mapped[str] = mapped_column(String(32), default="OTHER_VEHICLE", nullable=False)  # COLLEGE_VEHICLE / OTHER_VEHICLE
    current_status: Mapped[str] = mapped_column(String(32), default="OUTSIDE", nullable=False)  # INSIDE / OUTSIDE
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    total_sightings: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

