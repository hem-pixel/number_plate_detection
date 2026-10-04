"""
================================================================================
End-to-End Pipeline Integration Test with YOLO, EasyOCR, and Event Manager
================================================================================
Simulates a live webcam feed using the real test.jpeg image across multiple frames.
Verifies that:
1. YOLO (best.pt) detects plates in the frame.
2. EasyOCR validates the Indian plate format (TN45BD7321).
3. PlateTracker achieves temporal stability across continuous frames.
4. VehicleEventManager records exactly ONE event for continuous visibility.
5. The CSV file is created in output/ with the exact requested columns and values.
================================================================================
"""

import os
import csv
import cv2
import easyocr
from ultralytics import YOLO

from plate_ocr import (
    MODEL_PATH,
    crop_plate_with_padding,
    generate_preprocessing_variants,
    select_best_ocr_candidate,
)
from webcam_plate_recognition import PlateTracker, draw_live_annotation, draw_system_hud
from vehicle_event_manager import VehicleEventManager


def run_pipeline_test():
    image_path = "test.jpeg"
    assert os.path.exists(image_path), f"Test image '{image_path}' not found."
    test_frame = cv2.imread(image_path)
    assert test_frame is not None, "Failed to read test image."

    test_csv = os.path.join("output", "integration_test_events.csv")
    if os.path.exists(test_csv):
        os.remove(test_csv)

    print("[*] Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    print("[*] Initializing EasyOCR...")
    ocr_reader = easyocr.Reader(["en"], gpu=False)

    tracker = PlateTracker()
    event_manager = VehicleEventManager(cooldown_seconds=10.0, save_to_csv=True, csv_path=test_csv)

    print("[*] Simulating 10 consecutive frames of the same vehicle...")
    for frame_idx in range(10):
        # 1. YOLO detection
        raw_results = list(model(test_frame, conf=0.35, verbose=False))
        detections = []
        if raw_results:
            first_res = raw_results[0]
            boxes_obj = getattr(first_res, "boxes", None)
            if boxes_obj is not None:
                for box in boxes_obj:
                    coords = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    detections.append((coords, conf))

        # 2. Plate Tracker
        active_tracks = tracker.update(detections)

        # 3. OCR on eligible tracks
        for track in active_tracks:
            if track.should_run_ocr():
                cropped = crop_plate_with_padding(test_frame, track.box)
                if cropped.size > 0:
                    variants = generate_preprocessing_variants(cropped)
                    targeted = {
                        "clahe": variants["clahe"],
                        "denoised_otsu": variants["denoised_otsu"],
                        "raw": variants["raw"],
                    }
                    best_cand, _ = select_best_ocr_candidate(ocr_reader, targeted)
                    if best_cand and best_cand["is_valid"]:
                        track.add_ocr_result(
                            best_cand["text"],
                            best_cand["confidence"],
                            best_cand["description"],
                        )
                    else:
                        track.frames_since_ocr = 0

        # 4. Collect stable plates
        stable_plates = []
        for track in active_tracks:
            if track.is_stable and track.stable_text:
                stable_plates.append({
                    "plate_number": track.stable_text,
                    "yolo_conf": track.yolo_conf,
                    "ocr_conf": track.stable_ocr_conf,
                    "frames_observed": track.total_frames_observed,
                })

        # 5. Update Event Manager
        event_manager.update_frame(stable_plates)

    # 6. Save all to CSV (finalize)
    event_manager.save_all_to_csv()

    print(f"\n[+] Total Frames Processed: 10")
    print(f"[+] Total Discrete Vehicle Events: {event_manager.total_vehicles_recognized}")
    latest = event_manager.get_latest_recognition()
    if latest:
        print(f"[+] Recognized Plate: {latest.plate_number}")
        print(f"[+] YOLO Confidence: {latest.yolo_confidence:.3f}")
        print(f"[+] OCR Confidence: {latest.ocr_confidence:.3f}")
        print(f"[+] Frames Observed: {latest.frames_observed}")

    # Assertions
    assert event_manager.total_vehicles_recognized == 1, (
        f"Expected exactly 1 event for continuous visibility, got {event_manager.total_vehicles_recognized}"
    )
    assert latest is not None, "Expected latest recognition event to be present"
    assert latest.plate_number == "TN45BD7321", (
        f"Expected plate TN45BD7321, got {latest.plate_number}"
    )

    # Verify CSV content
    assert os.path.exists(test_csv), "CSV file was not created."
    with open(test_csv, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        print("\n[*] CSV Content:")
        for r in rows:
            print("   ", r)
        assert len(rows) == 2, f"Expected header + 1 row in CSV, got {len(rows)} lines"
        assert rows[0] == ["timestamp", "plate_number", "yolo_confidence", "ocr_confidence", "frames_observed", "status"]
        assert rows[1][1] == "TN45BD7321"
        assert rows[1][4] == "10", f"Expected finalized frames_observed to be 10, got {rows[1][4]}"
        assert rows[1][5] == "Verified"

    if os.path.exists(test_csv):
        os.remove(test_csv)

    print("\n[PASS] End-to-end integration test completed successfully!")


if __name__ == "__main__":
    run_pipeline_test()
