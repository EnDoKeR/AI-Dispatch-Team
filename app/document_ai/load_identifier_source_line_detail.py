"""Safe load identifier source-line detail sidecar helpers.

These helpers normalize existing evaluation, audit, and diagnostic metadata
into local-only diagnostic rows. They do not run extraction, generate
candidates, resolve fields, or change selected load-number behavior.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


LOAD_SOURCE_DETAIL_SCHEMA_VERSION = "ratecon_load_source_line_detail_inventory_v1"
LOAD_FIELD = "load_number"
REDACTED_VALUE = "[redacted]"

DETAIL_LOSS_COMPLETE = "candidate_has_complete_source_detail"
DETAIL_LOSS_MISSING_CANDIDATE_ID = "candidate_missing_candidate_id"
DETAIL_LOSS_MISSING_PAGE_LINE = "candidate_missing_page_line"
DETAIL_LOSS_MISSING_SOURCE = "candidate_missing_source"
DETAIL_LOSS_MISSING_PAIRING_METHOD = "candidate_missing_pairing_method"
DETAIL_LOSS_MISSING_LABEL_CONTEXT = "candidate_missing_label_context"
DETAIL_LOSS_MISSING_VALUE_CONTEXT = "candidate_missing_value_context"
DETAIL_LOSS_DROPPED_BEFORE_RESOLVER = "candidate_detail_dropped_before_resolver"
DETAIL_LOSS_DROPPED_IN_RESOLVER_TRACE = "candidate_detail_dropped_in_resolver_trace"
DETAIL_LOSS_DROPPED_BEFORE_AUDIT = "candidate_detail_dropped_before_audit"
DETAIL_LOSS_MISSING_FROM_EVALUATOR = "candidate_detail_missing_from_evaluator"
DETAIL_LOSS_DIAGNOSTIC_UNAVAILABLE = "diagnostic_detail_unavailable"
DETAIL_LOSS_PRIVATE_VALUES_REQUIRED = "private_values_required_for_value_comparison"
DETAIL_LOSS_NOT_APPLICABLE_MISSING_CANDIDATE = "detail_not_applicable_missing_candidate"
DETAIL_LOSS_UNKNOWN = "unknown"

DETAIL_LOSS_BUCKETS = (
    DETAIL_LOSS_COMPLETE,
    DETAIL_LOSS_MISSING_CANDIDATE_ID,
    DETAIL_LOSS_MISSING_PAGE_LINE,
    DETAIL_LOSS_MISSING_SOURCE,
    DETAIL_LOSS_MISSING_PAIRING_METHOD,
    DETAIL_LOSS_MISSING_LABEL_CONTEXT,
    DETAIL_LOSS_MISSING_VALUE_CONTEXT,
    DETAIL_LOSS_DROPPED_BEFORE_RESOLVER,
    DETAIL_LOSS_DROPPED_IN_RESOLVER_TRACE,
    DETAIL_LOSS_DROPPED_BEFORE_AUDIT,
    DETAIL_LOSS_MISSING_FROM_EVALUATOR,
    DETAIL_LOSS_DIAGNOSTIC_UNAVAILABLE,
    DETAIL_LOSS_PRIVATE_VALUES_REQUIRED,
    DETAIL_LOSS_NOT_APPLICABLE_MISSING_CANDIDATE,
    DETAIL_LOSS_UNKNOWN,
)

KNOWN_DEBT_DIAGNOSTIC_BUCKETS = {
    "selected_table_neighbor_wrong_cell",
    "selected_nearby_row_wrong_pair",
    "selected_footer_or_barcode_noise",
    "selected_reference_number_noise",
    "selected_po_number_noise",
    "selected_pro_number_noise",
    "selected_bol_number_noise",
    "ambiguous_multiple_load_ids",
}


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


def _document_id(row: dict[str, Any], fallback: str = "") -> str:
    return _text(
        row.get("document_id")
        or row.get("case_id")
        or row.get("measurement_alias")
        or row.get("file_hash")
        or fallback
    )


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _status(value: Any) -> str:
    return "present" if _text(value) else "missing"


def _value_for_output(value: Any, include_private_values: bool) -> str:
    text = _text(value)
    if include_private_values:
        return text
    return REDACTED_VALUE if text else ""


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


def _pairing_method(source: str, parser_name: str = "", explicit: Any = "") -> str:
    text = _text(explicit)
    if text:
        return text
    token = _token(f"{source} {parser_name}")
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


def _candidate_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    if isinstance(value, str):
        return [_text(item) for item in value.replace("|", ",").split(",") if _text(item)]
    return []


def _candidate_details(audit_row: dict[str, Any]) -> list[dict[str, Any]]:
    details = audit_row.get("candidate_details")
    if isinstance(details, list):
        return [dict(item) for item in details if isinstance(item, dict)]
    values = _candidate_values(
        audit_row.get("candidate_values") or audit_row.get("candidate_value_fingerprints")
    )
    rows = []
    for index, value in enumerate(values, start=1):
        rows.append(
            {
                "candidate_rank": index,
                "candidate_value": value,
                "selected": _token(value) == _token(audit_row.get("selected_value")),
                "source": audit_row.get("selected_source") if index == 1 else "",
                "label_text": audit_row.get("selected_label") if index == 1 else "",
                "page_number": audit_row.get("selected_page") or audit_row.get("selected_page_index"),
                "line_index": audit_row.get("selected_line_index"),
                "source_line": audit_row.get("selected_source_line") if index == 1 else "",
            }
        )
    return rows


def _serialization_details_by_doc(
    serialization_rows: list[dict[str, Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(serialization_rows or [], start=1):
        if not isinstance(row, dict):
            continue
        doc_id = _document_id(row, f"serialization_row_{index}")
        rows.setdefault(doc_id, []).append(dict(row))
    return rows


def _serialization_key(row: dict[str, Any]) -> str:
    return _token(row.get("candidate_id") or row.get("id") or row.get("candidate_value") or row.get("value"))


def _roundtrip_status(serialization_loss_stage: str) -> str:
    if not serialization_loss_stage:
        return "not_available"
    if serialization_loss_stage == "complete_detail_serialized":
        return "complete"
    return "loss_detected"


def _adapter_roundtrip_status(row: dict[str, Any]) -> str:
    return _text(row.get("adapter_roundtrip_status"))


def _adapter_loss_reason(row: dict[str, Any]) -> str:
    return _text(row.get("adapter_loss_reason"))


def _candidate_from_serialization(row: dict[str, Any], index: int) -> dict[str, Any]:
    serialization_loss_stage = _text(
        row.get("serialization_loss_stage") or row.get("serialization_loss_bucket")
    )
    return {
        "candidate_rank": row.get("candidate_rank") or index,
        "candidate_id": row.get("candidate_id"),
        "candidate_value": row.get("candidate_value") or row.get("value_preview"),
        "selected": row.get("selected") or row.get("resolver_selected"),
        "source": row.get("source"),
        "source_family": row.get("source_family"),
        "parser_name": row.get("parser_name"),
        "pairing_method": row.get("pairing_method"),
        "page_number": row.get("page_number"),
        "line_index": row.get("line_index"),
        "bbox_available": row.get("bbox_available"),
        "detail_loss_bucket_override": row.get("detail_loss_bucket"),
        "detail_loss_stage_override": row.get("detail_loss_stage"),
        "detail_loss_reason_override": row.get("detail_loss_reason"),
        "serialization_loss_stage": serialization_loss_stage,
        "serialization_loss_reason": row.get("detail_loss_reason"),
        "source_detail_roundtrip_status": _roundtrip_status(serialization_loss_stage),
        "adapter_roundtrip_status": _adapter_roundtrip_status(row),
        "adapter_loss_reason": _adapter_loss_reason(row),
    }


def _merge_serialization_details(
    candidate_details: list[dict[str, Any]],
    serialization_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not serialization_details:
        return candidate_details
    serialization_by_key = {
        _serialization_key(row): row
        for row in serialization_details
        if _serialization_key(row)
    }
    merged: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for candidate in candidate_details:
        row = dict(candidate)
        key = _serialization_key(row)
        serialization_row = serialization_by_key.get(key)
        if serialization_row:
            seen_keys.add(key)
            serialization_candidate = _candidate_from_serialization(
                serialization_row,
                len(merged) + 1,
            )
            for field, value in serialization_candidate.items():
                if field.startswith("detail_loss_") or field.startswith("serialization_"):
                    row[field] = value
                elif field == "source_detail_roundtrip_status":
                    row[field] = value
                elif not _text(row.get(field)) and value not in (None, ""):
                    row[field] = value
        merged.append(row)
    for index, serialization_row in enumerate(serialization_details, start=1):
        key = _serialization_key(serialization_row)
        if key and key in seen_keys:
            continue
        merged.append(_candidate_from_serialization(serialization_row, len(merged) + 1))
    return merged


def _diagnostic_bucket(
    doc_id: str,
    diagnostics_by_doc: dict[str, dict[str, Any]],
    error_row: dict[str, Any],
    selected_row: dict[str, Any],
    audit_row: dict[str, Any],
) -> str:
    diagnostic = diagnostics_by_doc.get(doc_id, {})
    return _first_text(
        diagnostic.get("diagnostic_bucket"),
        error_row.get("error_reason"),
        error_row.get("reason"),
        error_row.get("diagnosis"),
        selected_row.get("diagnostic_bucket"),
        audit_row.get("diagnostic_bucket"),
    ) or "unknown"


def _candidate_value(candidate: dict[str, Any], selected_row: dict[str, Any], audit_row: dict[str, Any]) -> str:
    return _first_text(
        candidate.get("candidate_value"),
        candidate.get("value"),
        selected_row.get("selected_value") if _bool(candidate.get("selected")) else "",
        audit_row.get("selected_value") if _bool(candidate.get("selected")) else "",
    )


def _loss_bucket(
    *,
    row: dict[str, Any],
    selected_row: dict[str, Any],
    audit_row: dict[str, Any],
    diagnostics_row: dict[str, Any],
    candidate_count: int,
) -> tuple[str, str, str]:
    if not selected_row and not audit_row and not diagnostics_row:
        return (
            DETAIL_LOSS_DIAGNOSTIC_UNAVAILABLE,
            "diagnostics",
            "No evaluator, audit, or diagnostics row was available.",
        )
    if candidate_count == 0:
        return (
            DETAIL_LOSS_NOT_APPLICABLE_MISSING_CANDIDATE,
            "candidate_collection",
            "No load candidate detail was available in the local inputs.",
        )
    if not row.get("_candidate_page_line_present") and (
        selected_row.get("selected_line_index") or selected_row.get("selected_page_index")
    ):
        return (
            DETAIL_LOSS_DROPPED_BEFORE_AUDIT,
            "audit",
            "Evaluator row has page/line detail that is absent from audit candidate detail.",
        )
    if not row["candidate_id"]:
        return (
            DETAIL_LOSS_MISSING_CANDIDATE_ID,
            "candidate_detail",
            "Candidate detail exists but lacks a stable candidate id.",
        )
    if row["source_line_status"] == "present" and selected_row and not (
        selected_row.get("selected_line_index") or selected_row.get("selected_page_index")
    ):
        return (
            DETAIL_LOSS_MISSING_FROM_EVALUATOR,
            "evaluator",
            "Audit candidate detail has page/line metadata that evaluator rows do not expose.",
        )
    if row["source_line_status"] == "missing":
        return (
            DETAIL_LOSS_MISSING_PAGE_LINE,
            "candidate_detail",
            "Candidate detail lacks page or line metadata.",
        )
    if row["source"] == "":
        return (
            DETAIL_LOSS_MISSING_SOURCE,
            "candidate_detail",
            "Candidate detail lacks source/source family metadata.",
        )
    if row["pairing_method"] == "":
        return (
            DETAIL_LOSS_MISSING_PAIRING_METHOD,
            "candidate_detail",
            "Candidate detail lacks same-row/nearby/table/layout pairing metadata.",
        )
    if row["label_text_status"] == "missing":
        return (
            DETAIL_LOSS_MISSING_LABEL_CONTEXT,
            "candidate_detail",
            "Candidate detail lacks label context.",
        )
    if row["value_text_status"] == "missing":
        return (
            DETAIL_LOSS_MISSING_VALUE_CONTEXT,
            "candidate_detail",
            "Candidate detail lacks value context.",
        )
    return (
        DETAIL_LOSS_COMPLETE,
        "none",
        "Candidate has source, page/line, label, value, and pairing metadata.",
    )


def _detail_row(
    *,
    doc_id: str,
    candidate: dict[str, Any],
    selected_row: dict[str, Any],
    audit_row: dict[str, Any],
    error_row: dict[str, Any],
    diagnostics_row: dict[str, Any],
    candidate_count: int,
    include_private_values: bool,
) -> dict[str, Any]:
    source = _first_text(
        candidate.get("source"),
        selected_row.get("selected_source") if _bool(candidate.get("selected")) else "",
        audit_row.get("selected_source") if _bool(candidate.get("selected")) else "",
    )
    parser_name = _text(candidate.get("parser_name") or candidate.get("parser"))
    pairing_method = _pairing_method(source, parser_name, candidate.get("pairing_method"))
    page_number = _first_text(
        candidate.get("page_number"),
        candidate.get("page_index"),
        selected_row.get("selected_page_index") if _bool(candidate.get("selected")) else "",
        audit_row.get("selected_page_index") if _bool(candidate.get("selected")) else "",
    )
    line_index = _first_text(
        candidate.get("line_index"),
        selected_row.get("selected_line_index") if _bool(candidate.get("selected")) else "",
        audit_row.get("selected_line_index") if _bool(candidate.get("selected")) else "",
    )
    source_line = _first_text(
        candidate.get("source_line"),
        audit_row.get("selected_source_line") if _bool(candidate.get("selected")) else "",
    )
    candidate_page_line_present = bool(
        _first_text(
            candidate.get("page_number"),
            candidate.get("page_index"),
            candidate.get("line_index"),
            candidate.get("source_line"),
        )
    )
    label_text = _first_text(
        candidate.get("label_text"),
        candidate.get("label"),
        selected_row.get("selected_label") if _bool(candidate.get("selected")) else "",
        audit_row.get("selected_label") if _bool(candidate.get("selected")) else "",
    )
    value = _candidate_value(candidate, selected_row, audit_row)
    diagnostic_bucket = _diagnostic_bucket(
        doc_id,
        {doc_id: diagnostics_row},
        error_row,
        selected_row,
        audit_row,
    )
    row = {
        "document_id": doc_id,
        "file_name_redacted_or_alias": _first_text(
            audit_row.get("measurement_alias"),
            selected_row.get("measurement_alias"),
            doc_id,
        ),
        "field": LOAD_FIELD,
        "candidate_id": _text(candidate.get("candidate_id") or candidate.get("id")),
        "selected": _bool(candidate.get("selected")),
        "candidate_rank": _text(candidate.get("candidate_rank") or candidate.get("rank")),
        "source": source,
        "source_family": _source_family(source, parser_name),
        "parser_name": parser_name,
        "pairing_method": pairing_method,
        "page_number": page_number,
        "line_index": line_index,
        "bbox_available": _bool(candidate.get("bbox") or candidate.get("bbox_available")),
        "source_line_status": "present" if page_number or line_index or source_line else "missing",
        "candidate_value_status": _status(value),
        "label_text_status": _status(label_text),
        "value_text_status": _status(value),
        "neighbor_context_status": _status(
            candidate.get("neighbor_context")
            or candidate.get("neighbor_line")
            or audit_row.get("neighbor_context")
        ),
        "detail_loss_stage": "",
        "detail_loss_reason": "",
        "serialization_loss_stage": _text(
            candidate.get("serialization_loss_stage")
            or candidate.get("serialization_loss_bucket")
        ),
        "serialization_loss_reason": _text(candidate.get("serialization_loss_reason")),
        "source_detail_roundtrip_status": _text(
            candidate.get("source_detail_roundtrip_status")
        ),
        "adapter_roundtrip_status": _text(candidate.get("adapter_roundtrip_status")),
        "adapter_loss_reason": _text(candidate.get("adapter_loss_reason")),
        "diagnostic_bucket": diagnostic_bucket,
        "known_debt": diagnostic_bucket in KNOWN_DEBT_DIAGNOSTIC_BUCKETS,
        "private_values_redacted": not include_private_values,
        "value_preview": _value_for_output(value, include_private_values),
        "gold_value_preview": _value_for_output(
            selected_row.get("gold_value") or audit_row.get("gold_value"),
            include_private_values,
        ),
        "_candidate_page_line_present": candidate_page_line_present,
    }
    loss_bucket, loss_stage, loss_reason = _loss_bucket(
        row=row,
        selected_row=selected_row,
        audit_row=audit_row,
        diagnostics_row=diagnostics_row,
        candidate_count=candidate_count,
    )
    row["detail_loss_bucket"] = loss_bucket
    row["detail_loss_stage"] = loss_stage
    row["detail_loss_reason"] = loss_reason
    override_bucket = _text(candidate.get("detail_loss_bucket_override"))
    override_stage = _text(candidate.get("detail_loss_stage_override"))
    override_reason = _text(candidate.get("detail_loss_reason_override"))
    if override_bucket:
        row["detail_loss_bucket"] = override_bucket
    if override_stage:
        row["detail_loss_stage"] = override_stage
    if override_reason:
        row["detail_loss_reason"] = override_reason
    if not row["serialization_loss_stage"]:
        row["serialization_loss_stage"] = "not_available"
    if not row["serialization_loss_reason"]:
        row["serialization_loss_reason"] = ""
    if not row["source_detail_roundtrip_status"]:
        row["source_detail_roundtrip_status"] = _roundtrip_status(
            row["serialization_loss_stage"]
        )
    row.pop("_candidate_page_line_present", None)
    return row


def _placeholder_row(
    *,
    doc_id: str,
    selected_row: dict[str, Any],
    audit_row: dict[str, Any],
    error_row: dict[str, Any],
    diagnostics_row: dict[str, Any],
    include_private_values: bool,
) -> dict[str, Any]:
    return _detail_row(
        doc_id=doc_id,
        candidate={"selected": bool(selected_row or audit_row), "candidate_rank": ""},
        selected_row=selected_row,
        audit_row=audit_row,
        error_row=error_row,
        diagnostics_row=diagnostics_row,
        candidate_count=0,
        include_private_values=include_private_values,
    )


def build_load_source_line_detail_inventory(
    *,
    selected_rows: dict[str, dict[str, Any]] | None = None,
    error_rows: dict[str, dict[str, Any]] | None = None,
    audit_rows: dict[str, dict[str, Any]] | None = None,
    diagnostic_rows: dict[str, dict[str, Any]] | None = None,
    diagnostics_summary: dict[str, Any] | None = None,
    serialization_rows: list[dict[str, Any]] | None = None,
    include_private_values: bool = False,
) -> dict[str, Any]:
    selected_rows = selected_rows or {}
    error_rows = error_rows or {}
    audit_rows = audit_rows or {}
    diagnostic_rows = diagnostic_rows or {}
    diagnostics_summary = diagnostics_summary or {}
    serialization_by_doc = _serialization_details_by_doc(serialization_rows)
    document_ids = sorted(
        set(selected_rows)
        | set(error_rows)
        | set(audit_rows)
        | set(diagnostic_rows)
        | set(serialization_by_doc)
    )

    detail_input_status = "available" if document_ids else "detail_input_unavailable"
    if not document_ids:
        document_ids = ["detail_input_unavailable"]

    detail_rows: list[dict[str, Any]] = []
    for doc_id in document_ids:
        selected_row = selected_rows.get(doc_id, {})
        error_row = error_rows.get(doc_id, {})
        audit_row = audit_rows.get(doc_id, {})
        diagnostics_row = diagnostic_rows.get(doc_id, {})
        candidate_details = _merge_serialization_details(
            _candidate_details(audit_row),
            serialization_by_doc.get(doc_id, []),
        )
        if candidate_details:
            for index, candidate in enumerate(candidate_details, start=1):
                candidate.setdefault("candidate_rank", index)
                if "selected" not in candidate:
                    candidate["selected"] = _token(
                        candidate.get("candidate_value") or candidate.get("value")
                    ) == _token(selected_row.get("selected_value") or audit_row.get("selected_value"))
                detail_rows.append(
                    _detail_row(
                        doc_id=doc_id,
                        candidate=candidate,
                        selected_row=selected_row,
                        audit_row=audit_row,
                        error_row=error_row,
                        diagnostics_row=diagnostics_row,
                        candidate_count=len(candidate_details),
                        include_private_values=include_private_values,
                    )
                )
        else:
            detail_rows.append(
                _placeholder_row(
                    doc_id=doc_id,
                    selected_row=selected_row,
                    audit_row=audit_row,
                    error_row=error_row,
                    diagnostics_row=diagnostics_row,
                    include_private_values=include_private_values,
                )
            )

    loss_counts = Counter(row["detail_loss_bucket"] for row in detail_rows)
    serialization_loss_counts = Counter(
        row["serialization_loss_stage"]
        for row in detail_rows
        if row["serialization_loss_stage"] != "not_available"
    )
    adapter_roundtrip_counts = Counter(
        row["adapter_roundtrip_status"]
        for row in detail_rows
        if row["adapter_roundtrip_status"]
    )
    adapter_detail_lost_count = sum(
        count
        for status, count in adapter_roundtrip_counts.items()
        if status.startswith("adapter_roundtrip_lost_")
    )
    adapter_detail_preserved_count = (
        adapter_roundtrip_counts["adapter_roundtrip_complete"]
        + adapter_roundtrip_counts["adapter_roundtrip_preserved_partial_detail"]
    )
    source_line_complete_count = loss_counts[DETAIL_LOSS_COMPLETE]
    missing_page_line_count = loss_counts[DETAIL_LOSS_MISSING_PAGE_LINE]
    missing_source_count = loss_counts[DETAIL_LOSS_MISSING_SOURCE]
    dropped_detail_count = (
        loss_counts[DETAIL_LOSS_DROPPED_BEFORE_RESOLVER]
        + loss_counts[DETAIL_LOSS_DROPPED_IN_RESOLVER_TRACE]
        + loss_counts[DETAIL_LOSS_DROPPED_BEFORE_AUDIT]
        + loss_counts[DETAIL_LOSS_MISSING_FROM_EVALUATOR]
    )
    unknown_diagnostic_count = 0
    if isinstance(diagnostics_summary.get("diagnostic_bucket_counts"), dict):
        unknown_diagnostic_count = int(
            diagnostics_summary.get("diagnostic_bucket_counts", {}).get("unknown") or 0
        )
    unknown_caused_by_missing_detail_count = sum(
        1
        for row in detail_rows
        if row["diagnostic_bucket"] == "unknown"
        and row["detail_loss_bucket"] != DETAIL_LOSS_COMPLETE
    )
    if unknown_diagnostic_count and not unknown_caused_by_missing_detail_count:
        unknown_caused_by_missing_detail_count = min(
            unknown_diagnostic_count,
            loss_counts[DETAIL_LOSS_DIAGNOSTIC_UNAVAILABLE]
            + loss_counts[DETAIL_LOSS_MISSING_PAGE_LINE]
            + loss_counts[DETAIL_LOSS_MISSING_SOURCE]
            + loss_counts[DETAIL_LOSS_NOT_APPLICABLE_MISSING_CANDIDATE],
        )

    document_count = len(set(row["document_id"] for row in detail_rows))
    candidate_count = len(detail_rows)
    coverage_rows = [
        {
            "coverage_metric": "candidate_detail_rows",
            "count": candidate_count,
            "detail": "Rows produced from existing eval/audit/diagnostic metadata.",
        },
        {
            "coverage_metric": "candidate_has_complete_source_detail",
            "count": source_line_complete_count,
            "detail": "Rows with source, page/line, label, value, and pairing metadata.",
        },
        {
            "coverage_metric": "candidate_missing_page_line",
            "count": missing_page_line_count,
            "detail": "Rows missing page or line metadata.",
        },
        {
            "coverage_metric": "candidate_missing_source",
            "count": missing_source_count,
            "detail": "Rows missing source metadata.",
        },
        {
            "coverage_metric": "detail_dropped_between_surfaces",
            "count": dropped_detail_count,
            "detail": "Rows where detail appears to exist in one local surface but not another.",
        },
        {
            "coverage_metric": "serialization_sidecar_rows",
            "count": sum(serialization_loss_counts.values()),
            "detail": "Rows augmented by local-only serialization sidecar metadata.",
        },
    ]
    review_rows = [
        {
            "document_id": row["document_id"],
            "detail_loss_bucket": row["detail_loss_bucket"],
            "diagnostic_bucket": row["diagnostic_bucket"],
            "recommended_action": "review_detail_serialization_only",
            "behavior_change_allowed": False,
        }
        for row in detail_rows
        if row["detail_loss_bucket"] != DETAIL_LOSS_COMPLETE
    ]
    return {
        "schema_version": LOAD_SOURCE_DETAIL_SCHEMA_VERSION,
        "summary": {
            "detail_input_status": detail_input_status,
            "document_count": document_count,
            "candidate_detail_row_count": candidate_count,
            "complete_source_detail_count": source_line_complete_count,
            "missing_page_line_count": missing_page_line_count,
            "missing_source_count": missing_source_count,
            "dropped_detail_count": dropped_detail_count,
            "unknown_caused_by_missing_detail_count": unknown_caused_by_missing_detail_count,
            "detail_loss_bucket_counts": dict(sorted(loss_counts.items())),
            "serialization_sidecar_status": (
                "present" if serialization_by_doc else "skipped_missing_optional_dir"
            ),
            "serialization_complete_detail_count": serialization_loss_counts[
                "complete_detail_serialized"
            ],
            "serialization_loss_bucket_counts": dict(sorted(serialization_loss_counts.items())),
            "adapter_roundtrip_status_counts": dict(sorted(adapter_roundtrip_counts.items())),
            "adapter_detail_preserved_count": adapter_detail_preserved_count,
            "adapter_detail_lost_count": adapter_detail_lost_count,
            "private_values_included": include_private_values,
            "values_redacted": not include_private_values,
            "pdf_processing_attempted": False,
            "ocr_attempted": False,
            "google_called": False,
            "model_or_cloud_called": False,
            "private_measurement_run": False,
        },
        "detail_rows": detail_rows,
        "detail_loss_rows": [
            {
                "document_id": row["document_id"],
                "candidate_id": row["candidate_id"],
                "detail_loss_bucket": row["detail_loss_bucket"],
                "detail_loss_stage": row["detail_loss_stage"],
                "detail_loss_reason": row["detail_loss_reason"],
                "serialization_loss_stage": row["serialization_loss_stage"],
                "serialization_loss_reason": row["serialization_loss_reason"],
                "source_detail_roundtrip_status": row["source_detail_roundtrip_status"],
                "adapter_roundtrip_status": row["adapter_roundtrip_status"],
                "adapter_loss_reason": row["adapter_loss_reason"],
                "diagnostic_bucket": row["diagnostic_bucket"],
            }
            for row in detail_rows
        ],
        "coverage_rows": coverage_rows,
        "review_rows": review_rows,
    }
