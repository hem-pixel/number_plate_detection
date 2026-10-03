import os
import sys
from pathlib import Path

# Add project root and ai-service to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_SERVICE_DIR = PROJECT_ROOT / "ai-service"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(AI_SERVICE_DIR))

import cv2
from pipeline.recognition_pipeline import RecognitionPipeline


def test_ai_pipeline():
    test_image_path = PROJECT_ROOT / "test.jpeg"
    assert test_image_path.exists(), f"test.jpeg not found at {test_image_path}"

    image = cv2.imread(str(test_image_path))
    assert image is not None, "Failed to load test.jpeg"

    model_path = AI_SERVICE_DIR / "models" / "best.pt"
    assert model_path.exists(), f"best.pt not found at {model_path}"

    print(f"[TEST] Initializing RecognitionPipeline with model: {model_path}")
    pipeline = RecognitionPipeline(model_path=str(model_path), gpu=False)

    print(f"[TEST] Running pipeline on test.jpeg (shape: {image.shape})")
    results = pipeline.process_frame(image)

    print(f"[TEST] Detections found: {len(results)}")
    for idx, res in enumerate(results, 1):
        print(f"  Result {idx}: Plate='{res['plate_number']}', YOLO Conf={res['yolo_confidence']:.2f}, "
              f"OCR Conf={res['ocr_confidence']:.2f}, Status='{res['status']}'")

    assert len(results) > 0, "No plates detected!"
    # Verify that TN45BD7321 was recognized
    plates_found = [r["plate_number"] for r in results]
    print(f"[TEST] Extracted plates: {plates_found}")

    assert any("TN45BD7321" in p for p in plates_found), f"Expected 'TN45BD7321' in {plates_found}"
    print("[TEST] SUCCESS! Modular AI recognition pipeline verified successfully on CPU.")


if __name__ == "__main__":
    test_ai_pipeline()
