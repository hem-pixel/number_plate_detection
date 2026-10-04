"""
Vehicle Event & Deduplication Manager (Phase 2)
Supports College Fleet classification and Entry/Exit state tracking.
"""

import os
import csv
import time
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Callable


@dataclass
class VehicleEvent:
    """
    Represents a discrete vehicle number plate recognition event.
    Stores all required temporal, spatial, and recognition metrics,
    including vehicle classification (College vs Other) and In/Out movement.
    """
    event_id: int
    plate_number: str
    first_detected_time: float
    last_seen_time: float
    yolo_confidence: float
    ocr_confidence: float
    frames_observed: int
    verification_status: str = "Verified"
    vehicle_category: str = "OTHER_VEHICLE"  # COLLEGE_VEHICLE / OTHER_VEHICLE
    vehicle_name: Optional[str] = None  # e.g., 'College Bus 01'
    movement_type: str = "ENTRY"  # ENTRY / EXIT
    current_status: str = "INSIDE"  # INSIDE / OUTSIDE
    timestamp_str: str = ""
    vehicle_image_path: Optional[str] = None
    plate_image_path: Optional[str] = None
    camera_id: str = "CAM-01"

    def __post_init__(self):
        if not self.timestamp_str:
            self.timestamp_str = datetime.fromtimestamp(self.first_detected_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    @property
    def status(self) -> str:
        return self.verification_status

    def to_csv_row(self) -> List[Any]:
        return [
            self.timestamp_str,
            self.plate_number,
            self.vehicle_category,
            self.vehicle_name or "",
            self.movement_type,
            self.current_status,
            f"{self.yolo_confidence:.3f}",
            f"{self.ocr_confidence:.3f}",
            self.frames_observed,
            self.verification_status,
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "plate_number": self.plate_number,
            "vehicle_category": self.vehicle_category,
            "vehicle_name": self.vehicle_name,
            "movement_type": self.movement_type,
            "current_status": self.current_status,
            "first_detected_time": self.first_detected_time,
            "last_seen_time": self.last_seen_time,
            "timestamp": self.timestamp_str,
            "yolo_confidence": self.yolo_confidence,
            "ocr_confidence": self.ocr_confidence,
            "frames_observed": self.frames_observed,
            "verification_status": self.verification_status,
            "status": self.verification_status,
            "vehicle_image_path": self.vehicle_image_path,
            "plate_image_path": self.plate_image_path,
            "camera_id": self.camera_id,
        }


class VehicleEventManager:
    """
    Tracks vehicle presence and manages recognition events with duplicate suppression,
    cooldown, college fleet identification, and entry/exit state toggling.
    """

    CSV_COLUMNS = [
        "timestamp",
        "plate_number",
        "vehicle_category",
        "vehicle_name",
        "movement_type",
        "current_status",
        "yolo_confidence",
        "ocr_confidence",
        "frames_observed",
        "status",
    ]

    # Predefined college fleet lookup fallback
    DEFAULT_COLLEGE_FLEET = {
        "TN45BD7321": {"name": "College Bus 01", "type": "BUS"},
        "TN45BD8456": {"name": "College Bus 02", "type": "BUS"},
        "TN45BD9999": {"name": "College Van 01", "type": "VAN"},
    }

    def __init__(
        self,
        cooldown_seconds: float = 10.0,
        save_to_csv: bool = False,
        csv_path: str = os.path.join("output", "recognition_events.csv"),
        college_lookup_fn: Optional[Callable[[str], Optional[Dict[str, str]]]] = None,
    ):
        self.cooldown_seconds = float(cooldown_seconds)
        self.save_to_csv = save_to_csv
        self.csv_path = csv_path
        self.college_lookup_fn = college_lookup_fn

        self.all_events: List[VehicleEvent] = []
        self.active_vehicles: Dict[str, VehicleEvent] = {}
        self.last_seen_history: Dict[str, float] = {}
        self.vehicle_state_history: Dict[str, str] = {}  # plate -> 'INSIDE' / 'OUTSIDE'
        self.latest_event: Optional[VehicleEvent] = None

        if self.save_to_csv:
            self._init_csv()

    def _init_csv(self):
        output_dir = os.path.dirname(self.csv_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(self.CSV_COLUMNS)
            except IOError as e:
                print(f"[!] Warning: Could not initialize CSV file '{self.csv_path}': {e}")

    def _append_to_csv(self, event: VehicleEvent):
        if not self.save_to_csv:
            return
        try:
            with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(event.to_csv_row())
        except IOError as e:
            print(f"[!] Warning: Could not write event to CSV '{self.csv_path}': {e}")

    def get_college_vehicle_info(self, plate_number: str) -> Optional[Dict[str, str]]:
        """Returns vehicle info dict if registered college vehicle, else None."""
        if not plate_number:
            return None
        clean_plate = plate_number.upper().replace(" ", "").replace("-", "").strip()
        if self.college_lookup_fn:
            res = self.college_lookup_fn(clean_plate)
            if res:
                return res
        if clean_plate in self.DEFAULT_COLLEGE_FLEET:
            return self.DEFAULT_COLLEGE_FLEET[clean_plate]
        return None

    def is_college_vehicle(self, plate_number: str) -> tuple[bool, Optional[str]]:
        """Checks if plate belongs to a registered college vehicle."""
        info = self.get_college_vehicle_info(plate_number)
        if info:
            return True, info.get("name") or info.get("vehicle_name")
        return False, None

    def process_plate_sighting(
        self,
        plate_number: str,
        yolo_conf: float,
        ocr_conf: float,
        frames_observed: int = 1,
        current_time: Optional[float] = None,
        vehicle_image_path: Optional[str] = None,
        plate_image_path: Optional[str] = None,
        camera_id: str = "CAM-01",
    ) -> Optional[VehicleEvent]:
        """
        Processes a verified plate detection:
        - If active: updates presence timestamp and confidences (DUPLICATE SUPPRESSION).
        - If not active and absent >= cooldown: logs a NEW vehicle event.
        - Toggles ENTRY vs EXIT movement state based on previous campus status.
        """
        if not plate_number:
            return None

        clean_plate = plate_number.upper().replace(" ", "").replace("-", "").strip()
        now = current_time if current_time is not None else time.time()

        # Check if currently active in camera view (continuous observation)
        if clean_plate in self.active_vehicles:
            event = self.active_vehicles[clean_plate]
            event.last_seen_time = now
            event.yolo_confidence = max(event.yolo_confidence, yolo_conf)
            event.ocr_confidence = max(event.ocr_confidence, ocr_conf)
            event.frames_observed += 1
            if vehicle_image_path:
                event.vehicle_image_path = vehicle_image_path
            if plate_image_path:
                event.plate_image_path = plate_image_path
            self.last_seen_history[clean_plate] = now
            return None

        # Check cooldown since last sighting
        last_seen = self.last_seen_history.get(clean_plate, 0.0)
        time_since_last_seen = now - last_seen if last_seen > 0 else float("inf")

        if time_since_last_seen < self.cooldown_seconds:
            self.last_seen_history[clean_plate] = now
            return None

        # Determine College vs Other Classification
        is_college, vehicle_name = self.is_college_vehicle(clean_plate)
        category = "COLLEGE_VEHICLE" if is_college else "OTHER_VEHICLE"

        # Determine Entry / Exit Movement
        last_campus_status = self.vehicle_state_history.get(clean_plate, "OUTSIDE")
        if last_campus_status == "INSIDE":
            movement_type = "EXIT"
            current_status = "OUTSIDE"
        else:
            movement_type = "ENTRY"
            current_status = "INSIDE"

        self.vehicle_state_history[clean_plate] = current_status

        new_event_id = len(self.all_events) + 1
        new_event = VehicleEvent(
            event_id=new_event_id,
            plate_number=clean_plate,
            first_detected_time=now,
            last_seen_time=now,
            yolo_confidence=yolo_conf,
            ocr_confidence=ocr_conf,
            frames_observed=frames_observed,
            verification_status="Verified",
            vehicle_category=category,
            vehicle_name=vehicle_name,
            movement_type=movement_type,
            current_status=current_status,
            vehicle_image_path=vehicle_image_path,
            plate_image_path=plate_image_path,
            camera_id=camera_id,
        )

        self.all_events.append(new_event)
        self.active_vehicles[clean_plate] = new_event
        self.last_seen_history[clean_plate] = now
        self.latest_event = new_event

        category_label = f"🚌 COLLEGE VEHICLE ({vehicle_name})" if is_college else "🚗 OTHER VEHICLE"
        print(
            f"[+] {category_label}: {clean_plate} -> {movement_type} "
            f"(YOLO: {yolo_conf * 100:.1f}%, OCR: {ocr_conf * 100:.1f}%, Status: {current_status})"
        )

        self._append_to_csv(new_event)
        return new_event

    def update_absences(self, active_plate_numbers_in_frame: List[str], current_time: Optional[float] = None):
        """Cleans up active vehicles that are no longer in frame beyond the cooldown window."""
        now = current_time if current_time is not None else time.time()
        active_set = {
            p.upper().replace(" ", "").replace("-", "").strip()
            for p in active_plate_numbers_in_frame
        }

        for plate in list(self.active_vehicles.keys()):
            if plate not in active_set:
                event = self.active_vehicles[plate]
                time_absent = now - event.last_seen_time
                if time_absent >= self.cooldown_seconds:
                    del self.active_vehicles[plate]
