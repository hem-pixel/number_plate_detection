from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from ..database.base import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_number = Column(String(32), unique=True, index=True, nullable=False)
    vehicle_category = Column(String(32), default="OTHER_VEHICLE", nullable=False)  # COLLEGE_VEHICLE / OTHER_VEHICLE
    current_status = Column(String(32), default="OUTSIDE", nullable=False)  # INSIDE / OUTSIDE
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_sightings = Column(Integer, default=1, nullable=False)
    notes = Column(String(256), nullable=True)
