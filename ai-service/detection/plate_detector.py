"""
YOLO Plate Detection Module for Indian Vehicle Number Plate Recognition
"""

import os
from typing import List, Dict, Any, Optional
import numpy as np
import cv2
from ultralytics import YOLO

import sys
from pathlib import Path

_AI_SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(_AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_DIR))

from preprocessing.image_preprocessor import crop_plate_with_padding


DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "best.pt")
FALLBACK_MODEL_PATH = "best.pt"


class PlateDetector:
    """
    Wraps the trained YOLO model (best.pt) to detect vehicle number plates in frames/images.
    """

    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = 0.35):
        if model_path is None:
            if os.path.exists(DEFAULT_MODEL_PATH):
                model_path = DEFAULT_MODEL_PATH
            elif os.path.exists(FALLBACK_MODEL_PATH):
                model_path = FALLBACK_MODEL_PATH
            else:
                model_path = DEFAULT_MODEL_PATH

        self.model_path = model_path
        self.conf_threshold = conf_threshold
        print(f"[*] Initializing YOLO PlateDetector with model: {self.model_path}")
        self.model = YOLO(self.model_path)

    def detect(self, image: np.ndarray, conf_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Runs YOLO inference on the input image.

        Returns list of detection dictionaries:
        [
            {
                "box": [x1, y1, x2, y2],
                "confidence": float,
                "class_id": int,
                "crop": np.ndarray
            },
            ...
        ]
        """
        if image is None:
            return []

        conf = conf_threshold if conf_threshold is not None else self.conf_threshold
        pred = self.model.predict(image, conf=conf, verbose=False)
        results = list(pred) if pred is not None else []

        detections = []
        if not results:
            return detections

        first_res = results[0]
        boxes = getattr(first_res, "boxes", None)
        if boxes is None:
            return detections

        for box in boxes:
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            score = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())

            crop = crop_plate_with_padding(image, xyxy)

            detections.append({
                "box": [float(c) for c in xyxy],
                "confidence": score,
                "class_id": cls_id,
                "crop": crop
            })

        return detections

    @staticmethod
    def crop(image: np.ndarray, box: Any, pad_pct_x: float = 0.05, pad_pct_y: float = 0.08) -> np.ndarray:
        return crop_plate_with_padding(image, box, pad_pct_x=pad_pct_x, pad_pct_y=pad_pct_y)
