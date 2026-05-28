import re

from app.market_intelligence.notes_parser_text_helpers import clean_text


def detect_cash_or_zelle(text):
    text = clean_text(text)

    patterns = [
        r"\bcash\s*or\s*zelle\b",
        r"\bzelle\s*or\s*cash\b",
        r"\bcashapp\b",
        r"\bcash\s*app\b",
        r"\bzelle\b",
        r"\bcash\s*on\s*delivery\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_quickpay_review(text):
    text = clean_text(text)

    patterns = [
        r"\bquickpay\b",
        r"\bquick\s*pay\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False
