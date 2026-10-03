"""
Validation Module for Indian Vehicle Registration Numbers
"""

import re
from typing import Tuple

# Official 2-letter State & Union Territory codes in India
INDIAN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UP", "WB"
}


def clean_ocr_text(raw_text: str) -> str:
    """
    Cleans OCR output:
    - Converts to uppercase
    - Removes whitespace, punctuation, and non-alphanumeric symbols
    - Removes common 'IND' prefix stamped on Indian HSRP plates if followed by state code
    """
    if not raw_text:
        return ""

    cleaned = re.sub(r"[^A-Z0-9]", "", raw_text.upper())

    # HSRP plates feature a vertical 'IND' mark on the left edge.
    # If OCR captures 'IND' followed by a valid Indian state code (e.g., INDTN45BD7321),
    # strip the prefix so we evaluate the actual registration number.
    if cleaned.startswith("IND") and len(cleaned) >= 11:
        if cleaned[3:5] in INDIAN_STATE_CODES:
            cleaned = cleaned[3:]

    return cleaned


def validate_indian_plate(plate_text: str) -> Tuple[bool, int, str, bool]:
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
