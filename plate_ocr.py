import os
import re
import cv2
import easyocr
from ultralytics import YOLO

# ==============================================================================
# Configuration & Constants
# ==============================================================================
MODEL_PATH = "best.pt"
TEST_IMAGE_PATH = "test.jpeg"
OUTPUT_DIR = "output"
OCR_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Official 2-letter State & Union Territory codes in India
INDIAN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB"
}


# ==============================================================================
# Image Processing & Preprocessing
# ==============================================================================
def crop_plate_with_padding(image, box, pad_pct_x=0.05, pad_pct_y=0.08):
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


def generate_preprocessing_variants(cropped_plate):
    """
    Creates multiple preprocessing variations of the cropped license plate:
    1. Raw Crop: Original cropped image with padding
    2. Upscaled Grayscale: 2.5x upscale with cubic interpolation + grayscale
    3. CLAHE: Contrast Limited Adaptive Histogram Equalization for lighting balance
    4. Denoised Otsu: Bilateral noise reduction + Otsu automated thresholding
    5. Adaptive Threshold: Bilateral filter + Adaptive Gaussian thresholding
    """
    variants = {}

    # 1. Raw cropped plate
    variants["raw"] = cropped_plate

    # 2. Resize/Upscale + Grayscale
    # License plates are often small; upscaling gives EasyOCR sharper character edges
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
    # Bilateral filter smooths background noise while keeping character edges crisp
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


# ==============================================================================
# Text Cleaning & Indian License Plate Validation
# ==============================================================================
def clean_ocr_text(raw_text):
    """
    Cleans OCR output:
    - Converts to uppercase
    - Removes whitespace, punctuation, and non-alphanumeric symbols
    - Removes common 'IND' prefix stamped on Indian HSRP plates if followed by state code
    """
    cleaned = re.sub(r"[^A-Z0-9]", "", raw_text.upper())

    # HSRP plates feature a vertical 'IND' mark on the left edge.
    # If OCR captures 'IND' followed by a valid Indian state code (e.g., INDTN45BD7321),
    # strip the prefix so we evaluate the actual registration number.
    if cleaned.startswith("IND") and len(cleaned) >= 11:
        if cleaned[3:5] in INDIAN_STATE_CODES:
            cleaned = cleaned[3:]

    return cleaned


def validate_indian_plate(plate_text):
    """
    Validates if the text conforms to Indian vehicle registration standards.

    Validation Tiers:
    - Tier 3: Standard Modern HSRP Format (e.g., TN45BD7321, DL01AB1234)
              or Bharat Series (e.g., 22BH1234AA).
    - Tier 2: Flexible/Vintage Indian Format (e.g., DL1C1234, TN091234).
    - Tier 1: Partial pattern (contains letters & digits, but abnormal length or extra noise).
    - Tier 0: Completely invalid / unstructured noise.

    Returns:
        (is_valid: bool, tier: int, format_name: str, has_valid_state: bool)
    """
    if not plate_text or len(plate_text) < 6:
        return False, 0, "Invalid / Too Short", False

    # Check 1: Standard Modern Indian Registration
    # Pattern: 2 Letters (State) + 2 Digits (RTO) + 1-2 Letters (Series) + 4 Digits (Number)
    # Examples: TN45BD7321 (10 chars), KA05M1234 (9 chars)
    if re.match(r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$", plate_text):
        state = plate_text[:2]
        is_known_state = state in INDIAN_STATE_CODES
        desc = (
            f"Standard Indian Plate ({state} State)"
            if is_known_state
            else "Standard Indian Plate Pattern"
        )
        return True, 3, desc, is_known_state

    # Check 2: Bharat (BH) Series
    # Pattern: 2 Digits (Year) + BH + 4 Digits + 1-2 Letters
    # Example: 22BH1234AA
    if re.match(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$", plate_text):
        return True, 3, "Bharat (BH) Series Plate", True

    # Check 3: Flexible / Older Indian Registration
    # Pattern: 2 Letters + 1-2 Digits + 0-3 Letters + 1-4 Digits (Length 7-10)
    # Example: DL1C1234, MH011234
    if re.match(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}$", plate_text):
        state = plate_text[:2]
        is_known_state = state in INDIAN_STATE_CODES
        if 7 <= len(plate_text) <= 10:
            return True, 2, "Flexible Indian Plate Format", is_known_state

    # Check 4: Partial / Noisy match (e.g. TN45BD67321 with 11 characters or 5 digits)
    if re.match(r"^[A-Z]{2}[0-9]", plate_text) and len(plate_text) > 4:
        return False, 1, "Partial Structure (Likely Extra Chars/Noise)", plate_text[:2] in INDIAN_STATE_CODES

    return False, 0, "Non-Matching Format", False


# ==============================================================================
# OCR Execution & Variant Candidate Selection
# ==============================================================================
def run_ocr_on_variant(reader, image_variant):
    """
    Executes EasyOCR on a single image variant and returns cleaned text and confidence.
    """
    results = reader.readtext(
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


def select_best_ocr_candidate(reader, variants):
    """
    Runs OCR on all preprocessing variants, validates each result against
    Indian vehicle registration rules, and selects the most plausible candidate.

    Scoring formula:
        score = (tier * 10.0) + (2.0 if valid_state else 0.0) + confidence
    This prioritizes structurally valid Indian plates over noisy strings with extra characters,
    while using OCR confidence to choose the best variant among valid candidates.
    """
    candidates = []

    for variant_name, img in variants.items():
        text, conf = run_ocr_on_variant(reader, img)
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
    best_candidate = candidates[0]

    # For the selected winning text, if multiple variants produced the same text,
    # report the maximum confidence achieved for that text
    same_text_candidates = [c for c in candidates if c["text"] == best_candidate["text"]]
    max_conf = max(c["confidence"] for c in same_text_candidates)
    best_candidate["confidence"] = max_conf

    return best_candidate, candidates


# ==============================================================================
# Visualization & Output Saving
# ==============================================================================
def draw_plate_annotation(image, box, label, confidence):
    """
    Draws a bounding box and an informative label with confidence on the image.
    """
    x1, y1, x2, y2 = map(int, box)

    # Draw bounding box
    box_color = (0, 255, 0)  # Bright Green
    cv2.rectangle(image, (x1, y1), (x2, y2), box_color, 3)

    # Prepare label text
    display_text = f"{label} ({confidence * 100:.1f}%)"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2

    (text_w, text_h), baseline = cv2.getTextSize(
        display_text, font, font_scale, thickness
    )

    # Position label above bounding box (or below if near top of image)
    label_y1 = max(0, y1 - text_h - 10)
    label_y2 = label_y1 + text_h + 10
    label_x1 = x1
    label_x2 = x1 + text_w + 10

    # Draw solid background rectangle for text readability
    cv2.rectangle(image, (label_x1, label_y1), (label_x2, label_y2), box_color, -1)
    # Draw dark text over green background
    cv2.putText(
        image,
        display_text,
        (label_x1 + 5, label_y2 - baseline - 2),
        font,
        font_scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA
    )


# ==============================================================================
# Main Pipeline
# ==============================================================================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("  INDIAN VEHICLE NUMBER PLATE RECOGNITION PIPELINE")
    print("=" * 60)

    # 1. Load YOLO model and EasyOCR reader
    print("[1/5] Loading YOLO model and EasyOCR (CPU mode)...")
    model = YOLO(MODEL_PATH)
    reader = easyocr.Reader(["en"], gpu=False)

    # 2. Read input image
    print(f"[2/5] Reading input image: {TEST_IMAGE_PATH}")
    image = cv2.imread(TEST_IMAGE_PATH)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {TEST_IMAGE_PATH}")

    annotated_image = image.copy()

    # 3. Detect number plates using YOLO
    print("[3/5] Running YOLO number-plate detection...")
    results = model(image)

    detected_plates = []
    plate_idx = 0

    for result in results:
        for box in result.boxes.xyxy:
            plate_idx += 1
            x1, y1, x2, y2 = map(int, box)
            print(f"\n--- Plate {plate_idx} [Box: ({x1}, {y1}) to ({x2}, {y2})] ---")

            # 4. Crop with padding
            cropped_plate = crop_plate_with_padding(image, box, pad_pct_x=0.05, pad_pct_y=0.08)

            # 5. Preprocess cropped plate into multiple variants
            variants = generate_preprocessing_variants(cropped_plate)

            # Save debug images
            for var_name, var_img in variants.items():
                debug_path = os.path.join(
                    OUTPUT_DIR, f"plate_{plate_idx}_{var_name}.jpg"
                )
                cv2.imwrite(debug_path, var_img)

            # 6. Run OCR across all variants and select the most plausible candidate
            best_candidate, all_candidates = select_best_ocr_candidate(reader, variants)

            # Display candidate comparison
            print(f"  Variant Comparison for Plate {plate_idx}:")
            for cand in all_candidates:
                status = "[VALID]" if cand["is_valid"] else "[INVALID]"
                print(
                    f"    - {cand['variant']:16}: '{cand['text']:14}' "
                    f"| Conf: {cand['confidence'] * 100:5.1f}% "
                    f"| {status} {cand['description']}"
                )

            if best_candidate and best_candidate["text"]:
                recognized_text = best_candidate["text"]
                conf = best_candidate["confidence"]
                desc = best_candidate["description"]
                from_var = best_candidate["variant"]
                print(
                    f"  => Selected Result: {recognized_text} "
                    f"(Confidence: {conf * 100:.2f}%, from '{from_var}', {desc})"
                )

                detected_plates.append({
                    "plate_index": plate_idx,
                    "box": (x1, y1, x2, y2),
                    "text": recognized_text,
                    "confidence": conf,
                    "description": desc,
                    "source_variant": from_var
                })

                # 7. Annotate image
                draw_plate_annotation(annotated_image, (x1, y1, x2, y2), recognized_text, conf)
            else:
                print("  => No text recognized for this plate.")

    # 8. Save final annotated image
    annotated_output_path = os.path.join(OUTPUT_DIR, "annotated_result.jpg")
    cv2.imwrite(annotated_output_path, annotated_image)
    print(f"\n[4/5] Saved annotated result image to: {annotated_output_path}")
    print(f"[5/5] Debug images saved in: {OUTPUT_DIR}/")

    # 9. Print final summary
    print("\n" + "=" * 60)
    print("  FINAL RECOGNIZED NUMBER PLATES SUMMARY")
    print("=" * 60)
    if detected_plates:
        for p in detected_plates:
            print(
                f"  Plate {p['plate_index']}: {p['text']} "
                f"| Confidence: {p['confidence'] * 100:.2f}% "
                f"| Format: {p['description']} "
                f"| Variant: {p['source_variant']}"
            )
    else:
        print("  No plates detected.")
    print("=" * 60)


if __name__ == "__main__":
    main()


