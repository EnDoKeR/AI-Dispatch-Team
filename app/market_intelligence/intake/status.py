"""Status classification for normalized intake records."""

READY_FOR_REVIEW = "READY_FOR_REVIEW"
MISSING_FIELDS = "MISSING_FIELDS"
NEEDS_CHECK = "NEEDS_CHECK"


def normalized_field_list(record, field_name):
    value = (record or {}).get(field_name, [])

    if value is None:
        return []

    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []

    if isinstance(value, (list, tuple, set)):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    text = str(value).strip()

    return [text] if text else []


def classify_intake_record_status(record):
    if normalized_field_list(record, "missing_fields"):
        return MISSING_FIELDS

    if normalized_field_list(record, "needs_check_fields"):
        return NEEDS_CHECK

    return READY_FOR_REVIEW


def intake_record_ready_for_review(record):
    return classify_intake_record_status(record) != MISSING_FIELDS
