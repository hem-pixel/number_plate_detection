from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.schemas.college_vehicle import (
    CollegeVehicleCreate,
    CollegeVehicleUpdate,
    CollegeVehicleResponse,
)
from backend.app.services.college_vehicle_service import CollegeVehicleService

router = APIRouter(prefix="/college-vehicles", tags=["College Vehicles"])


@router.get("", response_model=List[CollegeVehicleResponse])
def get_college_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    service = CollegeVehicleService(db)
    vehicles, _ = service.list_college_vehicles(
        skip=skip,
        limit=limit,
        search=search,
        status=status,
    )
    return vehicles


@router.get("/{vehicle_id}", response_model=CollegeVehicleResponse)
def get_college_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    service = CollegeVehicleService(db)
    vehicle = service.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College vehicle with ID {vehicle_id} not found",
        )
    return vehicle


@router.post("", response_model=CollegeVehicleResponse, status_code=status.HTTP_201_CREATED)
def create_college_vehicle(
    vehicle_in: CollegeVehicleCreate,
    db: Session = Depends(get_db),
):
    service = CollegeVehicleService(db)
    try:
        return service.create_college_vehicle(vehicle_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{vehicle_id}", response_model=CollegeVehicleResponse)
def update_college_vehicle(
    vehicle_id: int,
    vehicle_in: CollegeVehicleUpdate,
    db: Session = Depends(get_db),
):
    service = CollegeVehicleService(db)
    updated = service.update_college_vehicle(vehicle_id, vehicle_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College vehicle with ID {vehicle_id} not found",
        )
    return updated


@router.delete("/{vehicle_id}", status_code=status.HTTP_200_OK)
def delete_college_vehicle(
    vehicle_id: int,
    hard_delete: bool = Query(False, description="If true, permanently remove record"),
    db: Session = Depends(get_db),
):
    service = CollegeVehicleService(db)
    success = service.delete_college_vehicle(vehicle_id, hard_delete=hard_delete)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"College vehicle with ID {vehicle_id} not found",
        )
    action = "deleted" if hard_delete else "deactivated"
    return {"message": f"College vehicle {vehicle_id} {action} successfully"}
