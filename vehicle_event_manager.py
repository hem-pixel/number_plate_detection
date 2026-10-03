"""
================================================================================
Vehicle Recognition Event Tracker & Deduplication Manager
================================================================================
Manages vehicle number plate recognition events, continuous visibility deduplication,
configurable cooldown intervals, in-memory session persistence, and CSV export.

Key Specifications:
- Stores plate_number, first_detected_time, last_seen_time, yolo_confidence,
  ocr_confidence, frames_observed, and verification_status.
- Deduplication: Continuous visibility of the same vehicle generates ONE event.
- Cooldown: If a vehicle disappears and reappears after the cooldown window (e.g. 10s),
  it is logged as a NEW vehicle event.
- In-memory event history throughout the application session.
- Real-time terminal notification: "NEW VEHICLE: <PLATE>"
- Real-time CSV export with schema:
  timestamp,plate_number,yolo_confidence,ocr_confidence,frames_observed,status
- HUD integration metrics: total vehicles recognized & latest plate with timestamp.
================================================================================
"""

import os
import csv
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class VehicleEvent:
    """
    Represents a discrete vehicle number plate recognition event.
    Stores all required temporal, spatial, and recognition metrics.
    """
    event_id: int
    plate_number: str
    first_detected_time: float
    last_seen_time: float
    yolo_confidence: float
    ocr_confidence: float
    frames_observed: int
    verification_status: str = "Verified"
    timestamp_str: str = ""

    def __post_init__(self):
        if not self.timestamp_str:
            self.timestamp_str = datetime.fromtimestamp(self.first_detected_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    @property
    def status(self) -> str:
        """Alias for verification_status matching CSV column naming."""
        return self.verification_status

    def to_csv_row(self) -> List[Any]:
        """
        Formats event data into the required CSV column schema:
        timestamp,plate_number,yolo_confidence,ocr_confidence,frames_observed,status
        """
        return [
            self.timestamp_str,
            self.plate_number,
            f"{self.yolo_confidence:.3f}",
            f"{self.ocr_confidence:.3f}",
            self.frames_observed,
            self.verification_status,
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Returns event representation as a dictionary."""
        return {
            "event_id": self.event_id,
            "plate_number": self.plate_number,
            "first_detected_time": self.first_detected_time,
            "last_seen_time": self.last_seen_time,
            "timestamp": self.timestamp_str,
            "yolo_confidence": self.yolo_confidence,
            "ocr_confidence": self.ocr_confidence,
            "frames_observed": self.frames_observed,
            "verification_status": self.verification_status,
            "status": self.verification_status,
        }


class VehicleEventManager:
    """
    Tracks vehicle presence and manages recognition events with duplicate suppression.
    """

    CSV_COLUMNS = [
        "timestamp",
        "plate_number",
        "yolo_confidence",
        "ocr_confidence",
        "frames_observed",
        "status",
    ]

    def __init__(
        self,
        cooldown_seconds: float = 10.0,
        save_to_csv: bool = True,
        csv_path: str = os.path.join("output", "recognition_events.csv"),
    ):
        """
        Initializes the VehicleEventManager.

        Args:
            cooldown_seconds: Minimum seconds a plate must be absent before being
                              treated as a new vehicle event upon return.
            save_to_csv: Whether to automatically save recognition events to CSV.
            csv_path: Path to the output CSV file.
        """
        self.cooldown_seconds = float(cooldown_seconds)
        self.save_to_csv = save_to_csv
        self.csv_path = csv_path

        # All discrete events logged in current session
        self.all_events: List[VehicleEvent] = []

        # Currently active vehicles in view: plate_number -> VehicleEvent
        self.active_vehicles: Dict[str, VehicleEvent] = {}

        # History of when plates were last seen: plate_number -> last_seen_time (float)
        self.last_seen_history: Dict[str, float] = {}

        # Pointer to the most recent event
        self.latest_event: Optional[VehicleEvent] = None

        if self.save_to_csv:
            self._init_csv()

    def _init_csv(self):
        """Creates the output directory and CSV header if the file does not exist."""
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
        """Appends a single verified event row to the CSV file immediately."""
        if not self.save_to_csv:
            return

        try:
            # Check if file exists to write header if needed
            write_header = not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0
            with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(self.CSV_COLUMNS)
                writer.writerow(event.to_csv_row())
                f.flush()
        except IOError as e:
            print(f"[!] Warning: Could not write event to CSV '{self.csv_path}': {e}")

    def _get_latest_event_for_plate(self, plate_number: str) -> Optional[VehicleEvent]:
        """Finds the most recent logged event for a given plate number."""
        for ev in reversed(self.all_events):
            if ev.plate_number == plate_number:
                return ev
        return None

    def _create_new_event(
        self,
        plate_number: str,
        yolo_conf: float,
        ocr_conf: float,
        frames_observed: int,
        timestamp: float,
    ) -> VehicleEvent:
        """Instantiates, logs, and stores a new vehicle recognition event."""
        event_id = len(self.all_events) + 1
        event = VehicleEvent(
            event_id=event_id,
            plate_number=plate_number,
            first_detected_time=timestamp,
            last_seen_time=timestamp,
            yolo_confidence=yolo_conf,
            ocr_confidence=ocr_conf,
            frames_observed=frames_observed,
            verification_status="Verified",
        )

        self.all_events.append(event)
        self.active_vehicles[plate_number] = event
        self.latest_event = event

        # Terminal notification for new verified vehicle event
        print(
            f"[EVENT] NEW VEHICLE: {plate_number} "
            f"(YOLO: {yolo_conf * 100:.1f}%, OCR: {ocr_conf * 100:.1f}%, "
            f"Observed: {frames_observed} frames)"
        )

        # Write to CSV
        self._append_to_csv(event)

        return event

    def update_frame(
        self,
        visible_stable_plates: List[Dict[str, Any]],
        current_time: Optional[float] = None,
    ) -> List[VehicleEvent]:
        """
        Updates the event manager with stable/verified plates visible in the current frame.

        Args:
            visible_stable_plates: List of dictionaries containing:
                - plate_number (str)
                - yolo_conf (float)
                - ocr_conf (float)
                - frames_observed (int)
            current_time: Current timestamp (defaults to time.time()).

        Returns:
            List of newly triggered VehicleEvent objects in this frame.
        """
        if current_time is None:
            current_time = time.time()

        visible_plate_numbers = set()
        new_events = []

        for item in visible_stable_plates:
            plate = item.get("plate_number")
            if not plate:
                continue

            visible_plate_numbers.add(plate)
            yolo_conf = float(item.get("yolo_conf", 0.0))
            ocr_conf = float(item.get("ocr_conf", 0.0))
            frames_obs = int(item.get("frames_observed", 1))

            if plate in self.active_vehicles:
                # Continuous presence: update active session metrics without creating duplicate event
                active_ev = self.active_vehicles[plate]
                active_ev.last_seen_time = current_time
                active_ev.frames_observed = max(active_ev.frames_observed, frames_obs)
                active_ev.yolo_confidence = max(active_ev.yolo_confidence, yolo_conf)
                active_ev.ocr_confidence = max(active_ev.ocr_confidence, ocr_conf)
                self.last_seen_history[plate] = current_time
            else:
                # Plate not currently in active view
                last_seen = self.last_seen_history.get(plate, None)

                if last_seen is not None and (current_time - last_seen) < self.cooldown_seconds:
                    # Reappeared within cooldown window (e.g. brief obstruction or turn)
                    # Re-associate with recent event to suppress false duplicate
                    recent_ev = self._get_latest_event_for_plate(plate)
                    if recent_ev:
                        recent_ev.last_seen_time = current_time
                        recent_ev.frames_observed = max(recent_ev.frames_observed, frames_obs)
                        self.active_vehicles[plate] = recent_ev
                    else:
                        # Fallback if event wasn't in memory
                        ev = self._create_new_event(
                            plate, yolo_conf, ocr_conf, frames_obs, current_time
                        )
                        new_events.append(ev)
                    self.last_seen_history[plate] = current_time
                else:
                    # Truly new vehicle encounter: either never seen or cooldown elapsed
                    ev = self._create_new_event(
                        plate, yolo_conf, ocr_conf, frames_obs, current_time
                    )
                    new_events.append(ev)
                    self.last_seen_history[plate] = current_time

        # Update disappearance for vehicles no longer in current frame view
        absent_plates = [p for p in self.active_vehicles if p not in visible_plate_numbers]
        for p in absent_plates:
            # Mark the departure time
            self.last_seen_history[p] = self.active_vehicles[p].last_seen_time
            del self.active_vehicles[p]

        return new_events

    @property
    def total_vehicles_recognized(self) -> int:
        """Returns the total number of discrete vehicle events logged this session."""
        return len(self.all_events)

    def get_latest_recognition(self) -> Optional[VehicleEvent]:
        """Returns the most recently created VehicleEvent, or None."""
        return self.latest_event

    def get_all_events(self) -> List[VehicleEvent]:
        """Returns a list of all logged VehicleEvent objects in this session."""
        return list(self.all_events)

    def get_summary(self) -> Dict[str, Any]:
        """Returns a high-level summary of the current session."""
        latest = self.latest_event
        return {
            "total_recognized": self.total_vehicles_recognized,
            "active_vehicles": list(self.active_vehicles.keys()),
            "cooldown_seconds": self.cooldown_seconds,
            "csv_path": self.csv_path,
            "latest_plate": latest.plate_number if latest else None,
            "latest_time": latest.timestamp_str if latest else None,
        }

    def save_all_to_csv(self, csv_path: Optional[str] = None):
        """
        Finalizes and saves all session events to CSV.
        Ensures total frames_observed and updated metric values are persisted.
        """
        if not self.save_to_csv:
            return

        target_path = csv_path or self.csv_path
        output_dir = os.path.dirname(target_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        try:
            with open(target_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.CSV_COLUMNS)
                for ev in self.all_events:
                    writer.writerow(ev.to_csv_row())
        except IOError as e:
            print(f"[!] Warning: Could not write finalized events to CSV '{target_path}': {e}")

