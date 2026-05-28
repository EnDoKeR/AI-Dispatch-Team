import re

from app.market_intelligence.notes_parser_text_helpers import clean_text


def detect_no_conestoga(text):
    text = clean_text(text)

    keywords = [
        "no conestoga",
        "no conestogas",
        "no stoga",
        "no stogas",
        "conestoga no",
        "flatbed only",
        "flat only",
        "must be flatbed",
        "conestoga wouldn't work",
        "conestoga would not work",
        "conestoga wont work",
        "conestoga won't work",
        "no con",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_conestoga_ok(text):
    text = clean_text(text)

    patterns = [
        r"\bconestoga\s*ok\b",
        r"\bstoga\s*ok\b",
        r"\bconestoga\s*works\b",
        r"\bconestoga\s*accepted\b",
        r"\btarps?\s*/\s*conestoga\s*ok\b",
        r"\bconestoga\s*would\s*work\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_flatbed_required(text):
    text = clean_text(text)

    keywords = [
        "flatbed only",
        "must be flatbed",
        "flat only",
        "flatbed required",
        "flatbed needed",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_flatbed_preferred(text):
    text = clean_text(text)

    patterns = [
        r"\bflatbed\s*preferred\b",
        r"\bprefer\s*flatbed\b",
        r"\bpreferred\s*flatbed\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_stepdeck_allowed(text):
    text = clean_text(text)

    patterns = [
        r"\bflatbed\s*or\s*step\s*deck\b",
        r"\bflatbed\s*/\s*step\s*deck\b",
        r"\bfd\s*or\s*sd\b",
        r"\bsd\s*or\s*fd\b",
        r"\bstepdeck\s*ok\b",
        r"\bstep\s*deck\s*ok\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_no_box_truck(text):
    text = clean_text(text)

    patterns = [
        r"\bno\s*box\s*truck\b",
        r"\bno\s*box\s*trucks\b",
        r"\bno\s*box\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False
