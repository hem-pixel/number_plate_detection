"""
Webcam Processor Module for Live Number Plate Recognition
"""

import time
from typing import Optional, Callable
import cv2
import numpy as np

import sys
from pathlib import Path

_AI_SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(_AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_DIR))

from detection.plate_detector import PlateDetector
from ocr.plate_ocr import PlateOCR
from tracking.plate_tracker import PlateTracker
from tracking.event_manager import VehicleEventManager



class WebcamProcessor:
    """
    Handles live camera capture, real-time plate tracking, OCR scheduling,
    HUD rendering, and vehicle event triggering.
    """

    def __init__(
        self,
        camera_index: int = 0,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.35,
        cooldown_seconds: float = 10.0,
        on_event_callback: Optional[Callable] = None,
    ):
        self.camera_index = camera_index
        self.detector = PlateDetector(model_path=model_path, conf_threshold=conf_threshold)
        self.ocr = PlateOCR(gpu=False)
        self.tracker = PlateTracker()
        self.event_manager = VehicleEventManager(cooldown_seconds=cooldown_seconds)
        self.on_event_callback = on_event_callback
        self.is_running = False

    def draw_hud(self, frame: np.ndarray, fps: float):
        """Draws top status bar with FPS, recognition metrics, and active vehicle counts."""
        h, w = frame.shape[:2]
        hud_h = 42

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, hud_h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (12, 26),
            font,
            0.55,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

        total_recognized = len(self.event_manager.all_events)
        cv2.putText(
            frame,
            f"Events: {total_recognized}",
            (110, 26),
            font,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        if self.event_manager.latest_event:
            ev = self.event_manager.latest_event
            cat_tag = "COLLEGE" if ev.vehicle_category == "COLLEGE_VEHICLE" else "OTHER"
            name_str = f" ({ev.vehicle_name})" if ev.vehicle_name else ""
            txt = f"[{cat_tag}] {ev.plate_number}{name_str} - {ev.movement_type}"
            color = (0, 220, 255) if cat_tag == "COLLEGE" else (200, 200, 200)
            cv2.putText(
                frame,
                txt,
                (230, 26),
                font,
                0.52,
                color,
                1,
                cv2.LINE_AA,
            )

    def draw_live_annotation(self, frame: np.ndarray, track):
        """Draws bounding box and plate info on the frame with College vs Other vehicle distinction."""
        x1, y1, x2, y2 = map(int, track.box)

        if track.is_stable and track.stable_text:
            college_info = self.event_manager.get_college_vehicle_info(track.stable_text)
            if college_info:
                # College vehicle: Gold / Amber box
                box_color = (0, 200, 255)
                label_bg_color = (0, 140, 220)
                text_color = (10, 10, 10)
                v_name = college_info.get("name", "College Vehicle")
                display_label = (
                    f"[COLLEGE BUS] {v_name} ({track.stable_text}) | "
                    f"YOLO: {track.yolo_conf * 100:.0f}% OCR: {track.stable_ocr_conf * 100:.0f}%"
                )
            else:
                # Other vehicle: Green box
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
            display_label = f"Plate Detected ({track.yolo_conf * 100:.0f}%) - Reading..."

        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.52
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
        print(f"[*] Opening webcam device: {self.camera_index}")
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

                # 1. Detection
                detections = self.detector.detect(frame)
                det_inputs = [(d["box"], d["confidence"]) for d in detections]

                # 2. Tracking
                active_tracks = self.tracker.update(det_inputs)

                # 3. OCR on tracked plates
                active_plate_numbers = []
                for track in active_tracks:
                    if track.should_run_ocr():
                        crop = self.detector.crop(frame, track.box)
                        best_cand, _ = self.ocr.recognize(crop)
                        if best_cand and best_cand.get("is_valid"):
                            track.add_ocr_result(
                                best_cand["text"],
                                best_cand["confidence"],
                                best_cand.get("description", ""),
                            )

                    if track.is_stable and track.stable_text:
                        active_plate_numbers.append(track.stable_text)
                        event = self.event_manager.process_plate_sighting(
                            plate_number=track.stable_text,
                            yolo_conf=track.yolo_conf,
                            ocr_conf=track.stable_ocr_conf,
                            frames_observed=track.total_frames_observed,
                        )
                        if event and self.on_event_callback:
                            self.on_event_callback(event, frame, self.detector.crop(frame, track.box))

                    self.draw_live_annotation(frame, track)

                self.event_manager.update_absences(active_plate_numbers)
                self.draw_hud(frame, fps)

                cv2.imshow("Indian Vehicle Number Plate Recognition", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):  # 'q' or ESC
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.is_running = False
