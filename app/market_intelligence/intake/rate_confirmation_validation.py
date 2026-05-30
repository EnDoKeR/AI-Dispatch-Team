"""Validation helpers for Rate Confirmation intake contracts."""

from copy import deepcopy

from app.market_intelligence.intake.rate_confirmation_intake import (
    CONFIDENCE_LOW,
    STATUS_MISSING_FIELDS,
    STATUS_READY_FOR_REVIEW,
    STATUS_REVIEW_REQUIRED,
    build_rate_confirmation_intake,
    candidate_conflicts,
    computed_missing_fields,
    low_confidence_fields,
    normalize_list,
    status_from_fields,
)


OPTIONAL_REVIEW_FIELDS = [
    "broker_mc",
    "equipment",
]


def _value_from(record, field_name, default=""):
    if record is None:
        return default

    if isinstance(record, dict):
        return record.get(field_name, default)

    return getattr(record, field_name, default)


def _has_value(value):
    if value is None:
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, dict):
        return any(_has_value(item) for item in value.values())

    if isinstance(value, (list, tuple, set)):
        return any(_has_value(item) for item in value)

    return value != ""


def _append_once(values, value):
    if value and value not in values:
        values.append(value)


def _optional_missing_fields(intake):
    return [
        field_name
        for field_name in OPTIONAL_REVIEW_FIELDS
        if not _has_value(_value_from(intake, field_name, ""))
    ]


def _needs_check_fields(intake):
    needs_check = []
    low_confidence = low_confidence_fields(intake.get("field_confidences", {}))
    conflicts = candidate_conflicts(intake.get("field_candidates", []))

    for field_name in low_confidence:
        _append_once(needs_check, field_name)

    for field_name in conflicts:
        _append_once(needs_check, field_name)

    for field_name in normalize_list(_value_from(intake, "needs_check_fields", [])):
        _append_once(needs_check, field_name)

    return needs_check


def validate_rate_confirmation_intake(record=None):
    """Compute validation state without trusting caller-provided status fields."""
    original = deepcopy(record)
    intake = build_rate_confirmation_intake(record)
    missing_fields = computed_missing_fields(intake)

    for field_name in normalize_list(_value_from(original, "missing_fields", [])):
        _append_once(missing_fields, field_name)

    needs_check_fields = _needs_check_fields(intake)
    optional_missing = _optional_missing_fields(intake)
    conflict_fields = candidate_conflicts(intake.get("field_candidates", []))
    low_confidence = low_confidence_fields(intake.get("field_confidences", {}))
    status = status_from_fields(missing_fields, needs_check_fields)

    return {
        "status": status,
        "review_required": status != STATUS_READY_FOR_REVIEW,
        "missing_fields": missing_fields,
        "needs_check_fields": needs_check_fields,
        "optional_missing_fields": optional_missing,
        "low_confidence_fields": low_confidence,
        "conflict_fields": conflict_fields,
        "validated_intake": intake,
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }


def rate_confirmation_ready_for_review(record=None):
    validation = validate_rate_confirmation_intake(record)

    return validation["status"] == STATUS_READY_FOR_REVIEW


__all__ = [
    "CONFIDENCE_LOW",
    "OPTIONAL_REVIEW_FIELDS",
    "STATUS_MISSING_FIELDS",
    "STATUS_READY_FOR_REVIEW",
    "STATUS_REVIEW_REQUIRED",
    "rate_confirmation_ready_for_review",
    "validate_rate_confirmation_intake",
]
