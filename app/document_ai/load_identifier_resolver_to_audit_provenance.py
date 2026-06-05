"""Local-only load resolver-to-audit provenance helpers.

These helpers compare resolver-visible load candidate rows with audit-stage
diagnostic rows. They preserve already-visible resolver provenance only in
local diagnostic sidecars; they do not run resolution, infer missing metadata,
or change selected load-number behavior.
"""

from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any


LOAD_RESOLVER_TO_AUDIT_PROVENANCE_SCHEMA_VERSION = (
    "ratecon_load_resolver_to_audit_provenance_v1"
)
LOAD_FIELD = "load_number"
REDACTED_VALUE = "[redacted]"

STATUS_PRESERVED = "resolver_to_audit_preserved"
STATUS_MISSING_AUDIT_ROW = "resolver_to_audit_missing_audit_row"
STATUS_CANDIDATE_ID_LOST = "resolver_to_audit_candidate_id_lost"
STATUS_SOURCE_LOST = "resolver_to_audit_source_lost"
STATUS_PAGE_LINE_LOST = "resolver_to_audit_page_line_lost"
STATUS_PAIRING_METHOD_LOST = "resolver_to_audit_pairing_method_lost"
STATUS_BBOX_LOST = "resolver_to_audit_bbox_lost"
STATUS_SELECTED_FLAG_LOST = "resolver_to_audit_selected_flag_lost"
STATUS_STAGE_UNAVAILABLE = "resolver_to_audit_stage_unavailable"
STATUS_CANDIDATE_NOT_COMPARABLE = "resolver_to_audit_candidate_not_comparable"
STATUS_PRIVATE_VALUES_NOT_REQUESTED = "resolver_to_audit_private_values_not_requested"
STATUS_UNKNOWN = "resolver_to_audit_unknown"

STATUS_ORDER = (
    STATUS_PRESERVED,
    STATUS_MISSING_AUDIT_ROW,
    STATUS_CANDIDATE_ID_LOST,
    STATUS_SOURCE_LOST,
    STATUS_PAGE_LINE_LOST,
    STATUS_PAIRING_METHOD_LOST,
    STATUS_BBOX_LOST,
    STATUS_SELECTED_FLAG_LOST,
    STATUS_STAGE_UNAVAILABLE,
    STATUS_CANDIDATE_NOT_COMPARABLE,
    STATUS_PRIVATE_VALUES_NOT_REQUESTED,
    STATUS_UNKNOWN,
)

ROW_FIELDNAMES = [
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
    "resolver_stage",
    "resolver_selected",
    "resolver_eligible",
    "resolver_source",
    "resolver_source_family",
    "resolver_parser_name",
    "resolver_pairing_method",
    "resolver_page_number",
    "resolver_line_index",
    "resolver_bbox_available",
    "audit_row_available",
    "audit_candidate_id_available",
    "audit_source_available",
    "audit_page_line_available",
    "audit_pairing_available",
    "audit_preserved",
    "resolver_to_audit_status",
    "audit_loss_reason",
    "private_values_redacted",
    "value_preview",
]

LOSS_FIELDNAMES = [
    "resolver_to_audit_status",
    "count",
]

REVIEW_FIELDNAMES = [
    "document_id",
    "candidate_id",
    "resolver_to_audit_status",
    "recommended_action",
    "behavior_change_allowed",
]


def _text(value: Any) -> str:
    return str(value or "").strip()


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


def _metadata(row: dict[str, Any] | None) -> dict[str, Any]:
    row = row or {}
    if isinstance(row.get("metadata"), dict):
        return dict(row.get("metadata") or {})
    if isinstance(row.get("metadata_summary"), dict):
        return dict(row.get("metadata_summary") or {})
    return {}


def _document_id(row: dict[str, Any] | None) -> str:
    row = row or {}
    return _first_text(
        row.get("document_id"),
        row.get("measurement_alias"),
        row.get("document_alias"),
        row.get("case_id"),
        row.get("file_hash"),
    )


def _field(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(row.get("field"), row.get("field_name"), metadata.get("field"))


def _field_matches(row: dict[str, Any] | None) -> bool:
    field = _field(row)
    return not field or field == LOAD_FIELD


def _candidate_id(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(
        row.get("candidate_id"),
        row.get("id"),
        row.get("selected_candidate_id"),
        metadata.get("candidate_id"),
    )


def _source(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(row.get("source"), row.get("selected_source"), metadata.get("source"))


def _source_family(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    source = _source(row)
    explicit = _first_text(row.get("source_family"), metadata.get("source_family"))
    if explicit:
        return explicit
    token = f"{source} {_parser_name(row)}".lower()
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
    return "unknown" if source else ""


def _parser_name(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(row.get("parser_name"), row.get("parser"), metadata.get("parser_name"))


def _pairing(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(
        row.get("pairing_method"),
        row.get("selected_pairing_method"),
        metadata.get("pairing_method"),
        metadata.get("value_extraction_method"),
        metadata.get("match_kind"),
    )


def _page(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(
        row.get("page_number"),
        row.get("page"),
        row.get("page_index"),
        row.get("selected_page"),
        row.get("selected_page_index"),
        row.get("source_page"),
        metadata.get("page_number"),
        metadata.get("page"),
        metadata.get("page_index"),
        metadata.get("source_page"),
    )


def _line(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(
        row.get("line_index"),
        row.get("line_number"),
        row.get("selected_line_index"),
        row.get("source_line_index"),
        metadata.get("line_index"),
        metadata.get("line_number"),
        metadata.get("source_line_index"),
    )


def _page_line_available(row: dict[str, Any] | None) -> bool:
    return bool(_page(row) or _line(row))


def _bbox_available(row: dict[str, Any] | None) -> bool:
    row = row or {}
    metadata = _metadata(row)
    return _bool(row.get("bbox_available") or row.get("has_bbox") or metadata.get("bbox_available"))


def _selected(row: dict[str, Any] | None) -> bool:
    row = row or {}
    return _bool(row.get("selected") or row.get("resolver_selected"))


def _audit_selected(row: dict[str, Any] | None) -> bool:
    row = row or {}
    if "selected" in row:
        return _bool(row.get("selected"))
    return False


def _eligible(row: dict[str, Any] | None) -> bool:
    row = row or {}
    if "resolver_eligible" in row:
        return _bool(row.get("resolver_eligible"))
    if "eligible" in row:
        return _bool(row.get("eligible"))
    return bool(row)


def _candidate_value(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(
        row.get("candidate_value"),
        row.get("value"),
        row.get("normalized_value"),
        row.get("raw_value"),
        row.get("selected_value"),
        metadata.get("candidate_value"),
    )


def _value_for_output(row: dict[str, Any] | None, include_private_values: bool) -> str:
    value = _candidate_value(row)
    if include_private_values:
        return value
    return REDACTED_VALUE if value else ""


def _normalize_audit_row(row: dict[str, Any], document_id: str = "") -> dict[str, Any]:
    normalized = dict(row)
    if document_id and not _document_id(normalized):
        normalized["document_id"] = document_id
    if not _field(normalized):
        normalized["field"] = LOAD_FIELD
    return normalized


def audit_rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract already-serialized audit-stage load rows from one audit payload."""

    if not isinstance(payload, dict):
        return []
    document_id = _document_id(payload)
    rows: list[dict[str, Any]] = []
    candidate_details = payload.get("candidate_details")
    if isinstance(candidate_details, list):
        for detail in candidate_details:
            if isinstance(detail, dict):
                rows.append(_normalize_audit_row(detail, document_id))
    shadow = payload.get("shadow") if isinstance(payload.get("shadow"), dict) else {}
    resolved = shadow.get("resolved_fields") if isinstance(shadow, dict) else {}
    load_resolution = (resolved or {}).get(LOAD_FIELD, {}) if isinstance(resolved, dict) else {}
    selected = load_resolution.get("selected_candidate") if isinstance(load_resolution, dict) else {}
    if isinstance(selected, dict) and selected:
        rows.append(
            _normalize_audit_row(
                {
                    "candidate_id": selected.get("candidate_id"),
                    "candidate_value": selected.get("value") or selected.get("value_preview"),
                    "source": selected.get("source"),
                    "parser_name": selected.get("parser_name"),
                    "selected": True,
                    "metadata_summary": selected.get("metadata_summary") or {},
                },
                document_id,
            )
        )
    return [row for row in rows if _field_matches(row)]


def audit_rows_from_payloads(payloads: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in payloads or []:
        rows.extend(audit_rows_from_payload(payload))
    return rows


def _resolver_rows(resolver_rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows = []
    for row in resolver_rows or []:
        if isinstance(row, dict) and _field_matches(row):
            rows.append(dict(row))
    return rows


def _audit_rows(audit_rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows = []
    for row in audit_rows or []:
        if isinstance(row, dict) and _field_matches(row):
            rows.append(dict(row))
    return rows


def _audit_by_candidate(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        candidate_id = _candidate_id(row)
        if not candidate_id:
            continue
        indexed.setdefault((_document_id(row), candidate_id), row)
    return indexed


def _audit_selected_without_candidate_id(rows: list[dict[str, Any]], document_id: str) -> dict[str, Any] | None:
    matches = [
        row
        for row in rows
        if _document_id(row) == document_id and not _candidate_id(row) and _selected(row)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _classify(resolver: dict[str, Any] | None, audit: dict[str, Any] | None) -> tuple[str, str]:
    if resolver is None:
        return STATUS_STAGE_UNAVAILABLE, "Resolver-visible row is unavailable."
    if not _candidate_id(resolver):
        return STATUS_CANDIDATE_NOT_COMPARABLE, "Resolver row is missing candidate_id."
    if audit is None:
        return STATUS_MISSING_AUDIT_ROW, "Resolver row is visible but no comparable audit row exists."
    if not _candidate_id(audit):
        return STATUS_CANDIDATE_ID_LOST, "Audit row is present but candidate_id is missing."
    if _source(resolver) and not _source(audit):
        return STATUS_SOURCE_LOST, "Audit row is present but source is missing."
    if _page_line_available(resolver) and not _page_line_available(audit):
        return STATUS_PAGE_LINE_LOST, "Audit row is present but page/line detail is missing."
    if _pairing(resolver) and not _pairing(audit):
        return STATUS_PAIRING_METHOD_LOST, "Audit row is present but pairing_method is missing."
    if _bbox_available(resolver) and not _bbox_available(audit):
        return STATUS_BBOX_LOST, "Audit row is present but bbox availability is missing."
    if _selected(resolver) and not _audit_selected(audit):
        return STATUS_SELECTED_FLAG_LOST, "Audit row is present but selected flag is missing."
    return STATUS_PRESERVED, "Resolver-visible provenance is preserved in local audit diagnostics."


def _sidecar_row(
    resolver: dict[str, Any] | None,
    audit: dict[str, Any] | None,
    *,
    include_private_values: bool,
) -> dict[str, Any]:
    resolver = resolver or {}
    status, reason = _classify(resolver if resolver else None, audit)
    document_id = _document_id(resolver) or _document_id(audit)
    candidate_id = _candidate_id(resolver)
    audit_available = audit is not None
    return {
        "document_id": document_id,
        "field": LOAD_FIELD,
        "stage": "audit",
        "candidate_id": candidate_id,
        "source": _source(resolver),
        "source_family": _source_family(resolver),
        "parser_name": _parser_name(resolver),
        "pairing_method": _pairing(resolver),
        "page_number": _page(resolver),
        "line_index": _line(resolver),
        "bbox_available": _bbox_available(resolver),
        "resolver_stage": _first_text(resolver.get("stage"), "resolver" if resolver else ""),
        "resolver_selected": _selected(resolver),
        "resolver_eligible": _eligible(resolver),
        "resolver_source": _source(resolver),
        "resolver_source_family": _source_family(resolver),
        "resolver_parser_name": _parser_name(resolver),
        "resolver_pairing_method": _pairing(resolver),
        "resolver_page_number": _page(resolver),
        "resolver_line_index": _line(resolver),
        "resolver_bbox_available": _bbox_available(resolver),
        "audit_row_available": audit_available,
        "audit_candidate_id_available": bool(_candidate_id(audit)),
        "audit_source_available": bool(_source(audit)),
        "audit_page_line_available": _page_line_available(audit),
        "audit_pairing_available": bool(_pairing(audit)),
        "audit_preserved": status == STATUS_PRESERVED,
        "audit_loss_reason": reason,
        "private_values_redacted": not include_private_values,
        "value_preview": _value_for_output(resolver or audit, include_private_values),
        "resolver_to_audit_status": status,
    }


def build_resolver_to_audit_provenance_sidecar(
    *,
    resolver_rows: list[dict[str, Any]] | None = None,
    audit_rows: list[dict[str, Any]] | None = None,
    include_private_values: bool = False,
) -> dict[str, Any]:
    """Build local-only resolver-to-audit provenance comparison sidecars."""

    resolver = _resolver_rows(resolver_rows)
    audit = _audit_rows(audit_rows)
    audit_index = _audit_by_candidate(audit)
    rows: list[dict[str, Any]] = []
    for resolver_row in resolver:
        key = (_document_id(resolver_row), _candidate_id(resolver_row))
        audit_row = audit_index.get(key)
        if audit_row is None and _selected(resolver_row):
            audit_row = _audit_selected_without_candidate_id(audit, _document_id(resolver_row))
        rows.append(
            _sidecar_row(
                resolver_row,
                audit_row,
                include_private_values=include_private_values,
            )
        )
    if not resolver:
        rows.append(_sidecar_row(None, audit[0] if audit else None, include_private_values=include_private_values))

    counts = Counter(row["resolver_to_audit_status"] for row in rows)
    preserved_count = counts.get(STATUS_PRESERVED, 0)
    loss_count = len(rows) - preserved_count
    summary = {
        "schema_version": LOAD_RESOLVER_TO_AUDIT_PROVENANCE_SCHEMA_VERSION,
        "resolver_visible_candidate_count": len(resolver),
        "audit_candidate_count": len(audit),
        "resolver_to_audit_candidate_count": len(rows),
        "resolver_to_audit_preserved_count": preserved_count,
        "resolver_to_audit_loss_count": loss_count,
        "resolver_to_audit_status_counts": {
            status: counts.get(status, 0)
            for status in STATUS_ORDER
            if counts.get(status, 0)
        },
        "resolver_to_audit_stage_unavailable_count": counts.get(STATUS_STAGE_UNAVAILABLE, 0),
        "resolver_to_audit_missing_audit_row_count": counts.get(STATUS_MISSING_AUDIT_ROW, 0),
        "resolver_to_audit_candidate_not_comparable_count": counts.get(
            STATUS_CANDIDATE_NOT_COMPARABLE,
            0,
        ),
        "private_values_included": include_private_values,
        "private_values_redacted": not include_private_values,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "behavior_change_allowed": False,
    }
    return {
        "schema_version": LOAD_RESOLVER_TO_AUDIT_PROVENANCE_SCHEMA_VERSION,
        "summary": summary,
        "rows": rows,
        "loss_by_field_rows": [
            {"resolver_to_audit_status": status, "count": counts[status]}
            for status in STATUS_ORDER
            if counts[status]
        ],
        "review_rows": [
            {
                "document_id": row["document_id"],
                "candidate_id": row["candidate_id"],
                "resolver_to_audit_status": row["resolver_to_audit_status"],
                "recommended_action": "preserve_resolver_metadata_in_local_audit_diagnostics",
                "behavior_change_allowed": False,
            }
            for row in rows
            if row["resolver_to_audit_status"] != STATUS_PRESERVED
        ],
    }


def build_markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# RateCon Load Resolver-to-Audit Provenance",
        "",
        "Local-only resolver-to-audit provenance sidecar. Private values are redacted by default.",
        "",
        f"- resolver_visible_candidate_count: {summary['resolver_visible_candidate_count']}",
        f"- audit_candidate_count: {summary['audit_candidate_count']}",
        f"- resolver_to_audit_preserved_count: {summary['resolver_to_audit_preserved_count']}",
        f"- resolver_to_audit_loss_count: {summary['resolver_to_audit_loss_count']}",
        f"- private_values_redacted: {summary['private_values_redacted']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
        "",
        "## Status Counts",
    ]
    for status, count in summary["resolver_to_audit_status_counts"].items():
        lines.append(f"- {status}: {count}")
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_resolver_to_audit_outputs(output_dir: Path, payload: dict[str, Any]) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": output_dir / "load_resolver_to_audit_provenance_summary.json",
        "report": output_dir / "load_resolver_to_audit_provenance_report.md",
        "rows": output_dir / "load_resolver_to_audit_rows.csv",
        "loss_by_field": output_dir / "load_resolver_to_audit_loss_by_field.csv",
        "review_items": output_dir / "load_resolver_to_audit_review_items.csv",
    }
    write_json(paths["summary"], payload)
    paths["report"].write_text(build_markdown_report(payload), encoding="utf-8")
    write_csv(paths["rows"], payload["rows"], ROW_FIELDNAMES)
    write_csv(paths["loss_by_field"], payload["loss_by_field_rows"], LOSS_FIELDNAMES)
    write_csv(paths["review_items"], payload["review_rows"], REVIEW_FIELDNAMES)
    return paths
