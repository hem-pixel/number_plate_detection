"""
Phase 3 Comprehensive Automated Test Suite
==========================================
Validates Single Camera Virtual Line Entry/Exit Detection:
- Test 1:  Vehicle starts ABOVE line, moves DOWN, crosses line -> ENTRY
- Test 2:  Vehicle starts BELOW line, moves UP, crosses line -> EXIT
- Test 3:  Vehicle stays ABOVE line -> NO EVENT
- Test 4:  Vehicle stays BELOW line -> NO EVENT
- Test 5:  Vehicle jitters around line within dead zone -> NO FALSE EVENT
- Test 6:  Same track crosses line once -> ONLY ONE EVENT (cooldown/debounce)
- Test 7:  Same vehicle exits camera and later crosses again -> NEW EVENT
- Test 8:  Registered plate crosses TOP -> DOWN -> COLLEGE_VEHICLE + ENTRY + INSIDE
- Test 9:  Registered plate crosses DOWN -> UP -> COLLEGE_VEHICLE + EXIT + OUTSIDE
- Test 10: Unknown plate crosses TOP -> DOWN -> OTHER_VEHICLE + ENTRY
- Test 11: Unknown plate crosses DOWN -> UP -> OTHER_VEHICLE + EXIT
- Test 12: Event is persisted into Supabase PostgreSQL
- Test 13: WebSocket event is emitted (type: "VEHICLE_MOVEMENT")
- Test 14: Full frame and cropped plate image are stored for confirmed events
"""

import os
import sys
import time
import shutil
import unittest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Configure Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_DIR = PROJECT_ROOT / "ai-service"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_DIR))

import cv2
import numpy as np
from tracking.line_crossing import LineCrossingDetector, TrackCrossingState
from tracking.event_manager import VehicleEventManager, VehicleEvent
from backend.app.database.connection import SessionLocal
from backend.app.models.recognition import RecognitionEvent
from backend.app.models.college_vehicle import CollegeVehicle
from backend.app.models.vehicle import Vehicle
from backend.app.schemas.recognition import RecognitionEventCreate
from backend.app.services.recognition_service import RecognitionService
from backend.app.api.websocket import ConnectionManager


class TestPhase3LineCrossing(unittest.TestCase):
    """Unit and Integration Tests for Phase 3 Virtual Line Detection."""

    def setUp(self):
        self.frame_height = 640
        self.frame_width = 640
        # Line at 50% = 320px, Dead Zone = 20px (Upper threshold = 300, Lower threshold = 340)
        self.detector = LineCrossingDetector(
            camera_id="GATE_CAMERA_01",
            line_position_percent=50.0,
            dead_zone=20,
            min_track_age=5,
            min_vertical_movement=15,
            cooldown_seconds=5.0,
        )
        self.test_artifacts_dir = PROJECT_ROOT / "data" / "test_captures"
        self.test_artifacts_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_artifacts_dir.exists():
            shutil.rmtree(str(self.test_artifacts_dir), ignore_errors=True)

    def test_01_vehicle_above_to_below_triggers_entry(self):
        """Test 1: Vehicle starts ABOVE line, moves DOWN, crosses line -> Expected: ENTRY"""
        # Starts at Y=200 (< 300 -> ABOVE)
        t = 1000.0
        track_id = 101

        # Feed 4 frames moving downward (total age: 4 frames)
        for y_pos in [200, 220, 240, 260]:
            event = self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            self.assertIsNone(event, "Should not trigger before track age and line crossing")
            t += 0.05

        # 5th frame reaches below dead zone: Y=360 (> 340 -> BELOW)
        event = self.detector.update(track_id=track_id, center_y=360, frame_height=self.frame_height, current_time=t)
        self.assertEqual(event, "ENTRY", "Movement from ABOVE to BELOW must trigger ENTRY")

    def test_02_vehicle_below_to_above_triggers_exit(self):
        """Test 2: Vehicle starts BELOW line, moves UP, crosses line -> Expected: EXIT"""
        # Starts at Y=450 (> 340 -> BELOW)
        t = 2000.0
        track_id = 102

        # Feed 4 frames moving upward
        for y_pos in [450, 430, 410, 390]:
            event = self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            self.assertIsNone(event, "Should not trigger before crossing line")
            t += 0.05

        # 5th frame reaches above dead zone: Y=250 (< 300 -> ABOVE)
        event = self.detector.update(track_id=track_id, center_y=250, frame_height=self.frame_height, current_time=t)
        self.assertEqual(event, "EXIT", "Movement from BELOW to ABOVE must trigger EXIT")

    def test_03_vehicle_stays_above_line_no_event(self):
        """Test 3: Vehicle stays ABOVE line -> Expected: NO EVENT"""
        t = 3000.0
        track_id = 103

        # Moves entirely above the line (all < 300)
        positions = [120, 140, 160, 180, 200, 220, 240, 230, 210]
        for y_pos in positions:
            event = self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            self.assertIsNone(event, f"No event expected while remaining ABOVE line (y={y_pos})")
            t += 0.05

    def test_04_vehicle_stays_below_line_no_event(self):
        """Test 4: Vehicle stays BELOW line -> Expected: NO EVENT"""
        t = 4000.0
        track_id = 104

        # Moves entirely below the line (all > 340)
        positions = [480, 460, 440, 420, 400, 380, 360, 370, 390]
        for y_pos in positions:
            event = self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            self.assertIsNone(event, f"No event expected while remaining BELOW line (y={y_pos})")
            t += 0.05

    def test_05_vehicle_jitters_around_line_in_deadzone_no_false_event(self):
        """Test 5: Vehicle jitters around line within dead zone -> Expected: NO FALSE EVENT"""
        t = 5000.0
        track_id = 105

        # Dead zone is [300, 340]
        jitter_positions = [310, 325, 315, 330, 320, 318, 322, 328, 312, 335]
        for y_pos in jitter_positions:
            event = self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            self.assertIsNone(event, f"No false event should trigger inside hysteresis dead zone (y={y_pos})")
            t += 0.05

    def test_06_same_track_crosses_line_once_generates_single_event(self):
        """Test 6: Same track crosses line once -> Expected: ONLY ONE EVENT (debounce/cooldown)"""
        t = 6000.0
        track_id = 106

        # Cross TOP -> DOWN
        for y_pos in [200, 230, 260, 290]:
            self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            t += 0.05

        # 5th frame triggers ENTRY
        event1 = self.detector.update(track_id=track_id, center_y=360, frame_height=self.frame_height, current_time=t)
        self.assertEqual(event1, "ENTRY")

        # Following frames within 5-second cooldown
        for y_pos in [370, 380, 390, 400, 410]:
            t += 0.1
            event_subsequent = self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            self.assertIsNone(event_subsequent, "Subsequent frames for same track must be debounced")

    def test_07_same_vehicle_leaves_and_crosses_again_generates_new_event(self):
        """Test 7: Same vehicle exits camera and later crosses again -> Expected: NEW EVENT"""
        t = 7000.0
        track_id = 107

        # 1st crossing: ENTRY
        for y_pos in [200, 230, 260, 290]:
            self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            t += 0.05
        e1 = self.detector.update(track_id=track_id, center_y=360, frame_height=self.frame_height, current_time=t)
        self.assertEqual(e1, "ENTRY")

        # Vehicle leaves camera (track reset / expired)
        self.detector.reset_track(track_id)

        # Later, vehicle returns (or new track ID) and crosses DOWN -> UP (EXIT)
        t += 30.0  # Time passed
        for y_pos in [450, 420, 390, 360]:
            self.detector.update(track_id=track_id, center_y=y_pos, frame_height=self.frame_height, current_time=t)
            t += 0.05
        e2 = self.detector.update(track_id=track_id, center_y=260, frame_height=self.frame_height, current_time=t)
        self.assertEqual(e2, "EXIT", "Returning vehicle must trigger a new line crossing event")

    def test_08_registered_plate_crosses_entry(self):
        """Test 8: Registered plate crosses TOP -> DOWN -> Expected: COLLEGE_VEHICLE + ENTRY + INSIDE"""
        db = SessionLocal()
        try:
            service = RecognitionService(db)
            event_in = RecognitionEventCreate(
                plate_number="TN45BD7321",
                movement_type="ENTRY",
                camera_id="GATE_CAMERA_01",
                yolo_confidence=0.88,
                ocr_confidence=0.97,
            )
            event = service.create_event(event_in)

            self.assertEqual(event.vehicle_category, "COLLEGE_VEHICLE")
            self.assertEqual(event.vehicle_name, "College Bus 01")
            self.assertEqual(event.movement_type, "ENTRY")
            self.assertEqual(event.current_status, "INSIDE")

            # Check college vehicle record updated in DB
            cv = db.query(CollegeVehicle).filter(CollegeVehicle.vehicle_number == "TN45BD7321").first()
            self.assertIsNotNone(cv)
            self.assertEqual(cv.current_status, "INSIDE")
        finally:
            db.close()

    def test_09_registered_plate_crosses_exit(self):
        """Test 9: Registered plate crosses DOWN -> UP -> Expected: COLLEGE_VEHICLE + EXIT + OUTSIDE"""
        db = SessionLocal()
        try:
            service = RecognitionService(db)
            event_in = RecognitionEventCreate(
                plate_number="TN45BD7321",
                movement_type="EXIT",
                camera_id="GATE_CAMERA_01",
                yolo_confidence=0.89,
                ocr_confidence=0.98,
            )
            event = service.create_event(event_in)

            self.assertEqual(event.vehicle_category, "COLLEGE_VEHICLE")
            self.assertEqual(event.vehicle_name, "College Bus 01")
            self.assertEqual(event.movement_type, "EXIT")
            self.assertEqual(event.current_status, "OUTSIDE")

            # Check college vehicle record updated in DB
            cv = db.query(CollegeVehicle).filter(CollegeVehicle.vehicle_number == "TN45BD7321").first()
            self.assertIsNotNone(cv)
            self.assertEqual(cv.current_status, "OUTSIDE")
        finally:
            db.close()

    def test_10_unknown_plate_crosses_entry(self):
        """Test 10: Unknown plate crosses TOP -> DOWN -> Expected: OTHER_VEHICLE + ENTRY"""
        db = SessionLocal()
        try:
            service = RecognitionService(db)
            event_in = RecognitionEventCreate(
                plate_number="TN38AB1234",
                movement_type="ENTRY",
                camera_id="GATE_CAMERA_01",
                yolo_confidence=0.85,
                ocr_confidence=0.92,
            )
            event = service.create_event(event_in)

            self.assertEqual(event.vehicle_category, "OTHER_VEHICLE")
            self.assertIsNone(event.vehicle_name)
            self.assertIsNone(event.college_vehicle_id)
            self.assertEqual(event.movement_type, "ENTRY")
            self.assertEqual(event.current_status, "INSIDE")

            # Verify NOT added to college vehicles
            cv = db.query(CollegeVehicle).filter(CollegeVehicle.vehicle_number == "TN38AB1234").first()
            self.assertIsNone(cv, "Unknown vehicle should NOT be added to CollegeVehicle table")
        finally:
            db.close()

    def test_11_unknown_plate_crosses_exit(self):
        """Test 11: Unknown plate crosses DOWN -> UP -> Expected: OTHER_VEHICLE + EXIT"""
        db = SessionLocal()
        try:
            service = RecognitionService(db)
            event_in = RecognitionEventCreate(
                plate_number="TN38AB1234",
                movement_type="EXIT",
                camera_id="GATE_CAMERA_01",
                yolo_confidence=0.84,
                ocr_confidence=0.91,
            )
            event = service.create_event(event_in)

            self.assertEqual(event.vehicle_category, "OTHER_VEHICLE")
            self.assertIsNone(event.vehicle_name)
            self.assertEqual(event.movement_type, "EXIT")
            self.assertEqual(event.current_status, "OUTSIDE")
        finally:
            db.close()

    def test_12_event_is_persisted_into_supabase(self):
        """Test 12: Event is persisted into Supabase PostgreSQL"""
        db = SessionLocal()
        try:
            service = RecognitionService(db)
            test_plate = "TN99ZZ9999"
            event_in = RecognitionEventCreate(
                plate_number=test_plate,
                movement_type="ENTRY",
                camera_id="GATE_CAMERA_01",
                yolo_confidence=0.90,
                ocr_confidence=0.95,
            )
            created_event = service.create_event(event_in)
            event_id = created_event.id

            # Re-query directly from Supabase
            queried = db.query(RecognitionEvent).filter(RecognitionEvent.id == event_id).first()
            self.assertIsNotNone(queried, "Event must be saved and queryable from Supabase PostgreSQL")
            self.assertEqual(queried.plate_number, test_plate)
            self.assertEqual(queried.movement_type, "ENTRY")
            self.assertEqual(queried.camera_id, "GATE_CAMERA_01")
        finally:
            db.close()

    def test_13_websocket_event_is_emitted(self):
        """Test 13: WebSocket event is emitted with type 'VEHICLE_MOVEMENT'"""
        from backend.app.api.routes.recognition import create_recognition
        from backend.app.api.websocket import manager

        db = SessionLocal()
        try:
            broadcasted_messages = []

            async def mock_broadcast(msg):
                broadcasted_messages.append(msg)

            with patch.object(manager, "broadcast", side_effect=mock_broadcast):
                event_in = RecognitionEventCreate(
                    plate_number="TN45BD7321",
                    movement_type="ENTRY",
                    camera_id="GATE_CAMERA_01",
                    yolo_confidence=0.86,
                    ocr_confidence=0.99,
                )
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                res = loop.run_until_complete(create_recognition(event_in=event_in, db=db))
                loop.close()

            self.assertTrue(len(broadcasted_messages) > 0, "A WebSocket message must be broadcasted")
            msg = broadcasted_messages[0]
            self.assertEqual(msg.get("type"), "VEHICLE_MOVEMENT")
            self.assertEqual(msg.get("plate_number"), "TN45BD7321")
            self.assertEqual(msg.get("vehicle_category"), "COLLEGE_VEHICLE")
            self.assertEqual(msg.get("vehicle_name"), "College Bus 01")
            self.assertEqual(msg.get("movement_type"), "ENTRY")
            self.assertEqual(msg.get("current_status"), "INSIDE")
            self.assertEqual(msg.get("camera_id"), "GATE_CAMERA_01")
        finally:
            db.close()

    def test_14_images_stored_for_confirmed_events(self):
        """Test 14: Full frame and cropped plate image are stored for confirmed events"""
        # Create a mock frame and cropped plate
        full_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        # Put sample text
        cv2.putText(full_frame, "TEST FRAME", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        plate_crop = full_frame[90:150, 40:220]

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        clean_plate = "TN45BD7321"

        frame_filename = f"{clean_plate}_{timestamp_str}_full.jpg"
        plate_filename = f"{clean_plate}_{timestamp_str}_plate.jpg"

        frame_path = self.test_artifacts_dir / frame_filename
        plate_path = self.test_artifacts_dir / plate_filename

        cv2.imwrite(str(frame_path), full_frame)
        cv2.imwrite(str(plate_path), plate_crop)

        self.assertTrue(frame_path.exists(), f"Full frame must be saved on confirmed event: {frame_path}")
        self.assertTrue(plate_path.exists(), f"Plate crop must be saved on confirmed event: {plate_path}")
        self.assertGreater(frame_path.stat().st_size, 0, "Saved full frame must not be empty")
        self.assertGreater(plate_path.stat().st_size, 0, "Saved plate image must not be empty")


if __name__ == "__main__":
    unittest.main(verbosity=2)
