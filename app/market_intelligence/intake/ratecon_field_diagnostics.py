"""Redacted RateCon field-label signal diagnostics."""

import re


FIELD_SIGNAL_CATEGORIES = [
    "broker_name",
    "broker_mc",
    "rate",
    "pickup_location",
    "delivery_location",
    "pickup_date",
    "delivery_date",
    "weight",
    "commodity",
    "reference_id",
    "equipment",
    "special_requirements",
    "accessorials",
]


SIGNAL_PATTERNS = {
    "broker_name": [
        r"\bbroker\b",
        r"\bbroker\s+name\b",
        r"\bbill\s+to\b",
        r"\bcustomer\b",
    ],
    "broker_mc": [
        r"\bbroker\s+mc\b",
        r"\bmc\s*(number|#|no\.?)?\b",
        r"\bmotor\s+carrier\b",
    ],
    "rate": [
        r"\brate\b",
        r"\btotal\b",
        r"\btotal\s+rate\b",
        r"\btotal\s+carrier\s+pay\b",
        r"\bcarrier\s+pay\b",
        r"\blinehaul\s+total\b",
        r"\blinehaul\b",
    ],
    "pickup_location": [
        r"\bpick\s*up\b",
        r"\bpickup\b",
        r"\bshipper\b",
        r"\borigin\b",
    ],
    "delivery_location": [
        r"\bdelivery\b",
        r"\bdeliver\s*to\b",
        r"\bconsignee\b",
        r"\bdestination\b",
    ],
    "pickup_date": [
        r"\bpick\s*up\s+date\b",
        r"\bpickup\s+date\b",
        r"\bpick\s*up\s+time\b",
        r"\bpickup\s+time\b",
        r"\bpick\s*up\s+appt\b",
        r"\bpickup\s+appt\b",
        r"\bpick\s*up\s+window\b",
        r"\bpickup\s+window\b",
    ],
    "delivery_date": [
        r"\bdelivery\s+date\b",
        r"\bdeliver\s+date\b",
        r"\bdelivery\s+time\b",
        r"\bdeliver\s+time\b",
        r"\bdelivery\s+appt\b",
        r"\bdeliver\s+appt\b",
        r"\bdelivery\s+window\b",
        r"\bdeliver\s+window\b",
    ],
    "weight": [
        r"\bweight\b",
        r"\bwt\b",
        r"\blbs?\b",
        r"\bpounds?\b",
    ],
    "commodity": [
        r"\bcommodity\b",
        r"\bproduct\b",
        r"\bdescription\b",
    ],
    "reference_id": [
        r"\breference\b",
        r"\bref\s*(#|no\.?|number)?\b",
        r"\bload\s*(#|no\.?|number)?\b",
        r"\border\s*(#|no\.?|number)?\b",
        r"\bshipment\s*(id|#|number)?\b",
    ],
    "equipment": [
        r"\bequipment\b",
        r"\bmode\b",
        r"\btrailer\b",
        r"\bflatbed\b",
        r"\bconestoga\b",
        r"\breefer\b",
        r"\bvan\b",
        r"\bstep\s+deck\b",
    ],
    "special_requirements": [
        r"\bspecial\s+requirements\b",
        r"\brequirements\b",
        r"\binstructions\b",
        r"\bnotes\b",
    ],
    "accessorials": [
        r"\baccessorials?\b",
        r"\bdetention\b",
        r"\blayover\b",
        r"\blumper\b",
        r"\btonu\b",
        r"\bfuel\s+surcharge\b",
    ],
}


def _normalized_text(text):
    return str(text or "").lower()


def _count_pattern(text, pattern):
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _line_count(text):
    clean_text = str(text or "")
    if not clean_text.strip():
        return 0
    return len(clean_text.splitlines())


def detect_ratecon_field_signals(text):
    """Count field-label signals without returning matched text or values."""
    normalized = _normalized_text(text)
    signal_counts = {}

    for category in FIELD_SIGNAL_CATEGORIES:
        signal_counts[category] = sum(
            _count_pattern(normalized, pattern)
            for pattern in SIGNAL_PATTERNS[category]
        )

    detected_categories = [
        category
        for category in FIELD_SIGNAL_CATEGORIES
        if signal_counts[category] > 0
    ]
    missing_signal_categories = [
        category
        for category in FIELD_SIGNAL_CATEGORIES
        if signal_counts[category] == 0
    ]
    warnings = []

    if not str(text or "").strip():
        warnings.append("empty_text")

    return {
        "text_present": bool(str(text or "").strip()),
        "char_count": len(str(text or "")),
        "line_count": _line_count(text),
        "signal_counts": signal_counts,
        "detected_categories": detected_categories,
        "missing_signal_categories": missing_signal_categories,
        "warnings": warnings,
    }
