from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import nullslast, nullsfirst, desc, asc, func

from backend.app.models.college_vehicle import CollegeVehicle
from backend.app.models.recognition import RecognitionEvent
from backend.app.schemas.college_vehicle import CollegeVehicleCreate, CollegeVehicleUpdate


class CollegeVehicleService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def normalize_plate(plate: str) -> str:
        if not plate:
            return ""
        return plate.upper().replace(" ", "").replace("-", "").strip()

    def get_vehicle_by_plate(self, plate_number: str) -> Optional[CollegeVehicle]:
        normalized = self.normalize_plate(plate_number)
        return (
            self.db.query(CollegeVehicle)
            .filter(CollegeVehicle.vehicle_number == normalized)
            .first()
        )

    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[CollegeVehicle]:
        return (
            self.db.query(CollegeVehicle)
            .filter(CollegeVehicle.id == vehicle_id)
            .first()
        )

    def list_college_vehicles(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        status: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        current_status: Optional[str] = None,
        sort_by: str = "last_movement",
        sort_order: str = "desc",
    ) -> Tuple[List[CollegeVehicle], int]:
        query = self.db.query(CollegeVehicle)

        if search:
            clean_search = self.normalize_plate(search)
            raw_search = search.strip()
            query = query.filter(
                (CollegeVehicle.vehicle_number.ilike(f"%{clean_search}%")) |
                (CollegeVehicle.vehicle_name.ilike(f"%{raw_search}%"))
            )
        if status:
            query = query.filter(CollegeVehicle.status == status.upper().strip())
        if vehicle_type:
            query = query.filter(CollegeVehicle.vehicle_type == vehicle_type.upper().strip())
        if current_status:
            query = query.filter(CollegeVehicle.current_status == current_status.upper().strip())

        total = query.count()

        # Sorting logic
        order_fn = desc if sort_order.lower() == "desc" else asc
        if sort_by == "last_movement":
            if sort_order.lower() == "desc":
                query = query.order_by(nullslast(desc(CollegeVehicle.last_movement_at)), desc(CollegeVehicle.created_at))
            else:
                query = query.order_by(nullsfirst(asc(CollegeVehicle.last_movement_at)), asc(CollegeVehicle.created_at))
        elif sort_by == "vehicle_number":
            query = query.order_by(order_fn(CollegeVehicle.vehicle_number))
        elif sort_by == "vehicle_name":
            query = query.order_by(order_fn(CollegeVehicle.vehicle_name))
        elif sort_by == "created":
            query = query.order_by(order_fn(CollegeVehicle.created_at))
        else:
            query = query.order_by(nullslast(desc(CollegeVehicle.last_movement_at)), desc(CollegeVehicle.created_at))

        vehicles = query.offset(skip).limit(limit).all()
        return vehicles, total

    def create_college_vehicle(self, vehicle_in: CollegeVehicleCreate) -> CollegeVehicle:
        normalized_number = self.normalize_plate(vehicle_in.vehicle_number)
        existing = self.get_vehicle_by_plate(normalized_number)
        if existing:
            raise ValueError(f"College vehicle with plate {normalized_number} already exists.")

        vehicle = CollegeVehicle(
            vehicle_number=normalized_number,
            vehicle_name=vehicle_in.vehicle_name.strip(),
            vehicle_type=vehicle_in.vehicle_type.upper().strip(),
            description=vehicle_in.description.strip() if vehicle_in.description else None,
            status=vehicle_in.status.upper().strip(),
            current_status="OUTSIDE",
        )
        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def update_college_vehicle(
        self,
        vehicle_id: int,
        vehicle_in: CollegeVehicleUpdate,
    ) -> Optional[CollegeVehicle]:
        vehicle = self.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return None

        if vehicle_in.vehicle_number is not None:
            norm_num = self.normalize_plate(vehicle_in.vehicle_number)
            if norm_num != vehicle.vehicle_number:
                existing = self.get_vehicle_by_plate(norm_num)
                if existing and existing.id != vehicle_id:
                    raise ValueError(f"Plate number {norm_num} is already assigned to another vehicle.")
                vehicle.vehicle_number = norm_num

        if vehicle_in.vehicle_name is not None:
            vehicle.vehicle_name = vehicle_in.vehicle_name.strip()
        if vehicle_in.vehicle_type is not None:
            vehicle.vehicle_type = vehicle_in.vehicle_type.upper().strip()
        if vehicle_in.description is not None:
            vehicle.description = vehicle_in.description.strip() if vehicle_in.description else None
        if vehicle_in.status is not None:
            vehicle.status = vehicle_in.status.upper().strip()
        if vehicle_in.current_status is not None:
            vehicle.current_status = vehicle_in.current_status.upper().strip()

        vehicle.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def delete_college_vehicle(self, vehicle_id: int, hard_delete: bool = False) -> bool:
        vehicle = self.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return False

        if hard_delete:
            # Check if historical recognition events exist for this vehicle
            event_count = (
                self.db.query(func.count(RecognitionEvent.id))
                .filter(
                    (RecognitionEvent.college_vehicle_id == vehicle_id) |
                    (RecognitionEvent.plate_number == vehicle.vehicle_number)
                )
                .scalar() or 0
            )
            if event_count > 0:
                raise ValueError(
                    f"Cannot permanently delete vehicle {vehicle.vehicle_number}. "
                    f"It has {event_count} recognition event(s) in history. "
                    "Please deactivate the vehicle to preserve historical logs."
                )
            self.db.delete(vehicle)
        else:
            # Safe soft-delete: set status to INACTIVE
            vehicle.status = "INACTIVE"
            vehicle.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        return True

    def get_vehicle_history(
        self,
        vehicle_id: int,
        limit: int = 50,
    ) -> Dict[str, Any]:
        vehicle = self.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise ValueError(f"College vehicle with ID {vehicle_id} not found")

        events_query = (
            self.db.query(RecognitionEvent)
            .filter(
                (RecognitionEvent.college_vehicle_id == vehicle_id) |
                (RecognitionEvent.plate_number == vehicle.vehicle_number)
            )
        )

        total_entries = (
            events_query.filter(RecognitionEvent.movement_type == "ENTRY")
            .count()
        )
        total_exits = (
            events_query.filter(RecognitionEvent.movement_type == "EXIT")
            .count()
        )

        history_events = (
            events_query.order_by(RecognitionEvent.detected_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "vehicle": vehicle,
            "total_entries": total_entries,
            "total_exits": total_exits,
            "history": [
                {
                    "id": ev.id,
                    "plate_number": ev.plate_number,
                    "movement_type": ev.movement_type,
                    "current_status": ev.current_status,
                    "detected_at": ev.detected_at,
                    "camera_id": ev.camera_id,
                    "yolo_confidence": ev.yolo_confidence,
                    "ocr_confidence": ev.ocr_confidence,
                    "vehicle_image_path": ev.vehicle_image_path,
                    "plate_image_path": ev.plate_image_path,
                    "status": ev.status,
                }
                for ev in history_events
            ],
        }

    def seed_default_college_vehicles(self):
        """Seeds predefined college vehicles if empty, particularly the demo buses."""
        defaults = [
            {"vehicle_number": "TN45BD7321", "vehicle_name": "College Bus 01", "vehicle_type": "BUS", "description": "Route 1: Central Campus Express"},
            {"vehicle_number": "TN45BD8456", "vehicle_name": "College Bus 02", "vehicle_type": "BUS", "description": "Route 2: North Campus Transit"},
            {"vehicle_number": "TN45BD9999", "vehicle_name": "Staff Van 01", "vehicle_type": "VAN", "description": "Faculty shuttle service"},
        ]

        for item in defaults:
            norm_num = self.normalize_plate(item["vehicle_number"])
            exists = (
                self.db.query(CollegeVehicle)
                .filter(CollegeVehicle.vehicle_number == norm_num)
                .first()
            )
            if not exists:
                new_veh = CollegeVehicle(
                    vehicle_number=norm_num,
                    vehicle_name=item["vehicle_name"],
                    vehicle_type=item["vehicle_type"],
                    description=item.get("description"),
                    status="ACTIVE",
                    current_status="OUTSIDE",
                )
                self.db.add(new_veh)
        self.db.commit()
