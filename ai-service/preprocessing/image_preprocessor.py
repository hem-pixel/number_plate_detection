"""
Image Preprocessing Module for Indian Vehicle Number Plate Recognition
"""

import cv2
import numpy as np
from typing import Dict, Any


def crop_plate_with_padding(image: np.ndarray, box: Any, pad_pct_x: float = 0.05, pad_pct_y: float = 0.08) -> np.ndarray:
    """
    Crops the detected plate area with a small percentage padding.
    Padding ensures characters close to the bounding box boundary are not clipped.
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = map(int, box)

    box_w = x2 - x1
    box_h = y2 - y1

    pad_x = int(box_w * pad_pct_x)
    pad_y = int(box_h * pad_pct_y)

    px1 = max(0, x1 - pad_x)
    py1 = max(0, y1 - pad_y)
    px2 = min(w, x2 + pad_x)
    py2 = min(h, y2 + pad_y)

    return image[py1:py2, px1:px2]


def generate_preprocessing_variants(cropped_plate: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Creates multiple preprocessing variations of the cropped license plate:
    1. Raw Crop: Original cropped image with padding
    2. Upscaled Grayscale: 2.5x upscale with cubic interpolation + grayscale
    3. CLAHE: Contrast Limited Adaptive Histogram Equalization for lighting balance
    4. Denoised Otsu: Bilateral noise reduction + Otsu automated thresholding
    5. Adaptive Threshold: Bilateral filter + Adaptive Gaussian thresholding
    """
    variants = {}

    if cropped_plate is None or cropped_plate.size == 0:
        return variants

    # 1. Raw cropped plate
    variants["raw"] = cropped_plate

    # 2. Resize/Upscale + Grayscale
    scale = 2.5
    upscaled = cv2.resize(
        cropped_plate, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
    )
    gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
    variants["upscaled_gray"] = gray

    # 3. Enhance Contrast via CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_img = clahe.apply(gray)
    variants["clahe"] = contrast_img

    # 4. Noise Reduction (Bilateral Filter) + Otsu's Thresholding
    denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    _, otsu_thresh = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    variants["denoised_otsu"] = otsu_thresh

    # 5. Adaptive Thresholding
    adaptive_thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    variants["adaptive_thresh"] = adaptive_thresh

    return variants
