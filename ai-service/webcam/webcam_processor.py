"""
Webcam Processor Module for Live Number Plate Recognition & Single-Camera Line Crossing
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import cv2
import numpy as np
import requests

_AI_SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(_AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_DIR))

_PROJECT_ROOT = _AI_SERVICE_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from detection.plate_detector import PlateDetector
from ocr.plate_ocr import PlateOCR
from tracking.plate_tracker import PlateTracker
from tracking.event_manager import VehicleEventManager
from tracking.line_crossing import LineCrossingDetector

# Default Phase 3 Configurations
DEFAULT_CAMERA_ID = "GATE_CAMERA_01"
DEFAULT_LINE_POSITION_PERCENT = 50.0
DEFAULT_DEAD_ZONE = 20
DEFAULT_MIN_TRACK_AGE = 5
DEFAULT_MIN_VERTICAL_MOVEMENT = 15
DEFAULT_EVENT_COOLDOWN_SECONDS = 5.0


class WebcamProcessor:
    """
    Handles live camera capture, real-time plate tracking, OCR scheduling,
    virtual horizontal line crossing detection (ENTRY/EXIT), HUD rendering,
    image persistence, and vehicle event dispatch.
    """

    def __init__(
        self,
        camera_index: int = 0,
        camera_id: str = DEFAULT_CAMERA_ID,
        line_position_percent: float = DEFAULT_LINE_POSITION_PERCENT,
        dead_zone: int = DEFAULT_DEAD_ZONE,
        min_track_age: int = DEFAULT_MIN_TRACK_AGE,
        min_vertical_movement: int = DEFAULT_MIN_VERTICAL_MOVEMENT,
        cooldown_seconds: float = DEFAULT_EVENT_COOLDOWN_SECONDS,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.35,
        api_base_url: str = "http://localhost:8000/api/v1",
        on_event_callback: Optional[Callable] = None,
    ):
        self.camera_index = camera_index
        self.camera_id = camera_id
        self.detector = PlateDetector(model_path=model_path, conf_threshold=conf_threshold)
        self.ocr = PlateOCR(gpu=False)
        self.tracker = PlateTracker()
        self.event_manager = VehicleEventManager(cooldown_seconds=cooldown_seconds)
        self.line_crossing = LineCrossingDetector(
            camera_id=camera_id,
            line_position_percent=line_position_percent,
            dead_zone=dead_zone,
            min_track_age=min_track_age,
            min_vertical_movement=min_vertical_movement,
            cooldown_seconds=cooldown_seconds,
        )
        self.api_base_url = api_base_url.rstrip("/")
        self.on_event_callback = on_event_callback
        self.is_running = False

        # Visual indicator for recent crossing events (for HUD flashing)
        self.last_crossing_type: Optional[str] = None
        self.last_crossing_time: float = 0.0

        # Storage directories
        self.vehicles_dir = _PROJECT_ROOT / "storage" / "vehicles"
        self.plates_dir = _PROJECT_ROOT / "storage" / "plates"
        self.vehicles_dir.mkdir(parents=True, exist_ok=True)
        self.plates_dir.mkdir(parents=True, exist_ok=True)

    def save_event_images(
        self, frame: np.ndarray, plate_crop: np.ndarray, plate_number: str
    ) -> tuple[str, str]:
        """Saves full frame and cropped plate only when a confirmed event occurs."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        clean_plate = "".join(c for c in plate_number if c.isalnum())
        vehicle_filename = f"vehicle_{clean_plate}_{timestamp}.jpg"
        plate_filename = f"plate_{clean_plate}_{timestamp}.jpg"

        vehicle_path = self.vehicles_dir / vehicle_filename
        plate_path = self.plates_dir / plate_filename

        cv2.imwrite(str(vehicle_path), frame)
        if plate_crop is not None and plate_crop.size > 0:
            cv2.imwrite(str(plate_path), plate_crop)
        else:
            cv2.imwrite(str(plate_path), frame)

        rel_vehicle = f"storage/vehicles/{vehicle_filename}"
        rel_plate = f"storage/plates/{plate_filename}"
        return rel_vehicle, rel_plate

    def dispatch_event_to_backend(self, event_data: dict):
        """Sends recognition event to backend API if available."""
        if not self.api_base_url:
            return
        url = f"{self.api_base_url}/recognitions/"
        try:
            resp = requests.post(url, json=event_data, timeout=3.0)
            if resp.status_code in (200, 201):
                print(f"[API] Event dispatched successfully: {event_data.get('plate_number')} ({event_data.get('movement_type')})")
            else:
                print(f"[API] Backend returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            # Backend might not be running in isolated script mode, which is expected
            pass

    def draw_virtual_line(self, frame: np.ndarray):
        """Draws the virtual horizontal line, dead zone boundaries, and crossing feedback."""
        h, w = frame.shape[:2]
        line_y = int(self.line_crossing.get_line_y(h))
        dz = self.line_crossing.dead_zone

        now = time.time()
        # Visual pulse if crossing occurred within 2 seconds
        is_recent_event = (now - self.last_crossing_time) < 2.0
        if is_recent_event and self.last_crossing_type == "ENTRY":
            line_color = (0, 255, 0)      # Bright Green for ENTRY
            line_thickness = 3
        elif is_recent_event and self.last_crossing_type == "EXIT":
            line_color = (0, 0, 255)      # Bright Red for EXIT
            line_thickness = 3
        else:
            line_color = (0, 220, 255)    # Amber/Yellow default
            line_thickness = 2

        # Draw main horizontal virtual line
        cv2.line(frame, (0, line_y), (w, line_y), line_color, line_thickness)

        # Draw subtle dashed/thin dead zone lines
        above_boundary = line_y - dz
        below_boundary = line_y + dz
        cv2.line(frame, (0, above_boundary), (w, above_boundary), (80, 80, 80), 1, cv2.LINE_AA)
        cv2.line(frame, (0, below_boundary), (w, below_boundary), (80, 80, 80), 1, cv2.LINE_AA)

        # Label badges on left and right
        font = cv2.FONT_HERSHEY_SIMPLEX
        label_text = f"ENTRY <-- [{self.line_crossing.line_position_percent:.0f}%] --> EXIT"
        (lw, lh), _ = cv2.getTextSize(label_text, font, 0.45, 1)

        # Left tag
        cv2.rectangle(frame, (10, line_y - 18), (10 + lw + 12, line_y - 2), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, line_y - 18), (10 + lw + 12, line_y - 2), line_color, 1)
        cv2.putText(frame, label_text, (16, line_y - 6), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Right direction arrows
        dir_text = "TOP->DOWN: ENTRY | DOWN->UP: EXIT"
        (rw, rh), _ = cv2.getTextSize(dir_text, font, 0.42, 1)
        rx = w - rw - 16
        cv2.rectangle(frame, (rx - 6, line_y + 4), (w - 10, line_y + 20), (20, 20, 20), -1)
        cv2.putText(frame, dir_text, (rx, line_y + 16), font, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

    def draw_hud(self, frame: np.ndarray, fps: float):
        """Draws top status bar with Camera ID, Line info, FPS, and Latest Movement."""
        h, w = frame.shape[:2]
        hud_h = 44

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, hud_h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        # Camera & Line
        cv2.putText(
            frame,
            f"CAMERA: {self.camera_id} | LINE: {self.line_crossing.line_position_percent:.0f}%",
            (12, 18),
            font,
            0.46,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            f"FPS: {fps:.1f} | Events: {len(self.event_manager.all_events)}",
            (12, 36),
            font,
            0.44,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

        if self.event_manager.latest_event:
            ev = self.event_manager.latest_event
            cat_tag = "COLLEGE" if ev.vehicle_category == "COLLEGE_VEHICLE" else "OTHER"
            name_str = f" ({ev.vehicle_name})" if ev.vehicle_name else ""
            txt = f"[{cat_tag}] {ev.plate_number}{name_str} | {ev.movement_type} -> {ev.current_status}"
            mv_color = (0, 255, 0) if ev.movement_type == "ENTRY" else (0, 100, 255)
            cv2.putText(
                frame,
                txt,
                (280, 26),
                font,
                0.48,
                mv_color,
                1,
                cv2.LINE_AA,
            )

    def draw_live_annotation(self, frame: np.ndarray, track):
        """Draws bounding box, center point, and plate info on the frame."""
        x1, y1, x2, y2 = map(int, track.box)
        cx, cy = int(track.center_x), int(track.center_y)

        # Draw center point
        cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)

        if track.is_stable and track.stable_text:
            college_info = self.event_manager.get_college_vehicle_info(track.stable_text)
            if college_info:
                box_color = (0, 200, 255)
                label_bg_color = (0, 140, 220)
                text_color = (10, 10, 10)
                v_name = college_info.get("name", "College Vehicle")
                display_label = (
                    f"[COLLEGE] {v_name} ({track.stable_text}) | "
                    f"YOLO: {track.yolo_conf * 100:.0f}% OCR: {track.stable_ocr_conf * 100:.0f}%"
                )
            else:
                box_color = (0, 230, 0)
                label_bg_color = (0, 160, 0)
                text_color = (255, 255, 255)
                display_label = (
                    f"[OTHER] {track.stable_text} | "
                    f"YOLO: {track.yolo_conf * 100:.0f}% OCR: {track.stable_ocr_conf * 100:.0f}%"
                )
        else:
            box_color = (220, 180, 50)
            label_bg_color = (160, 120, 20)
            text_color = (255, 255, 255)
            display_label = f"Plate ({track.yolo_conf * 100:.0f}%) Y={cy}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.48
        thickness = 1
        (tw, th), baseline = cv2.getTextSize(display_label, font, font_scale, thickness)

        lbl_y1 = max(0, y1 - th - 8)
        lbl_y2 = y1
        lbl_x1 = x1
        lbl_x2 = min(frame.shape[1], x1 + tw + 8)

        cv2.rectangle(frame, (lbl_x1, lbl_y1), (lbl_x2, lbl_y2), label_bg_color, -1)
        cv2.putText(
            frame,
            display_label,
            (lbl_x1 + 4, lbl_y2 - baseline - 2),
            font,
            font_scale,
            text_color,
            thickness,
            cv2.LINE_AA,
        )

    def run(self):
        """Runs the continuous webcam loop."""
        print(f"[*] Opening webcam device: {self.camera_index} (Camera ID: {self.camera_id})")
        if sys.platform.startswith("win"):
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            print(f"[!] Error: Could not open camera {self.camera_index}")
            return

        self.is_running = True
        prev_time = time.time()

        try:
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    break

                curr_time = time.time()
                fps = 1.0 / (curr_time - prev_time) if curr_time > prev_time else 30.0
                prev_time = curr_time

                frame_h = frame.shape[0]

                # 1. YOLO Detection
                detections = self.detector.detect(frame)
                det_inputs = [(d["box"], d["confidence"]) for d in detections]

                # 2. Tracking
                active_tracks = self.tracker.update(det_inputs)
                active_track_ids = set()

                # 3. OCR & Line Crossing Analysis on tracked plates
                for track in active_tracks:
                    active_track_ids.add(track.track_id)

                    # Scheduled OCR
                    if track.should_run_ocr():
                        crop = self.detector.crop(frame, track.box)
                        best_cand, _ = self.ocr.recognize(crop)
                        if best_cand and best_cand.get("is_valid"):
                            track.add_ocr_result(
                                best_cand["text"],
                                best_cand["confidence"],
                                best_cand.get("description", ""),
                            )

                    # 4. Line crossing check using track center_y
                    crossing = self.line_crossing.update(
                        track_id=track.track_id,
                        center_y=track.center_y,
                        frame_height=frame_h,
                    )

                    # Line crossing event triggered ONLY when stable OCR exists and crossing detected
                    if crossing and track.is_stable and track.stable_text:
                        plate_crop = self.detector.crop(frame, track.box)
                        v_img_path, p_img_path = self.save_event_images(frame, plate_crop, track.stable_text)

                        event = self.event_manager.process_plate_sighting(
                            plate_number=track.stable_text,
                            yolo_conf=track.yolo_conf,
                            ocr_conf=track.stable_ocr_conf,
                            frames_observed=track.total_frames_observed,
                            movement_type=crossing,
                            camera_id=self.camera_id,
                            vehicle_image_path=v_img_path,
                            plate_image_path=p_img_path,
                        )

                        self.last_crossing_type = crossing
                        self.last_crossing_time = time.time()

                        if event:
                            payload = {
                                "plate_number": event.plate_number,
                                "vehicle_category": event.vehicle_category,
                                "movement_type": event.movement_type,
                                "current_status": event.current_status,
                                "camera_id": self.camera_id,
                                "yolo_confidence": float(event.yolo_confidence),
                                "ocr_confidence": float(event.ocr_confidence),
                                "college_vehicle_id": event.college_vehicle_id,
                                "vehicle_name": event.vehicle_name,
                                "vehicle_image_path": v_img_path,
                                "plate_image_path": p_img_path,
                                "timestamp": event.timestamp,
                            }
                            self.dispatch_event_to_backend(payload)
                            if self.on_event_callback:
                                self.on_event_callback(event, frame, plate_crop)

                    self.draw_live_annotation(frame, track)

                # Clean up expired crossing tracks
                self.line_crossing.cleanup_expired_tracks(list(active_track_ids))

                # Draw Virtual Line & HUD
                self.draw_virtual_line(frame)
                self.draw_hud(frame, fps)

                cv2.imshow("Indian Vehicle Number Plate Recognition", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):  # 'q' or ESC
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.is_running = False


if __name__ == "__main__":
    processor = WebcamProcessor()
    processor.run()
