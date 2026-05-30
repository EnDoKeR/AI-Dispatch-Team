"""Layout-aware stop association contracts and helpers."""

from app.document_ai.ratecon_candidates import normalize_list


STOP_ASSOCIATION_SOURCE_TABLE_ROW = "table_row"
STOP_ASSOCIATION_SOURCE_SECTION_BLOCK = "section_block"
STOP_ASSOCIATION_SOURCE_LABEL_VALUE = "label_value"
STOP_ASSOCIATION_SOURCE_TEXT_REGEX = "text_regex"
STOP_ASSOCIATION_SOURCE_TEMPLATE_RULE = "template_rule"
STOP_ASSOCIATION_SOURCE_UNKNOWN = "unknown"

STOP_ASSOCIATION_SOURCES = {
    STOP_ASSOCIATION_SOURCE_TABLE_ROW,
    STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
    STOP_ASSOCIATION_SOURCE_LABEL_VALUE,
    STOP_ASSOCIATION_SOURCE_TEXT_REGEX,
    STOP_ASSOCIATION_SOURCE_TEMPLATE_RULE,
    STOP_ASSOCIATION_SOURCE_UNKNOWN,
}

STOP_TYPE_PICKUP = "pickup"
STOP_TYPE_DELIVERY = "delivery"
STOP_TYPE_STOP = "stop"
STOP_TYPE_UNKNOWN = "unknown"

STOP_TYPES = {
    STOP_TYPE_PICKUP,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_STOP,
    STOP_TYPE_UNKNOWN,
}

STOP_FIELD_LOCATION = "location"
STOP_FIELD_DATE = "date"
STOP_FIELD_TIME = "time"
STOP_FIELD_REFERENCE = "reference"
STOP_FIELD_NOTES = "notes"
STOP_FIELD_FACILITY_NAME = "facility_name"
STOP_FIELD_ADDRESS = "address"
STOP_FIELD_CONTACT = "contact"

STOP_FIELD_NAMES = {
    STOP_FIELD_LOCATION,
    STOP_FIELD_DATE,
    STOP_FIELD_TIME,
    STOP_FIELD_REFERENCE,
    STOP_FIELD_NOTES,
    STOP_FIELD_FACILITY_NAME,
    STOP_FIELD_ADDRESS,
    STOP_FIELD_CONTACT,
}

STOP_ASSOCIATION_VERSION = "stop_association_v1"


def _text(value):
    return str(value or "").strip()


def _normalize_source(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    return text if text in STOP_ASSOCIATION_SOURCES else STOP_ASSOCIATION_SOURCE_UNKNOWN


def _normalize_stop_type(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    return text if text in STOP_TYPES else STOP_TYPE_UNKNOWN


def _normalize_field_name(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    return text if text in STOP_FIELD_NAMES else STOP_FIELD_NOTES


def build_stop_field_candidate(
    stop_group_id="",
    stop_sequence=None,
    stop_type=STOP_TYPE_UNKNOWN,
    field_name=STOP_FIELD_NOTES,
    candidate_id="",
    confidence=0.0,
    evidence_ref=None,
    source=STOP_ASSOCIATION_SOURCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
):
    return {
        "stop_group_id": _text(stop_group_id),
        "stop_sequence": stop_sequence if stop_sequence not in [None, ""] else "",
        "stop_type": _normalize_stop_type(stop_type),
        "field_name": _normalize_field_name(field_name),
        "candidate_id": _text(candidate_id),
        "confidence": float(confidence or 0.0),
        "evidence_ref": evidence_ref if isinstance(evidence_ref, dict) else {},
        "source": _normalize_source(source),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_group_candidate(
    stop_group_id="",
    stop_sequence=None,
    stop_type=STOP_TYPE_UNKNOWN,
    source=STOP_ASSOCIATION_SOURCE_UNKNOWN,
    page_number="",
    section_role="",
    table_id="",
    row_index=None,
    field_candidates=None,
    confidence=0.0,
    reasons=None,
    warning_codes=None,
):
    return {
        "stop_group_id": _text(stop_group_id),
        "stop_sequence": stop_sequence if stop_sequence not in [None, ""] else "",
        "stop_type": _normalize_stop_type(stop_type),
        "source": _normalize_source(source),
        "page_number": page_number if page_number not in [None, ""] else "",
        "section_role": _text(section_role),
        "table_id": _text(table_id),
        "row_index": row_index if row_index not in [None, ""] else "",
        "field_candidates": [
            candidate for candidate in field_candidates or [] if isinstance(candidate, dict)
        ],
        "confidence": float(confidence or 0.0),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_association_result(
    stop_groups=None,
    unresolved_stop_fields=None,
    conflict_stop_fields=None,
    warning_codes=None,
):
    return {
        "stop_groups": [group for group in stop_groups or [] if isinstance(group, dict)],
        "unresolved_stop_fields": normalize_list(unresolved_stop_fields),
        "conflict_stop_fields": normalize_list(conflict_stop_fields),
        "warning_codes": normalize_list(warning_codes),
        "association_version": STOP_ASSOCIATION_VERSION,
    }
