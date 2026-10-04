import os
import sys
import time

# Ensure backend root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database.connection import engine, SessionLocal
from backend.app.database.base import Base
from backend.app.models import CollegeVehicle, RecognitionEvent, Vehicle
from backend.app.services.college_vehicle_service import CollegeVehicleService
from backend.app.services.recognition_service import RecognitionService
from backend.app.schemas.recognition import RecognitionCreate
from backend.app.schemas.college_vehicle import CollegeVehicleCreate, CollegeVehicleUpdate

def test_phase2():
    print("=" * 60)
    print("RUNNING PHASE 2 END-TO-END VALIDATION TEST")
    print("=" * 60)

    # 1. Initialize tables & seed data
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        college_service = CollegeVehicleService(db)
        college_service.seed_default_college_vehicles()

        # 2. Test College Vehicle Service (Seed check)
        college_vehicles, total = college_service.list_college_vehicles()
        print(f"\n[1] College Vehicles in Database: {total}")
        for cv in college_vehicles:
            print(f"    - {cv.vehicle_number} | {cv.vehicle_name} | {cv.vehicle_type} | Current: {cv.current_status}")

        # Check lookup
        bus1 = college_service.get_vehicle_by_plate("TN45BD7321")
        assert bus1 is not None, "TN45BD7321 should be in database"
        assert bus1.vehicle_name == "College Bus 01"
        print("    -> Lookup TN45BD7321: SUCCESS (College Bus 01)")

        # Reset bus1 to OUTSIDE for test repeatability
        college_service.update_college_vehicle(bus1.id, CollegeVehicleUpdate(current_status="OUTSIDE"))
        rec_service = RecognitionService(db)

        # 3. Test Recognition Service - Case A: College Vehicle First Detection (ENTRY)
        print("\n[2] Testing College Vehicle Recognition (TN45BD7321)...")
        rec_in = RecognitionCreate(
            plate_number="TN45BD7321",
            camera_id="CAM-01",
            yolo_confidence=0.88,
            ocr_confidence=0.99,
            vehicle_image_path="captures/full_test_bus1.jpg",
            plate_image_path="captures/plate_test_bus1.jpg"
        )
        rec1 = rec_service.create_event(rec_in)
        print(f"    Event 1 Created: ID={rec1.id}")
        print(f"    Category: {rec1.vehicle_category}")
        print(f"    Vehicle Name: {rec1.vehicle_name}")
        print(f"    Movement Type: {rec1.movement_type}")
        print(f"    Current Status: {rec1.current_status}")
        assert rec1.vehicle_category == "COLLEGE_VEHICLE", "Must be COLLEGE_VEHICLE"
        assert rec1.vehicle_name == "College Bus 01", "Must match College Bus 01"
        assert rec1.movement_type == "ENTRY", "First event must be ENTRY"
        assert rec1.current_status == "INSIDE", "Status must be INSIDE"
        print("    -> College Vehicle First Detection: PASSED")

        # 4. Test Recognition Service - Case A2: College Vehicle Next Detection (EXIT)
        print("\n[3] Testing College Vehicle Return/Exit (TN45BD7321)...")
        rec_exit = RecognitionCreate(
            plate_number="TN45BD7321",
            camera_id="CAM-01",
            yolo_confidence=0.85,
            ocr_confidence=0.98,
            vehicle_image_path="captures/full_test_bus1_exit.jpg",
            plate_image_path="captures/plate_test_bus1_exit.jpg"
        )
        rec2 = rec_service.create_event(rec_exit)
        print(f"    Event 2 Created: ID={rec2.id}")
        print(f"    Category: {rec2.vehicle_category}")
        print(f"    Movement Type: {rec2.movement_type}")
        print(f"    Current Status: {rec2.current_status}")
        assert rec2.movement_type == "EXIT", "Subsequent event must be EXIT"
        assert rec2.current_status == "OUTSIDE", "Status must be OUTSIDE"
        print("    -> College Vehicle Exit Detection: PASSED")

        # 5. Test Recognition Service - Case B: Other / Unregistered Vehicle with unique plate
        test_other_plate = f"TN99XY{int(time.time()) % 10000:04d}"
        print(f"\n[4] Testing Other Vehicle Recognition ({test_other_plate})...")
        rec_other = RecognitionCreate(
            plate_number=test_other_plate,
            camera_id="CAM-01",
            yolo_confidence=0.82,
            ocr_confidence=0.95,
            vehicle_image_path="captures/full_test_other.jpg",
            plate_image_path="captures/plate_test_other.jpg"
        )
        rec3 = rec_service.create_event(rec_other)
        print(f"    Event 3 Created: ID={rec3.id}")
        print(f"    Category: {rec3.vehicle_category}")
        print(f"    Vehicle Name: {rec3.vehicle_name}")
        print(f"    Movement Type: {rec3.movement_type}")
        print(f"    Current Status: {rec3.current_status}")
        assert rec3.vehicle_category == "OTHER_VEHICLE", "Must be OTHER_VEHICLE"
        assert rec3.vehicle_name is None, "Vehicle Name must be None for other vehicle"
        assert rec3.movement_type == "ENTRY", "First event must be ENTRY"
        assert rec3.current_status == "INSIDE", "Status must be INSIDE"
        print("    -> Other Vehicle Detection: PASSED")

        # 6. Test Dashboard Summary API Service
        print("\n[5] Testing Dashboard Summary...")
        summary = rec_service.get_dashboard_summary()
        print("    College Vehicles Stats:", summary.college_vehicles)
        print("    Other Vehicles Stats:", summary.other_vehicles)
        assert summary.college_vehicles.total >= 3
        assert summary.college_vehicles.outside >= 1
        assert summary.other_vehicles.inside >= 1
        print("    -> Dashboard Summary: PASSED")

        # 7. Test College Vehicle Admin CRUD
        print("\n[6] Testing College Vehicle Admin CRUD...")
        new_bus = CollegeVehicleCreate(
            vehicle_number="TN45BD1122",
            vehicle_name="College Bus 03",
            vehicle_type="BUS",
            status="ACTIVE"
        )
        created_bus = college_service.create_college_vehicle(new_bus)
        print(f"    Created: {created_bus.vehicle_name} ({created_bus.vehicle_number})")
        assert created_bus.vehicle_number == "TN45BD1122"

        # Update
        updated_bus = college_service.update_college_vehicle(created_bus.id, CollegeVehicleUpdate(vehicle_name="College Bus 03 (Special)"))
        assert updated_bus is not None, "Failed to update college vehicle"
        print(f"    Updated Name: {updated_bus.vehicle_name}")
        assert updated_bus.vehicle_name == "College Bus 03 (Special)"

        # Delete (Hard delete for test cleanup)
        del_success = college_service.delete_college_vehicle(created_bus.id, hard_delete=True)
        assert del_success is True
        print(f"    Deleted ID={created_bus.id}: SUCCESS")

        print("\n" + "=" * 60)
        print("ALL PHASE 2 VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    test_phase2()
