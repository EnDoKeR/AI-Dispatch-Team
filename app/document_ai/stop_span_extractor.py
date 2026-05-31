"""Provider-line stop span extraction contracts.

The span extractor consumes layout lines/tables before the older raw stop group
path fragments provider evidence into many stop candidates.
"""

from app.document_ai.layout_artifacts import normalize_bbox
from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_ADDRESS,
    NORMALIZED_STOP_FIELD_APPOINTMENT_WINDOW,
    NORMALIZED_STOP_FIELD_CITY_STATE,
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_FACILITY_NAME,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_NOTES,
    NORMALIZED_STOP_FIELD_REFERENCE,
    NORMALIZED_STOP_FIELD_TIME,
    NORMALIZED_STOP_TYPE_DELIVERY,
    NORMALIZED_STOP_TYPE_PICKUP,
    NORMALIZED_STOP_TYPE_STOP,
    NORMALIZED_STOP_TYPE_UNKNOWN,
    NORMALIZED_STOP_TYPES,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_UNKNOWN,
    normalize_confidence,
    normalize_list,
)


STOP_SPAN_ANCHOR_TYPE_PICKUP = "pickup"
STOP_SPAN_ANCHOR_TYPE_DELIVERY = "delivery"
STOP_SPAN_ANCHOR_TYPE_STOP = "stop"
STOP_SPAN_ANCHOR_TYPE_SHIPPER = "shipper"
STOP_SPAN_ANCHOR_TYPE_CONSIGNEE = "consignee"
STOP_SPAN_ANCHOR_TYPE_ORIGIN = "origin"
STOP_SPAN_ANCHOR_TYPE_DESTINATION = "destination"
STOP_SPAN_ANCHOR_TYPE_LOAD_AT = "load_at"
STOP_SPAN_ANCHOR_TYPE_DELIVER_TO = "deliver_to"
STOP_SPAN_ANCHOR_TYPE_PU = "pu"
STOP_SPAN_ANCHOR_TYPE_SO = "so"
STOP_SPAN_ANCHOR_TYPE_UNKNOWN = "unknown"

STOP_SPAN_ANCHOR_TYPES = {
    STOP_SPAN_ANCHOR_TYPE_PICKUP,
    STOP_SPAN_ANCHOR_TYPE_DELIVERY,
    STOP_SPAN_ANCHOR_TYPE_STOP,
    STOP_SPAN_ANCHOR_TYPE_SHIPPER,
    STOP_SPAN_ANCHOR_TYPE_CONSIGNEE,
    STOP_SPAN_ANCHOR_TYPE_ORIGIN,
    STOP_SPAN_ANCHOR_TYPE_DESTINATION,
    STOP_SPAN_ANCHOR_TYPE_LOAD_AT,
    STOP_SPAN_ANCHOR_TYPE_DELIVER_TO,
    STOP_SPAN_ANCHOR_TYPE_PU,
    STOP_SPAN_ANCHOR_TYPE_SO,
    STOP_SPAN_ANCHOR_TYPE_UNKNOWN,
}

STOP_SPAN_SOURCE_LAYOUT_LINE = "layout_line"
STOP_SPAN_SOURCE_LAYOUT_TABLE_ROW = "layout_table_row"
STOP_SPAN_SOURCE_LAYOUT_BLOCK = "layout_block"
STOP_SPAN_SOURCE_SYNTHETIC_FIXTURE = "synthetic_fixture"
STOP_SPAN_SOURCE_UNKNOWN = "unknown"

STOP_SPAN_SOURCES = {
    STOP_SPAN_SOURCE_LAYOUT_LINE,
    STOP_SPAN_SOURCE_LAYOUT_TABLE_ROW,
    STOP_SPAN_SOURCE_LAYOUT_BLOCK,
    STOP_SPAN_SOURCE_SYNTHETIC_FIXTURE,
    STOP_SPAN_SOURCE_UNKNOWN,
}

STOP_SPAN_FIELD_FACILITY_NAME = NORMALIZED_STOP_FIELD_FACILITY_NAME
STOP_SPAN_FIELD_ADDRESS = NORMALIZED_STOP_FIELD_ADDRESS
STOP_SPAN_FIELD_CITY_STATE = NORMALIZED_STOP_FIELD_CITY_STATE
STOP_SPAN_FIELD_LOCATION = NORMALIZED_STOP_FIELD_LOCATION
STOP_SPAN_FIELD_DATE = NORMALIZED_STOP_FIELD_DATE
STOP_SPAN_FIELD_TIME = NORMALIZED_STOP_FIELD_TIME
STOP_SPAN_FIELD_APPOINTMENT_WINDOW = NORMALIZED_STOP_FIELD_APPOINTMENT_WINDOW
STOP_SPAN_FIELD_REFERENCE = NORMALIZED_STOP_FIELD_REFERENCE
STOP_SPAN_FIELD_NOTES = NORMALIZED_STOP_FIELD_NOTES

STOP_SPAN_FIELDS = {
    STOP_SPAN_FIELD_FACILITY_NAME,
    STOP_SPAN_FIELD_ADDRESS,
    STOP_SPAN_FIELD_CITY_STATE,
    STOP_SPAN_FIELD_LOCATION,
    STOP_SPAN_FIELD_DATE,
    STOP_SPAN_FIELD_TIME,
    STOP_SPAN_FIELD_APPOINTMENT_WINDOW,
    STOP_SPAN_FIELD_REFERENCE,
    STOP_SPAN_FIELD_NOTES,
}

STOP_SPAN_EXTRACTOR_VERSION = "stop_span_extractor_v1"


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int_or_empty(value):
    if value in [None, ""]:
        return ""
    try:
        return int(value)
    except (TypeError, ValueError):
        return ""


def _normalize_anchor_type(value):
    token = _token(value)
    return token if token in STOP_SPAN_ANCHOR_TYPES else STOP_SPAN_ANCHOR_TYPE_UNKNOWN


def _normalize_source(value):
    token = _token(value)
    return token if token in STOP_SPAN_SOURCES else STOP_SPAN_SOURCE_UNKNOWN


def _normalize_stop_type(value):
    token = _token(value)
    return token if token in NORMALIZED_STOP_TYPES else NORMALIZED_STOP_TYPE_UNKNOWN


def _normalize_field_name(value):
    token = _token(value)
    return token if token in STOP_SPAN_FIELDS else STOP_SPAN_FIELD_NOTES


def build_stop_span_anchor(
    anchor_id="",
    anchor_type=STOP_SPAN_ANCHOR_TYPE_UNKNOWN,
    page_number=0,
    line_id="",
    block_id="",
    table_id="",
    row_index=None,
    bbox=None,
    label_category="unknown",
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
):
    return {
        "anchor_id": _text(anchor_id),
        "anchor_type": _normalize_anchor_type(anchor_type),
        "page_number": int(page_number or 0),
        "line_id": _text(line_id),
        "block_id": _text(block_id),
        "table_id": _text(table_id),
        "row_index": _int_or_empty(row_index),
        "bbox": normalize_bbox(bbox, page_number=page_number) if bbox else None,
        "label_category": _text(label_category) or STOP_SPAN_ANCHOR_TYPE_UNKNOWN,
        "confidence": normalize_confidence(confidence),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_span(
    span_id="",
    anchor=None,
    page_number=0,
    start_line_id="",
    end_line_id="",
    line_ids=None,
    table_id="",
    row_indices=None,
    section_role="",
    stop_type=NORMALIZED_STOP_TYPE_UNKNOWN,
    sequence=None,
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
):
    return {
        "span_id": _text(span_id),
        "anchor": anchor if isinstance(anchor, dict) else {},
        "page_number": int(page_number or 0),
        "start_line_id": _text(start_line_id),
        "end_line_id": _text(end_line_id),
        "line_ids": normalize_list(line_ids),
        "table_id": _text(table_id),
        "row_indices": [
            int(row)
            for row in row_indices or []
            if str(row).strip() and str(row).strip().lstrip("-").isdigit()
        ],
        "section_role": _text(section_role),
        "stop_type": _normalize_stop_type(stop_type),
        "sequence": sequence if sequence not in [None, ""] else "",
        "confidence": normalize_confidence(confidence),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_span_field_candidate(
    span_id="",
    field_name=STOP_SPAN_FIELD_NOTES,
    candidate_id="",
    confidence=CANDIDATE_CONFIDENCE_UNKNOWN,
    evidence_ref=None,
    source=STOP_SPAN_SOURCE_UNKNOWN,
    reasons=None,
    warning_codes=None,
):
    return {
        "span_id": _text(span_id),
        "field_name": _normalize_field_name(field_name),
        "candidate_id": _text(candidate_id),
        "confidence": normalize_confidence(confidence),
        "evidence_ref": evidence_ref if isinstance(evidence_ref, dict) else {},
        "source": _normalize_source(source),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
    }


def build_stop_span_extraction_result(
    document_alias="",
    anchors=None,
    spans=None,
    field_candidates=None,
    raw_line_count=0,
    warning_codes=None,
):
    safe_anchors = [anchor for anchor in anchors or [] if isinstance(anchor, dict)]
    safe_spans = [span for span in spans or [] if isinstance(span, dict)]
    safe_fields = [
        candidate
        for candidate in field_candidates or []
        if isinstance(candidate, dict)
    ]
    raw_count = int(raw_line_count or 0)
    span_count = len(safe_spans)

    return {
        "document_alias": _text(document_alias),
        "anchors": safe_anchors,
        "spans": safe_spans,
        "field_candidates": safe_fields,
        "raw_line_count": raw_count,
        "anchor_count": len(safe_anchors),
        "span_count": span_count,
        "passthrough_detected": bool(span_count and raw_count and span_count >= raw_count),
        "warning_codes": normalize_list(warning_codes),
        "extractor_version": STOP_SPAN_EXTRACTOR_VERSION,
        "raw_text_included": False,
        "private_values_redacted": True,
    }

