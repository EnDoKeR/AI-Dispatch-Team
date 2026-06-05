"""Local-only load generated/resolver provenance sidecar helpers.

These helpers normalize already-existing load candidate provenance metadata
across generated, adapter, dedupe, resolver, audit, and serialization surfaces.
They do not generate candidates, infer missing source-line detail, run
resolution, or change selected load-number behavior.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from typing import Any


LOAD_GENERATED_RESOLVER_PROVENANCE_SCHEMA_VERSION = (
    "ratecon_load_generated_resolver_provenance_v1"
)
LOAD_FIELD = "load_number"
REDACTED_VALUE = "[redacted]"

STAGE_GENERATED_DETAIL_AVAILABLE = "generated_detail_available"
STAGE_GENERATED_DETAIL_MISSING = "generated_detail_missing"
STAGE_ADAPTER_INPUT_AVAILABLE = "adapter_input_available"
STAGE_ADAPTER_INPUT_MISSING = "adapter_input_missing"
STAGE_ADAPTER_OUTPUT_AVAILABLE = "adapter_output_available"
STAGE_ADAPTER_OUTPUT_MISSING = "adapter_output_missing"
STAGE_LOST_BETWEEN_GENERATION_AND_ADAPTER = "lost_between_generation_and_adapter"
STAGE_LOST_BETWEEN_ADAPTER_AND_DEDUPE = "lost_between_adapter_and_dedupe"
STAGE_LOST_BETWEEN_DEDUPE_AND_RESOLVER = "lost_between_dedupe_and_resolver"
STAGE_LOST_BETWEEN_RESOLVER_AND_AUDIT = "lost_between_resolver_and_audit"
STAGE_LOST_BETWEEN_AUDIT_AND_EVALUATOR = "lost_between_audit_and_evaluator"
STAGE_RESOLVER_TRACE_UNAVAILABLE = "resolver_trace_unavailable"
STAGE_DEDUPE_LINEAGE_UNAVAILABLE = "dedupe_lineage_unavailable"
STAGE_PRIVATE_VALUES_NOT_REQUESTED = "private_values_not_requested"
STAGE_NOT_APPLICABLE_CANDIDATE_MISSING = "not_applicable_candidate_missing"
STAGE_UNKNOWN = "unknown"

ADAPTER_STAGE_COMPLETE = "adapter_stage_complete"
ADAPTER_STAGE_UNAVAILABLE = "adapter_stage_unavailable"
ADAPTER_INPUT_DETAIL_AVAILABLE = "adapter_input_detail_available"
ADAPTER_INPUT_DETAIL_MISSING = "adapter_input_detail_missing"
ADAPTER_OUTPUT_DETAIL_PRESERVED = "adapter_output_detail_preserved"
ADAPTER_OUTPUT_DETAIL_LOST = "adapter_output_detail_lost"
DEDUPE_STAGE_COMPLETE = "dedupe_stage_complete"
DEDUPE_STAGE_UNAVAILABLE = "dedupe_stage_unavailable"
DEDUPE_INPUT_DETAIL_AVAILABLE = "dedupe_input_detail_available"
DEDUPE_OUTPUT_DETAIL_PRESERVED = "dedupe_output_detail_preserved"
DEDUPE_OUTPUT_DETAIL_LOST = "dedupe_output_detail_lost"
DEDUPE_MERGED_DETAIL_PRESERVED = "dedupe_merged_detail_preserved"
DEDUPE_DROPPED_DETAIL_PRESERVED = "dedupe_dropped_detail_preserved"
DEDUPE_LINEAGE_UNAVAILABLE = "dedupe_lineage_unavailable"
NOT_APPLICABLE_CANDIDATE_MISSING = "not_applicable_candidate_missing"
ADAPTER_DEDUPE_UNKNOWN = "unknown"

ADAPTER_DEDUPE_STAGE_STATUSES = (
    ADAPTER_STAGE_COMPLETE,
    ADAPTER_STAGE_UNAVAILABLE,
    ADAPTER_INPUT_DETAIL_AVAILABLE,
    ADAPTER_INPUT_DETAIL_MISSING,
    ADAPTER_OUTPUT_DETAIL_PRESERVED,
    ADAPTER_OUTPUT_DETAIL_LOST,
    DEDUPE_STAGE_COMPLETE,
    DEDUPE_STAGE_UNAVAILABLE,
    DEDUPE_INPUT_DETAIL_AVAILABLE,
    DEDUPE_OUTPUT_DETAIL_PRESERVED,
    DEDUPE_OUTPUT_DETAIL_LOST,
    DEDUPE_MERGED_DETAIL_PRESERVED,
    DEDUPE_DROPPED_DETAIL_PRESERVED,
    DEDUPE_LINEAGE_UNAVAILABLE,
    NOT_APPLICABLE_CANDIDATE_MISSING,
    ADAPTER_DEDUPE_UNKNOWN,
)

STAGE_LOSS_BUCKETS = (
    STAGE_GENERATED_DETAIL_AVAILABLE,
    STAGE_GENERATED_DETAIL_MISSING,
    STAGE_ADAPTER_INPUT_AVAILABLE,
    STAGE_ADAPTER_INPUT_MISSING,
    STAGE_ADAPTER_OUTPUT_AVAILABLE,
    STAGE_ADAPTER_OUTPUT_MISSING,
    STAGE_LOST_BETWEEN_GENERATION_AND_ADAPTER,
    STAGE_LOST_BETWEEN_ADAPTER_AND_DEDUPE,
    STAGE_LOST_BETWEEN_DEDUPE_AND_RESOLVER,
    STAGE_LOST_BETWEEN_RESOLVER_AND_AUDIT,
    STAGE_LOST_BETWEEN_AUDIT_AND_EVALUATOR,
    STAGE_RESOLVER_TRACE_UNAVAILABLE,
    STAGE_DEDUPE_LINEAGE_UNAVAILABLE,
    STAGE_PRIVATE_VALUES_NOT_REQUESTED,
    STAGE_NOT_APPLICABLE_CANDIDATE_MISSING,
    STAGE_UNKNOWN,
)

ROUNDTRIP_COMPLETE = "generated_resolver_roundtrip_complete"
ROUNDTRIP_LOSS_DETECTED = "generated_resolver_roundtrip_loss_detected"
ROUNDTRIP_PARTIAL = "generated_resolver_roundtrip_partial_detail"
ROUNDTRIP_UNMEASURABLE = "current_like_eval_audit_only_unmeasurable"
ROUNDTRIP_NO_INPUTS = "generated_resolver_inputs_unavailable"

STAGE_ROW_FIELDNAMES = [
    "document_id",
    "field",
    "stage",
    "candidate_id",
    "source",
    "source_family",
    "parser_name",
    "pairing_method",
    "page_number",
    "line_index",
    "bbox_available",
    "candidate_rank",
    "generated",
    "adapter_input",
    "adapter_output",
    "dedupe_input",
    "dedupe_output",
    "resolver_input",
    "resolver_eligible",
    "resolver_selected",
    "resolver_trace_available",
    "dedupe_merged",
    "dedupe_dropped",
    "dedupe_parent_candidate_ids",
    "dedupe_child_candidate_ids",
    "detail_roundtrip_status",
    "detail_loss_stage",
    "detail_loss_reason",
    "private_values_redacted",
    "value_preview",
]

ADAPTER_DEDUPE_LOSS_FIELDNAMES = [
    "document_id",
    "field",
    "candidate_id",
    "adapter_stage_status",
    "dedupe_stage_status",
    "adapter_dedupe_loss_stage",
    "adapter_dedupe_loss_reason",
    "adapter_input_detail_available",
    "adapter_output_detail_available",
    "dedupe_input_detail_available",
    "dedupe_output_detail_available",
    "dedupe_merged",
    "dedupe_dropped",
    "dedupe_parent_candidate_ids",
    "dedupe_child_candidate_ids",
    "private_values_redacted",
]

LOSS_ROW_FIELDNAMES = [
    "document_id",
    "field",
    "candidate_id",
    "stage_loss_bucket",
    "generated_resolver_roundtrip_status",
    "generated_resolver_loss_stage",
    "generated_resolver_loss_reason",
    "generated_detail_available",
    "adapter_input_available",
    "adapter_output_available",
    "dedupe_lineage_available",
    "resolver_visible",
    "resolver_detail_available",
    "audit_visible",
    "serialization_visible",
    "private_values_redacted",
]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _token(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _joined_texts(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return ";".join(_text(item) for item in value if _text(item))
    return ""


def _metadata(row: dict[str, Any] | None) -> dict[str, Any]:
    row = row or {}
    if isinstance(row.get("metadata"), dict):
        return dict(row.get("metadata") or {})
    if isinstance(row.get("metadata_summary"), dict):
        return dict(row.get("metadata_summary") or {})
    return {}


def _document_id(row: dict[str, Any] | None, fallback: str = "") -> str:
    row = row or {}
    return _first_text(
        row.get("document_id"),
        row.get("case_id"),
        row.get("measurement_alias"),
        row.get("document_alias"),
        row.get("file_hash"),
        fallback,
    )


def _field_matches(row: dict[str, Any] | None) -> bool:
    field = _text((row or {}).get("field") or (row or {}).get("field_name"))
    return not field or field == LOAD_FIELD


def _is_load_candidate(row: dict[str, Any] | None) -> bool:
    row = row or {}
    metadata = _metadata(row)
    field = _text(row.get("field") or row.get("field_name") or metadata.get("field"))
    return field == LOAD_FIELD


def _candidate_id(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    row = row or {}
    return _first_text(
        row.get("candidate_id"),
        row.get("id"),
        row.get("selected_candidate_id"),
        metadata.get("candidate_id"),
    )


def _candidate_value(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    row = row or {}
    return _first_text(
        row.get("candidate_value"),
        row.get("value"),
        row.get("normalized_value"),
        row.get("raw_value"),
        row.get("selected_value"),
        metadata.get("candidate_value"),
    )


def _source(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    row = row or {}
    return _first_text(
        row.get("source"),
        row.get("selected_source"),
        metadata.get("source"),
        metadata.get("original_source"),
    )


def _parser_name(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    row = row or {}
    return _first_text(row.get("parser_name"), row.get("parser"), metadata.get("parser_name"))


def _page(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    row = row or {}
    return _first_text(
        row.get("page_number"),
        row.get("page_index"),
        row.get("page"),
        row.get("selected_page_index"),
        row.get("selected_page"),
        row.get("source_page"),
        metadata.get("page_number"),
        metadata.get("page_index"),
        metadata.get("page"),
        metadata.get("source_page"),
    )


def _line(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    row = row or {}
    return _first_text(
        row.get("line_index"),
        row.get("line_number"),
        row.get("selected_line_index"),
        row.get("source_line_index"),
        row.get("reading_order_index"),
        metadata.get("line_index"),
        metadata.get("line_number"),
        metadata.get("source_line_index"),
        metadata.get("reading_order_index"),
    )


def _pairing(row: dict[str, Any] | None) -> str:
    metadata = _metadata(row)
    row = row or {}
    explicit = _first_text(
        row.get("pairing_method"),
        row.get("selected_pairing_method"),
        metadata.get("pairing_method"),
        metadata.get("value_extraction_method"),
        metadata.get("match_kind"),
    )
    if explicit:
        return explicit
    token = _token(f"{_source(row)} {_parser_name(row)}")
    if "same_row" in token:
        return "same_row"
    if "nearby" in token:
        return "nearby_row"
    if "table" in token and ("key" in token or "neighbor" in token):
        return "table_key_value"
    if "layout" in token:
        return "layout"
    if "ocr" in token:
        return "ocr"
    if "footer" in token:
        return "footer"
    if "barcode" in token:
        return "barcode"
    if "native" in token or "text" in token:
        return "native_text"
    return ""


def _source_family(source: str, parser_name: str = "") -> str:
    token = _token(f"{source} {parser_name}")
    if "table" in token:
        return "table"
    if "nearby" in token:
        return "nearby_row"
    if "layout" in token:
        return "layout"
    if "ocr" in token:
        return "ocr"
    if "footer" in token:
        return "footer"
    if "barcode" in token:
        return "barcode"
    if "native" in token or "text" in token:
        return "native_text"
    return "unknown"


def _has_page_line(row: dict[str, Any] | None) -> bool:
    row = row or {}
    return bool(_page(row) or _line(row) or _text(row.get("source_line")))


def _has_bbox(row: dict[str, Any] | None) -> bool:
    metadata = _metadata(row)
    row = row or {}
    return bool(row.get("bbox") or row.get("bbox_available") or metadata.get("bbox_available"))


def _detail_available(row: dict[str, Any] | None) -> bool:
    return bool(_candidate_id(row) and _source(row) and _has_page_line(row) and _pairing(row))


def _value_for_output(value: Any, include_private_values: bool) -> str:
    text = _text(value)
    if include_private_values:
        return text
    return REDACTED_VALUE if text else ""


def _selected(row: dict[str, Any] | None) -> bool:
    row = row or {}
    return _bool(row.get("selected") or row.get("resolver_selected"))


def _eligible(row: dict[str, Any] | None) -> bool:
    row = row or {}
    if "resolver_eligible" in row:
        return _bool(row.get("resolver_eligible"))
    if "eligible" in row:
        return _bool(row.get("eligible"))
    return bool(row)


def _normalize_stage_row(
    row: dict[str, Any],
    *,
    stage: str,
    fallback: str,
    include_private_values: bool,
) -> dict[str, Any]:
    source = _source(row)
    parser_name = _parser_name(row)
    candidate_id = _candidate_id(row) or fallback
    normalized = {
        "document_id": _document_id(row, fallback),
        "field": LOAD_FIELD,
        "stage": stage,
        "candidate_id": candidate_id,
        "source": source,
        "source_family": _source_family(source, parser_name),
        "parser_name": parser_name,
        "pairing_method": _pairing(row),
        "page_number": _page(row),
        "line_index": _line(row),
        "bbox_available": _has_bbox(row),
        "candidate_rank": _first_text(row.get("candidate_rank"), row.get("rank")),
        "generated": stage == "generated",
        "adapter_input": stage == "adapter_input",
        "adapter_output": stage == "adapter_output",
        "dedupe_input": stage == "dedupe_input",
        "dedupe_output": stage == "dedupe_output",
        "resolver_input": stage == "resolver",
        "resolver_eligible": _eligible(row) if stage == "resolver" else False,
        "resolver_selected": _selected(row) if stage == "resolver" else False,
        "resolver_trace_available": stage == "resolver",
        "dedupe_merged": _bool(row.get("dedupe_merged")),
        "dedupe_dropped": _bool(row.get("dedupe_dropped")),
        "dedupe_parent_candidate_ids": _joined_texts(row.get("dedupe_parent_candidate_ids")),
        "dedupe_child_candidate_ids": _joined_texts(row.get("dedupe_child_candidate_ids")),
        "detail_roundtrip_status": "",
        "detail_loss_stage": "",
        "detail_loss_reason": "",
        "private_values_redacted": not include_private_values,
        "value_preview": _value_for_output(_candidate_value(row), include_private_values),
    }
    normalized["_detail_available"] = _detail_available(row)
    return normalized


def _stage_rows(
    rows: list[dict[str, Any]] | None,
    *,
    stage: str,
    include_private_values: bool,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows or [], start=1):
        if not isinstance(row, dict) or not _field_matches(row):
            continue
        normalized.append(
            _normalize_stage_row(
                row,
                stage=stage,
                fallback=f"{stage}_candidate_{index}",
                include_private_values=include_private_values,
            )
        )
    return normalized


def build_adapter_stage_row(
    candidate: dict[str, Any] | None,
    *,
    stage: str,
    include_private_values: bool = False,
) -> dict[str, Any]:
    """Build a redacted adapter-stage row from already-visible metadata."""

    return _normalize_stage_row(
        dict(candidate or {}),
        stage=stage,
        fallback="",
        include_private_values=include_private_values,
    )


def build_dedupe_stage_row(
    candidate: dict[str, Any] | None,
    *,
    stage: str,
    include_private_values: bool = False,
) -> dict[str, Any]:
    """Build a redacted dedupe-stage row from already-visible metadata."""

    return _normalize_stage_row(
        dict(candidate or {}),
        stage=stage,
        fallback="",
        include_private_values=include_private_values,
    )


def _generated_stage_record(
    candidate: dict[str, Any],
    *,
    document_id: str,
    index: int,
) -> dict[str, Any]:
    metadata = _metadata(candidate)
    source = _source(candidate)
    parser_name = _parser_name(candidate)
    return {
        "document_id": document_id,
        "field": LOAD_FIELD,
        "stage": "generated",
        "candidate_id": _candidate_id(candidate),
        "source": source,
        "source_family": _first_text(
            candidate.get("source_family"),
            metadata.get("source_family"),
            _source_family(source, parser_name),
        ),
        "parser_name": parser_name,
        "pairing_method": _pairing(candidate),
        "page_number": _page(candidate),
        "line_index": _line(candidate),
        "bbox_available": _has_bbox(candidate),
        "candidate_rank": _first_text(candidate.get("candidate_rank"), candidate.get("rank"), index),
    }


def generated_provenance_records_from_shadow_result(
    shadow_result: dict[str, Any] | None,
    *,
    document_id: str = "",
) -> list[dict[str, Any]]:
    """Return generated-stage load metadata already present in debug candidates.

    The records intentionally omit candidate values and do not synthesize missing
    candidate ids, page/line detail, source labels, or pairing methods.
    """

    shadow_result = shadow_result or {}
    debug = shadow_result.get("debug") if isinstance(shadow_result.get("debug"), dict) else {}
    candidates = debug.get("candidates") if isinstance(debug, dict) else []
    triage = debug.get("triage") if isinstance(debug.get("triage"), dict) else {}
    fallback_document_id = _first_text(
        document_id,
        triage.get("document_id"),
        shadow_result.get("document_id"),
    )
    records: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates or [], start=1):
        if not isinstance(candidate, dict) or not _is_load_candidate(candidate):
            continue
        records.append(
            _generated_stage_record(
                candidate,
                document_id=fallback_document_id,
                index=index,
            )
        )
    return records


def generated_resolver_provenance_records_from_shadow_result(
    shadow_result: dict[str, Any] | None,
    *,
    document_id: str = "",
) -> list[dict[str, Any]]:
    """Return generated plus adapter/dedupe stage rows already in debug output."""

    shadow_result = shadow_result or {}
    debug = shadow_result.get("debug") if isinstance(shadow_result.get("debug"), dict) else {}
    records = generated_provenance_records_from_shadow_result(
        shadow_result,
        document_id=document_id,
    )
    for record in debug.get("adapter_dedupe_provenance_records", []) or []:
        if not isinstance(record, dict):
            continue
        stage = _text(record.get("stage"))
        if stage not in {"adapter_input", "adapter_output", "dedupe_input", "dedupe_output"}:
            continue
        item = dict(record)
        if document_id and not _text(item.get("document_id")):
            item["document_id"] = document_id
        records.append(item)
    return records


def _group(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[row["document_id"]][row["candidate_id"]] = row
    return grouped


def _candidate_keys(*groups: dict[str, dict[str, dict[str, Any]]]) -> dict[str, set[str]]:
    keys: dict[str, set[str]] = defaultdict(set)
    for group in groups:
        for doc_id, candidates in group.items():
            keys[doc_id].update(candidates)
    return keys


def _stage_detail_available(row: dict[str, Any] | None) -> bool:
    return bool((row or {}).get("_detail_available"))


def classify_adapter_dedupe_stage_loss(
    *,
    adapter_input: dict[str, Any] | None = None,
    adapter_output: dict[str, Any] | None = None,
    dedupe_input: dict[str, Any] | None = None,
    dedupe_output: dict[str, Any] | None = None,
) -> tuple[str, str, str, str]:
    """Classify adapter/dedupe stage visibility without inferring metadata."""

    adapter_input_detail = _stage_detail_available(adapter_input)
    adapter_output_detail = _stage_detail_available(adapter_output)
    dedupe_input_detail = _stage_detail_available(dedupe_input)
    dedupe_output_detail = _stage_detail_available(dedupe_output)

    if not any([adapter_input, adapter_output, dedupe_input, dedupe_output]):
        return (
            ADAPTER_STAGE_UNAVAILABLE,
            DEDUPE_STAGE_UNAVAILABLE,
            "adapter",
            "Adapter and dedupe diagnostic rows were unavailable.",
        )
    if adapter_input and not adapter_input_detail:
        return (
            ADAPTER_INPUT_DETAIL_MISSING,
            DEDUPE_STAGE_UNAVAILABLE if not (dedupe_input or dedupe_output) else ADAPTER_DEDUPE_UNKNOWN,
            "adapter",
            "Adapter input row is present but lacks candidate id, source, page/line, or pairing detail.",
        )
    if adapter_input_detail and not adapter_output:
        return (
            ADAPTER_OUTPUT_DETAIL_LOST,
            DEDUPE_STAGE_UNAVAILABLE if not (dedupe_input or dedupe_output) else ADAPTER_DEDUPE_UNKNOWN,
            "adapter",
            "Adapter input detail is present but adapter output row is unavailable.",
        )
    if adapter_input_detail and adapter_output and not adapter_output_detail:
        return (
            ADAPTER_OUTPUT_DETAIL_LOST,
            DEDUPE_STAGE_UNAVAILABLE if not (dedupe_input or dedupe_output) else ADAPTER_DEDUPE_UNKNOWN,
            "adapter",
            "Adapter output row is present but lost source-line detail.",
        )

    adapter_status = (
        ADAPTER_STAGE_COMPLETE
        if adapter_input_detail and adapter_output_detail
        else ADAPTER_OUTPUT_DETAIL_PRESERVED
        if adapter_output_detail
        else ADAPTER_STAGE_UNAVAILABLE
    )
    if not (dedupe_input or dedupe_output):
        return (
            adapter_status,
            DEDUPE_STAGE_UNAVAILABLE,
            "dedupe",
            "Adapter detail is visible but dedupe diagnostic rows were unavailable.",
        )
    if dedupe_input and not dedupe_input_detail:
        return (
            adapter_status,
            DEDUPE_INPUT_DETAIL_AVAILABLE if dedupe_output_detail else DEDUPE_OUTPUT_DETAIL_LOST,
            "dedupe",
            "Dedupe input row is present but lacks source-line detail.",
        )
    if dedupe_input_detail and not dedupe_output:
        return (
            adapter_status,
            DEDUPE_OUTPUT_DETAIL_LOST,
            "dedupe",
            "Dedupe input detail is present but dedupe output row is unavailable.",
        )
    if dedupe_output and not dedupe_output_detail:
        return (
            adapter_status,
            DEDUPE_OUTPUT_DETAIL_LOST,
            "dedupe",
            "Dedupe output row is present but lost source-line detail.",
        )

    dedupe_status = (
        DEDUPE_STAGE_COMPLETE
        if dedupe_input_detail and dedupe_output_detail
        else DEDUPE_OUTPUT_DETAIL_PRESERVED
    )
    return (
        adapter_status,
        dedupe_status,
        "none",
        "Adapter and dedupe diagnostic rows preserve available source-line detail.",
    )


def _lineage_ids(row: dict[str, Any] | None, key: str) -> str:
    value = (row or {}).get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return ";".join(_text(item) for item in value if _text(item))
    return ""


def _adapter_dedupe_loss_row(
    doc_id: str,
    candidate_id: str,
    rows: dict[str, dict[str, Any] | None],
    *,
    include_private_values: bool,
) -> dict[str, Any]:
    adapter_status, dedupe_status, loss_stage, reason = classify_adapter_dedupe_stage_loss(
        adapter_input=rows.get("adapter_input"),
        adapter_output=rows.get("adapter_output"),
        dedupe_input=rows.get("dedupe_input"),
        dedupe_output=rows.get("dedupe_output"),
    )
    dedupe_input = rows.get("dedupe_input") or {}
    dedupe_output = rows.get("dedupe_output") or {}
    return {
        "document_id": doc_id,
        "field": LOAD_FIELD,
        "candidate_id": candidate_id,
        "adapter_stage_status": adapter_status,
        "dedupe_stage_status": dedupe_status,
        "adapter_dedupe_loss_stage": loss_stage,
        "adapter_dedupe_loss_reason": reason,
        "adapter_input_detail_available": _stage_detail_available(rows.get("adapter_input")),
        "adapter_output_detail_available": _stage_detail_available(rows.get("adapter_output")),
        "dedupe_input_detail_available": _stage_detail_available(rows.get("dedupe_input")),
        "dedupe_output_detail_available": _stage_detail_available(rows.get("dedupe_output")),
        "dedupe_merged": _bool(dedupe_output.get("dedupe_merged")),
        "dedupe_dropped": _bool(dedupe_input.get("dedupe_dropped")),
        "dedupe_parent_candidate_ids": _lineage_ids(dedupe_output, "dedupe_parent_candidate_ids"),
        "dedupe_child_candidate_ids": _lineage_ids(dedupe_output, "dedupe_child_candidate_ids"),
        "private_values_redacted": not include_private_values,
    }


def summarize_adapter_dedupe_roundtrip(
    adapter_dedupe_rows: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    rows = list(adapter_dedupe_rows or [])
    adapter_counts = Counter(
        row.get("adapter_stage_status", ADAPTER_DEDUPE_UNKNOWN) for row in rows
    )
    dedupe_counts = Counter(
        row.get("dedupe_stage_status", ADAPTER_DEDUPE_UNKNOWN) for row in rows
    )
    return {
        "adapter_dedupe_candidate_count": len(rows),
        "adapter_stage_status_counts": dict(sorted(adapter_counts.items())),
        "dedupe_stage_status_counts": dict(sorted(dedupe_counts.items())),
        "adapter_detail_preserved_count": adapter_counts.get(ADAPTER_STAGE_COMPLETE, 0)
        + adapter_counts.get(ADAPTER_OUTPUT_DETAIL_PRESERVED, 0),
        "adapter_detail_lost_count": adapter_counts.get(ADAPTER_INPUT_DETAIL_MISSING, 0)
        + adapter_counts.get(ADAPTER_OUTPUT_DETAIL_LOST, 0),
        "dedupe_detail_preserved_count": dedupe_counts.get(DEDUPE_STAGE_COMPLETE, 0)
        + dedupe_counts.get(DEDUPE_OUTPUT_DETAIL_PRESERVED, 0),
        "dedupe_detail_lost_count": dedupe_counts.get(DEDUPE_OUTPUT_DETAIL_LOST, 0),
        "adapter_stage_unavailable_count": adapter_counts.get(ADAPTER_STAGE_UNAVAILABLE, 0),
        "dedupe_stage_unavailable_count": dedupe_counts.get(DEDUPE_STAGE_UNAVAILABLE, 0),
    }


def _loss_classification(
    *,
    generated: dict[str, Any] | None,
    adapter_input: dict[str, Any] | None,
    adapter_output: dict[str, Any] | None,
    dedupe_input: dict[str, Any] | None,
    dedupe_output: dict[str, Any] | None,
    resolver: dict[str, Any] | None,
    audit: dict[str, Any] | None,
    serialization: dict[str, Any] | None,
) -> tuple[str, str, str, str]:
    any_stage = any([generated, adapter_input, adapter_output, dedupe_input, dedupe_output, resolver])
    if not any_stage and (audit or serialization):
        return (
            STAGE_UNKNOWN,
            ROUNDTRIP_UNMEASURABLE,
            "generated_resolver_sidecar",
            "Only audit/eval/serialization artifacts were available; generated/resolver roundtrip is not measurable.",
        )
    if not any_stage:
        return (
            STAGE_NOT_APPLICABLE_CANDIDATE_MISSING,
            ROUNDTRIP_NO_INPUTS,
            "candidate_collection",
            "No generated, adapter, dedupe, resolver, audit, or serialization row was available.",
        )
    if not generated:
        return (
            STAGE_GENERATED_DETAIL_MISSING,
            ROUNDTRIP_LOSS_DETECTED,
            "generation",
            "Generated candidate row was not available before later provenance surfaces.",
        )
    if not generated.get("_detail_available"):
        return (
            STAGE_GENERATED_DETAIL_MISSING,
            ROUNDTRIP_LOSS_DETECTED,
            "generation",
            "Generated candidate row lacks candidate id, source, page/line, or pairing detail.",
        )
    if not adapter_input:
        return (
            STAGE_LOST_BETWEEN_GENERATION_AND_ADAPTER,
            ROUNDTRIP_LOSS_DETECTED,
            "candidate_adapter",
            "Generated candidate detail was present but no adapter input row was serialized.",
        )
    if not adapter_input.get("_detail_available"):
        return (
            STAGE_ADAPTER_INPUT_MISSING,
            ROUNDTRIP_LOSS_DETECTED,
            "candidate_adapter",
            "Adapter input row is visible but lacks generated source-line detail.",
        )
    if not adapter_output:
        return (
            STAGE_ADAPTER_OUTPUT_MISSING,
            ROUNDTRIP_LOSS_DETECTED,
            "candidate_adapter",
            "Adapter input detail was present but no adapter output row was serialized.",
        )
    if not adapter_output.get("_detail_available"):
        return (
            STAGE_ADAPTER_OUTPUT_MISSING,
            ROUNDTRIP_LOSS_DETECTED,
            "candidate_adapter",
            "Adapter output row is visible but lacks source-line detail.",
        )
    if dedupe_input and not dedupe_output:
        return (
            STAGE_LOST_BETWEEN_ADAPTER_AND_DEDUPE,
            ROUNDTRIP_LOSS_DETECTED,
            "dedupe",
            "Adapter output detail was present but dedupe output lineage was not serialized.",
        )
    if resolver and not dedupe_input and not dedupe_output:
        return (
            STAGE_DEDUPE_LINEAGE_UNAVAILABLE,
            ROUNDTRIP_PARTIAL,
            "dedupe",
            "Resolver detail is visible but dedupe lineage rows were not serialized.",
        )
    if dedupe_output and not resolver:
        return (
            STAGE_LOST_BETWEEN_DEDUPE_AND_RESOLVER,
            ROUNDTRIP_LOSS_DETECTED,
            "resolver",
            "Dedupe output detail was present but no resolver-visible row was serialized.",
        )
    if not resolver:
        return (
            STAGE_RESOLVER_TRACE_UNAVAILABLE,
            ROUNDTRIP_LOSS_DETECTED,
            "resolver",
            "Adapter output detail was present but resolver trace rows were unavailable.",
        )
    if not resolver.get("_detail_available"):
        return (
            STAGE_RESOLVER_TRACE_UNAVAILABLE,
            ROUNDTRIP_LOSS_DETECTED,
            "resolver",
            "Resolver-visible row lacks source-line detail that was available earlier.",
        )
    if audit is None and serialization is None:
        return (
            STAGE_LOST_BETWEEN_RESOLVER_AND_AUDIT,
            ROUNDTRIP_PARTIAL,
            "shadow_audit",
            "Resolver-visible detail exists but no later audit/serialization row was provided.",
        )
    return (
        STAGE_GENERATED_DETAIL_AVAILABLE,
        ROUNDTRIP_COMPLETE,
        "none",
        "Generated, adapter, and resolver-visible load candidate detail is measurable.",
    )


def _loss_row(
    doc_id: str,
    candidate_id: str,
    rows: dict[str, dict[str, Any] | None],
    *,
    include_private_values: bool,
) -> dict[str, Any]:
    bucket, status, stage, reason = _loss_classification(**rows)
    return {
        "document_id": doc_id,
        "field": LOAD_FIELD,
        "candidate_id": candidate_id,
        "stage_loss_bucket": bucket,
        "generated_resolver_roundtrip_status": status,
        "generated_resolver_loss_stage": stage,
        "generated_resolver_loss_reason": reason,
        "generated_detail_available": bool((rows.get("generated") or {}).get("_detail_available")),
        "adapter_input_available": bool((rows.get("adapter_input") or {}).get("_detail_available")),
        "adapter_output_available": bool((rows.get("adapter_output") or {}).get("_detail_available")),
        "dedupe_lineage_available": bool(
            rows.get("dedupe_input") or rows.get("dedupe_output")
        ),
        "resolver_visible": rows.get("resolver") is not None,
        "resolver_detail_available": bool((rows.get("resolver") or {}).get("_detail_available")),
        "audit_visible": rows.get("audit") is not None,
        "serialization_visible": rows.get("serialization") is not None,
        "private_values_redacted": not include_private_values,
    }


def _apply_loss_to_stage_rows(
    stage_rows: list[dict[str, Any]],
    loss_rows: list[dict[str, Any]],
) -> None:
    loss_by_key = {
        (row["document_id"], row["candidate_id"]): row
        for row in loss_rows
    }
    for row in stage_rows:
        loss = loss_by_key.get((row["document_id"], row["candidate_id"]), {})
        row["detail_roundtrip_status"] = loss.get("generated_resolver_roundtrip_status", "")
        row["detail_loss_stage"] = loss.get("generated_resolver_loss_stage", "")
        row["detail_loss_reason"] = loss.get("generated_resolver_loss_reason", "")
        row.pop("_detail_available", None)


def build_load_generated_resolver_provenance_sidecars(
    *,
    generated_rows: list[dict[str, Any]] | None = None,
    adapter_input_rows: list[dict[str, Any]] | None = None,
    adapter_output_rows: list[dict[str, Any]] | None = None,
    dedupe_input_rows: list[dict[str, Any]] | None = None,
    dedupe_output_rows: list[dict[str, Any]] | None = None,
    resolver_rows: list[dict[str, Any]] | None = None,
    audit_rows: list[dict[str, Any]] | None = None,
    serialization_rows: list[dict[str, Any]] | None = None,
    include_private_values: bool = False,
) -> dict[str, Any]:
    """Build redacted generated/resolver provenance sidecars from existing rows."""

    generated_stage = _stage_rows(
        generated_rows,
        stage="generated",
        include_private_values=include_private_values,
    )
    adapter_input_stage = _stage_rows(
        adapter_input_rows,
        stage="adapter_input",
        include_private_values=include_private_values,
    )
    adapter_output_stage = _stage_rows(
        adapter_output_rows,
        stage="adapter_output",
        include_private_values=include_private_values,
    )
    dedupe_input_stage = _stage_rows(
        dedupe_input_rows,
        stage="dedupe_input",
        include_private_values=include_private_values,
    )
    dedupe_output_stage = _stage_rows(
        dedupe_output_rows,
        stage="dedupe_output",
        include_private_values=include_private_values,
    )
    resolver_stage = _stage_rows(
        resolver_rows,
        stage="resolver",
        include_private_values=include_private_values,
    )
    audit_stage = _stage_rows(
        audit_rows,
        stage="audit",
        include_private_values=include_private_values,
    )
    serialization_stage = _stage_rows(
        serialization_rows,
        stage="serialization",
        include_private_values=include_private_values,
    )
    grouped = {
        "generated": _group(generated_stage),
        "adapter_input": _group(adapter_input_stage),
        "adapter_output": _group(adapter_output_stage),
        "dedupe_input": _group(dedupe_input_stage),
        "dedupe_output": _group(dedupe_output_stage),
        "resolver": _group(resolver_stage),
        "audit": _group(audit_stage),
        "serialization": _group(serialization_stage),
    }
    keys_by_doc = _candidate_keys(*grouped.values())
    if not keys_by_doc:
        keys_by_doc["generated_resolver_inputs_unavailable"].add("candidate_missing")

    loss_rows: list[dict[str, Any]] = []
    adapter_dedupe_loss_rows: list[dict[str, Any]] = []
    for doc_id in sorted(keys_by_doc):
        for candidate_id in sorted(keys_by_doc[doc_id]):
            rows = {
                stage: grouped[stage].get(doc_id, {}).get(candidate_id)
                for stage in grouped
            }
            loss_rows.append(
                _loss_row(
                    doc_id,
                    candidate_id,
                    rows,
                    include_private_values=include_private_values,
                )
            )
            adapter_dedupe_loss_rows.append(
                _adapter_dedupe_loss_row(
                    doc_id,
                    candidate_id,
                    rows,
                    include_private_values=include_private_values,
                )
            )

    all_stage_rows = (
        generated_stage
        + adapter_input_stage
        + adapter_output_stage
        + dedupe_input_stage
        + dedupe_output_stage
        + resolver_stage
        + audit_stage
        + serialization_stage
    )
    _apply_loss_to_stage_rows(all_stage_rows, loss_rows)
    for row in all_stage_rows:
        row.pop("_detail_available", None)

    bucket_counts = Counter(row["stage_loss_bucket"] for row in loss_rows)
    status_counts = Counter(row["generated_resolver_roundtrip_status"] for row in loss_rows)
    adapter_dedupe_summary = summarize_adapter_dedupe_roundtrip(adapter_dedupe_loss_rows)
    measurable = bool(
        generated_stage
        or adapter_input_stage
        or adapter_output_stage
        or dedupe_input_stage
        or dedupe_output_stage
        or resolver_stage
    )
    if not measurable and (audit_stage or serialization_stage):
        artifact_status = ROUNDTRIP_UNMEASURABLE
    elif not measurable:
        artifact_status = ROUNDTRIP_NO_INPUTS
    elif bucket_counts.get(STAGE_GENERATED_DETAIL_AVAILABLE, 0) == len(loss_rows):
        artifact_status = "full_roundtrip_measurable"
    else:
        artifact_status = "partial_roundtrip_measurable"

    summary = {
        "schema_version": LOAD_GENERATED_RESOLVER_PROVENANCE_SCHEMA_VERSION,
        "document_count": len({row["document_id"] for row in loss_rows}),
        "provenance_candidate_count": len(loss_rows),
        "provenance_stage_row_count": len(all_stage_rows),
        "generated_candidate_count": len(generated_stage),
        "adapter_input_count": len(adapter_input_stage),
        "adapter_output_count": len(adapter_output_stage),
        "dedupe_input_count": len(dedupe_input_stage),
        "dedupe_output_count": len(dedupe_output_stage),
        "dedupe_lineage_row_count": len(dedupe_input_stage) + len(dedupe_output_stage),
        "adapter_dedupe_stage_row_count": (
            len(adapter_input_stage)
            + len(adapter_output_stage)
            + len(dedupe_input_stage)
            + len(dedupe_output_stage)
        ),
        "resolver_visible_candidate_count": len(resolver_stage),
        "audit_visible_candidate_count": len(audit_stage),
        "serialization_visible_candidate_count": len(serialization_stage),
        "generated_candidate_detail_available_count": sum(
            1 for row in generated_stage if row.get("source") and row.get("page_number") and row.get("pairing_method")
        ),
        "resolver_visible_detail_available_count": sum(
            1 for row in resolver_stage if row.get("source") and row.get("page_number") and row.get("pairing_method")
        ),
        "complete_roundtrip_count": bucket_counts[STAGE_GENERATED_DETAIL_AVAILABLE],
        "current_artifacts_measurable": measurable,
        "current_artifacts_status": artifact_status,
        "stage_loss_bucket_counts": dict(sorted(bucket_counts.items())),
        "generated_resolver_roundtrip_status_counts": dict(sorted(status_counts.items())),
        "private_values_included": include_private_values,
        "values_redacted": not include_private_values,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
        **adapter_dedupe_summary,
    }
    return {
        "schema_version": LOAD_GENERATED_RESOLVER_PROVENANCE_SCHEMA_VERSION,
        "summary": summary,
        "stage_rows": all_stage_rows,
        "generated_rows": generated_stage,
        "adapter_input_rows": adapter_input_stage,
        "adapter_output_rows": adapter_output_stage,
        "adapter_rows": adapter_input_stage + adapter_output_stage,
        "dedupe_input_rows": dedupe_input_stage,
        "dedupe_output_rows": dedupe_output_stage,
        "dedupe_rows": dedupe_input_stage + dedupe_output_stage,
        "resolver_rows": resolver_stage,
        "loss_rows": loss_rows,
        "adapter_dedupe_loss_rows": adapter_dedupe_loss_rows,
        "review_rows": [
            {
                "document_id": row["document_id"],
                "candidate_id": row["candidate_id"],
                "stage_loss_bucket": row["stage_loss_bucket"],
                "recommended_action": "review_generated_resolver_sidecar_only",
                "behavior_change_allowed": False,
            }
            for row in loss_rows
            if row["stage_loss_bucket"] != STAGE_GENERATED_DETAIL_AVAILABLE
        ],
    }


def _candidate_from_resolver_trace(
    *,
    document_id: str,
    candidate: dict[str, Any],
    selected: bool,
    index: int,
) -> dict[str, Any]:
    metadata = dict(candidate.get("metadata_summary") or {})
    row = {
        "document_id": document_id,
        "field": LOAD_FIELD,
        "candidate_id": candidate.get("candidate_id"),
        "candidate_value": candidate.get("value") or candidate.get("value_preview"),
        "source": candidate.get("source"),
        "parser_name": candidate.get("parser_name"),
        "pairing_method": metadata.get("pairing_method"),
        "page_number": metadata.get("page_number") or candidate.get("page_number"),
        "line_index": metadata.get("line_index") or metadata.get("line_number"),
        "bbox_available": candidate.get("has_bbox") or metadata.get("bbox_available"),
        "selected": selected,
        "candidate_rank": index,
        "resolver_eligible": True,
    }
    return row


def resolver_rows_from_shadow_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract load resolver-visible candidates from a sanitized shadow record."""

    document_id = _document_id(record)
    shadow = record.get("shadow") if isinstance(record.get("shadow"), dict) else {}
    traces = shadow.get("resolver_decision_traces") if isinstance(shadow, dict) else {}
    trace = (traces or {}).get(LOAD_FIELD, {}) if isinstance(traces, dict) else {}
    if not isinstance(trace, dict):
        return []
    rows: list[dict[str, Any]] = []
    selected = trace.get("selected_candidate")
    if isinstance(selected, dict) and selected:
        rows.append(
            _candidate_from_resolver_trace(
                document_id=document_id,
                candidate=selected,
                selected=True,
                index=1,
            )
        )
    for index, candidate in enumerate(trace.get("top_rejected_or_not_selected", []) or [], start=2):
        if isinstance(candidate, dict):
            rows.append(
                _candidate_from_resolver_trace(
                    document_id=document_id,
                    candidate=candidate,
                    selected=False,
                    index=index,
                )
            )
    return rows


def audit_rows_from_shadow_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    document_id = _document_id(record)
    candidate_details = record.get("candidate_details")
    if isinstance(candidate_details, list):
        return [
            {
                **dict(detail),
                "document_id": document_id,
                "field": LOAD_FIELD,
            }
            for detail in candidate_details
            if isinstance(detail, dict)
        ]
    shadow = record.get("shadow") if isinstance(record.get("shadow"), dict) else {}
    resolved = shadow.get("resolved_fields") if isinstance(shadow, dict) else {}
    load_resolution = (resolved or {}).get(LOAD_FIELD, {}) if isinstance(resolved, dict) else {}
    selected = load_resolution.get("selected_candidate") if isinstance(load_resolution, dict) else {}
    if isinstance(selected, dict) and selected:
        return [
            {
                "document_id": document_id,
                "field": LOAD_FIELD,
                "candidate_id": selected.get("candidate_id"),
                "candidate_value": selected.get("value"),
                "source": selected.get("source"),
                "parser_name": selected.get("parser_name"),
                "selected": True,
            }
        ]
    return []


def rows_from_audit_payloads(payloads: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolver_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for payload in payloads or []:
        if not isinstance(payload, dict):
            continue
        resolver_rows.extend(resolver_rows_from_shadow_record(payload))
        audit_rows.extend(audit_rows_from_shadow_record(payload))
    return resolver_rows, audit_rows


def build_load_generated_resolver_provenance_from_measurement_rows(
    rows: list[dict[str, Any]] | None,
    *,
    include_private_values: bool = False,
) -> dict[str, Any]:
    """Build sidecars from already-produced measurement rows."""

    generated_rows: list[dict[str, Any]] = []
    adapter_input_rows: list[dict[str, Any]] = []
    adapter_output_rows: list[dict[str, Any]] = []
    dedupe_input_rows: list[dict[str, Any]] = []
    dedupe_output_rows: list[dict[str, Any]] = []
    resolver_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    serialization_rows: list[dict[str, Any]] = []

    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for record in row.get("load_generated_resolver_provenance_records", []) or []:
            if not isinstance(record, dict):
                continue
            stage = _text(record.get("stage"))
            if stage == "generated":
                generated_rows.append(record)
            elif stage == "adapter_input":
                adapter_input_rows.append(record)
            elif stage == "adapter_output":
                adapter_output_rows.append(record)
            elif stage == "dedupe_input":
                dedupe_input_rows.append(record)
            elif stage == "dedupe_output":
                dedupe_output_rows.append(record)
            elif stage == "resolver":
                resolver_rows.append(record)
            elif stage == "serialization":
                serialization_rows.append(record)
        for record in row.get("ratecon_shadow_audit_records", []) or []:
            if isinstance(record, dict):
                extracted_resolver, extracted_audit = rows_from_audit_payloads([record])
                resolver_rows.extend(extracted_resolver)
                audit_rows.extend(extracted_audit)
        for record in row.get("load_identifier_source_line_records", []) or []:
            if isinstance(record, dict):
                audit_rows.append(
                    {
                        **record,
                        "document_id": row.get("document_alias") or record.get("document_id"),
                        "field": LOAD_FIELD,
                    }
                )

    return build_load_generated_resolver_provenance_sidecars(
        generated_rows=generated_rows,
        adapter_input_rows=adapter_input_rows,
        adapter_output_rows=adapter_output_rows,
        dedupe_input_rows=dedupe_input_rows,
        dedupe_output_rows=dedupe_output_rows,
        resolver_rows=resolver_rows,
        audit_rows=audit_rows,
        serialization_rows=serialization_rows,
        include_private_values=include_private_values,
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def build_markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# RateCon Load Generated/Resolver Provenance Sidecars",
        "",
        "Local-only sidecars over existing generated, adapter, dedupe, resolver, audit, and serialization artifacts.",
        "",
        f"- current_artifacts_status: {summary['current_artifacts_status']}",
        f"- current_artifacts_measurable: {summary['current_artifacts_measurable']}",
        f"- provenance_candidate_count: {summary['provenance_candidate_count']}",
        f"- generated_candidate_count: {summary['generated_candidate_count']}",
        f"- adapter_input_count: {summary['adapter_input_count']}",
        f"- adapter_output_count: {summary['adapter_output_count']}",
        f"- dedupe_input_count: {summary['dedupe_input_count']}",
        f"- dedupe_output_count: {summary['dedupe_output_count']}",
        f"- resolver_visible_candidate_count: {summary['resolver_visible_candidate_count']}",
        f"- generated_candidate_detail_available_count: {summary['generated_candidate_detail_available_count']}",
        f"- resolver_visible_detail_available_count: {summary['resolver_visible_detail_available_count']}",
        f"- complete_roundtrip_count: {summary['complete_roundtrip_count']}",
        f"- boundary_compare_status: {summary.get('boundary_compare_status', 'skipped_not_requested')}",
        f"- boundary_first_loss_boundary: {summary.get('boundary_first_loss_boundary', '')}",
        f"- boundary_complete_roundtrip_count: {summary.get('boundary_complete_roundtrip_count', 0)}",
        f"- private_values_included: {summary['private_values_included']}",
        f"- values_redacted: {summary['values_redacted']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
        "",
        "## Stage Loss Buckets",
    ]
    for bucket, count in summary["stage_loss_bucket_counts"].items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Roundtrip Statuses"])
    for status, count in summary["generated_resolver_roundtrip_status_counts"].items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Adapter/Dedupe Stage Statuses", "### Adapter"])
    for status, count in summary.get("adapter_stage_status_counts", {}).items():
        lines.append(f"- {status}: {count}")
    lines.append("### Dedupe")
    for status, count in summary.get("dedupe_stage_status_counts", {}).items():
        lines.append(f"- {status}: {count}")
    return "\n".join(lines) + "\n"


def write_load_generated_resolver_provenance_outputs(
    output_dir: Path,
    payload: dict[str, Any],
) -> dict[str, Path]:
    """Write generated/resolver provenance sidecar files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": output_dir / "load_generated_resolver_provenance_summary.json",
        "report": output_dir / "load_generated_resolver_provenance_report.md",
        "generated_candidates": output_dir / "load_generated_candidates.csv",
        "adapter_input_candidates": output_dir / "load_adapter_input_candidates.csv",
        "adapter_output_candidates": output_dir / "load_adapter_output_candidates.csv",
        "adapter_roundtrip_rows": output_dir / "load_adapter_roundtrip_rows.csv",
        "resolver_visible_candidates": output_dir / "load_resolver_visible_candidates.csv",
        "dedupe_input_candidates": output_dir / "load_dedupe_input_candidates.csv",
        "dedupe_output_candidates": output_dir / "load_dedupe_output_candidates.csv",
        "dedupe_lineage_rows": output_dir / "load_dedupe_lineage_rows.csv",
        "adapter_dedupe_loss_by_stage": output_dir / "load_adapter_dedupe_loss_by_stage.csv",
        "provenance_loss_by_stage": output_dir / "load_provenance_loss_by_stage.csv",
        "review_items": output_dir / "load_generated_resolver_review_items.csv",
    }
    write_json(paths["summary"], payload)
    paths["report"].write_text(build_markdown_report(payload), encoding="utf-8")
    write_csv(paths["generated_candidates"], payload["generated_rows"], STAGE_ROW_FIELDNAMES)
    write_csv(
        paths["adapter_input_candidates"],
        payload.get("adapter_input_rows", []),
        STAGE_ROW_FIELDNAMES,
    )
    write_csv(
        paths["adapter_output_candidates"],
        payload.get("adapter_output_rows", []),
        STAGE_ROW_FIELDNAMES,
    )
    write_csv(paths["adapter_roundtrip_rows"], payload["adapter_rows"], STAGE_ROW_FIELDNAMES)
    write_csv(paths["resolver_visible_candidates"], payload["resolver_rows"], STAGE_ROW_FIELDNAMES)
    write_csv(
        paths["dedupe_input_candidates"],
        payload.get("dedupe_input_rows", []),
        STAGE_ROW_FIELDNAMES,
    )
    write_csv(
        paths["dedupe_output_candidates"],
        payload.get("dedupe_output_rows", []),
        STAGE_ROW_FIELDNAMES,
    )
    write_csv(paths["dedupe_lineage_rows"], payload["dedupe_rows"], STAGE_ROW_FIELDNAMES)
    write_csv(
        paths["adapter_dedupe_loss_by_stage"],
        payload.get("adapter_dedupe_loss_rows", []),
        ADAPTER_DEDUPE_LOSS_FIELDNAMES,
    )
    write_csv(paths["provenance_loss_by_stage"], payload["loss_rows"], LOSS_ROW_FIELDNAMES)
    write_csv(
        paths["review_items"],
        payload["review_rows"],
        [
            "document_id",
            "candidate_id",
            "stage_loss_bucket",
            "recommended_action",
            "behavior_change_allowed",
        ],
    )
    return paths
