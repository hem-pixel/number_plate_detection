"""
OCR Module for Indian Vehicle Number Plate Recognition
"""

from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import easyocr

import sys
from pathlib import Path

_AI_SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(_AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_DIR))

from preprocessing.image_preprocessor import generate_preprocessing_variants
from validation.plate_validator import clean_ocr_text, validate_indian_plate


OCR_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class PlateOCR:
    """
    Handles character recognition on cropped plate images using EasyOCR with
    multi-variant preprocessing and Indian registration validation.
    """

    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = False):
        if languages is None:
            languages = ["en"]
        self.languages = languages
        self.gpu = gpu
        print(f"[*] Initializing EasyOCR Reader (languages={self.languages}, gpu={self.gpu})...")
        self.reader = easyocr.Reader(self.languages, gpu=self.gpu)

    def run_ocr_on_variant(self, image_variant: np.ndarray) -> Tuple[str, float]:
        """
        Executes EasyOCR on a single image variant and returns cleaned text and confidence.
        """
        if image_variant is None or image_variant.size == 0:
            return "", 0.0

        results: Any = self.reader.readtext(
            image_variant,
            detail=1,
            allowlist=OCR_ALLOWLIST
        )

        if not results:
            return "", 0.0

        # Sort text boxes from left to right in case plate text was detected in chunks
        sorted_results = sorted(results, key=lambda item: item[0][0][0])
        raw_combined = "".join([item[1] for item in sorted_results])
        cleaned_text = clean_ocr_text(raw_combined)

        # Average confidence score across detected chunks
        confidences = [float(item[2]) for item in sorted_results]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return cleaned_text, avg_conf

    def select_best_candidate(self, variants: Dict[str, np.ndarray]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Runs OCR on all preprocessing variants, validates each result against
        Indian vehicle registration rules, and selects the most plausible candidate.

        Scoring formula:
            score = (tier * 10.0) + (2.0 if valid_state else 0.0) + confidence
        """
        candidates = []

        for variant_name, img in variants.items():
            text, conf = self.run_ocr_on_variant(img)
            if not text:
                continue

            is_valid, tier, desc, has_valid_state = validate_indian_plate(text)
            score = (tier * 10.0) + (2.0 if has_valid_state else 0.0) + conf

            candidates.append({
                "variant": variant_name,
                "text": text,
                "confidence": conf,
                "is_valid": is_valid,
                "tier": tier,
                "description": desc,
                "score": score
            })

        if not candidates:
            return None, candidates

        # Sort candidates by score descending
        candidates.sort(key=lambda c: c["score"], reverse=True)
        best_candidate = candidates[0].copy()

        # For the selected winning text, report maximum confidence achieved across variants
        same_text_candidates = [c for c in candidates if c["text"] == best_candidate["text"]]
        max_conf = max(c["confidence"] for c in same_text_candidates)
        best_candidate["confidence"] = max_conf

        return best_candidate, candidates

    def recognize(self, cropped_plate: np.ndarray) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Takes a cropped plate image, generates preprocessing variants, and extracts
        the best validated plate candidate.
        """
        variants = generate_preprocessing_variants(cropped_plate)
        return self.select_best_candidate(variants)
