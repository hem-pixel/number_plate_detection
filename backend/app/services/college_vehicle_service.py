from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.college_vehicle import CollegeVehicle
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
    ) -> Tuple[List[CollegeVehicle], int]:
        query = self.db.query(CollegeVehicle)

        if search:
            clean_search = self.normalize_plate(search)
            query = query.filter(
                (CollegeVehicle.vehicle_number.ilike(f"%{clean_search}%")) |
                (CollegeVehicle.vehicle_name.ilike(f"%{search}%"))
            )
        if status:
            query = query.filter(CollegeVehicle.status == status.upper())

        total = query.count()
        vehicles = (
            query.order_by(desc(CollegeVehicle.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
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

        if vehicle_in.vehicle_name is not None:
            vehicle.vehicle_name = vehicle_in.vehicle_name.strip()
        if vehicle_in.vehicle_type is not None:
            vehicle.vehicle_type = vehicle_in.vehicle_type.upper().strip()
        if vehicle_in.status is not None:
            vehicle.status = vehicle_in.status.upper().strip()
        if vehicle_in.current_status is not None:
            vehicle.current_status = vehicle_in.current_status.upper().strip()

        vehicle.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def delete_college_vehicle(self, vehicle_id: int, hard_delete: bool = False) -> bool:
        vehicle = self.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return False

        if hard_delete:
            self.db.delete(vehicle)
        else:
            vehicle.status = "INACTIVE"
            vehicle.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def seed_default_college_vehicles(self):
        """Seeds predefined college vehicles if empty, particularly the demo buses."""
        defaults = [
            {"vehicle_number": "TN45BD7321", "vehicle_name": "College Bus 01", "vehicle_type": "BUS"},
            {"vehicle_number": "TN45BD8456", "vehicle_name": "College Bus 02", "vehicle_type": "BUS"},
            {"vehicle_number": "TN45BD9999", "vehicle_name": "Staff Van 01", "vehicle_type": "VAN"},
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
                    status="ACTIVE",
                    current_status="OUTSIDE",
                )
                self.db.add(new_veh)
        self.db.commit()
