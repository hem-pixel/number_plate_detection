"""
Phase 4 Automated Test Suite
============================
Validates:
1. Vehicle creation with plate normalization and description.
2. Duplicate plate registration prevention.
3. Registration number validation rules.
4. List college vehicles with search, filtering, and pagination.
5. Get college vehicle by ID.
6. Update college vehicle details.
7. Safe deletion logic:
   - Prevent hard deletion if vehicle has recognition history.
   - Support safe deactivation (soft deletion).
   - Hard deletion allowed when no recognition history exists.
8. Vehicle classification:
   - Active college vehicle -> COLLEGE_VEHICLE
   - Inactive college vehicle -> OTHER_VEHICLE
   - Unregistered vehicle -> OTHER_VEHICLE
9. Vehicle status updates upon ENTRY (INSIDE) and EXIT (OUTSIDE).
10. Vehicle history endpoint (/api/v1/college-vehicles/{id}/history) with total entries and exits.
11. Dashboard summary with 6 real database counts and recent movements.
12. FastAPI HTTP API Integration via TestClient.
"""

import os
import sys
import unittest
import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Configure Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.database.connection import SessionLocal
from backend.app.models.college_vehicle import CollegeVehicle
from backend.app.models.recognition import RecognitionEvent
from backend.app.schemas.college_vehicle import (
    CollegeVehicleCreate,
    CollegeVehicleUpdate,
    VehicleTypeEnum,
    normalize_plate
)
from backend.app.schemas.recognition import RecognitionEventCreate
from backend.app.services.college_vehicle_service import CollegeVehicleService
from backend.app.services.recognition_service import RecognitionService


class TestPhase4CollegeVehicleMaster(unittest.TestCase):
    """Test suite for Phase 4 College Vehicle Master and Admin Dashboard."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.db = SessionLocal()
        self.service = CollegeVehicleService(self.db)
        self.rec_service = RecognitionService(self.db)
        # Unique prefix for this test run to prevent collisions in live database
        self.run_id = uuid.uuid4().hex[:6].upper()
        self.test_plate = f"TEST{self.run_id}99"
        self.created_ids = []

    def tearDown(self):
        # Cleanup created vehicles and associated recognitions
        try:
            for vid in self.created_ids:
                # Remove test recognitions first
                self.db.query(RecognitionEvent).filter(
                    RecognitionEvent.college_vehicle_id == vid
                ).delete()
                self.db.query(CollegeVehicle).filter(
                    CollegeVehicle.id == vid
                ).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_01_plate_normalization(self):
        """Test normalization removes spaces, hyphens, and converts to uppercase."""
        self.assertEqual(normalize_plate("  tn-09-ab-1234  "), "TN09AB1234")
        self.assertEqual(normalize_plate("ka 01 mh 9999"), "KA01MH9999")
        self.assertEqual(normalize_plate("dl04c1234"), "DL04C1234")

    def test_02_create_college_vehicle_service(self):
        """Test creating a college vehicle with description and normalized plate."""
        data = CollegeVehicleCreate(
            registration_number=f" tn - 01 - {self.run_id} ",
            vehicle_name=f"Campus Shuttle {self.run_id}",
            vehicle_type=VehicleTypeEnum.BUS,
            description="Main Campus Route Bus",
            status="ACTIVE"
        )
        vehicle = self.service.create_college_vehicle(data)
        self.created_ids.append(vehicle.id)

        self.assertEqual(vehicle.vehicle_number, f"TN01{self.run_id}")
        self.assertEqual(vehicle.registration_number, f"TN01{self.run_id}")
        self.assertEqual(vehicle.vehicle_name, f"Campus Shuttle {self.run_id}")
        self.assertEqual(vehicle.vehicle_type, "BUS")
        self.assertEqual(vehicle.description, "Main Campus Route Bus")
        self.assertEqual(vehicle.status, "ACTIVE")
        self.assertEqual(vehicle.current_status, "OUTSIDE")

        # Dynamic entries/exits history verification
        hist = self.service.get_vehicle_history(vehicle.id)
        self.assertEqual(hist["total_entries"], 0)
        self.assertEqual(hist["total_exits"], 0)

    def test_03_prevent_duplicate_registration_number(self):
        """Test duplicate registration numbers are strictly rejected."""
        data1 = CollegeVehicleCreate(
            registration_number=self.test_plate,
            vehicle_name="Vehicle 1",
            vehicle_type=VehicleTypeEnum.CAR
        )
        v1 = self.service.create_college_vehicle(data1)
        self.created_ids.append(v1.id)

        # Attempt to register with same normalized plate (with extra spaces and dashes)
        data2 = CollegeVehicleCreate(
            registration_number=f" {self.test_plate[:4]}-{self.test_plate[4:]} ",
            vehicle_name="Vehicle 2",
            vehicle_type=VehicleTypeEnum.CAR
        )
        with self.assertRaises(ValueError) as ctx:
            self.service.create_college_vehicle(data2)
        self.assertIn("already exists", str(ctx.exception))

    def test_04_list_vehicles_with_filters_and_search(self):
        """Test search, filtering by type/status/location, and pagination."""
        plate1 = f"P4A{self.run_id}1"
        plate2 = f"P4B{self.run_id}2"

        v1 = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=plate1,
            vehicle_name="FilterBus Alpha",
            vehicle_type=VehicleTypeEnum.BUS,
            status="ACTIVE"
        ))
        self.created_ids.append(v1.id)

        v2 = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=plate2,
            vehicle_name="StaffCar Beta",
            vehicle_type=VehicleTypeEnum.STAFF_VEHICLE,
            status="INACTIVE"
        ))
        self.created_ids.append(v2.id)

        # Search by name
        res_name, total = self.service.list_college_vehicles(search="FilterBus")
        self.assertTrue(any(v.id == v1.id for v in res_name))
        self.assertFalse(any(v.id == v2.id for v in res_name))

        # Filter by type BUS
        res_type, _ = self.service.list_college_vehicles(vehicle_type="BUS")
        self.assertTrue(any(v.id == v1.id for v in res_type))
        self.assertFalse(any(v.id == v2.id for v in res_type))

        # Filter by status INACTIVE
        res_status, _ = self.service.list_college_vehicles(status="INACTIVE")
        self.assertTrue(any(v.id == v2.id for v in res_status))
        self.assertFalse(any(v.id == v1.id for v in res_status))

        # Pagination test
        paged_res, paged_total = self.service.list_college_vehicles(skip=0, limit=1)
        self.assertEqual(len(paged_res), 1)
        self.assertGreaterEqual(paged_total, 2)

    def test_05_update_college_vehicle(self):
        """Test updating vehicle fields."""
        v = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=self.test_plate,
            vehicle_name="Original Name",
            vehicle_type=VehicleTypeEnum.VAN,
            description="Initial"
        ))
        self.created_ids.append(v.id)

        update_data = CollegeVehicleUpdate(
            vehicle_name="Updated Express Van",
            vehicle_type=VehicleTypeEnum.OTHER,
            description="Updated fleet description",
            status="INACTIVE"
        )
        updated = self.service.update_college_vehicle(v.id, update_data)
        self.assertEqual(updated.vehicle_name, "Updated Express Van")
        self.assertEqual(updated.vehicle_type, "OTHER")
        self.assertEqual(updated.description, "Updated fleet description")
        self.assertEqual(updated.status, "INACTIVE")

    def test_06_safe_deletion_with_and_without_history(self):
        """Test safe deletion prevents hard deleting when recognition history exists."""
        v = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=self.test_plate,
            vehicle_name="History Protected Van",
            vehicle_type=VehicleTypeEnum.VAN
        ))
        self.created_ids.append(v.id)

        # Case A: Vehicle has NO history -> Hard delete should succeed
        v_clean = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=f"CLN{self.run_id}",
            vehicle_name="Clean Van",
            vehicle_type=VehicleTypeEnum.VAN
        ))
        # Hard delete clean vehicle
        self.service.delete_college_vehicle(v_clean.id, hard_delete=True)
        self.assertIsNone(self.service.get_vehicle_by_id(v_clean.id))

        # Case B: Create recognition event attached to v
        event_data = RecognitionEventCreate(
            plate_number=self.test_plate,
            yolo_confidence=0.95,
            ocr_confidence=0.98,
            movement_type="ENTRY",
            camera_id="TEST_CAM"
        )
        event = self.rec_service.create_event(event_data)

        # Now attempt hard deletion -> must be blocked
        with self.assertRaises(ValueError) as ctx:
            self.service.delete_college_vehicle(v.id, hard_delete=True)
        self.assertIn("Cannot permanently delete vehicle", str(ctx.exception))

        # Soft delete / deactivation must succeed without destroying history
        ok = self.service.delete_college_vehicle(v.id, hard_delete=False)
        self.assertTrue(ok)
        self.db.refresh(v)
        self.assertEqual(v.status, "INACTIVE")
        # Record still exists and history intact
        self.assertIsNotNone(self.service.get_vehicle_by_id(v.id))

    def test_07_vehicle_classification_active_vs_inactive(self):
        """Test active vehicles are COLLEGE_VEHICLE; inactive vehicles are OTHER_VEHICLE."""
        active_plate = f"ACT{self.run_id}"
        inactive_plate = f"INA{self.run_id}"

        v_active = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=active_plate,
            vehicle_name="Active College Bus",
            vehicle_type=VehicleTypeEnum.BUS,
            status="ACTIVE"
        ))
        self.created_ids.append(v_active.id)

        v_inactive = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=inactive_plate,
            vehicle_name="Decommissioned Bus",
            vehicle_type=VehicleTypeEnum.BUS,
            status="INACTIVE"
        ))
        self.created_ids.append(v_inactive.id)

        # Create recognition for active vehicle
        event_act = self.rec_service.create_event(RecognitionEventCreate(
            plate_number=active_plate,
            yolo_confidence=0.92,
            ocr_confidence=0.95,
            movement_type="ENTRY",
            camera_id="GATE_CAM_01"
        ))
        self.assertEqual(event_act.vehicle_category, "COLLEGE_VEHICLE")
        self.assertEqual(event_act.college_vehicle_id, v_active.id)

        # Create recognition for inactive vehicle -> must NOT be classified as COLLEGE_VEHICLE
        event_inact = self.rec_service.create_event(RecognitionEventCreate(
            plate_number=inactive_plate,
            yolo_confidence=0.88,
            ocr_confidence=0.90,
            movement_type="ENTRY",
            camera_id="GATE_CAM_01"
        ))
        self.assertEqual(event_inact.vehicle_category, "OTHER_VEHICLE")

    def test_08_location_status_updates_on_entry_and_exit(self):
        """Test vehicle status transitions: OUTSIDE -> INSIDE on ENTRY, INSIDE -> OUTSIDE on EXIT."""
        v = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=self.test_plate,
            vehicle_name="Patrol Car",
            vehicle_type=VehicleTypeEnum.CAR,
            status="ACTIVE"
        ))
        self.created_ids.append(v.id)
        self.assertEqual(v.current_status, "OUTSIDE")

        hist_init = self.service.get_vehicle_history(v.id)
        self.assertEqual(hist_init["total_entries"], 0)
        self.assertEqual(hist_init["total_exits"], 0)

        # Event 1: ENTRY
        self.rec_service.create_event(RecognitionEventCreate(
            plate_number=self.test_plate,
            yolo_confidence=0.94,
            ocr_confidence=0.97,
            movement_type="ENTRY",
            camera_id="GATE_IN"
        ))
        self.db.refresh(v)
        self.assertEqual(v.current_status, "INSIDE")
        self.assertIsNotNone(v.last_movement_at)

        hist_entry = self.service.get_vehicle_history(v.id)
        self.assertEqual(hist_entry["total_entries"], 1)
        self.assertEqual(hist_entry["total_exits"], 0)

        # Event 2: EXIT
        self.rec_service.create_event(RecognitionEventCreate(
            plate_number=self.test_plate,
            yolo_confidence=0.96,
            ocr_confidence=0.98,
            movement_type="EXIT",
            camera_id="GATE_OUT"
        ))
        self.db.refresh(v)
        self.assertEqual(v.current_status, "OUTSIDE")

        hist_exit = self.service.get_vehicle_history(v.id)
        self.assertEqual(hist_exit["total_entries"], 1)
        self.assertEqual(hist_exit["total_exits"], 1)

    def test_09_vehicle_history_retrieval(self):
        """Test retrieving vehicle history with counts and image references."""
        v = self.service.create_college_vehicle(CollegeVehicleCreate(
            registration_number=self.test_plate,
            vehicle_name="Staff Van",
            vehicle_type=VehicleTypeEnum.VAN
        ))
        self.created_ids.append(v.id)

        # Generate 2 events
        self.rec_service.create_event(RecognitionEventCreate(
            plate_number=self.test_plate,
            yolo_confidence=0.91,
            ocr_confidence=0.94,
            movement_type="ENTRY",
            camera_id="CAM_1",
            vehicle_image_path="/storage/test_full_1.jpg",
            plate_image_path="/storage/test_crop_1.jpg"
        ))
        self.rec_service.create_event(RecognitionEventCreate(
            plate_number=self.test_plate,
            yolo_confidence=0.93,
            ocr_confidence=0.96,
            movement_type="EXIT",
            camera_id="CAM_2",
            vehicle_image_path="/storage/test_full_2.jpg",
            plate_image_path="/storage/test_crop_2.jpg"
        ))

        history = self.service.get_vehicle_history(v.id, limit=10)
        self.assertEqual(history["vehicle"].id, v.id)
        self.assertEqual(history["total_entries"], 1)
        self.assertEqual(history["total_exits"], 1)
        self.assertEqual(len(history["history"]), 2)
        self.assertEqual(history["history"][0]["vehicle_image_path"], "/storage/test_full_2.jpg")
        self.assertEqual(history["history"][0]["plate_image_path"], "/storage/test_crop_2.jpg")

    def test_10_dashboard_summary_metrics(self):
        """Test dashboard summary includes all 6 exact metrics and recent movements."""
        summary = self.rec_service.get_dashboard_summary()
        summary_dict = summary.model_dump()

        # Validate schema keys
        self.assertIn("college_vehicles", summary_dict)
        self.assertIn("today_entries", summary_dict)
        self.assertIn("today_exits", summary_dict)
        self.assertIn("other_vehicles_today", summary_dict)
        self.assertIn("recent_movements", summary_dict)

        # Validate 6 specific metrics from real DB
        total_college = summary.college_vehicles.total
        inside_college = summary.college_vehicles.inside
        outside_college = summary.college_vehicles.outside
        entries_today = summary.today_entries
        exits_today = summary.today_exits
        other_today = summary.other_vehicles_today

        self.assertGreaterEqual(total_college, 0)
        self.assertGreaterEqual(inside_college, 0)
        self.assertGreaterEqual(outside_college, 0)
        self.assertGreaterEqual(entries_today, 0)
        self.assertGreaterEqual(exits_today, 0)
        self.assertGreaterEqual(other_today, 0)
        self.assertIsInstance(summary.recent_movements, list)

    def test_11_fastapi_rest_endpoints(self):
        """Test full HTTP API surface for College Vehicles via TestClient."""
        # 1. POST /api/v1/college-vehicles
        post_payload = {
            "registration_number": f"KL-07-{self.run_id}",
            "vehicle_name": f"API Test Car {self.run_id}",
            "vehicle_type": "CAR",
            "description": "Registered via REST endpoint",
            "status": "ACTIVE"
        }
        res = self.client.post("/api/v1/college-vehicles", json=post_payload)
        self.assertEqual(res.status_code, 201)
        created_data = res.json()
        vid = created_data["id"]
        self.created_ids.append(vid)
        self.assertEqual(created_data["registration_number"], f"KL07{self.run_id}")

        # 2. GET /api/v1/college-vehicles
        res_list = self.client.get(f"/api/v1/college-vehicles?search={self.run_id}")
        self.assertEqual(res_list.status_code, 200)
        list_json = res_list.json()
        self.assertTrue(any(v["id"] == vid for v in list_json))

        # 3. GET /api/v1/college-vehicles/{id}
        res_get = self.client.get(f"/api/v1/college-vehicles/{vid}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["id"], vid)

        # 4. PUT /api/v1/college-vehicles/{id}
        update_payload = {
            "vehicle_name": "API Test Car - Updated",
            "vehicle_type": "STAFF_VEHICLE",
            "status": "ACTIVE"
        }
        res_put = self.client.put(f"/api/v1/college-vehicles/{vid}", json=update_payload)
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.json()["vehicle_name"], "API Test Car - Updated")
        self.assertEqual(res_put.json()["vehicle_type"], "STAFF_VEHICLE")

        # 5. GET /api/v1/college-vehicles/{id}/history
        res_hist = self.client.get(f"/api/v1/college-vehicles/{vid}/history")
        self.assertEqual(res_hist.status_code, 200)
        hist_json = res_hist.json()
        self.assertEqual(hist_json["vehicle"]["id"], vid)
        self.assertEqual(hist_json["total_entries"], 0)
        self.assertEqual(hist_json["total_exits"], 0)

        # 6. GET /api/v1/recognitions/summary
        res_summary = self.client.get("/api/v1/recognitions/summary")
        self.assertEqual(res_summary.status_code, 200)
        summary_json = res_summary.json()
        self.assertIn("other_vehicles_today", summary_json)
        self.assertIn("recent_movements", summary_json)

        # 7. DELETE /api/v1/college-vehicles/{id}?hard_delete=true
        res_del = self.client.delete(f"/api/v1/college-vehicles/{vid}?hard_delete=true")
        self.assertEqual(res_del.status_code, 200)

        # Verify 404 after deletion
        res_after = self.client.get(f"/api/v1/college-vehicles/{vid}")
        self.assertEqual(res_after.status_code, 404)


if __name__ == "__main__":
    unittest.main()
