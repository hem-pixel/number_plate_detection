from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from ..database.base import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    camera_code = Column(String(64), unique=True, index=True, nullable=False)
    camera_name = Column(String(128), nullable=False)
    location = Column(String(256), nullable=True)
    source_type = Column(String(32), default="WEBCAM", nullable=False)
    source = Column(String(256), default="0", nullable=False)
    status = Column(String(32), default="Active", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
