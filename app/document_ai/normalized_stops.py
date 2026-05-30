"""Normalized stop contracts for layout-backed RateCon extraction."""

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_UNKNOWN,
    normalize_confidence,
    normalize_list,
)


NORMALIZED_STOP_TYPE_PICKUP = "pickup"
NORMALIZED_STOP_TYPE_DELIVERY = "delivery"
NORMALIZED_STOP_TYPE_STOP = "stop"
NORMALIZED_STOP_TYPE_UNKNOWN = "unknown"

NORMALIZED_STOP_TYPES = {
    NORMALIZED_STOP_TYPE_PICKUP,
    NORMALIZED_STOP_TYPE_DELIVERY,
    NORMALIZED_STOP_TYPE_STOP,
    NORMALIZED_STOP_TYPE_UNKNOWN,
}

NORMALIZED_STOP_FIELD_STATUS_RESOLVED = "resolved"
NORMALIZED_STOP_FIELD_STATUS_MISSING = "missing"
NORMALIZED_STOP_FIELD_STATUS_LOW_CONFIDENCE = "low_confidence"
NORMALIZED_STOP_FIELD_STATUS_CONFLICT = "conflict"
NORMALIZED_STOP_FIELD_STATUS_NOT_APPLICABLE = "not_applicable"
NORMALIZED_STOP_FIELD_STATUS_REVIEW_REQUIRED = "review_required"

NORMALIZED_STOP_FIELD_STATUSES = {
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_STATUS_MISSING,
    NORMALIZED_STOP_FIELD_STATUS_LOW_CONFIDENCE,
    NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
    NORMALIZED_STOP_FIELD_STATUS_NOT_APPLICABLE,
    NORMALIZED_STOP_FIELD_STATUS_REVIEW_REQUIRED,
}

NORMALIZED_STOP_FIELD_FACILITY_NAME = "facility_name"
NORMALIZED_STOP_FIELD_LOCATION = "location"
NORMALIZED_STOP_FIELD_ADDRESS = "address"
NORMALIZED_STOP_FIELD_CITY_STATE = "city_state"
NORMALIZED_STOP_FIELD_DATE = "date"
NORMALIZED_STOP_FIELD_TIME = "time"
NORMALIZED_STOP_FIELD_APPOINTMENT_WINDOW = "appointment_window"
NORMALIZED_STOP_FIELD_REFERENCE = "reference"
NORMALIZED_STOP_FIELD_NOTES = "notes"

NORMALIZED_STOP_FIELDS = {
    NORMALIZED_STOP_FIELD_FACILITY_NAME,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_ADDRESS,
    NORMALIZED_STOP_FIELD_CITY_STATE,
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_TIME,
    NORMALIZED_STOP_FIELD_APPOINTMENT_WINDOW,
    NORMALIZED_STOP_FIELD_REFERENCE,
    NORMALIZED_STOP_FIELD_NOTES,
}

NORMALIZED_STOP_SET_VERSION = "normalized_stop_set_v1"


def _text(value):
    return str(value or "").strip()


def _normalized_token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def normalize_stop_type(value):
    token = _normalized_token(value)
    return token if token in NORMALIZED_STOP_TYPES else NORMALIZED_STOP_TYPE_UNKNOWN


def normalize_stop_field_status(value):
    token = _normalized_token(value)
    if token in NORMALIZED_STOP_FIELD_STATUSES:
        return token
    return NORMALIZED_STOP_FIELD_STATUS_REVIEW_REQUIRED


def normalize_stop_field_name(value):
    token = _normalized_token(value)
    return token if token in NORMALIZED_STOP_FIELDS else NORMALIZED_STOP_FIELD_NOTES


def _safe_evidence_refs(value):
    return [item for item in value or [] if isinstance(item, dict)]


def build_normalized_stop_field(
    field_name=NORMALIZED_STOP_FIELD_NOTES,
    status=NORMALIZED_STOP_FIELD_STATUS_MISSING,
    selected_candidate_id="",
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    evidence_refs=None,
    reasons=None,
    warning_codes=None,
):
    return {
        "field_name": normalize_stop_field_name(field_name),
        "status": normalize_stop_field_status(status),
        "selected_candidate_id": _text(selected_candidate_id),
        "confidence": normalize_confidence(confidence),
        "evidence_refs": _safe_evidence_refs(evidence_refs),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_normalized_stop(
    stop_id="",
    sequence=None,
    stop_type=NORMALIZED_STOP_TYPE_UNKNOWN,
    source_group_ids=None,
    page_numbers=None,
    section_roles=None,
    table_ids=None,
    row_indices=None,
    fields=None,
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
    review_required=False,
):
    normalized_fields = [
        field for field in fields or [] if isinstance(field, dict)
    ]
    return {
        "stop_id": _text(stop_id),
        "sequence": sequence if sequence not in [None, ""] else "",
        "stop_type": normalize_stop_type(stop_type),
        "source_group_ids": normalize_list(source_group_ids),
        "page_numbers": [
            int(page)
            for page in page_numbers or []
            if str(page).strip() and str(page).strip().lstrip("-").isdigit()
        ],
        "section_roles": normalize_list(section_roles),
        "table_ids": normalize_list(table_ids),
        "row_indices": [
            int(row)
            for row in row_indices or []
            if str(row).strip() and str(row).strip().lstrip("-").isdigit()
        ],
        "fields": normalized_fields,
        "confidence": normalize_confidence(confidence),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
        "review_required": bool(review_required),
    }


def _field_key(stop, field_name):
    return f"{(stop or {}).get('stop_id', '')}.{field_name}"


def build_normalized_stop_set(
    document_alias="",
    stops=None,
    unresolved_fields=None,
    conflict_fields=None,
    warning_codes=None,
):
    normalized_stops = [stop for stop in stops or [] if isinstance(stop, dict)]
    pickup_count = sum(
        1
        for stop in normalized_stops
        if stop.get("stop_type") == NORMALIZED_STOP_TYPE_PICKUP
    )
    delivery_count = sum(
        1
        for stop in normalized_stops
        if stop.get("stop_type") == NORMALIZED_STOP_TYPE_DELIVERY
    )
    unknown_count = sum(
        1
        for stop in normalized_stops
        if stop.get("stop_type") == NORMALIZED_STOP_TYPE_UNKNOWN
    )

    unresolved = list(normalize_list(unresolved_fields))
    conflicts = list(normalize_list(conflict_fields))
    for stop in normalized_stops:
        for field in stop.get("fields", []) or []:
            field_name = field.get("field_name", "")
            status = field.get("status", "")
            if status in {
                NORMALIZED_STOP_FIELD_STATUS_MISSING,
                NORMALIZED_STOP_FIELD_STATUS_LOW_CONFIDENCE,
                NORMALIZED_STOP_FIELD_STATUS_REVIEW_REQUIRED,
            }:
                unresolved.append(_field_key(stop, field_name))
            if status == NORMALIZED_STOP_FIELD_STATUS_CONFLICT:
                conflicts.append(_field_key(stop, field_name))

    return {
        "document_alias": _text(document_alias),
        "stops": normalized_stops,
        "pickup_count": pickup_count,
        "delivery_count": delivery_count,
        "unknown_count": unknown_count,
        "unresolved_fields": sorted(set(unresolved)),
        "conflict_fields": sorted(set(conflicts)),
        "warning_codes": normalize_list(warning_codes),
        "stop_set_version": NORMALIZED_STOP_SET_VERSION,
    }
