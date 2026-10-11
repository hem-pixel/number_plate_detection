from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.schemas.college_vehicle import (
    CollegeVehicleCreate,
    CollegeVehicleUpdate,
    CollegeVehicleResponse,
    CollegeVehicleHistoryResponse,
)
from backend.app.services.college_vehicle_service import CollegeVehicleService

router = APIRouter(prefix="/college-vehicles", tags=["College Vehicles"])


@router.get("", response_model=List[CollegeVehicleResponse])
def get_college_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    status: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    current_status: Optional[str] = None,
    sort_by: str = Query("last_movement", description="last_movement, created, vehicle_number, vehicle_name"),
    sort_order: str = Query("desc", description="asc or desc"),
    db: Session = Depends(get_db),
):
    service = CollegeVehicleService(db)
    vehicles, _ = service.list_college_vehicles(
        skip=skip,
        limit=limit,
        search=search,
        status=status,
        vehicle_type=vehicle_type,
        current_status=current_status,
        sort_by=sort_by,
        sort_order=sort_order,
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


@router.get("/{vehicle_id}/history", response_model=CollegeVehicleHistoryResponse)
def get_college_vehicle_history(
    vehicle_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = CollegeVehicleService(db)
    try:
        history_data = service.get_vehicle_history(vehicle_id, limit=limit)
        return history_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


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
    try:
        updated = service.update_college_vehicle(vehicle_id, vehicle_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"College vehicle with ID {vehicle_id} not found",
            )
        return updated
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{vehicle_id}", status_code=status.HTTP_200_OK)
def delete_college_vehicle(
    vehicle_id: int,
    hard_delete: bool = Query(False, description="If true, permanently remove record"),
    db: Session = Depends(get_db),
):
    service = CollegeVehicleService(db)
    try:
        success = service.delete_college_vehicle(vehicle_id, hard_delete=hard_delete)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"College vehicle with ID {vehicle_id} not found",
            )
        action = "permanently deleted" if hard_delete else "deactivated"
        return {"message": f"College vehicle {vehicle_id} {action} successfully", "action": action}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
