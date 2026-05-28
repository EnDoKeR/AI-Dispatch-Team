import re

from app.market_intelligence.notes_parser_text_helpers import clean_text


def detect_dedicated_lane(text):
    text = clean_text(text)

    patterns = [
        r"\bdedicated\s*lane\b",
        r"\bneed\s*solid\s*drivers\b",
        r"\bneed\s*solid\s*driver\b",
        r"\bconsistent\s*lane\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_double_brokering_language(text):
    text = clean_text(text)

    patterns = [
        r"\bno\s*double\s*brokering\b",
        r"\bno\s*double\s*broker\b",
        r"\bdouble\s*brokering\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_mc_must_match(text):
    text = clean_text(text)

    patterns = [
        r"\bmc\s*must\s*match\b",
        r"\bname\s*must\s*match\b",
        r"\bcarrier\s*name\s*must\s*match\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False
