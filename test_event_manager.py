"""
================================================================================
Test Suite for VehicleEventManager & Recognition Event Tracking
================================================================================
Tests:
1. Single vehicle continuous visibility deduplication.
2. Disappearance and return within cooldown window (no duplicate event).
3. Disappearance and return after cooldown window (creates new event).
4. Multiple distinct vehicles visible simultaneously.
5. CSV persistence and schema validation.
================================================================================
"""

import os
import csv
import time
from vehicle_event_manager import VehicleEventManager, VehicleEvent


def test_continuous_visibility():
    """Verify that a plate visible for 50 continuous frames yields exactly 1 event."""
    test_csv = os.path.join("output", "test_continuous.csv")
    if os.path.exists(test_csv):
        os.remove(test_csv)

    manager = VehicleEventManager(cooldown_seconds=10.0, save_to_csv=True, csv_path=test_csv)

    base_time = 1000.0
    for i in range(50):
        t = base_time + (i * 0.1)  # 10 fps, 5 seconds total
        plates = [{
            "plate_number": "TN45BD7321",
            "yolo_conf": 0.88,
            "ocr_conf": 0.95,
            "frames_observed": i + 1,
        }]
        new_events = manager.update_frame(plates, current_time=t)
        if i == 0:
            assert len(new_events) == 1, f"Expected 1 event on frame 0, got {len(new_events)}"
            assert new_events[0].plate_number == "TN45BD7321"
        else:
            assert len(new_events) == 0, f"Expected 0 new events on frame {i}, got {len(new_events)}"

    assert manager.total_vehicles_recognized == 1, f"Expected 1 total event, got {manager.total_vehicles_recognized}"
    active_ev = manager.active_vehicles["TN45BD7321"]
    assert active_ev.frames_observed == 50
    assert active_ev.first_detected_time == base_time
    assert abs(active_ev.last_seen_time - (base_time + 49 * 0.1)) < 1e-4

    # Verify CSV has exactly header + 1 row
    with open(test_csv, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 2, f"Expected 2 lines in CSV (header + 1 row), got {len(reader)}"
        assert reader[0] == ["timestamp", "plate_number", "yolo_confidence", "ocr_confidence", "frames_observed", "status"]
        assert reader[1][1] == "TN45BD7321"

    if os.path.exists(test_csv):
        os.remove(test_csv)
    print("[PASS] test_continuous_visibility passed.")


def test_cooldown_behavior():
    """
    Verify:
    - Disappearance for 3 seconds (< 10s cooldown) -> reattaches to existing event (0 new events).
    - Disappearance for 12 seconds (>= 10s cooldown) -> triggers a new event (total 2 events).
    """
    test_csv = os.path.join("output", "test_cooldown.csv")
    if os.path.exists(test_csv):
        os.remove(test_csv)

    manager = VehicleEventManager(cooldown_seconds=10.0, save_to_csv=True, csv_path=test_csv)

    # 1. Vehicle seen at t=100.0 for 5 frames (100.0 to 100.4)
    for i in range(5):
        manager.update_frame([{
            "plate_number": "KA01AB1234",
            "yolo_conf": 0.90,
            "ocr_conf": 0.92,
            "frames_observed": i + 1,
        }], current_time=100.0 + i * 0.1)

    assert manager.total_vehicles_recognized == 1

    # 2. Vehicle disappears for 3 seconds (t=100.5 to 103.4)
    for i in range(30):
        manager.update_frame([], current_time=100.5 + i * 0.1)

    assert len(manager.active_vehicles) == 0, "Expected active_vehicles to be empty after disappearance"
    assert manager.total_vehicles_recognized == 1

    # 3. Vehicle returns at t=103.5 (only 3.1s elapsed, cooldown is 10.0s)
    events = manager.update_frame([{
        "plate_number": "KA01AB1234",
        "yolo_conf": 0.91,
        "ocr_conf": 0.94,
        "frames_observed": 10,
    }], current_time=103.5)

    assert len(events) == 0, f"Expected 0 new events within cooldown window, got {len(events)}"
    assert manager.total_vehicles_recognized == 1, "Vehicle within cooldown should not increment event count"
    assert "KA01AB1234" in manager.active_vehicles

    # 4. Vehicle disappears again at t=104.0
    manager.update_frame([], current_time=104.0)

    # 5. Vehicle reappears after 15 seconds at t=119.0 (15.0s > 10.0s cooldown)
    events_after_cooldown = manager.update_frame([{
        "plate_number": "KA01AB1234",
        "yolo_conf": 0.89,
        "ocr_conf": 0.96,
        "frames_observed": 1,
    }], current_time=119.0)

    assert len(events_after_cooldown) == 1, f"Expected 1 new event after cooldown elapsed, got {len(events_after_cooldown)}"
    assert manager.total_vehicles_recognized == 2, f"Expected 2 total events, got {manager.total_vehicles_recognized}"

    with open(test_csv, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 3, f"Expected 3 lines (header + 2 rows), got {len(reader)}"

    if os.path.exists(test_csv):
        os.remove(test_csv)
    print("[PASS] test_cooldown_behavior passed.")


def test_multiple_vehicles():
    """Verify that multiple distinct plates are tracked independently."""
    test_csv = os.path.join("output", "test_multiple.csv")
    if os.path.exists(test_csv):
        os.remove(test_csv)

    manager = VehicleEventManager(cooldown_seconds=10.0, save_to_csv=True, csv_path=test_csv)

    # Frame 1: Plate A appears
    ev1 = manager.update_frame([{"plate_number": "MH12DE1433", "yolo_conf": 0.85, "ocr_conf": 0.90, "frames_observed": 3}], current_time=10.0)
    assert len(ev1) == 1
    assert manager.total_vehicles_recognized == 1

    # Frame 2: Both Plate A and Plate B appear
    ev2 = manager.update_frame([
        {"plate_number": "MH12DE1433", "yolo_conf": 0.86, "ocr_conf": 0.91, "frames_observed": 4},
        {"plate_number": "DL04CA9999", "yolo_conf": 0.92, "ocr_conf": 0.98, "frames_observed": 2},
    ], current_time=10.1)

    assert len(ev2) == 1, f"Expected only Plate B to trigger new event, got {len(ev2)}"
    assert ev2[0].plate_number == "DL04CA9999"
    assert manager.total_vehicles_recognized == 2

    # Frame 3: Both plates still present
    ev3 = manager.update_frame([
        {"plate_number": "MH12DE1433", "yolo_conf": 0.86, "ocr_conf": 0.91, "frames_observed": 5},
        {"plate_number": "DL04CA9999", "yolo_conf": 0.92, "ocr_conf": 0.98, "frames_observed": 3},
    ], current_time=10.2)
    assert len(ev3) == 0
    assert manager.total_vehicles_recognized == 2

    # Verify latest event
    latest = manager.get_latest_recognition()
    assert latest is not None
    assert latest.plate_number == "DL04CA9999"

    if os.path.exists(test_csv):
        os.remove(test_csv)
    print("[PASS] test_multiple_vehicles passed.")


if __name__ == "__main__":
    print("Running VehicleEventManager test suite...")
    test_continuous_visibility()
    test_cooldown_behavior()
    test_multiple_vehicles()
    print("All tests passed successfully!")
