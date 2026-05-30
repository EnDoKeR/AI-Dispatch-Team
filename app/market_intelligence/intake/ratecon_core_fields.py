"""RateCon-specific core field policy for dry-run review."""

DEFERRED_GOOGLE_MAPS = "DEFERRED_GOOGLE_MAPS"
NOT_FROM_RATECON = "NOT_FROM_RATECON"

CORE_REQUIRED_FIELDS = [
    "customer_name",
    "load_label",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "load_number",
    "rate",
    "commodity",
    "weight",
]

OPTIONAL_FIELDS = [
    "broker_mc",
    "equipment",
]

DEFERRED_FIELDS = [
    "loaded_miles",
]

FIELD_ALIASES = {
    "customer_name": ["customer_name", "broker_name"],
    "load_label": ["load_label", "load_type", "load_title"],
    "load_number": ["load_number", "reference_id"],
}


def _value_from(record, field_name):
    if record is None:
        return ""

    if isinstance(record, dict):
        return record.get(field_name, "")

    return getattr(record, field_name, "")


def _value_present(value):
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)

    return True


def field_value(record, field_name):
    aliases = FIELD_ALIASES.get(field_name, [field_name])

    for alias in aliases:
        value = _value_from(record, alias)

        if _value_present(value):
            return value

    return ""


def missing_core_fields(record=None):
    return [
        field_name
        for field_name in CORE_REQUIRED_FIELDS
        if not _value_present(field_value(record, field_name))
    ]


def optional_missing_fields(record=None):
    return [
        field_name
        for field_name in OPTIONAL_FIELDS
        if not _value_present(field_value(record, field_name))
    ]


def deferred_fields(record=None):
    return list(DEFERRED_FIELDS)


def core_fields_present(record=None):
    return not missing_core_fields(record)


def _status_map(record, fields):
    return {
        field_name: "present"
        if _value_present(field_value(record, field_name))
        else "missing"
        for field_name in fields
    }


def _deferred_status_map():
    return {field_name: DEFERRED_GOOGLE_MAPS for field_name in DEFERRED_FIELDS}


def build_ratecon_core_field_summary(record=None):
    missing = missing_core_fields(record)

    return {
        "core_required_fields": list(CORE_REQUIRED_FIELDS),
        "missing_core_fields": missing,
        "core_field_statuses": _status_map(record, CORE_REQUIRED_FIELDS),
        "optional_fields": list(OPTIONAL_FIELDS),
        "optional_missing_fields": optional_missing_fields(record),
        "optional_field_statuses": _status_map(record, OPTIONAL_FIELDS),
        "deferred_fields": deferred_fields(record),
        "deferred_field_statuses": _deferred_status_map(),
        "loaded_miles": "",
        "miles_status": DEFERRED_GOOGLE_MAPS,
        "miles_source": NOT_FROM_RATECON,
        "core_fields_present": not missing,
        "ready_for_review": not missing,
    }
