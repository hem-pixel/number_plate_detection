from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from ..database.base import Base


class RecognitionEvent(Base):
    __tablename__ = "recognition_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    plate_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    college_vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("college_vehicles.id", ondelete="SET NULL"), nullable=True)
    vehicle_category: Mapped[str] = mapped_column(String(32), default="OTHER_VEHICLE", index=True, nullable=False)  # COLLEGE_VEHICLE / OTHER_VEHICLE
    vehicle_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # e.g., 'College Bus 01'
    movement_type: Mapped[str] = mapped_column(String(32), default="ENTRY", index=True, nullable=False)  # ENTRY / EXIT
    current_status: Mapped[str] = mapped_column(String(32), default="INSIDE", nullable=False)  # INSIDE / OUTSIDE
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    entry_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    yolo_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    ocr_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    vehicle_image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    plate_image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    camera_id: Mapped[str] = mapped_column(String(64), default="CAM-01", index=True, nullable=False)
    frames_observed: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="VERIFIED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

