"""
================================================================================
Real-Time Webcam Indian Vehicle Number Plate Recognition System
================================================================================
Features:
- Continuous frame capture via OpenCV webcam.
- Number plate detection using YOLOv8/26 model (best.pt).
- Reuses robust preprocessing, validation, scoring, and candidate-selection
  from plate_ocr.py.
- Filters out invalid/random OCR text using official Indian plate validation rules.
- Temporal stability mechanism across consecutive frames to prevent flickering.
- CPU-optimized execution with smart frame scheduling and targeted variants.
- Clean real-time HUD and bounding box overlays with YOLO & OCR confidences.
- Safe termination on pressing 'Q' or 'ESC'.
================================================================================
"""

import os
import sys
import time
from collections import deque, Counter
import cv2
import easyocr
from ultralytics import YOLO

# Reuse established OCR pipeline & constants from plate_ocr.py
from plate_ocr import (
    MODEL_PATH,
    crop_plate_with_padding,
    generate_preprocessing_variants,
    select_best_ocr_candidate,
    validate_indian_plate,
)
from vehicle_event_manager import VehicleEventManager

# ==============================================================================
# Configuration Parameters
# ==============================================================================
CAMERA_INDEX = 0             # Default webcam index
FRAME_WIDTH = 640            # Frame width (balanced for CPU speed and clarity)
FRAME_HEIGHT = 480           # Frame height
YOLO_CONF_THRESHOLD = 0.35   # Minimum YOLO detection confidence
OCR_INTERVAL_UNSTABLE = 3    # Run OCR every N frames when stabilizing a track
OCR_INTERVAL_STABLE = 12     # Run OCR every N frames once already stable to verify
MIN_STABLE_COUNT = 2         # Minimum matching valid OCR readings needed for stability
HISTORY_WINDOW_SIZE = 8      # Number of recent OCR readings tracked per plate
MAX_DISAPPEARED_FRAMES = 15  # Frames to retain a track after it leaves view
IOU_MATCH_THRESHOLD = 0.3    # Minimum IoU to associate detections across frames


# ==============================================================================
# Helper Math: IoU Calculation for Tracking
# ==============================================================================
def compute_iou(box1, box2):
    """
    Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2].
    """
    x1_max = max(box1[0], box2[0])
    y1_max = max(box1[1], box2[1])
    x2_min = min(box1[2], box2[2])
    y2_min = min(box1[3], box2[3])

    intersection_w = max(0, x2_min - x1_max)
    intersection_h = max(0, y2_min - y1_max)
    intersection_area = intersection_w * intersection_h

    area1 = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
    area2 = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])

    union_area = area1 + area2 - intersection_area
    if union_area <= 0:
        return 0.0
    return intersection_area / union_area


# ==============================================================================
# Temporal Stability & Plate Tracker
# ==============================================================================
class TrackedPlate:
    """
    Maintains temporal state and OCR history for a detected plate over time.
    """
    def __init__(self, track_id, box, yolo_conf):
        self.track_id = track_id
        self.box = box
        self.yolo_conf = yolo_conf
        self.disappeared = 0
        self.frames_since_ocr = 0
        self.total_frames_observed = 1

        # OCR History buffer: stores recent valid OCR readings (text, confidence)
        self.ocr_history = deque(maxlen=HISTORY_WINDOW_SIZE)

        # Stability state
        self.is_stable = False
        self.stable_text = None
        self.stable_ocr_conf = 0.0
        self.stable_desc = ""

    def update_detection(self, box, yolo_conf):
        """Updates box position and resets disappearance counter."""
        self.box = box
        self.yolo_conf = yolo_conf
        self.disappeared = 0
        self.frames_since_ocr += 1
        self.total_frames_observed += 1

    def add_ocr_result(self, text, conf, desc):
        """
        Records a valid OCR result and evaluates temporal stability.
        Only valid Indian plate results should be passed here.
        """
        self.frames_since_ocr = 0
        if not text:
            return

        self.ocr_history.append((text, conf, desc))

        # Check frequency of readings in recent window
        texts = [item[0] for item in self.ocr_history]
        counts = Counter(texts)
        most_common_text, frequency = counts.most_common(1)[0]

        # Require at least MIN_STABLE_COUNT matching readings to declare stability
        if frequency >= MIN_STABLE_COUNT:
            matching_items = [item for item in self.ocr_history if item[0] == most_common_text]
            avg_conf = sum(item[1] for item in matching_items) / len(matching_items)
            desc_val = matching_items[-1][2]

            self.is_stable = True
            self.stable_text = most_common_text
            self.stable_ocr_conf = avg_conf
            self.stable_desc = desc_val

    def should_run_ocr(self):
        """
        Determines if OCR should be executed on this frame to conserve CPU.
        """
        # Run immediately on new detections with no history
        if len(self.ocr_history) == 0:
            return True

        if not self.is_stable:
            # Unstable track: run frequently until stability is established
            return self.frames_since_ocr >= OCR_INTERVAL_UNSTABLE
        else:
            # Already stable: run periodically to verify or refresh
            return self.frames_since_ocr >= OCR_INTERVAL_STABLE


class PlateTracker:
    """
    Coordinates multi-plate tracking across continuous webcam video frames.
    """
    def __init__(self):
        self.next_id = 1
        self.tracks = {}  # track_id -> TrackedPlate

    def update(self, current_detections):
        """
        Matches current frame detections [ (box, yolo_conf), ... ]
        with existing tracked plates using IoU.
        Returns the active TrackedPlate objects.
        """
        updated_tracks = []
        unmatched_detections = list(current_detections)

        # Match existing tracks with best overlapping detection
        for track_id, track in list(self.tracks.items()):
            best_iou = 0.0
            best_det_idx = -1

            for idx, (det_box, det_conf) in enumerate(unmatched_detections):
                iou = compute_iou(track.box, det_box)
                if iou > best_iou:
                    best_iou = iou
                    best_det_idx = idx

            if best_iou >= IOU_MATCH_THRESHOLD and best_det_idx != -1:
                det_box, det_conf = unmatched_detections.pop(best_det_idx)
                track.update_detection(det_box, det_conf)
                updated_tracks.append(track)
            else:
                track.disappeared += 1
                track.frames_since_ocr += 1
                if track.disappeared > MAX_DISAPPEARED_FRAMES:
                    del self.tracks[track_id]

        # Register any remaining unmatched detections as new tracks
        for det_box, det_conf in unmatched_detections:
            new_track = TrackedPlate(self.next_id, det_box, det_conf)
            self.tracks[self.next_id] = new_track
            updated_tracks.append(new_track)
            self.next_id += 1

        return updated_tracks


# ==============================================================================
# Live Annotation & Drawing
# ==============================================================================
def draw_live_annotation(frame, track):
    """
    Draws bounding box and informative tags for a tracked plate:
    - If stable: Bright green box with plate number, YOLO conf, and OCR conf.
    - If verifying/unstable: Cyan box indicating plate detected & reading.
      Does NOT display raw/random OCR noise.
    """
    x1, y1, x2, y2 = map(int, track.box)

    if track.is_stable and track.stable_text:
        # Recognized & Stable
        box_color = (0, 230, 0)      # Bright Green
        label_bg_color = (0, 180, 0)
        text_color = (255, 255, 255)
        display_label = (
            f"{track.stable_text} | YOLO: {track.yolo_conf * 100:.0f}% "
            f"| OCR: {track.stable_ocr_conf * 100:.0f}%"
        )
    else:
        # Detected by YOLO, OCR stabilizing or pending
        box_color = (0, 215, 255)    # Amber/Cyan
        label_bg_color = (0, 160, 200)
        text_color = (20, 20, 20)
        display_label = f"Plate Detected (YOLO: {track.yolo_conf * 100:.0f}%) - Reading..."

    # Draw plate bounding box
    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

    # Calculate text size and placement directly above bounding box
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    thickness = 2
    (text_w, text_h), baseline = cv2.getTextSize(display_label, font, font_scale, thickness)

    # Place above box; fallback below box if near top margin
    label_y1 = max(0, y1 - text_h - 10)
    label_y2 = label_y1 + text_h + 8
    label_x1 = max(0, x1)
    label_x2 = min(frame.shape[1], label_x1 + text_w + 12)

    # Draw label badge
    cv2.rectangle(frame, (label_x1, label_y1), (label_x2, label_y2), label_bg_color, -1)
    cv2.putText(
        frame,
        display_label,
        (label_x1 + 6, label_y2 - baseline - 2),
        font,
        font_scale,
        text_color,
        thickness,
        cv2.LINE_AA,
    )


def draw_system_hud(frame, fps, active_count, total_vehicles_recognized, latest_event=None):
    """
    Draws a dashboard banner on the top of the video feed showing:
    Line 1: FPS, Active Tracks, Total Vehicles Recognized, Exit Prompt.
    Line 2: Latest Recognized Plate and its timestamp.
    """
    hud_h = 58
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], hud_h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)

    font = cv2.FONT_HERSHEY_SIMPLEX

    # Line 1: Real-time system performance & event count
    line1_text = (
        f"FPS: {fps:4.1f} | Active: {active_count} | "
        f"Total Vehicles Recognized: {total_vehicles_recognized} | Press 'Q' to Exit"
    )
    cv2.putText(
        frame,
        line1_text,
        (12, 22),
        font,
        0.50,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )

    # Line 2: Latest recognition and timestamp
    if latest_event and latest_event.plate_number:
        line2_text = (
            f"Latest: {latest_event.plate_number} at {latest_event.timestamp_str} "
            f"(YOLO: {latest_event.yolo_confidence * 100:.0f}%, OCR: {latest_event.ocr_confidence * 100:.0f}%)"
        )
        cv2.putText(
            frame,
            line2_text,
            (12, 46),
            font,
            0.50,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    else:
        line2_text = "Latest: None (Waiting for verified plate...)"
        cv2.putText(
            frame,
            line2_text,
            (12, 46),
            font,
            0.48,
            (180, 180, 180),
            1,
            cv2.LINE_AA,
        )


# ==============================================================================
# Live Recognition Core Loop
# ==============================================================================
def run_webcam_recognition(
    model_path=MODEL_PATH,
    camera_index=CAMERA_INDEX,
    frame_width=FRAME_WIDTH,
    frame_height=FRAME_HEIGHT,
    cooldown_seconds=10.0,
    save_to_csv=True,
    csv_path=os.path.join("output", "recognition_events.csv"),
    max_frames=None,  # Useful for headless/automated testing
):
    """
    Initializes models and processes continuous webcam feed with vehicle event tracking.
    """
    print("=" * 65)
    print("   INDIAN VEHICLE NUMBER PLATE RECOGNITION (LIVE WEBCAM)")
    print("=" * 65)
    print(f"[*] Loading YOLO model from '{model_path}'...")
    if not os.path.exists(model_path):
        print(f"[!] ERROR: Model file '{model_path}' not found.")
        return False

    model = YOLO(model_path)
    print("[+] YOLO model loaded successfully.")

    print("[*] Initializing EasyOCR engine (CPU Mode)...")
    ocr_reader = easyocr.Reader(["en"], gpu=False)
    print("[+] EasyOCR engine ready.")

    print(f"[*] Opening webcam index {camera_index}...")
    # On Windows, cv2.CAP_DSHOW provides fast camera initialization
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print(f"[!] ERROR: Could not open webcam at index {camera_index}.")
        print("[!] Tip: Verify that your webcam is plugged in and permissions are enabled.")
        return False

    # Configure resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[+] Webcam connected. Resolution: {actual_w}x{actual_h}")
    print(f"[+] Event Manager initialized with {cooldown_seconds}s cooldown.")
    if save_to_csv:
        print(f"[+] Saving recognition events to '{csv_path}'")
    print("[+] Recognition loop running. Press 'Q' in the video window to quit.\n")

    tracker = PlateTracker()
    event_manager = VehicleEventManager(
        cooldown_seconds=cooldown_seconds,
        save_to_csv=save_to_csv,
        csv_path=csv_path,
    )

    window_name = "Indian Number Plate Recognition - Live Webcam"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    prev_time = time.time()
    fps_frame_count = 0
    total_frames_processed = 0
    fps = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[!] Warning: Received empty frame from webcam. Retrying...")
                time.sleep(0.05)
                continue

            total_frames_processed += 1
            fps_frame_count += 1
            curr_time = time.time()
            elapsed = curr_time - prev_time
            if elapsed >= 0.5:
                fps = fps_frame_count / elapsed
                fps_frame_count = 0
                prev_time = curr_time

            # 1. Run YOLO detection on current frame (CPU mode, verbose off)
            yolo_results = model(frame, conf=YOLO_CONF_THRESHOLD, verbose=False)[0]

            current_detections = []
            if yolo_results.boxes and len(yolo_results.boxes) > 0:
                for box in yolo_results.boxes:
                    coords = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    current_detections.append((coords, conf))

            # 2. Update multi-plate tracker
            active_tracks = tracker.update(current_detections)

            # 3. Process OCR for eligible tracks
            for track in active_tracks:
                # Run OCR only when schedule allows to preserve CPU throughput
                if track.should_run_ocr():
                    # Crop plate with proportional padding
                    cropped = crop_plate_with_padding(frame, track.box)
                    if cropped.size > 0 and cropped.shape[0] >= 10 and cropped.shape[1] >= 20:
                        # Generate preprocessing variants from plate_ocr.py
                        all_variants = generate_preprocessing_variants(cropped)

                        # For real-time CPU speed, evaluate the top 3 highest-performing variants:
                        # CLAHE, Denoised Otsu, and Raw
                        targeted_variants = {
                            "clahe": all_variants["clahe"],
                            "denoised_otsu": all_variants["denoised_otsu"],
                            "raw": all_variants["raw"],
                        }

                        # Select candidate and validate Indian plate format
                        best_cand, _ = select_best_ocr_candidate(ocr_reader, targeted_variants)

                        if best_cand and best_cand["is_valid"]:
                            # Only record if the plate text passes Indian format validation
                            track.add_ocr_result(
                                best_cand["text"],
                                best_cand["confidence"],
                                best_cand["description"],
                            )
                        else:
                            # If OCR produced text but failed validation, record empty to avoid noise
                            track.frames_since_ocr = 0

            # 4. Render bounding boxes and recognized labels on frame
            for track in active_tracks:
                draw_live_annotation(frame, track)

            # 5. Collect stable plates for vehicle recognition event tracking
            current_stable_plates = []
            for track in active_tracks:
                if track.is_stable and track.stable_text:
                    current_stable_plates.append({
                        "plate_number": track.stable_text,
                        "yolo_conf": track.yolo_conf,
                        "ocr_conf": track.stable_ocr_conf,
                        "frames_observed": track.total_frames_observed,
                    })

            # Update event manager (handles continuous visibility deduplication and cooldowns)
            event_manager.update_frame(current_stable_plates)

            # 6. Draw system status HUD with total recognized counter and latest plate info
            draw_system_hud(
                frame,
                fps=fps,
                active_count=len(active_tracks),
                total_vehicles_recognized=event_manager.total_vehicles_recognized,
                latest_event=event_manager.get_latest_recognition(),
            )

            # 7. Display frame
            cv2.imshow(window_name, frame)

            # Check for user exit (Q or ESC)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == ord("Q") or key == 27:
                print("\n[*] 'Q' pressed. Exiting recognition loop...")
                break

            if max_frames and total_frames_processed >= max_frames:
                print(f"\n[*] Reached test limit of {max_frames} frames. Stopping.")
                break

    except KeyboardInterrupt:
        print("\n[*] Interrupted by user (Ctrl+C). Closing gracefully...")
    finally:
        # Safe release of camera resources
        cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[+] Webcam released and display windows closed.")

        # Finalize and persist all event metrics (including final frames_observed) to CSV
        if save_to_csv:
            event_manager.save_all_to_csv()

        summary = event_manager.get_summary()
        print("\n" + "=" * 65)
        print("   SESSION SUMMARY")
        print("=" * 65)
        print(f"[*] Total Vehicles Recognized: {summary['total_recognized']}")
        if summary["latest_plate"]:
            print(f"[*] Latest Vehicle: {summary['latest_plate']} at {summary['latest_time']}")
        if save_to_csv:
            print(f"[*] Events saved to CSV: {summary['csv_path']}")
        print("=" * 65)

    return True


# ==============================================================================
# Script Entry Point
# ==============================================================================
if __name__ == "__main__":
    run_webcam_recognition()
