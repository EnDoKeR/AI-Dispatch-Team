import re

from app.market_intelligence.notes_parser_text_helpers import clean_text


def detect_hazmat_required(text):
    text = clean_text(text)

    patterns = [
        r"\bhazmat\b",
        r"\bhaz\s*mat\b",
        r"\bhazmat\s*required\b",
        r"\bhazmat\s*with\s*tarps\b",
        r"\bhazmat\s*load\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_tanker_required(text):
    text = clean_text(text)

    patterns = [
        r"\btanker\b",
        r"\btanker\s*endorsement\b",
        r"\btanker\s*endorsment\b",
        r"\btanker\s*required\b",
        r"\btanker\s*endorsement\s*required\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_twic_required(text):
    text = clean_text(text)

    patterns = [
        r"\btwic\b",
        r"\btwic\s*card\b",
        r"\btwic\s*required\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_document_required(text):
    text = clean_text(text)

    patterns = [
        r"\bus\s*citizen\b",
        r"\bu\.s\.\s*citizen\b",
        r"\bgreen\s*card\b",
        r"\bwork\s*permit\b",
        r"\bpassport\b",
        r"\bdriver\s*license\b",
        r"\bdl\s*required\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_iso_tank_required(text):
    text = clean_text(text)

    patterns = [
        r"\biso\s*tank\b",
        r"\biso\s*tanks\b",
        r"\bisotank\b",
        r"\bisotanks\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False
