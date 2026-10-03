from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database.connection import get_db
from backend.app.models.recognition import RecognitionEvent
from backend.app.schemas.recognition import RecognitionEventResponse

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("/{plate_number}/history", response_model=List[RecognitionEventResponse])
def get_vehicle_history(plate_number: str, db: Session = Depends(get_db)):
    events = (
        db.query(RecognitionEvent)
        .filter(RecognitionEvent.plate_number == plate_number.upper().strip())
        .order_by(desc(RecognitionEvent.detected_at))
        .all()
    )
    if not events:
        raise HTTPException(status_code=404, detail="No history found for vehicle plate")
    return events
