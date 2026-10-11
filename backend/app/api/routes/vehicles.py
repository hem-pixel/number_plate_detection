from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.recognition import RecognitionEvent
from backend.app.schemas.recognition import RecognitionEventResponse
from backend.app.core.auth_deps import require_viewer_or_admin
from backend.app.models.user import User

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("/{plate_number}/history", response_model=List[RecognitionEventResponse])
def get_vehicle_history(
    plate_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_admin),
):
    events = (
        db.query(RecognitionEvent)
        .filter(RecognitionEvent.plate_number == plate_number.upper().strip())
        .order_by(RecognitionEvent.detected_at.desc())
        .all()
    )
    if not events:
        raise HTTPException(status_code=404, detail="No history found for vehicle plate")
    return events
