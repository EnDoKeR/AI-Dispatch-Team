"""JSON-ready intake record helpers."""

RECORD_FIELDS = [
    "intake_id",
    "source_type",
    "source_file_name",
    "received_at_utc",
    "customer_name",
    "load_label",
    "load_number",
    "loaded_miles",
    "miles_status",
    "miles_source",
    "broker_name",
    "broker_mc",
    "rate",
    "pickup_location",
    "pickup_date",
    "pickup_time",
    "delivery_location",
    "delivery_date",
    "delivery_time",
    "commodity",
    "weight",
    "reference_id",
    "equipment",
    "special_requirements",
    "missing_fields",
    "needs_check_fields",
    "field_confidence",
    "linked_dispatch_case_id",
]

MANDATORY_FIELDS = [
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
]

LIST_FIELDS = {"special_requirements", "missing_fields", "needs_check_fields"}
DICT_FIELDS = {"field_confidence"}


def source_value(source, field_name, default=""):
    if source is None:
        return default

    if isinstance(source, dict):
        value = source.get(field_name, default)
    else:
        value = getattr(source, field_name, default)

    if value is None:
        return default

    return value


def is_missing(value):
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    return value == ""


def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]

    normalized = []

    for item in items:
        text = str(item).strip()

        if text:
            normalized.append(text)

    return normalized


def normalize_dict(value):
    if not isinstance(value, dict):
        return {}

    return dict(value)


def normalized_value(source, field_name):
    value = source_value(source, field_name, "")

    if field_name in LIST_FIELDS:
        return normalize_list(value)

    if field_name in DICT_FIELDS:
        return normalize_dict(value)

    return value


def append_once(values, field_name):
    if field_name not in values:
        values.append(field_name)


def build_missing_fields(record):
    missing_fields = []

    for field_name in MANDATORY_FIELDS:
        if is_missing(record.get(field_name, "")):
            missing_fields.append(field_name)

    return missing_fields


def build_needs_check_fields(record, missing_fields):
    needs_check_fields = []

    if record.get("broker_name") and "broker_mc" in missing_fields:
        append_once(needs_check_fields, "broker_mc")

    if record.get("broker_mc") and "broker_name" in missing_fields:
        append_once(needs_check_fields, "broker_name")

    if record.get("pickup_location") and "pickup_date" in missing_fields:
        append_once(needs_check_fields, "pickup_date")

    if record.get("delivery_location") and "delivery_date" in missing_fields:
        append_once(needs_check_fields, "delivery_date")

    return needs_check_fields


def build_intake_record(source=None, received_at_utc="", intake_id=""):
    record = {}

    for field_name in RECORD_FIELDS:
        record[field_name] = normalized_value(source, field_name)

    if intake_id:
        record["intake_id"] = intake_id

    if received_at_utc:
        record["received_at_utc"] = received_at_utc

    missing_fields = build_missing_fields(record)
    needs_check_fields = build_needs_check_fields(record, missing_fields)

    record["missing_fields"] = missing_fields
    record["needs_check_fields"] = needs_check_fields

    return record
