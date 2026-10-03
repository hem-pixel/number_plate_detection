from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from ..database.base import Base


class RecognitionEvent(Base):
    __tablename__ = "recognition_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_number = Column(String(32), index=True, nullable=False)
    college_vehicle_id = Column(Integer, ForeignKey("college_vehicles.id", ondelete="SET NULL"), nullable=True)
    vehicle_category = Column(String(32), default="OTHER_VEHICLE", index=True, nullable=False)  # COLLEGE_VEHICLE / OTHER_VEHICLE
    vehicle_name = Column(String(128), nullable=True)  # e.g., 'College Bus 01'
    movement_type = Column(String(32), default="ENTRY", index=True, nullable=False)  # ENTRY / EXIT
    current_status = Column(String(32), default="INSIDE", nullable=False)  # INSIDE / OUTSIDE
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    entry_time = Column(DateTime, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    yolo_confidence = Column(Float, nullable=False)
    ocr_confidence = Column(Float, nullable=False)
    vehicle_image_path = Column(String(512), nullable=True)
    plate_image_path = Column(String(512), nullable=True)
    camera_id = Column(String(64), default="CAM-01", index=True, nullable=False)
    frames_observed = Column(Integer, default=1, nullable=False)
    status = Column(String(32), default="VERIFIED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
