from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.schemas.recognition import (
    RecognitionEventCreate,
    RecognitionEventResponse,
    RecognitionEventDetail,
    RecognitionStats,
    DashboardSummary,
)
from backend.app.services.recognition_service import RecognitionService
from backend.app.api.websocket import manager
from backend.app.core.auth_deps import require_viewer_or_admin, verify_m2m_or_user_auth
from backend.app.models.user import User

router = APIRouter(prefix="/recognitions", tags=["Recognitions"])


@router.get("", response_model=List[RecognitionEventResponse])
def get_recognitions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    plate_number: Optional[str] = None,
    search: Optional[str] = None,
    vehicle_category: Optional[str] = Query(None, description="COLLEGE_VEHICLE or OTHER_VEHICLE"),
    movement_type: Optional[str] = Query(None, description="ENTRY or EXIT"),
    camera_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_admin),
):
    service = RecognitionService(db)
    effective_plate = plate_number or search
    events, _ = service.get_events(
        skip=skip,
        limit=limit,
        plate_number=effective_plate,
        vehicle_category=vehicle_category,
        movement_type=movement_type,
        camera_id=camera_id,
        from_date=from_date,
        to_date=to_date,
    )
    return events


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_admin),
):
    service = RecognitionService(db)
    return service.get_dashboard_summary()


@router.get("/stats", response_model=RecognitionStats)
def get_recognition_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_admin),
):
    service = RecognitionService(db)
    return service.get_stats()


@router.get("/live", response_model=List[RecognitionEventResponse])
def get_live_recognitions(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_admin),
):
    service = RecognitionService(db)
    events, _ = service.get_events(skip=0, limit=limit)
    return events


@router.get("/{event_id}", response_model=RecognitionEventDetail)
def get_recognition_by_id(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer_or_admin),
):
    service = RecognitionService(db)
    event = service.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Recognition event not found")
    return event


@router.post("", response_model=RecognitionEventResponse, status_code=status.HTTP_201_CREATED)
async def create_recognition(
    event_in: RecognitionEventCreate,
    db: Session = Depends(get_db),
    _auth=Depends(verify_m2m_or_user_auth),
):
    service = RecognitionService(db)
    event = service.create_event(event_in)

    timestamp_str = event.detected_at.isoformat() if event.detected_at else datetime.utcnow().isoformat()
    event_data = {
        "id": event.id,
        "plate_number": event.plate_number,
        "college_vehicle_id": event.college_vehicle_id,
        "vehicle_category": event.vehicle_category,
        "vehicle_name": event.vehicle_name,
        "movement_type": event.movement_type,
        "current_status": event.current_status,
        "detected_at": timestamp_str,
        "entry_time": event.entry_time.isoformat() if event.entry_time else None,
        "exit_time": event.exit_time.isoformat() if event.exit_time else None,
        "yolo_confidence": event.yolo_confidence,
        "ocr_confidence": event.ocr_confidence,
        "vehicle_image_path": event.vehicle_image_path,
        "plate_image_path": event.plate_image_path,
        "camera_id": event.camera_id,
        "status": event.status,
    }

    # Broadcast event via WebSocket to live clients with Phase 3 VEHICLE_MOVEMENT format
    await manager.broadcast({
        "type": "VEHICLE_MOVEMENT",
        "plate_number": event.plate_number,
        "vehicle_category": event.vehicle_category,
        "vehicle_name": event.vehicle_name,
        "movement_type": event.movement_type,
        "current_status": event.current_status,
        "camera_id": event.camera_id,
        "timestamp": timestamp_str,
        "yolo_confidence": event.yolo_confidence,
        "ocr_confidence": event.ocr_confidence,
        "vehicle_image_path": event.vehicle_image_path,
        "plate_image_path": event.plate_image_path,
        "data": event_data,
    })

    return event

