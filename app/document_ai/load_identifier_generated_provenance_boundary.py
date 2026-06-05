"""Local-only generated load provenance boundary comparison helpers.

These helpers compare already-serialized generated, adapter, dedupe, resolver,
audit, evaluator, and sidecar rows. They do not generate candidates, infer
missing metadata, run resolution, or change selected load-number behavior.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


LOAD_GENERATED_PROVENANCE_BOUNDARY_SCHEMA_VERSION = (
    "ratecon_load_generated_provenance_boundary_v1"
)
LOAD_FIELD = "load_number"

BOUNDARY_GENERATION_TO_ADAPTER_LOSS = "boundary_generation_to_adapter_loss"
BOUNDARY_ADAPTER_TO_DEDUPE_LOSS = "boundary_adapter_to_dedupe_loss"
BOUNDARY_DEDUPE_TO_RESOLVER_LOSS = "boundary_dedupe_to_resolver_loss"
BOUNDARY_RESOLVER_TO_AUDIT_LOSS = "boundary_resolver_to_audit_loss"
BOUNDARY_AUDIT_TO_EVALUATOR_LOSS = "boundary_audit_to_evaluator_loss"
BOUNDARY_EVALUATOR_TO_SIDECAR_LOSS = "boundary_evaluator_to_sidecar_loss"
BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP = "boundary_no_loss_complete_roundtrip"
BOUNDARY_INPUT_DETAIL_MISSING = "boundary_input_detail_missing"
BOUNDARY_CANDIDATE_NOT_COMPARABLE = "boundary_candidate_not_comparable"
BOUNDARY_STAGE_UNAVAILABLE = "boundary_stage_unavailable"
BOUNDARY_PRIVATE_VALUES_NOT_REQUESTED = "boundary_private_values_not_requested"
BOUNDARY_UNKNOWN = "boundary_unknown"

BOUNDARY_STATUSES = (
    BOUNDARY_GENERATION_TO_ADAPTER_LOSS,
    BOUNDARY_ADAPTER_TO_DEDUPE_LOSS,
    BOUNDARY_DEDUPE_TO_RESOLVER_LOSS,
    BOUNDARY_RESOLVER_TO_AUDIT_LOSS,
    BOUNDARY_AUDIT_TO_EVALUATOR_LOSS,
    BOUNDARY_EVALUATOR_TO_SIDECAR_LOSS,
    BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP,
    BOUNDARY_INPUT_DETAIL_MISSING,
    BOUNDARY_CANDIDATE_NOT_COMPARABLE,
    BOUNDARY_STAGE_UNAVAILABLE,
    BOUNDARY_PRIVATE_VALUES_NOT_REQUESTED,
    BOUNDARY_UNKNOWN,
)

STAGE_GENERATED = "generated"
STAGE_ADAPTER_INPUT = "adapter_input"
STAGE_ADAPTER_OUTPUT = "adapter_output"
STAGE_DEDUPE_INPUT = "dedupe_input"
STAGE_DEDUPE_OUTPUT = "dedupe_output"
STAGE_RESOLVER = "resolver"
STAGE_AUDIT = "audit"
STAGE_EVALUATOR = "evaluator"
STAGE_SIDECAR = "sidecar"

BOUNDARY_ROW_FIELDNAMES = [
    "document_id",
    "candidate_id",
    "stage_from",
    "stage_to",
    "field_name",
    "input_available",
    "output_available",
    "preserved",
    "loss_boundary",
    "loss_reason",
    "detail_available_at_generation",
    "detail_available_at_adapter",
    "detail_available_at_dedupe",
    "detail_available_at_resolver",
    "detail_available_at_audit",
    "detail_available_at_evaluator",
    "detail_available_at_sidecar",
    "private_values_redacted",
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


def _document_id(row: dict[str, Any] | None) -> str:
    row = row or {}
    return _first_text(
        row.get("document_id"),
        row.get("measurement_alias"),
        row.get("document_alias"),
        row.get("case_id"),
        row.get("file_hash"),
    )


def _source(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(row.get("source"), row.get("selected_source"), metadata.get("source"))


def _page_or_line(row: dict[str, Any] | None) -> str:
    row = row or {}
    metadata = _metadata(row)
    return _first_text(
        row.get("page_number"),
        row.get("page"),
        row.get("line_index"),
        row.get("line_number"),
        row.get("source_line_index"),
        metadata.get("page_number"),
        metadata.get("page"),
        metadata.get("line_index"),
        metadata.get("line_number"),
        metadata.get("source_line_index"),
    )


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


def _detail_available(row: dict[str, Any] | None) -> bool:
    return bool(_candidate_id(row) and _source(row) and _page_or_line(row) and _pairing(row))


def _normalized_stage(stage: Any) -> str:
    text = _text(stage).lower()
    if text == "serialization":
        return STAGE_SIDECAR
    return text


def _normalize_row(row: dict[str, Any], default_stage: str = "") -> dict[str, Any]:
    stage = _normalized_stage(row.get("stage") or default_stage)
    return {
        "document_id": _document_id(row),
        "candidate_id": _candidate_id(row),
        "field_name": _field(row) or LOAD_FIELD,
        "stage": stage,
        "detail_available": _detail_available(row),
        "private_values_redacted": not _bool(row.get("private_values_included")),
    }


def normalize_boundary_stage_rows(
    rows: list[dict[str, Any]] | None,
    *,
    default_stage: str = "",
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict) or not _field_matches(row):
            continue
        normalized.append(_normalize_row(row, default_stage=default_stage))
    return normalized


def _group_by_candidate(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, list[dict[str, Any]]]]:
    grouped: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        key = (row.get("document_id", ""), row.get("candidate_id", ""))
        grouped[key][row.get("stage", "")].append(row)
    return grouped


def _has(stage_rows: dict[str, list[dict[str, Any]]], *stages: str) -> bool:
    return any(stage_rows.get(stage) for stage in stages)


def _has_detail(stage_rows: dict[str, list[dict[str, Any]]], *stages: str) -> bool:
    return any(
        bool(row.get("detail_available"))
        for stage in stages
        for row in stage_rows.get(stage, [])
    )


def _boundary_for_candidate(
    document_id: str,
    candidate_id: str,
    stage_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    if not candidate_id:
        status = BOUNDARY_CANDIDATE_NOT_COMPARABLE
        stage_from = "candidate"
        stage_to = "candidate_id"
        reason = "Candidate id is missing, so stage rows cannot be compared without fabricating identity."
    elif not _has(stage_rows, STAGE_GENERATED):
        status = BOUNDARY_STAGE_UNAVAILABLE
        stage_from = "generated"
        stage_to = "adapter"
        reason = "Generated stage row is unavailable for this candidate."
    elif not _has_detail(stage_rows, STAGE_GENERATED):
        status = BOUNDARY_INPUT_DETAIL_MISSING
        stage_from = "generated"
        stage_to = "adapter"
        reason = "Generated row is present but lacks candidate id, source, page/line, or pairing detail."
    elif not _has(stage_rows, STAGE_ADAPTER_INPUT, STAGE_ADAPTER_OUTPUT):
        status = BOUNDARY_GENERATION_TO_ADAPTER_LOSS
        stage_from = "generated"
        stage_to = "adapter"
        reason = "Generated detail is present but no adapter stage row is serialized."
    elif _has(stage_rows, STAGE_ADAPTER_OUTPUT) and not _has(
        stage_rows, STAGE_DEDUPE_INPUT, STAGE_DEDUPE_OUTPUT
    ):
        status = BOUNDARY_ADAPTER_TO_DEDUPE_LOSS
        stage_from = "adapter"
        stage_to = "dedupe"
        reason = "Adapter detail is present but no dedupe stage row is serialized."
    elif _has(stage_rows, STAGE_DEDUPE_OUTPUT) and not _has(stage_rows, STAGE_RESOLVER):
        status = BOUNDARY_DEDUPE_TO_RESOLVER_LOSS
        stage_from = "dedupe"
        stage_to = "resolver"
        reason = "Dedupe detail is present but no resolver stage row is serialized."
    elif _has(stage_rows, STAGE_RESOLVER) and not _has(stage_rows, STAGE_AUDIT):
        status = BOUNDARY_RESOLVER_TO_AUDIT_LOSS
        stage_from = "resolver"
        stage_to = "audit"
        reason = "Resolver detail is present but no audit stage row is serialized."
    elif _has(stage_rows, STAGE_AUDIT) and not _has(stage_rows, STAGE_EVALUATOR):
        status = BOUNDARY_AUDIT_TO_EVALUATOR_LOSS
        stage_from = "audit"
        stage_to = "evaluator"
        reason = "Audit detail is present but no evaluator stage row is serialized."
    elif _has(stage_rows, STAGE_EVALUATOR) and not _has(stage_rows, STAGE_SIDECAR):
        status = BOUNDARY_EVALUATOR_TO_SIDECAR_LOSS
        stage_from = "evaluator"
        stage_to = "sidecar"
        reason = "Evaluator detail is present but no final sidecar stage row is serialized."
    elif all(
        _has(stage_rows, stage)
        for stage in [
            STAGE_GENERATED,
            STAGE_ADAPTER_OUTPUT,
            STAGE_DEDUPE_OUTPUT,
            STAGE_RESOLVER,
            STAGE_AUDIT,
            STAGE_EVALUATOR,
            STAGE_SIDECAR,
        ]
    ):
        status = BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP
        stage_from = "generated"
        stage_to = "sidecar"
        reason = "Generated load provenance detail is visible across all expected diagnostic stages."
    else:
        status = BOUNDARY_UNKNOWN
        stage_from = "unknown"
        stage_to = "unknown"
        reason = "Stage rows are present but do not match a known boundary classification."
    return {
        "document_id": document_id,
        "candidate_id": candidate_id,
        "stage_from": stage_from,
        "stage_to": stage_to,
        "field_name": LOAD_FIELD,
        "input_available": _has(stage_rows, STAGE_GENERATED),
        "output_available": status == BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP,
        "preserved": status == BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP,
        "loss_boundary": status,
        "loss_reason": reason,
        "detail_available_at_generation": _has_detail(stage_rows, STAGE_GENERATED),
        "detail_available_at_adapter": _has_detail(
            stage_rows,
            STAGE_ADAPTER_INPUT,
            STAGE_ADAPTER_OUTPUT,
        ),
        "detail_available_at_dedupe": _has_detail(
            stage_rows,
            STAGE_DEDUPE_INPUT,
            STAGE_DEDUPE_OUTPUT,
        ),
        "detail_available_at_resolver": _has_detail(stage_rows, STAGE_RESOLVER),
        "detail_available_at_audit": _has_detail(stage_rows, STAGE_AUDIT),
        "detail_available_at_evaluator": _has_detail(stage_rows, STAGE_EVALUATOR),
        "detail_available_at_sidecar": _has_detail(stage_rows, STAGE_SIDECAR),
        "private_values_redacted": True,
    }


def compare_generated_provenance_boundaries(
    stage_rows: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Compare stage rows and identify the first provenance loss boundary."""

    normalized = normalize_boundary_stage_rows(stage_rows or [])
    grouped = _group_by_candidate(normalized)
    if not grouped:
        grouped[("", "")] = defaultdict(list)
    boundary_rows = [
        _boundary_for_candidate(document_id, candidate_id, stages)
        for (document_id, candidate_id), stages in sorted(grouped.items())
    ]
    counts = Counter(row["loss_boundary"] for row in boundary_rows)
    complete_count = counts[BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP]
    first_loss_boundary = BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP
    for status in BOUNDARY_STATUSES:
        if status != BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP and counts.get(status):
            first_loss_boundary = status
            break
    summary = {
        "schema_version": LOAD_GENERATED_PROVENANCE_BOUNDARY_SCHEMA_VERSION,
        "candidate_count": len(boundary_rows),
        "complete_roundtrip_count": complete_count,
        "first_loss_boundary": first_loss_boundary,
        "loss_boundary_counts": dict(sorted(counts.items())),
        "private_values_included": False,
        "private_values_redacted": True,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
    }
    return {
        "schema_version": LOAD_GENERATED_PROVENANCE_BOUNDARY_SCHEMA_VERSION,
        "summary": summary,
        "boundary_rows": boundary_rows,
        "loss_by_stage_rows": [
            {"loss_boundary": status, "count": count}
            for status, count in sorted(counts.items())
        ],
        "review_rows": [
            {
                "document_id": row["document_id"],
                "candidate_id": row["candidate_id"],
                "loss_boundary": row["loss_boundary"],
                "recommended_action": "repair_exact_boundary_only",
                "behavior_change_allowed": False,
            }
            for row in boundary_rows
            if row["loss_boundary"] != BOUNDARY_NO_LOSS_COMPLETE_ROUNDTRIP
        ],
    }
