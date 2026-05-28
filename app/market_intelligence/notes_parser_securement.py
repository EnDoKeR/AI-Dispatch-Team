import re

from app.market_intelligence.notes_parser_text_helpers import clean_text


def detect_tarp_required(text):
    text = clean_text(text)

    no_tarp_patterns = [
        r"\bno\s*tarp\b",
        r"\bno\s*tarps\b",
        r"\bno\s*tarping\b",
        r"\bnot\s*tarp\b",
        r"\bnot\s*tarps\b",
        r"\btarp\s*not\s*required\b",
        r"\btarps\s*not\s*required\b",
        r"\btarp\s*not\s*needed\b",
        r"\btarps\s*not\s*needed\b",
        r"\bno\s*tarp\s*needed\b",
        r"\bno\s*tarps\s*needed\b",
    ]

    for pattern in no_tarp_patterns:
        if re.search(pattern, text):
            return False

    tarp_patterns = [
        r"\btarp\s*required\b",
        r"\btarps\s*required\b",
        r"\btarp\s*req\b",
        r"\btarps\s*req\b",
        r"\btarp\s*needed\b",
        r"\btarps\s*needed\b",
        r"\bneed\s*tarp\b",
        r"\bneed\s*tarps\b",
        r"\bneeds\s*tarp\b",
        r"\bneeds\s*tarps\b",
        r"\b\d+\s*ft\s*tarp\b",
        r"\b\d+\s*ft\s*tarps\b",
        r"\b\d+ft\s*tarp\b",
        r"\b\d+ft\s*tarps\b",
        r"\b\d+'\s*tarp\b",
        r"\b\d+'\s*tarps\b",
        r"\b\d+\s*foot\s*tarp\b",
        r"\b\d+\s*foot\s*tarps\b",
    ]

    for pattern in tarp_patterns:
        if re.search(pattern, text):
            return True

    if re.search(r"\b(4|6|8)\s*ft\b", text):
        return True

    return False


def detect_tarp_size(text):
    text = clean_text(text)

    patterns = [
        r"\b(4|6|8)\s*ft\s*tarps?\b",
        r"\b(4|6|8)ft\s*tarps?\b",
        r"\b(4|6|8)'\s*tarps?\b",
        r"\b(4|6|8)\s*foot\s*tarps?\b",
        r"\bneed\s*(4|6|8)\s*ft\b",
        r"\b(4|6|8)\s*ft\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return f"{match.group(1)} ft"

    return ""


def detect_straps_required(text):
    text = clean_text(text)

    patterns = [
        r"\bstrap\s*and\s*go\b",
        r"\bstraps?\s*required\b",
        r"\bstraps?\s*req\b",
        r"\bneed\s*straps?\b",
        r"\bneeds\s*straps?\b",
        r"\b\d+\s*straps?\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_number_of_straps(text):
    text = clean_text(text)

    match = re.search(r"\b(\d+)\s*straps?\b", text)
    if match:
        return int(match.group(1))

    return 0
