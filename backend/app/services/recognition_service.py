from datetime import datetime, date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.app.models.recognition import RecognitionEvent
from backend.app.models.college_vehicle import CollegeVehicle
from backend.app.models.vehicle import Vehicle
from backend.app.schemas.recognition import (
    RecognitionEventCreate,
    RecognitionStats,
    DashboardSummary,
    CategoryStats,
    RecognitionResponse,
)


class RecognitionService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def normalize_plate(plate: str) -> str:
        if not plate:
            return ""
        return plate.upper().replace(" ", "").replace("-", "").strip()

    def create_event(self, event_in: RecognitionEventCreate) -> RecognitionEvent:
        now = event_in.detected_at or datetime.utcnow()
        clean_plate = self.normalize_plate(event_in.plate_number)

        # 1. Check if the plate belongs to a registered College Vehicle
        college_vehicle = (
            self.db.query(CollegeVehicle)
            .filter(
                CollegeVehicle.vehicle_number == clean_plate,
                CollegeVehicle.status == "ACTIVE",
            )
            .first()
        )

        if college_vehicle:
            # === REGISTERED COLLEGE VEHICLE ===
            vehicle_category = "COLLEGE_VEHICLE"
            vehicle_name = college_vehicle.vehicle_name
            college_vehicle_id = college_vehicle.id

            # Determine movement (ENTRY / EXIT)
            if event_in.movement_type:
                movement_type = event_in.movement_type.upper().strip()
                current_status = "INSIDE" if movement_type == "ENTRY" else "OUTSIDE"
            else:
                # Toggle current state: if currently inside campus, next movement is EXIT
                if college_vehicle.current_status == "INSIDE":
                    movement_type = "EXIT"
                    current_status = "OUTSIDE"
                else:
                    movement_type = "ENTRY"
                    current_status = "INSIDE"

            # Update college vehicle record
            college_vehicle.current_status = current_status
            college_vehicle.last_movement_at = now

        else:
            # === OTHER / UNREGISTERED VEHICLE ===
            vehicle_category = "OTHER_VEHICLE"
            vehicle_name = None
            college_vehicle_id = None

            # Check or track in general vehicles table
            gen_vehicle = (
                self.db.query(Vehicle)
                .filter(Vehicle.plate_number == clean_plate)
                .first()
            )

            if gen_vehicle:
                if event_in.movement_type:
                    movement_type = event_in.movement_type.upper().strip()
                    current_status = "INSIDE" if movement_type == "ENTRY" else "OUTSIDE"
                else:
                    if gen_vehicle.current_status == "INSIDE":
                        movement_type = "EXIT"
                        current_status = "OUTSIDE"
                    else:
                        movement_type = "ENTRY"
                        current_status = "INSIDE"

                gen_vehicle.current_status = current_status
                gen_vehicle.last_seen_at = now
                gen_vehicle.total_sightings += 1
            else:
                movement_type = event_in.movement_type.upper().strip() if event_in.movement_type else "ENTRY"
                current_status = "INSIDE" if movement_type == "ENTRY" else "OUTSIDE"

                gen_vehicle = Vehicle(
                    plate_number=clean_plate,
                    vehicle_category="OTHER_VEHICLE",
                    current_status=current_status,
                    first_seen_at=now,
                    last_seen_at=now,
                    total_sightings=1,
                )
                self.db.add(gen_vehicle)

        entry_time = now if movement_type == "ENTRY" else None
        exit_time = now if movement_type == "EXIT" else None

        event = RecognitionEvent(
            plate_number=clean_plate,
            college_vehicle_id=college_vehicle_id,
            vehicle_category=vehicle_category,
            vehicle_name=vehicle_name,
            movement_type=movement_type,
            current_status=current_status,
            detected_at=now,
            entry_time=entry_time,
            exit_time=exit_time,
            yolo_confidence=event_in.yolo_confidence,
            ocr_confidence=event_in.ocr_confidence,
            vehicle_image_path=event_in.vehicle_image_path,
            plate_image_path=event_in.plate_image_path,
            camera_id=event_in.camera_id,
            frames_observed=event_in.frames_observed,
            status=event_in.status,
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_events(
        self,
        skip: int = 0,
        limit: int = 50,
        plate_number: Optional[str] = None,
        vehicle_category: Optional[str] = None,
        movement_type: Optional[str] = None,
        camera_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Tuple[List[RecognitionEvent], int]:
        query = self.db.query(RecognitionEvent)

        if plate_number:
            clean_search = self.normalize_plate(plate_number)
            query = query.filter(RecognitionEvent.plate_number.ilike(f"%{clean_search}%"))
        if vehicle_category:
            query = query.filter(RecognitionEvent.vehicle_category == vehicle_category.upper().strip())
        if movement_type:
            query = query.filter(RecognitionEvent.movement_type == movement_type.upper().strip())
        if camera_id:
            query = query.filter(RecognitionEvent.camera_id == camera_id)
        if from_date:
            query = query.filter(RecognitionEvent.detected_at >= from_date)
        if to_date:
            query = query.filter(RecognitionEvent.detected_at <= to_date)

        total = query.count()
        events = (
            query.order_by(desc(RecognitionEvent.detected_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return events, total

    def get_event_by_id(self, event_id: int) -> Optional[RecognitionEvent]:
        return (
            self.db.query(RecognitionEvent)
            .filter(RecognitionEvent.id == event_id)
            .first()
        )

    def get_dashboard_summary(self) -> DashboardSummary:
        # College Vehicles Stats
        total_college = (
            self.db.query(func.count(CollegeVehicle.id))
            .filter(CollegeVehicle.status == "ACTIVE")
            .scalar() or 0
        )
        inside_college = (
            self.db.query(func.count(CollegeVehicle.id))
            .filter(
                CollegeVehicle.status == "ACTIVE",
                CollegeVehicle.current_status == "INSIDE"
            )
            .scalar() or 0
        )
        outside_college = max(0, total_college - inside_college)

        # Other Vehicles Stats
        total_other = (
            self.db.query(func.count(Vehicle.id))
            .filter(Vehicle.vehicle_category == "OTHER_VEHICLE")
            .scalar() or 0
        )
        inside_other = (
            self.db.query(func.count(Vehicle.id))
            .filter(
                Vehicle.vehicle_category == "OTHER_VEHICLE",
                Vehicle.current_status == "INSIDE"
            )
            .scalar() or 0
        )
        outside_other = max(0, total_other - inside_other)

        # Total events today
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_events = (
            self.db.query(func.count(RecognitionEvent.id))
            .filter(RecognitionEvent.detected_at >= today_start)
            .scalar() or 0
        )

        # Recent 10 College Vehicle movements
        recent_college = (
            self.db.query(RecognitionEvent)
            .filter(RecognitionEvent.vehicle_category == "COLLEGE_VEHICLE")
            .order_by(desc(RecognitionEvent.detected_at))
            .limit(10)
            .all()
        )

        # Recent 10 Other Vehicle movements
        recent_other = (
            self.db.query(RecognitionEvent)
            .filter(RecognitionEvent.vehicle_category == "OTHER_VEHICLE")
            .order_by(desc(RecognitionEvent.detected_at))
            .limit(10)
            .all()
        )

        return DashboardSummary(
            college_vehicles=CategoryStats(
                total=total_college,
                inside=inside_college,
                outside=outside_college,
            ),
            other_vehicles=CategoryStats(
                total=total_other,
                inside=inside_other,
                outside=outside_other,
            ),
            total_events_today=today_events,
            recent_college_movements=[RecognitionResponse.model_validate(e) for e in recent_college],
            recent_other_movements=[RecognitionResponse.model_validate(e) for e in recent_other],
        )

    def get_stats(self) -> RecognitionStats:
        total = self.db.query(func.count(RecognitionEvent.id)).scalar() or 0

        today_start = datetime.combine(date.today(), datetime.min.time())
        today = (
            self.db.query(func.count(RecognitionEvent.id))
            .filter(RecognitionEvent.detected_at >= today_start)
            .scalar() or 0
        )

        latest = (
            self.db.query(RecognitionEvent.plate_number)
            .order_by(desc(RecognitionEvent.detected_at))
            .first()
        )
        latest_plate = latest[0] if latest else None

        return RecognitionStats(
            total_vehicles=total,
            today_vehicles=today,
            active_cameras=1,
            last_recognized_plate=latest_plate,
        )
