import re

from app.market_intelligence.notes_parser_text_helpers import (
    normalize_email,
    normalize_phone,
    normalize_text,
)


def detect_contact_override(text):
    original = normalize_text(text)

    result = {
        "phone": "",
        "extension": "",
        "email": "",
    }

    phone_match = re.search(
        r"(\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})(?:\s*(?:x|ext|extension|ex)\s*\.?\s*(\d+))?",
        original,
        re.IGNORECASE,
    )

    if phone_match:
        result["phone"] = normalize_phone(phone_match.group(1))
        if phone_match.group(2):
            result["extension"] = phone_match.group(2).strip()

    # Direct or broken email:
    # name@domain.com
    # name@domain`com
    # name at domain dot com
    # name@domain com
    email_patterns = [
        r"(?<![A-Za-z0-9])(?:[A-Za-z0-9]\s+){2,}[A-Za-z0-9]\s+at\s+[A-Za-z0-9.\-]+\s+dot\s+[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s*@\s*[A-Za-z0-9.\-]+\s*(?:\.|`|,|\s+dot\s+|\s+)\s*[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s+at\s+[A-Za-z0-9.\-]+\s*(?:\.|\s+dot\s+|\s+)\s*[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s*\(\s*at\s*\)\s*[A-Za-z0-9.\-]+\s*\(\s*dot\s*\)\s*[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s*\[\s*at\s*\]\s*[A-Za-z0-9.\-]+\s*\[\s*dot\s*\]\s*[A-Za-z]{2,}",
    ]

    for pattern in email_patterns:
        email_match = re.search(pattern, original, re.IGNORECASE)
        if email_match:
            email = normalize_email(email_match.group(0))
            if email:
                result["email"] = email
                break

    return result
