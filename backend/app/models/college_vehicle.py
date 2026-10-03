from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from ..database.base import Base


class CollegeVehicle(Base):
    __tablename__ = "college_vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_number = Column(String(32), unique=True, index=True, nullable=False)
    vehicle_name = Column(String(128), nullable=False)
    vehicle_type = Column(String(64), default="BUS", nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE / INACTIVE
    current_status = Column(String(32), default="OUTSIDE", nullable=False)  # INSIDE / OUTSIDE
    last_movement_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
