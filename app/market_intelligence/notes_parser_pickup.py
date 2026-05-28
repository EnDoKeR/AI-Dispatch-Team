import re

from app.market_intelligence.notes_parser_load_requirements import detect_appointment_required
from app.market_intelligence.notes_parser_text_helpers import clean_text, normalize_text


def detect_pickup_time_from_text(text):
    original = normalize_text(text)
    text_lower = clean_text(text)

    if "fcfs" in text_lower:
        match = re.search(
            r"\bfcfs\s*\d{1,2}\s*(?:am|pm)?\s*(?:-|to)\s*\d{1,2}\s*(?:am|pm)?\b",
            text_lower,
        )

        if match:
            return match.group(0).upper()

        return "FCFS - NEEDS HOURS CHECK"

    time_window = re.search(
        r"\b\d{1,2}\s*(?:am|pm)\s*(?:-|to)\s*\d{1,2}\s*(?:am|pm)\b",
        text_lower,
    )

    if time_window:
        return time_window.group(0).upper()

    # Important: require 4 digits on both sides, so phone numbers like 443-2707 are NOT detected as time.
    military_window = re.search(
        r"\b([01]\d{3}|2[0-3]\d{2})\s*(?:-|to)\s*([01]\d{3}|2[0-3]\d{2})\b",
        text_lower,
    )

    if military_window:
        return military_window.group(0).upper()

    if re.search(r"\bready\s*now\b", text_lower):
        return "Ready now"

    if detect_appointment_required(original):
        return "Appointment required"

    return ""


def detect_actual_pickup_city(text):
    original = normalize_text(text)

    city_state_patterns = [
        r"actual\s*pickup\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actual\s*pick\s*up\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actual\s*pu\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actual\s*pickup\s*city\s+([a-zA-Z\s.]+),?\s+([A-Z]{2})",
        r"actual\s*pick\s*up\s*[-:]+\s*([a-zA-Z\s.]+)\s*\(\s*([A-Z]{2})\s*\)",
        r"actual\s*pickup\s*[-:]+\s*([a-zA-Z\s.]+)\s*\(\s*([A-Z]{2})\s*\)",
        r"actual\s*pu\s*[-:]+\s*([a-zA-Z\s.]+)\s*\(\s*([A-Z]{2})\s*\)",
        r"load\s*actually\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actually\s*load\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actually\s*loads\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"real\s*pickup\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"correct\s*pickup\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"pickup\s*is\s*actually\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
    ]

    for pattern in city_state_patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            city = match.group(1).strip(" .,-:")
            state = match.group(2).strip().upper()
            return f"{city}, {state}"

    return ""


def detect_extra_pickup(text):
    text = clean_text(text)

    patterns = [
        r"\bextra\s*pick\s*up\b",
        r"\bextra\s*pickup\b",
        r"\bextra\s*pu\b",
        r"\badditional\s*pickup\b",
        r"\badditional\s*pu\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_multiple_loads_available(text):
    text = clean_text(text)

    patterns = [
        r"\bmultiple\s*loads\s*available\b",
        r"\bmore\s*loads\s*available\b",
        r"\bseveral\s*loads\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False
