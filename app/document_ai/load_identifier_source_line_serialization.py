"""Local-only load identifier source-line serialization sidecar helpers.

These helpers compare existing generated/resolver/audit/evaluator metadata for
`load_number` candidates. They do not generate candidates, run resolution,
process PDFs, or change selected load-number behavior.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.document_ai.load_identifier_candidate_adapter_provenance import (
    LOAD_ADAPTER_ROUNDTRIP_COMPLETE,
    LOAD_ADAPTER_ROUNDTRIP_LOST_CANDIDATE_ID,
    LOAD_ADAPTER_ROUNDTRIP_LOST_PAGE_LINE,
    LOAD_ADAPTER_ROUNDTRIP_LOST_PAIRING_METHOD,
    LOAD_ADAPTER_ROUNDTRIP_LOST_SOURCE,
    LOAD_ADAPTER_ROUNDTRIP_PRESERVED_PARTIAL_DETAIL,
    summarize_adapter_provenance_roundtrip,
)


LOAD_SOURCE_LINE_SERIALIZATION_SCHEMA_VERSION = "ratecon_load_source_line_serialization_v1"
LOAD_FIELD = "load_number"
REDACTED_VALUE = "[redacted]"

SERIALIZATION_COMPLETE = "complete_detail_serialized"
SERIALIZATION_MISSING_CANDIDATE_ID_AT_GENERATION = "missing_candidate_id_at_generation"
SERIALIZATION_MISSING_PAGE_LINE_AT_GENERATION = "missing_page_line_at_generation"
SERIALIZATION_MISSING_SOURCE_AT_GENERATION = "missing_source_at_generation"
SERIALIZATION_MISSING_PAIRING_METHOD_AT_GENERATION = "missing_pairing_method_at_generation"
SERIALIZATION_LOST_IN_CANDIDATE_ADAPTER = "lost_in_candidate_adapter"
SERIALIZATION_LOST_IN_DEDUPE = "lost_in_dedupe"
SERIALIZATION_LOST_IN_RESOLVER_TRACE = "lost_in_resolver_trace"
SERIALIZATION_LOST_IN_SHADOW_AUDIT = "lost_in_shadow_audit"
SERIALIZATION_LOST_IN_GOLD_EVALUATOR = "lost_in_gold_evaluator"
SERIALIZATION_LOST_IN_DETAIL_INVENTORY_READER = "lost_in_detail_inventory_reader"
SERIALIZATION_PRIVATE_VALUES_NOT_REQUESTED = "private_values_not_requested"
SERIALIZATION_NOT_APPLICABLE_CANDIDATE_MISSING = "not_applicable_candidate_missing"
SERIALIZATION_UNKNOWN = "unknown"

SERIALIZATION_LOSS_BUCKETS = (
    SERIALIZATION_COMPLETE,
    SERIALIZATION_MISSING_CANDIDATE_ID_AT_GENERATION,
    SERIALIZATION_MISSING_PAGE_LINE_AT_GENERATION,
    SERIALIZATION_MISSING_SOURCE_AT_GENERATION,
    SERIALIZATION_MISSING_PAIRING_METHOD_AT_GENERATION,
    SERIALIZATION_LOST_IN_CANDIDATE_ADAPTER,
    SERIALIZATION_LOST_IN_DEDUPE,
    SERIALIZATION_LOST_IN_RESOLVER_TRACE,
    SERIALIZATION_LOST_IN_SHADOW_AUDIT,
    SERIALIZATION_LOST_IN_GOLD_EVALUATOR,
    SERIALIZATION_LOST_IN_DETAIL_INVENTORY_READER,
    SERIALIZATION_PRIVATE_VALUES_NOT_REQUESTED,
    SERIALIZATION_NOT_APPLICABLE_CANDIDATE_MISSING,
    SERIALIZATION_UNKNOWN,
)

DETAIL_BUCKET_BY_SERIALIZATION_BUCKET = {
    SERIALIZATION_COMPLETE: "candidate_has_complete_source_detail",
    SERIALIZATION_MISSING_CANDIDATE_ID_AT_GENERATION: "candidate_missing_candidate_id",
    SERIALIZATION_MISSING_PAGE_LINE_AT_GENERATION: "candidate_missing_page_line",
    SERIALIZATION_MISSING_SOURCE_AT_GENERATION: "candidate_missing_source",
    SERIALIZATION_MISSING_PAIRING_METHOD_AT_GENERATION: "candidate_missing_pairing_method",
    SERIALIZATION_LOST_IN_CANDIDATE_ADAPTER: "candidate_detail_dropped_before_resolver",
    SERIALIZATION_LOST_IN_DEDUPE: "candidate_detail_dropped_in_resolver_trace",
    SERIALIZATION_LOST_IN_RESOLVER_TRACE: "candidate_detail_dropped_in_resolver_trace",
    SERIALIZATION_LOST_IN_SHADOW_AUDIT: "candidate_detail_dropped_before_audit",
    SERIALIZATION_LOST_IN_GOLD_EVALUATOR: "candidate_detail_missing_from_evaluator",
    SERIALIZATION_LOST_IN_DETAIL_INVENTORY_READER: "diagnostic_detail_unavailable",
    SERIALIZATION_PRIVATE_VALUES_NOT_REQUESTED: "private_values_required_for_value_comparison",
    SERIALIZATION_NOT_APPLICABLE_CANDIDATE_MISSING: "detail_not_applicable_missing_candidate",
    SERIALIZATION_UNKNOWN: "unknown",
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


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    if isinstance((row or {}).get("metadata"), dict):
        return dict((row or {}).get("metadata") or {})
    if isinstance((row or {}).get("metadata_summary"), dict):
        return dict((row or {}).get("metadata_summary") or {})
    return {}


def _document_id(row: dict[str, Any], fallback: str = "") -> str:
    return _first_text(
        row.get("document_id"),
        row.get("case_id"),
        row.get("measurement_alias"),
        row.get("file_hash"),
        fallback,
    )


def _field_matches(row: dict[str, Any]) -> bool:
    field = _text(row.get("field") or row.get("field_name"))
    return not field or field == LOAD_FIELD


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


def _normalize_pairing(source: str, parser_name: str = "", explicit: Any = "") -> str:
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


def _page(row: dict[str, Any]) -> str:
    metadata = _metadata(row)
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


def _line(row: dict[str, Any]) -> str:
    metadata = _metadata(row)
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


def _candidate_id(row: dict[str, Any]) -> str:
    metadata = _metadata(row)
    return _first_text(
        row.get("candidate_id"),
        row.get("id"),
        row.get("selected_candidate_id"),
        metadata.get("candidate_id"),
    )


def _candidate_value(row: dict[str, Any]) -> str:
    metadata = _metadata(row)
    return _first_text(
        row.get("candidate_value"),
        row.get("value"),
        row.get("selected_value"),
        metadata.get("candidate_value"),
    )


def _source(row: dict[str, Any]) -> str:
    metadata = _metadata(row)
    return _first_text(
        row.get("source"),
        row.get("selected_source"),
        metadata.get("source"),
        metadata.get("original_source"),
    )


def _parser(row: dict[str, Any]) -> str:
    metadata = _metadata(row)
    return _first_text(row.get("parser_name"), row.get("parser"), metadata.get("parser_name"))


def _pairing(row: dict[str, Any]) -> str:
    metadata = _metadata(row)
    source = _source(row)
    parser = _parser(row)
    return _normalize_pairing(
        source,
        parser,
        _first_text(
            row.get("pairing_method"),
            metadata.get("pairing_method"),
            metadata.get("value_extraction_method"),
            metadata.get("match_kind"),
        ),
    )


def _has_page_line(row: dict[str, Any]) -> bool:
    return bool(_page(row) or _line(row) or _text(row.get("source_line")))


def _detail_complete(row: dict[str, Any]) -> bool:
    return bool(_candidate_id(row) and _source(row) and _has_page_line(row) and _pairing(row))


def _selected(row: dict[str, Any]) -> bool:
    return _bool(row.get("selected") or row.get("resolver_selected"))


def _normalize_row(row: dict[str, Any], surface: str, fallback: str) -> dict[str, Any]:
    normalized = dict(row)
    normalized["_surface"] = surface
    normalized["_document_id"] = _document_id(row, fallback)
    normalized["_candidate_id"] = _candidate_id(row)
    normalized["_candidate_value"] = _candidate_value(row)
    normalized["_source"] = _source(row)
    normalized["_parser_name"] = _parser(row)
    normalized["_pairing_method"] = _pairing(row)
    normalized["_page_number"] = _page(row)
    normalized["_line_index"] = _line(row)
    normalized["_selected"] = _selected(row)
    normalized["_detail_complete"] = _detail_complete(row)
    return normalized


def _rows_by_doc_and_candidate(rows: list[dict[str, Any]], surface: str) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for index, row in enumerate(rows or [], start=1):
        if not isinstance(row, dict) or not _field_matches(row):
            continue
        normalized = _normalize_row(row, surface, f"{surface}_{index}")
        candidate_key = normalized["_candidate_id"] or f"{surface}_candidate_{index}"
        grouped[normalized["_document_id"]][candidate_key] = normalized
    return grouped


def _evaluator_by_doc(evaluator_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(evaluator_rows or [], start=1):
        if not isinstance(row, dict) or not _field_matches(row):
            continue
        normalized = _normalize_row(row, "evaluator", f"evaluator_{index}")
        rows[normalized["_document_id"]] = normalized
    return rows


def _candidate_keys(*groups: dict[str, dict[str, dict[str, Any]]]) -> dict[str, set[str]]:
    by_doc: dict[str, set[str]] = defaultdict(set)
    for group in groups:
        for doc_id, candidates in group.items():
            by_doc[doc_id].update(candidates)
    return by_doc


def _pick(*rows: dict[str, Any] | None, key: str) -> str:
    for row in rows:
        if row:
            value = _text(row.get(key))
            if value:
                return value
    return ""


def _loss_bucket(
    generated: dict[str, Any] | None,
    resolver: dict[str, Any] | None,
    audit: dict[str, Any] | None,
    evaluator: dict[str, Any] | None,
) -> tuple[str, str, str]:
    if not generated and not resolver and not audit and not evaluator:
        return (
            SERIALIZATION_NOT_APPLICABLE_CANDIDATE_MISSING,
            "candidate_collection",
            "No load candidate row was available on any local diagnostic surface.",
        )
    first = generated or resolver or audit or evaluator or {}
    if generated:
        if not _candidate_id(generated):
            return (
                SERIALIZATION_MISSING_CANDIDATE_ID_AT_GENERATION,
                "generation",
                "Generated candidate row lacks candidate_id.",
            )
        if not _has_page_line(generated):
            return (
                SERIALIZATION_MISSING_PAGE_LINE_AT_GENERATION,
                "generation",
                "Generated candidate row lacks page or line metadata.",
            )
        if not _source(generated):
            return (
                SERIALIZATION_MISSING_SOURCE_AT_GENERATION,
                "generation",
                "Generated candidate row lacks source metadata.",
            )
        if not _pairing(generated):
            return (
                SERIALIZATION_MISSING_PAIRING_METHOD_AT_GENERATION,
                "generation",
                "Generated candidate row lacks pairing method metadata.",
            )
    elif audit or evaluator:
        return (
            SERIALIZATION_LOST_IN_CANDIDATE_ADAPTER,
            "candidate_adapter",
            "Audit/evaluator metadata exists but generated candidate detail was not serialized.",
        )

    if generated and not resolver:
        return (
            SERIALIZATION_LOST_IN_CANDIDATE_ADAPTER,
            "candidate_adapter",
            "Generated candidate detail did not roundtrip into resolver trace rows.",
        )
    if resolver and _bool(resolver.get("dedupe_detail_missing")):
        return (
            SERIALIZATION_LOST_IN_DEDUPE,
            "dedupe",
            "Resolver trace indicates detail was lost during dedupe.",
        )
    if resolver and not _detail_complete(resolver):
        return (
            SERIALIZATION_LOST_IN_RESOLVER_TRACE,
            "resolver_trace",
            "Resolver trace row lacks source/page/line/pairing detail that was present earlier.",
        )
    if resolver and not audit:
        return (
            SERIALIZATION_LOST_IN_SHADOW_AUDIT,
            "shadow_audit",
            "Resolver detail did not roundtrip into shadow audit rows.",
        )
    if audit and not _detail_complete(audit):
        return (
            SERIALIZATION_LOST_IN_SHADOW_AUDIT,
            "shadow_audit",
            "Shadow audit row lacks source/page/line/pairing detail that was present earlier.",
        )
    if audit and not evaluator:
        return (
            SERIALIZATION_LOST_IN_GOLD_EVALUATOR,
            "gold_evaluator",
            "Audit detail did not roundtrip into evaluator rows.",
        )
    if evaluator and not _detail_complete(evaluator):
        return (
            SERIALIZATION_LOST_IN_GOLD_EVALUATOR,
            "gold_evaluator",
            "Evaluator row lacks source/page/line/pairing detail that was present earlier.",
        )
    if _detail_complete(first):
        return (
            SERIALIZATION_COMPLETE,
            "none",
            "Candidate id, source, page/line, and pairing method roundtripped through local diagnostic surfaces.",
        )
    return (
        SERIALIZATION_UNKNOWN,
        "unknown",
        "Serialization surface did not expose enough detail to classify the loss stage.",
    )


def build_load_source_line_serialization_sidecar(
    *,
    generated_rows: list[dict[str, Any]] | None = None,
    resolver_rows: list[dict[str, Any]] | None = None,
    audit_rows: list[dict[str, Any]] | None = None,
    evaluator_rows: list[dict[str, Any]] | None = None,
    include_private_values: bool = False,
) -> dict[str, Any]:
    generated = _rows_by_doc_and_candidate(generated_rows or [], "generated")
    resolver = _rows_by_doc_and_candidate(resolver_rows or [], "resolver")
    audit = _rows_by_doc_and_candidate(audit_rows or [], "audit")
    evaluator_by_doc = _evaluator_by_doc(evaluator_rows or [])
    keys_by_doc = _candidate_keys(generated, resolver, audit)
    for doc_id, evaluator in evaluator_by_doc.items():
        candidate_id = evaluator.get("_candidate_id") or "evaluator_selected"
        keys_by_doc[doc_id].add(candidate_id)

    if not keys_by_doc:
        keys_by_doc["detail_input_unavailable"].add("candidate_missing")

    sidecar_rows: list[dict[str, Any]] = []
    for doc_id in sorted(keys_by_doc):
        evaluator = evaluator_by_doc.get(doc_id)
        for candidate_key in sorted(keys_by_doc[doc_id]):
            generated_row = generated.get(doc_id, {}).get(candidate_key)
            resolver_row = resolver.get(doc_id, {}).get(candidate_key)
            audit_row = audit.get(doc_id, {}).get(candidate_key)
            evaluator_row = evaluator if evaluator and (
                evaluator.get("_candidate_id") == candidate_key
                or candidate_key == "evaluator_selected"
                or evaluator.get("_selected")
            ) else None
            bucket, stage, reason = _loss_bucket(generated_row, resolver_row, audit_row, evaluator_row)
            adapter_roundtrip = summarize_adapter_provenance_roundtrip(
                generated_row,
                resolver_row,
            )
            source = _pick(generated_row, resolver_row, audit_row, evaluator_row, key="_source")
            parser_name = _pick(generated_row, resolver_row, audit_row, evaluator_row, key="_parser_name")
            value = _pick(generated_row, resolver_row, audit_row, evaluator_row, key="_candidate_value")
            row = {
                "document_id": doc_id,
                "field": LOAD_FIELD,
                "candidate_id": _pick(
                    generated_row,
                    resolver_row,
                    audit_row,
                    evaluator_row,
                    key="_candidate_id",
                ) or candidate_key,
                "source": source,
                "source_family": _source_family(source, parser_name),
                "parser_name": parser_name,
                "pairing_method": _pick(
                    generated_row,
                    resolver_row,
                    audit_row,
                    evaluator_row,
                    key="_pairing_method",
                ),
                "page_number": _pick(
                    generated_row,
                    resolver_row,
                    audit_row,
                    evaluator_row,
                    key="_page_number",
                ),
                "line_index": _pick(
                    generated_row,
                    resolver_row,
                    audit_row,
                    evaluator_row,
                    key="_line_index",
                ),
                "bbox_available": any(
                    _bool((item or {}).get("bbox") or (item or {}).get("bbox_available"))
                    for item in (generated_row, resolver_row, audit_row, evaluator_row)
                ),
                "selected": any(
                    _bool((item or {}).get("_selected"))
                    for item in (generated_row, resolver_row, audit_row, evaluator_row)
                ),
                "candidate_rank": _pick(
                    generated_row,
                    resolver_row,
                    audit_row,
                    evaluator_row,
                    key="candidate_rank",
                ) or _pick(generated_row, resolver_row, audit_row, evaluator_row, key="rank"),
                "resolver_seen": resolver_row is not None,
                "resolver_eligible": _bool((resolver_row or {}).get("resolver_eligible", True))
                if resolver_row
                else False,
                "resolver_selected": _bool((resolver_row or {}).get("_selected")),
                "audit_serialized": audit_row is not None,
                "evaluator_serialized": evaluator_row is not None,
                "serialization_loss_bucket": bucket,
                "detail_loss_bucket": DETAIL_BUCKET_BY_SERIALIZATION_BUCKET[bucket],
                "detail_loss_stage": stage,
                "detail_loss_reason": reason,
                **adapter_roundtrip,
                "private_values_redacted": not include_private_values,
                "value_preview": _value_for_output(value, include_private_values),
            }
            sidecar_rows.append(row)

    bucket_counts = Counter(row["serialization_loss_bucket"] for row in sidecar_rows)
    adapter_status_counts = Counter(row["adapter_roundtrip_status"] for row in sidecar_rows)
    adapter_lost_count = sum(
        adapter_status_counts[status]
        for status in (
            LOAD_ADAPTER_ROUNDTRIP_LOST_CANDIDATE_ID,
            LOAD_ADAPTER_ROUNDTRIP_LOST_PAGE_LINE,
            LOAD_ADAPTER_ROUNDTRIP_LOST_SOURCE,
            LOAD_ADAPTER_ROUNDTRIP_LOST_PAIRING_METHOD,
        )
    )
    adapter_preserved_count = (
        adapter_status_counts[LOAD_ADAPTER_ROUNDTRIP_COMPLETE]
        + adapter_status_counts[LOAD_ADAPTER_ROUNDTRIP_PRESERVED_PARTIAL_DETAIL]
    )
    summary = {
        "schema_version": LOAD_SOURCE_LINE_SERIALIZATION_SCHEMA_VERSION,
        "document_count": len({row["document_id"] for row in sidecar_rows}),
        "candidate_serialization_row_count": len(sidecar_rows),
        "complete_detail_serialized_count": bucket_counts[SERIALIZATION_COMPLETE],
        "missing_at_generation_count": (
            bucket_counts[SERIALIZATION_MISSING_CANDIDATE_ID_AT_GENERATION]
            + bucket_counts[SERIALIZATION_MISSING_PAGE_LINE_AT_GENERATION]
            + bucket_counts[SERIALIZATION_MISSING_SOURCE_AT_GENERATION]
            + bucket_counts[SERIALIZATION_MISSING_PAIRING_METHOD_AT_GENERATION]
        ),
        "lost_after_generation_count": (
            bucket_counts[SERIALIZATION_LOST_IN_CANDIDATE_ADAPTER]
            + bucket_counts[SERIALIZATION_LOST_IN_DEDUPE]
            + bucket_counts[SERIALIZATION_LOST_IN_RESOLVER_TRACE]
            + bucket_counts[SERIALIZATION_LOST_IN_SHADOW_AUDIT]
            + bucket_counts[SERIALIZATION_LOST_IN_GOLD_EVALUATOR]
            + bucket_counts[SERIALIZATION_LOST_IN_DETAIL_INVENTORY_READER]
        ),
        "serialization_loss_bucket_counts": dict(sorted(bucket_counts.items())),
        "adapter_roundtrip_status_counts": dict(sorted(adapter_status_counts.items())),
        "adapter_detail_preserved_count": adapter_preserved_count,
        "adapter_detail_lost_count": adapter_lost_count,
        "private_values_included": include_private_values,
        "values_redacted": not include_private_values,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }
    return {
        "schema_version": LOAD_SOURCE_LINE_SERIALIZATION_SCHEMA_VERSION,
        "summary": summary,
        "serialization_rows": sidecar_rows,
    }
