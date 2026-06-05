"""Load identifier adapter provenance helpers.

These helpers preserve already-existing load candidate source metadata across
adapter and diagnostic boundaries. They do not generate candidates, infer
missing page/line detail, score candidates, or change resolver selection.
"""

from __future__ import annotations

from typing import Any


LOAD_ADAPTER_PROVENANCE_SCHEMA_VERSION = "ratecon_load_candidate_adapter_provenance_v1"

LOAD_ADAPTER_ROUNDTRIP_COMPLETE = "adapter_roundtrip_complete"
LOAD_ADAPTER_ROUNDTRIP_MISSING_INPUT_DETAIL = "adapter_roundtrip_missing_input_detail"
LOAD_ADAPTER_ROUNDTRIP_PRESERVED_PARTIAL_DETAIL = (
    "adapter_roundtrip_preserved_partial_detail"
)
LOAD_ADAPTER_ROUNDTRIP_LOST_CANDIDATE_ID = "adapter_roundtrip_lost_candidate_id"
LOAD_ADAPTER_ROUNDTRIP_LOST_PAGE_LINE = "adapter_roundtrip_lost_page_line"
LOAD_ADAPTER_ROUNDTRIP_LOST_SOURCE = "adapter_roundtrip_lost_source"
LOAD_ADAPTER_ROUNDTRIP_LOST_PAIRING_METHOD = "adapter_roundtrip_lost_pairing_method"
LOAD_ADAPTER_ROUNDTRIP_NOT_APPLICABLE = "adapter_roundtrip_not_applicable"
LOAD_ADAPTER_ROUNDTRIP_UNKNOWN = "adapter_roundtrip_unknown"

LOAD_ADAPTER_ROUNDTRIP_STATUSES = (
    LOAD_ADAPTER_ROUNDTRIP_COMPLETE,
    LOAD_ADAPTER_ROUNDTRIP_MISSING_INPUT_DETAIL,
    LOAD_ADAPTER_ROUNDTRIP_PRESERVED_PARTIAL_DETAIL,
    LOAD_ADAPTER_ROUNDTRIP_LOST_CANDIDATE_ID,
    LOAD_ADAPTER_ROUNDTRIP_LOST_PAGE_LINE,
    LOAD_ADAPTER_ROUNDTRIP_LOST_SOURCE,
    LOAD_ADAPTER_ROUNDTRIP_LOST_PAIRING_METHOD,
    LOAD_ADAPTER_ROUNDTRIP_NOT_APPLICABLE,
    LOAD_ADAPTER_ROUNDTRIP_UNKNOWN,
)

LOAD_CANDIDATE_FIELDS = {"load_number", "reference", "reference_numbers"}
REDACTED_VALUE = "[redacted]"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _token(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _metadata(row: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance((row or {}).get("metadata"), dict):
        return dict((row or {}).get("metadata") or {})
    if isinstance((row or {}).get("metadata_summary"), dict):
        return dict((row or {}).get("metadata_summary") or {})
    return {}


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _candidate_field(row: dict[str, Any] | None) -> str:
    return _token(
        (row or {}).get("field")
        or (row or {}).get("field_name")
        or _metadata(row).get("field")
    )


def _looks_like_load_candidate(row: dict[str, Any] | None) -> bool:
    metadata = _metadata(row)
    field = _candidate_field(row)
    return (
        field in LOAD_CANDIDATE_FIELDS
        or bool(metadata.get("identifier_type"))
        or bool(metadata.get("id_type_hint"))
        or bool((row or {}).get("primary_load_identifier_candidate"))
    )


def _candidate_id(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    return _first_text(
        (row or {}).get("candidate_id"),
        (row or {}).get("id"),
        (row or {}).get("selected_candidate_id"),
        metadata.get("candidate_id"),
    )


def _source(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    return _first_text(
        (row or {}).get("source"),
        (row or {}).get("selected_source"),
        metadata.get("source"),
        metadata.get("original_source"),
    )


def _parser_name(row: dict[str, Any] | None, parser_name: str = "") -> str:
    metadata = _metadata(row)
    return _first_text(
        (row or {}).get("parser_name"),
        (row or {}).get("parser"),
        metadata.get("parser_name"),
        parser_name,
    )


def _page_number(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    return _first_text(
        (row or {}).get("page_number"),
        (row or {}).get("page_index"),
        (row or {}).get("page"),
        (row or {}).get("selected_page_index"),
        (row or {}).get("selected_page"),
        (row or {}).get("source_page"),
        metadata.get("page_number"),
        metadata.get("page_index"),
        metadata.get("page"),
        metadata.get("source_page"),
    )


def _line_index(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    return _first_text(
        (row or {}).get("line_index"),
        (row or {}).get("line_number"),
        (row or {}).get("selected_line_index"),
        (row or {}).get("source_line_index"),
        (row or {}).get("reading_order_index"),
        metadata.get("line_index"),
        metadata.get("line_number"),
        metadata.get("source_line_index"),
        metadata.get("reading_order_index"),
    )


def _has_page_line(row: dict[str, Any] | None) -> bool:
    metadata = _metadata(row)
    return bool(
        _page_number(row)
        or _line_index(row)
        or _text((row or {}).get("source_line"))
        or _text(metadata.get("source_line"))
    )


def _pairing_method(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    return _first_text(
        (row or {}).get("pairing_method"),
        (row or {}).get("selected_pairing_method"),
        metadata.get("pairing_method"),
        metadata.get("value_extraction_method"),
        metadata.get("match_kind"),
    )


def _bbox(row: dict[str, Any] | None) -> Any:
    metadata = _metadata(row)
    bbox = (row or {}).get("bbox")
    if isinstance(bbox, dict):
        bbox = bbox.get("bbox")
    return bbox or metadata.get("bbox") or metadata.get("value_bbox")


def _has_bbox(row: dict[str, Any] | None) -> bool:
    metadata = _metadata(row)
    return bool(
        _bbox(row)
        or (row or {}).get("bbox_available")
        or metadata.get("bbox_available")
        or metadata.get("has_bbox")
    )


def _status_from_text(value: Any) -> str:
    return "present" if _text(value) else ""


def load_candidate_provenance_fields(
    candidate: dict[str, Any] | None,
    *,
    parser_name: str = "",
) -> dict[str, Any]:
    """Return source-line fields already present on a load/reference candidate."""

    candidate = candidate or {}
    if not _looks_like_load_candidate(candidate):
        return {}
    metadata = _metadata(candidate)
    fields: dict[str, Any] = {}
    for key, value in [
        ("candidate_id", _candidate_id(candidate)),
        ("source", _source(candidate)),
        ("source_family", _first_text(candidate.get("source_family"), metadata.get("source_family"))),
        ("parser_name", _parser_name(candidate, parser_name)),
        ("page_number", _page_number(candidate)),
        ("line_index", _line_index(candidate)),
        ("line_number", _line_index(candidate)),
        ("source_line", _first_text(candidate.get("source_line"), metadata.get("source_line"))),
        ("pairing_method", _pairing_method(candidate)),
        ("label_text_status", _first_text(metadata.get("label_text_status"), _status_from_text(candidate.get("label")))),
        (
            "value_text_status",
            _first_text(
                metadata.get("value_text_status"),
                _status_from_text(candidate.get("raw_value") or candidate.get("value")),
            ),
        ),
        (
            "neighbor_context_status",
            _first_text(
                metadata.get("neighbor_context_status"),
                _status_from_text(candidate.get("context_before") or candidate.get("context_after")),
            ),
        ),
    ]:
        if value not in ("", None):
            fields[key] = value
    bbox = _bbox(candidate)
    if bbox:
        fields["bbox"] = bbox
    if _has_bbox(candidate):
        fields["bbox_available"] = True
    if fields:
        fields["adapter_provenance_schema_version"] = LOAD_ADAPTER_PROVENANCE_SCHEMA_VERSION
    return fields


def preserve_load_candidate_provenance(
    candidate: dict[str, Any] | None,
    *,
    metadata: dict[str, Any] | None = None,
    parser_name: str = "",
) -> dict[str, Any]:
    """Copy existing load candidate provenance into metadata without inventing it."""

    payload = dict(metadata or {})
    fields = load_candidate_provenance_fields(candidate, parser_name=parser_name)
    for key, value in fields.items():
        if value not in ("", None) and key not in payload:
            payload[key] = value
    if fields:
        payload["adapter_provenance_preserved"] = True
    return payload


def _availability(row: dict[str, Any] | None) -> dict[str, bool]:
    return {
        "candidate_id": bool(_candidate_id(row)),
        "page_line": _has_page_line(row),
        "source": bool(_source(row)),
        "pairing_method": bool(_pairing_method(row)),
    }


def summarize_adapter_provenance_roundtrip(
    input_candidate: dict[str, Any] | None,
    output_candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    """Summarize whether source-line provenance survived adapter output."""

    if not input_candidate:
        return {
            "adapter_input_candidate_id_available": False,
            "adapter_output_candidate_id_available": bool(_candidate_id(output_candidate)),
            "adapter_input_page_line_available": False,
            "adapter_output_page_line_available": _has_page_line(output_candidate),
            "adapter_input_source_available": False,
            "adapter_output_source_available": bool(_source(output_candidate)),
            "adapter_input_pairing_method_available": False,
            "adapter_output_pairing_method_available": bool(_pairing_method(output_candidate)),
            "adapter_roundtrip_status": LOAD_ADAPTER_ROUNDTRIP_NOT_APPLICABLE,
            "adapter_loss_reason": "No adapter input candidate detail was available.",
        }
    input_availability = _availability(input_candidate)
    output_availability = _availability(output_candidate)
    any_input = any(input_availability.values())
    all_input = all(input_availability.values())
    if not any_input:
        status = LOAD_ADAPTER_ROUNDTRIP_MISSING_INPUT_DETAIL
        reason = "Adapter input candidate lacks candidate id, page/line, source, and pairing detail."
    elif input_availability["candidate_id"] and not output_availability["candidate_id"]:
        status = LOAD_ADAPTER_ROUNDTRIP_LOST_CANDIDATE_ID
        reason = "Candidate id existed before adapter output but was not visible after adaptation."
    elif input_availability["page_line"] and not output_availability["page_line"]:
        status = LOAD_ADAPTER_ROUNDTRIP_LOST_PAGE_LINE
        reason = "Page or line detail existed before adapter output but was not visible after adaptation."
    elif input_availability["source"] and not output_availability["source"]:
        status = LOAD_ADAPTER_ROUNDTRIP_LOST_SOURCE
        reason = "Source detail existed before adapter output but was not visible after adaptation."
    elif input_availability["pairing_method"] and not output_availability["pairing_method"]:
        status = LOAD_ADAPTER_ROUNDTRIP_LOST_PAIRING_METHOD
        reason = "Pairing method existed before adapter output but was not visible after adaptation."
    elif all_input and all(output_availability.values()):
        status = LOAD_ADAPTER_ROUNDTRIP_COMPLETE
        reason = "Candidate id, page/line, source, and pairing method survived adapter output."
    else:
        status = LOAD_ADAPTER_ROUNDTRIP_PRESERVED_PARTIAL_DETAIL
        reason = "Adapter output preserved the subset of source detail present at input."
    return {
        "adapter_input_candidate_id_available": input_availability["candidate_id"],
        "adapter_output_candidate_id_available": output_availability["candidate_id"],
        "adapter_input_page_line_available": input_availability["page_line"],
        "adapter_output_page_line_available": output_availability["page_line"],
        "adapter_input_source_available": input_availability["source"],
        "adapter_output_source_available": output_availability["source"],
        "adapter_input_pairing_method_available": input_availability["pairing_method"],
        "adapter_output_pairing_method_available": output_availability["pairing_method"],
        "adapter_roundtrip_status": status,
        "adapter_loss_reason": reason,
    }


def redacted_adapter_provenance_row(
    candidate: dict[str, Any] | None,
    *,
    include_private_values: bool = False,
) -> dict[str, Any]:
    """Return a safe diagnostic row for tests/local tooling."""

    candidate = candidate or {}
    value = _first_text(
        candidate.get("candidate_value"),
        candidate.get("raw_value"),
        candidate.get("value"),
        candidate.get("selected_value"),
    )
    fields = load_candidate_provenance_fields(candidate)
    return {
        "schema_version": LOAD_ADAPTER_PROVENANCE_SCHEMA_VERSION,
        "candidate_id": fields.get("candidate_id", ""),
        "source": fields.get("source", ""),
        "page_number": fields.get("page_number", ""),
        "line_index": fields.get("line_index", ""),
        "pairing_method": fields.get("pairing_method", ""),
        "private_values_redacted": not include_private_values,
        "value_preview": value if include_private_values else REDACTED_VALUE if value else "",
    }
