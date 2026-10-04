from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from ..database.base import Base


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    camera_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    camera_name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="WEBCAM", nullable=False)
    source: Mapped[str] = mapped_column(String(256), default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

