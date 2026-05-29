HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
UNKNOWN = "UNKNOWN"

CONFIDENCE_LEVELS = [HIGH, MEDIUM, LOW, UNKNOWN]
_CONFIDENCE_LEVEL_SET = set(CONFIDENCE_LEVELS)


def normalize_confidence(value):
    text = str(value or "").strip().upper()

    if text in _CONFIDENCE_LEVEL_SET:
        return text

    return UNKNOWN


def normalize_field_confidence(field_confidence=None, expected_fields=None):
    normalized = {}

    if isinstance(field_confidence, dict):
        for field_name, value in field_confidence.items():
            key = str(field_name or "").strip()

            if key:
                normalized[key] = normalize_confidence(value)

    for field_name in expected_fields or []:
        key = str(field_name or "").strip()

        if key and key not in normalized:
            normalized[key] = UNKNOWN

    return normalized


def confidence_for_field(field_confidence=None, field_name=""):
    key = str(field_name or "").strip()

    if not key:
        return UNKNOWN

    normalized = normalize_field_confidence(field_confidence)

    return normalized.get(key, UNKNOWN)


def low_confidence_fields(field_confidence=None):
    normalized = normalize_field_confidence(field_confidence)

    return [
        field_name
        for field_name, confidence in normalized.items()
        if confidence == LOW
    ]
