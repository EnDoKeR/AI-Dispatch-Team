import re

from app.market_intelligence.notes_parser_text_helpers import clean_text


def detect_forklift_required(text):
    text = clean_text(text)

    keywords = [
        "forklift",
        "moffett",
        "moffet",
        "piggyback",
        "loader required",
        "unload equipment",
        "unloading equipment",
        "driver unload",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_ramps_required(text):
    text = clean_text(text)

    patterns = [
        r"\bneed\s*ramps\b",
        r"\bneeds\s*ramps\b",
        r"\bramps?\s*required\b",
        r"\bramps?\s*needed\b",
        r"\bramps?\s*req\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_tracking_required(text):
    text = clean_text(text)

    keywords = [
        "tracking required",
        "tracking req",
        "tracking must",
        "macropoint",
        "macro point",
        "trucker tools",
        "12 month active mc required",
        "12 months active mc required",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_appointment_required(text):
    text = clean_text(text)

    keywords = [
        "appt",
        "appointment",
        "appointment required",
        "by appointment",
        "appt only",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_straight_through(text):
    text = clean_text(text)

    keywords = [
        "straight through",
        "deliver straight through",
        "must deliver straight",
        "straight thru",
        "deliver straight thru",
        "straight thru delivery",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False
