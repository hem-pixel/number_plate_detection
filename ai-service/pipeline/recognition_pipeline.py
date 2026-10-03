"""
Reusable Indian Vehicle Number Plate Recognition Pipeline
Combines Plate Detection, Crop Preprocessing, EasyOCR, and Plate Format Validation.
"""

from typing import List, Dict, Any, Optional
import numpy as np

import sys
from pathlib import Path

_AI_SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(_AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_DIR))

from detection.plate_detector import PlateDetector
from ocr.plate_ocr import PlateOCR
from validation.plate_validator import validate_indian_plate



class RecognitionPipeline:
    """
    Unified end-to-end recognition pipeline:
    Frame -> YOLO Detection -> Plate Crop -> Preprocessing Variants -> EasyOCR -> Indian Plate Validation
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.35,
        gpu: bool = False,
    ):
        self.detector = PlateDetector(model_path=model_path, conf_threshold=conf_threshold)
        self.ocr = PlateOCR(gpu=gpu)

    def process_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Processes a single vehicle frame or image.

        Returns a list of recognition result dictionaries:
        [
            {
                "plate_number": str,
                "yolo_confidence": float,
                "ocr_confidence": float,
                "bbox": [x1, y1, x2, y2],
                "vehicle_frame": np.ndarray,
                "plate_crop": np.ndarray,
                "status": "VERIFIED" | "CANDIDATE" | "INVALID",
                "tier": int,
                "description": str,
                "all_candidates": list
            },
            ...
        ]
        """
        if frame is None or frame.size == 0:
            return []

        detections = self.detector.detect(frame)
        results = []

        for det in detections:
            bbox = det["box"]
            yolo_conf = det["confidence"]
            plate_crop = det["crop"]

            best_candidate, all_candidates = self.ocr.recognize(plate_crop)

            if best_candidate and best_candidate.get("is_valid"):
                status = "VERIFIED" if best_candidate.get("tier", 0) >= 2 else "CANDIDATE"
                plate_number = best_candidate.get("text", "")
                ocr_conf = best_candidate.get("confidence", 0.0)
                tier = best_candidate.get("tier", 0)
                desc = best_candidate.get("description", "")
            elif best_candidate:
                status = "INVALID"
                plate_number = best_candidate.get("text", "")
                ocr_conf = best_candidate.get("confidence", 0.0)
                tier = best_candidate.get("tier", 0)
                desc = best_candidate.get("description", "")
            else:
                status = "NO_TEXT"
                plate_number = ""
                ocr_conf = 0.0
                tier = 0
                desc = "No OCR detection"

            results.append({
                "plate_number": plate_number,
                "yolo_confidence": round(float(yolo_conf), 4),
                "ocr_confidence": round(float(ocr_conf), 4),
                "bbox": [round(float(c), 1) for c in bbox],
                "vehicle_frame": frame,
                "plate_crop": plate_crop,
                "status": status,
                "tier": tier,
                "description": desc,
                "all_candidates": all_candidates,
            })

        return results
