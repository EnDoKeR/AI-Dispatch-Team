"""Summarize multiple local-only RateCon hybrid benchmark batches.

This script aggregates completed manual hybrid benchmark output folders and can
write a remaining-document plan. It does not call AI models, cloud services,
OCR, local model runtimes, PDF readers, or modify gold/template files.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.ratecon_gold_labels import (  # noqa: E402
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
    STATUS_EXACT,
    STATUS_MISSING,
    STATUS_NORMALIZED_MATCH,
    STATUS_UNLABELED,
    load_gold_labels,
)
from app.document_ai.ratecon_hybrid_contract import is_under_local_outputs  # noqa: E402
from scripts.create_ratecon_hybrid_private_manual_pilot import infer_document_pattern  # noqa: E402


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_multi_batch_summary")
AGGREGATE_STATUSES = {
    "manual_hybrid_workflow_validated",
    "manual_hybrid_validated_with_review_items",
    "manual_hybrid_workflow_validated_full_corpus_with_review_items",
    "manual_hybrid_failed_schema",
    "manual_hybrid_failed_safety",
    "manual_hybrid_failed_accuracy",
    "manual_hybrid_inconclusive",
}
UNCERTAIN_STOP_TIERS = {
    "matches_uncertain_gold_review_required",
    "partial_match_uncertain_gold_review_required",
    "gold_uncertain_review_required",
}
STOP_TIERS = (
    "exact_complete",
    "dispatch_usable",
    "useful_partial",
    "matches_uncertain_gold_review_required",
    "partial_match_uncertain_gold_review_required",
    "gold_uncertain_review_required",
    "not_applicable",
    "unsafe_wrong",
    "missing_review_required",
)
NOT_APPLICABLE_NON_RC_STATUS = "not_applicable_non_rc"
SUCCESS_FIELDNAMES = ["criterion", "value", "passes", "failure_status", "notes"]
COVERAGE_FIELDNAMES = [
    "batch_index",
    "batch_name",
    "document_id",
    "file_name_or_label",
    "document_type",
    "included_in_aggregate",
    "duplicate_of",
    "schema_valid",
    "document_type_status",
    "gold_matched",
]
FIELD_METRIC_FIELDNAMES = ["field", "metric", "value"]
REVIEW_ITEM_FIELDNAMES = [
    "batch_index",
    "batch_name",
    "document_id",
    "file_name_or_label",
    "document_type",
    "field",
    "stop_role",
    "stop_index",
    "status",
    "review_reason",
    "evidence_status",
    "confidence",
    "auto_accept_violation",
    "missing_evidence",
    "recommended_action",
]
REMAINING_PLAN_FIELDNAMES = [
    "document_id",
    "file_name",
    "suggested_pattern",
    "difficulty",
    "reason_selected",
    "expected_fields_to_fill",
    "notes_for_reviewer",
    "already_completed",
    "duplicate_group",
    "exclusion_reason",
    "no_action",
]
CLOSEOUT_SUCCESS_FIELDNAMES = ["criterion", "value", "passes", "notes"]
CLOSEOUT_VERDICT = "manual_hybrid_workflow_validated_full_corpus_with_review_items"


class HybridMultiBatchSummaryError(ValueError):
    """Raised when multi-batch summary generation would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int:
    try:
        if value in [None, ""]:
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _read_json(path: Path) -> dict[str, Any]:
    resolved = _repo_relative(path)
    if not resolved.exists():
        return {}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, Any]]:
    resolved = _repo_relative(path)
    if not resolved.exists():
        return []
    with resolved.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _identity_keys(record: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for key in ("document_id", "file_name", "file_name_or_label", "file_hash", "file_hash_prefix"):
        value = _text(record.get(key))
        if value:
            keys.add(value)
            if key in {"file_hash", "file_hash_prefix"}:
                keys.add(value[:16])
    return keys


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_audit(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    resolved = _repo_relative(path)
    if not resolved.exists():
        return []
    rows: list[dict[str, Any]] = []
    with resolved.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _metric(summary: dict[str, Any], *keys: str) -> int:
    current: Any = summary
    for key in keys:
        if not isinstance(current, dict):
            return 0
        current = current.get(key)
    return _safe_int(current)


def _is_correct_scalar_status(status: str) -> bool:
    return status in {STATUS_EXACT, STATUS_NORMALIZED_MATCH, "exact", "normalized_match"}


def _is_missing_scalar_status(status: str) -> bool:
    return status in {STATUS_MISSING, STATUS_UNLABELED, "missing", "unlabeled"}


def _is_non_rc_not_applicable_row(row: dict[str, Any]) -> bool:
    status = _text(row.get("status"))
    tier = _text(row.get("tier"))
    issues = _text(row.get("issues")).lower()
    return (
        status in {NOT_APPLICABLE_NON_RC_STATUS, "not_applicable"}
        or tier == "not_applicable"
        or "non_rc_filtered" in issues
    )


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"true", "1", "yes", "y"}


def _empty_scalar_metrics() -> dict[str, dict[str, int]]:
    return {
        FIELD_LOAD_NUMBER: {"correct": 0, "wrong": 0, "missing": 0, "not_applicable_non_rc": 0, "high_confidence_wrong": 0},
        FIELD_TOTAL_CARRIER_RATE: {"correct": 0, "wrong": 0, "missing": 0, "not_applicable_non_rc": 0, "high_confidence_wrong": 0},
    }


def _empty_stop_metrics() -> dict[str, dict[str, int]]:
    return {
        FIELD_PICKUP_STOPS: {tier: 0 for tier in STOP_TIERS},
        FIELD_DELIVERY_STOPS: {tier: 0 for tier in STOP_TIERS},
    }


def _batch_name(path: Path, index: int) -> str:
    return _text(path.name) or f"batch_{index}"


def _read_batch(path: Path, index: int) -> dict[str, Any]:
    resolved = _repo_relative(path)
    return {
        "index": index,
        "path": resolved,
        "name": _batch_name(resolved, index),
        "summary": _read_json(resolved / "hybrid_benchmark_summary.json"),
        "documents": _read_csv(resolved / "hybrid_document_metrics.csv"),
        "fields": _read_csv(resolved / "hybrid_field_metrics.csv"),
        "review_items": _read_csv(resolved / "hybrid_review_items.csv"),
        "schema_errors": _read_csv(resolved / "hybrid_schema_errors.csv"),
    }


def _safe_or_private(value: Any, *, include_private_values_local_only: bool) -> str:
    if include_private_values_local_only:
        return _text(value)
    return "<redacted>" if _text(value) else ""


def _completed_documents(
    batches: list[dict[str, Any]],
    *,
    include_private_values_local_only: bool,
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    seen: dict[str, dict[str, Any]] = {}
    completed_identity_keys: set[str] = set()
    coverage_rows: list[dict[str, Any]] = []
    for batch in batches:
        for row in batch["documents"]:
            document_id = _text(row.get("document_id"))
            if not document_id:
                continue
            duplicate_of = seen.get(document_id)
            included = duplicate_of is None
            if included:
                seen[document_id] = row
                completed_identity_keys.update(_identity_keys(row))
            coverage_rows.append(
                {
                    "batch_index": batch["index"],
                    "batch_name": batch["name"],
                    "document_id": document_id,
                    "file_name_or_label": _safe_or_private(
                        row.get("file_name_or_label"),
                        include_private_values_local_only=include_private_values_local_only,
                    ),
                    "document_type": _text(row.get("document_type")),
                    "included_in_aggregate": "true" if included else "false",
                    "duplicate_of": "" if included else document_id,
                    "schema_valid": _text(row.get("schema_valid")),
                    "document_type_status": _text(row.get("document_type_status")),
                    "gold_matched": _text(row.get("gold_matched")),
                }
            )
    return coverage_rows, set(seen), completed_identity_keys


def _document_type_counts(coverage_rows: list[dict[str, Any]]) -> dict[str, int]:
    rate_confirmation_count = 0
    non_rc_count = 0
    unknown_count = 0
    for row in coverage_rows:
        if row.get("included_in_aggregate") != "true":
            continue
        document_type = _text(row.get("document_type"))
        document_type_status = _text(row.get("document_type_status"))
        if document_type_status == "non_rc_filtered_correct" or document_type in {
            "bol_pod",
            "non_rate_confirmation",
            "bill_of_lading_or_delivery_receipt",
        }:
            non_rc_count += 1
        elif document_type == "rate_confirmation":
            rate_confirmation_count += 1
        else:
            unknown_count += 1
    return {
        "rate_confirmation_document_count": rate_confirmation_count,
        "non_rc_document_count": non_rc_count,
        "unknown_document_count": unknown_count,
    }


def _aggregate_metrics(
    batches: list[dict[str, Any]],
    completed_document_ids: set[str],
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]], list[dict[str, Any]], Counter]:
    scalar_metrics = _empty_scalar_metrics()
    stop_metrics = _empty_stop_metrics()
    output_field_rows: list[dict[str, Any]] = []
    review_policy = Counter()
    processed_by_field: set[tuple[str, str, str]] = set()

    for batch in batches:
        for row in batch["fields"]:
            document_id = _text(row.get("document_id"))
            field = _text(row.get("field"))
            if document_id not in completed_document_ids or not field:
                continue
            stop_index = _text(row.get("stop_index"))
            dedupe_key = (document_id, field, stop_index)
            if dedupe_key in processed_by_field:
                continue
            processed_by_field.add(dedupe_key)
            output_field_rows.append({**row, "batch_index": batch["index"], "batch_name": batch["name"]})
            if field in scalar_metrics:
                status = _text(row.get("status"))
                if _is_non_rc_not_applicable_row(row):
                    scalar_metrics[field]["not_applicable_non_rc"] += 1
                elif _is_correct_scalar_status(status):
                    scalar_metrics[field]["correct"] += 1
                elif _is_missing_scalar_status(status):
                    scalar_metrics[field]["missing"] += 1
                else:
                    scalar_metrics[field]["wrong"] += 1
                continue
            if field in stop_metrics:
                tier = _text(row.get("tier")) or "missing_review_required"
                if tier not in stop_metrics[field]:
                    stop_metrics[field][tier] = 0
                stop_metrics[field][tier] += 1
                if _boolish(row.get("auto_accept")):
                    review_policy["stop_auto_accept_violation"] += 1
                if _boolish(row.get("missing_evidence")):
                    review_policy["missing_evidence"] += 1

    return scalar_metrics, stop_metrics, output_field_rows, review_policy


def _aggregate_summary_counts(
    batches: list[dict[str, Any]],
) -> dict[str, int]:
    counts = Counter()
    for batch in batches:
        summary = batch["summary"]
        counts["schema_errors"] += _metric(summary, "schema_error_count") or _metric(summary, "one_screen_summary", "schema_errors")
        counts["unfilled_manual_templates"] += _metric(summary, "unfilled_manual_template_count") or _metric(
            summary, "one_screen_summary", "unfilled_manual_templates"
        )
        counts["missing_evidence"] += _metric(summary, "one_screen_summary", "missing_evidence")
        counts["stop_auto_accept_violations"] += _metric(summary, "one_screen_summary", "stop_auto_accept_violations")
        counts["unsafe_wrong_stops"] += _metric(summary, "one_screen_summary", "unsafe_wrong_stops")
        counts["gold_uncertain_review_required"] += _metric(summary, "one_screen_summary", "gold_uncertain_review_required") or _metric(
            summary, "gold_uncertain_metrics", "review_required"
        )
        counts["error_cases"] += _metric(summary, "one_screen_summary", "error_cases")
    return dict(counts)


def _aggregate_review_items(
    batches: list[dict[str, Any]],
    completed_document_ids: set[str],
    *,
    include_private_values_local_only: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for batch in batches:
        for row in batch["review_items"]:
            document_id = _text(row.get("document_id"))
            if document_id not in completed_document_ids:
                continue
            key = (document_id, _text(row.get("field")), _text(row.get("stop_index")), _text(row.get("status")))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    **row,
                    "file_name_or_label": _safe_or_private(
                        row.get("file_name_or_label"),
                        include_private_values_local_only=include_private_values_local_only,
                    ),
                    "batch_index": batch["index"],
                    "batch_name": batch["name"],
                }
            )
    return rows


def classify_multi_batch_status(summary: dict[str, Any]) -> str:
    if not summary or summary.get("aggregate_document_count", 0) == 0:
        return "manual_hybrid_inconclusive"
    if summary.get("schema_error_count", 0):
        return "manual_hybrid_failed_schema"
    if summary.get("stop_auto_accept_violation_count", 0) or summary.get("missing_evidence_count", 0):
        return "manual_hybrid_failed_safety"
    scalar = summary.get("field_metrics", {})
    scalar_wrong = _metric(scalar, FIELD_LOAD_NUMBER, "wrong") + _metric(scalar, FIELD_TOTAL_CARRIER_RATE, "wrong")
    unsafe_wrong = summary.get("unsafe_wrong_stop_count", 0)
    if scalar_wrong or unsafe_wrong:
        return "manual_hybrid_failed_accuracy"
    if summary.get("gold_uncertain_review_required_count", 0):
        return "manual_hybrid_validated_with_review_items"
    return "manual_hybrid_workflow_validated"


def classify_closeout_verdict(summary: dict[str, Any]) -> str:
    status = classify_multi_batch_status(summary)
    if status not in {"manual_hybrid_workflow_validated", "manual_hybrid_validated_with_review_items"}:
        return status
    if summary.get("remaining_plan_count", 0):
        return "manual_hybrid_inconclusive"
    if summary.get("aggregate_document_count", 0) == 0:
        return "manual_hybrid_inconclusive"
    return CLOSEOUT_VERDICT


def _success_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    scalar = summary.get("field_metrics", {})
    scalar_wrong = _metric(scalar, FIELD_LOAD_NUMBER, "wrong") + _metric(scalar, FIELD_TOTAL_CARRIER_RATE, "wrong")
    criteria = [
        ("schema_errors", summary.get("schema_error_count", 0), "manual_hybrid_failed_schema", "Schema errors block aggregate validation."),
        (
            "auto_accept_violations",
            summary.get("stop_auto_accept_violation_count", 0),
            "manual_hybrid_failed_safety",
            "Stops must remain auto_accept=false.",
        ),
        (
            "missing_evidence",
            summary.get("missing_evidence_count", 0),
            "manual_hybrid_failed_safety",
            "Every filled value needs evidence.",
        ),
        (
            "unsafe_wrong_stops",
            summary.get("unsafe_wrong_stop_count", 0),
            "manual_hybrid_failed_accuracy",
            "Unsafe wrong stops are aggregate failures.",
        ),
        (
            "load_or_rate_wrong",
            scalar_wrong,
            "manual_hybrid_failed_accuracy",
            "Only true wrong scalar fields fail accuracy; non-RC not-applicable scalar rows are no-action.",
        ),
        (
            "uncertain_gold_review_required",
            summary.get("gold_uncertain_review_required_count", 0),
            "",
            "Uncertain gold review items are expected review work, not failures.",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for criterion, value, failure_status, notes in criteria:
        rows.append(
            {
                "criterion": criterion,
                "value": value,
                "passes": "true" if criterion == "uncertain_gold_review_required" or not value else "false",
                "failure_status": failure_status if value and criterion != "uncertain_gold_review_required" else "",
                "notes": notes,
            }
        )
    return rows


def _closeout_success_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    scalar = summary.get("field_metrics", {})
    scalar_wrong = _metric(scalar, FIELD_LOAD_NUMBER, "wrong") + _metric(scalar, FIELD_TOTAL_CARRIER_RATE, "wrong")
    rows = [
        ("schema_errors", summary.get("schema_error_count", 0), "No schema errors are allowed."),
        ("missing_evidence", summary.get("missing_evidence_count", 0), "Every filled value must retain evidence."),
        ("auto_accept_violations", summary.get("stop_auto_accept_violation_count", 0), "Stops must remain auto_accept=false."),
        ("unsafe_wrong_stops", summary.get("unsafe_wrong_stop_count", 0), "Unsafe wrong stop drafts fail closeout."),
        ("scalar_true_wrong", scalar_wrong, "True load/rate wrong rows fail closeout."),
        ("remaining_actionable_docs", summary.get("remaining_plan_count", 0), "Full-corpus closeout requires no actionable remaining docs."),
        (
            "uncertain_gold_review_items",
            summary.get("gold_uncertain_review_required_count", 0),
            "Uncertain-gold items remain review-required and are not failures.",
        ),
    ]
    return [
        {
            "criterion": criterion,
            "value": value,
            "passes": "true" if criterion == "uncertain_gold_review_items" or not value else "false",
            "notes": notes,
        }
        for criterion, value, notes in rows
    ]


def _field_metric_rows(scalar_metrics: dict[str, dict[str, int]], stop_metrics: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field, metrics in scalar_metrics.items():
        for metric, value in metrics.items():
            rows.append({"field": field, "metric": metric, "value": value})
    for field, metrics in stop_metrics.items():
        for metric, value in metrics.items():
            rows.append({"field": field, "metric": metric, "value": value})
    return rows


def _stop_uncertain_count(metrics: dict[str, int]) -> int:
    return sum(metrics.get(tier, 0) for tier in UNCERTAIN_STOP_TIERS)


def _record_key(record: dict[str, Any]) -> str:
    return _text(record.get("document_id")) or _text(record.get("file_name")) or _text(record.get("file_hash"))


def _audit_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for record in records:
        for key in ("document_id", "file_name", "file_hash", "file_hash_prefix"):
            value = _text(record.get(key))
            if value and value not in index:
                index[value] = record
    return index


def _match_audit(label: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for key in ("document_id", "file_name", "file_hash"):
        value = _text(label.get(key))
        if value and value in index:
            return index[value]
    return {}


def _gold_document_type(label: dict[str, Any]) -> str:
    gold = label.get("gold", {}) if isinstance(label, dict) else {}
    return _text(gold.get("document_type")) if isinstance(gold, dict) else ""


def _difficulty(pattern: str, document_type: str) -> str:
    lowered = pattern.lower()
    if document_type == "bol_pod" or "non_rc" in lowered:
        return "classification"
    if any(token in lowered for token in ("scanned", "ocr", "pu_so", "unsafe", "ambiguous", "multi")):
        return "hard"
    if any(token in lowered for token in ("compact", "table", "pickup_drop", "structured")):
        return "medium"
    return "unknown"


def _reason_selected(pattern: str, difficulty: str) -> str:
    if difficulty == "hard":
        return "include hard scanned/OCR, multi-stop, or ambiguous stop pattern"
    if "compact" in pattern or "table" in pattern:
        return "include clean table or compact-row coverage"
    if "structured" in pattern:
        return "include structured shipper/consignee block coverage"
    if "city" in pattern or "verbal" in pattern:
        return "include city-level-only or verbal-agreement coverage"
    return "continue remaining manual coverage"


def _expected_fields(document_type: str) -> str:
    if document_type == "bol_pod":
        return "document_type"
    return "document_type; load_number; total_carrier_rate; pickup_stops; delivery_stops; evidence"


def _duplicate_group(file_name: str, pattern: str) -> str:
    base = Path(file_name).stem.lower() if file_name else pattern.lower()
    return "".join(char if char.isalnum() else "_" for char in base)[:48]


def build_remaining_plan(
    *,
    completed_document_ids: set[str],
    audit: Path | None,
    gold_dir: Path | None,
    completed_identity_keys: set[str] | None = None,
    max_next_docs: int = 10,
    include_private_values_local_only: bool = False,
) -> list[dict[str, Any]]:
    audit_records = _read_audit(audit)
    labels = load_gold_labels(_repo_relative(gold_dir)) if gold_dir and _repo_relative(gold_dir).exists() else []
    audit_by_key = _audit_index(audit_records)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    completed_keys = completed_identity_keys or set(completed_document_ids)
    if labels and len(completed_document_ids) >= len(labels):
        return []

    for label in labels:
        audit_record = _match_audit(label, audit_by_key)
        document_id = _text(label.get("document_id")) or _text(audit_record.get("document_id"))
        candidate_keys = _identity_keys(label) | _identity_keys(audit_record) | ({document_id} if document_id else set())
        if not document_id or document_id in seen or candidate_keys.intersection(completed_keys):
            continue
        document_type = _gold_document_type(label) or _text(audit_record.get("document_type")) or "unknown"
        if document_type == "bol_pod":
            continue
        pattern = infer_document_pattern(audit_record, label)
        difficulty = _difficulty(pattern, document_type)
        file_name = _text(label.get("file_name")) or _text(audit_record.get("file_name"))
        rows.append(
            {
                "document_id": document_id,
                "file_name": _safe_or_private(
                    file_name,
                    include_private_values_local_only=include_private_values_local_only,
                ),
                "suggested_pattern": pattern,
                "difficulty": difficulty,
                "reason_selected": _reason_selected(pattern, difficulty),
                "expected_fields_to_fill": _expected_fields(document_type),
                "notes_for_reviewer": "keep stops review_required=true and auto_accept=false",
                "already_completed": "false",
                "duplicate_group": _duplicate_group(file_name, pattern),
                "exclusion_reason": "",
                "no_action": "false",
            }
        )
        seen.add(document_id)

    for record in audit_records:
        document_id = _record_key(record)
        candidate_keys = _identity_keys(record) | ({document_id} if document_id else set())
        if not document_id or document_id in seen or candidate_keys.intersection(completed_keys):
            continue
        document_type = _text(record.get("document_type")) or "unknown"
        if document_type == "bol_pod":
            continue
        pattern = infer_document_pattern(record, {})
        difficulty = _difficulty(pattern, document_type)
        file_name = _text(record.get("file_name"))
        rows.append(
            {
                "document_id": document_id,
                "file_name": _safe_or_private(
                    file_name,
                    include_private_values_local_only=include_private_values_local_only,
                ),
                "suggested_pattern": pattern,
                "difficulty": difficulty,
                "reason_selected": _reason_selected(pattern, difficulty),
                "expected_fields_to_fill": _expected_fields(document_type),
                "notes_for_reviewer": "keep stops review_required=true and auto_accept=false",
                "already_completed": "false",
                "duplicate_group": _duplicate_group(file_name, pattern),
                "exclusion_reason": "",
                "no_action": "false",
            }
        )
        seen.add(document_id)

    def sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
        priority = {"hard": 0, "medium": 1, "unknown": 2, "classification": 3}
        return (priority.get(row["difficulty"], 9), row["suggested_pattern"], row["document_id"])

    return sorted(rows, key=sort_key)[:max_next_docs]


def _actionable_remaining_count(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if not _boolish(row.get("already_completed")) and not _boolish(row.get("no_action")) and not _text(row.get("exclusion_reason"))
    )


def summarize_hybrid_batches(
    *,
    benchmark_dirs: list[Path],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    audit: Path | None = None,
    gold_dir: Path | None = None,
    write_remaining_plan: bool = False,
    write_closeout_report: bool = False,
    max_next_docs: int = 10,
    include_private_values_local_only: bool = False,
) -> dict[str, Any]:
    if not benchmark_dirs:
        raise HybridMultiBatchSummaryError("At least one --benchmark-dir is required.")
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise HybridMultiBatchSummaryError("Output directory must be under .local_outputs.")
    if max_next_docs < 1:
        raise HybridMultiBatchSummaryError("--max-next-docs must be at least 1.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)

    batches = [_read_batch(path, index) for index, path in enumerate(benchmark_dirs, start=1)]
    coverage_rows, completed_document_ids, completed_identity_keys = _completed_documents(
        batches,
        include_private_values_local_only=include_private_values_local_only,
    )
    scalar_metrics, stop_metrics, field_rows, review_policy = _aggregate_metrics(batches, completed_document_ids)
    document_type_counts = _document_type_counts(coverage_rows)
    summary_counts = _aggregate_summary_counts(batches)
    review_rows = _aggregate_review_items(
        batches,
        completed_document_ids,
        include_private_values_local_only=include_private_values_local_only,
    )
    remaining_rows = (
        build_remaining_plan(
            completed_document_ids=completed_document_ids,
            audit=audit,
            gold_dir=gold_dir,
            completed_identity_keys=completed_identity_keys,
            max_next_docs=max_next_docs,
            include_private_values_local_only=include_private_values_local_only,
        )
        if write_remaining_plan
        else []
    )

    pickup_uncertain = _stop_uncertain_count(stop_metrics[FIELD_PICKUP_STOPS])
    delivery_uncertain = _stop_uncertain_count(stop_metrics[FIELD_DELIVERY_STOPS])
    unsafe_wrong = stop_metrics[FIELD_PICKUP_STOPS].get("unsafe_wrong", 0) + stop_metrics[FIELD_DELIVERY_STOPS].get("unsafe_wrong", 0)
    summary = {
        "schema_version": "ratecon_hybrid_multi_batch_summary_v1",
        "batch_count": len(batches),
        "aggregate_document_count": len(completed_document_ids),
        "rate_confirmation_document_count": document_type_counts["rate_confirmation_document_count"],
        "non_rc_document_count": document_type_counts["non_rc_document_count"],
        "unknown_document_count": document_type_counts["unknown_document_count"],
        "duplicate_document_count": sum(1 for row in coverage_rows if row["included_in_aggregate"] == "false"),
        "completed_document_ids": sorted(completed_document_ids),
        "schema_error_count": summary_counts.get("schema_errors", 0),
        "unfilled_manual_template_count": summary_counts.get("unfilled_manual_templates", 0),
        "missing_evidence_count": summary_counts.get("missing_evidence", 0) or review_policy.get("missing_evidence", 0),
        "stop_auto_accept_violation_count": summary_counts.get("stop_auto_accept_violations", 0)
        or review_policy.get("stop_auto_accept_violation", 0),
        "unsafe_wrong_stop_count": summary_counts.get("unsafe_wrong_stops", 0) or unsafe_wrong,
        "gold_uncertain_review_required_count": pickup_uncertain + delivery_uncertain,
        "non_rc_not_applicable_scalar_count": scalar_metrics[FIELD_LOAD_NUMBER].get("not_applicable_non_rc", 0)
        + scalar_metrics[FIELD_TOTAL_CARRIER_RATE].get("not_applicable_non_rc", 0),
        "scalar_true_wrong_count": scalar_metrics[FIELD_LOAD_NUMBER].get("wrong", 0) + scalar_metrics[FIELD_TOTAL_CARRIER_RATE].get("wrong", 0),
        "field_metrics": scalar_metrics,
        "stop_metrics": stop_metrics,
        "remaining_plan_count": _actionable_remaining_count(remaining_rows),
        "remaining_plan_row_count": len(remaining_rows),
        "private_values_included": bool(include_private_values_local_only),
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
        "gold_labels_modified": False,
        "filled_hybrid_templates_modified": False,
    }
    summary["aggregate_status"] = classify_multi_batch_status(summary)
    if write_closeout_report:
        summary["closeout_verdict"] = classify_closeout_verdict(summary)
    success_rows = _success_rows(summary)
    _write_outputs(
        resolved_output,
        summary=summary,
        coverage_rows=coverage_rows,
        field_metric_rows=_field_metric_rows(scalar_metrics, stop_metrics),
        review_rows=review_rows,
        success_rows=success_rows,
        remaining_rows=remaining_rows,
        write_remaining_plan=write_remaining_plan,
        write_closeout_report=write_closeout_report,
    )
    return summary


def _write_outputs(
    output_dir: Path,
    *,
    summary: dict[str, Any],
    coverage_rows: list[dict[str, Any]],
    field_metric_rows: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    success_rows: list[dict[str, Any]],
    remaining_rows: list[dict[str, Any]],
    write_remaining_plan: bool,
    write_closeout_report: bool,
) -> None:
    _write_json(output_dir / "multi_batch_summary.json", summary)
    _write_csv(output_dir / "multi_batch_document_coverage.csv", coverage_rows, COVERAGE_FIELDNAMES)
    _write_csv(output_dir / "multi_batch_field_metrics.csv", field_metric_rows, FIELD_METRIC_FIELDNAMES)
    _write_csv(output_dir / "multi_batch_review_items.csv", review_rows, REVIEW_ITEM_FIELDNAMES)
    _write_csv(output_dir / "multi_batch_success_criteria.csv", success_rows, SUCCESS_FIELDNAMES)
    if write_remaining_plan:
        _write_csv(output_dir / "remaining_manual_batch_plan.csv", remaining_rows, REMAINING_PLAN_FIELDNAMES)
    if write_closeout_report:
        _write_closeout_report(output_dir, summary)

    load = summary["field_metrics"][FIELD_LOAD_NUMBER]
    rate = summary["field_metrics"][FIELD_TOTAL_CARRIER_RATE]
    pickup = summary["stop_metrics"][FIELD_PICKUP_STOPS]
    delivery = summary["stop_metrics"][FIELD_DELIVERY_STOPS]
    lines = [
        "# RateCon Hybrid Multi-Batch Summary",
        "",
        "This local-only summary made no AI, cloud, OCR, model, or PDF processing calls.",
        "",
        "## Outcome",
        "",
        f"- aggregate status: {summary['aggregate_status']}",
        f"- batches: {summary['batch_count']}",
        f"- completed documents: {summary['aggregate_document_count']}",
        f"- rate confirmations: {summary.get('rate_confirmation_document_count', 0)}",
        f"- non-RC/BOL-POD filtered: {summary.get('non_rc_document_count', 0)}",
        f"- duplicate documents excluded: {summary['duplicate_document_count']}",
        f"- schema errors: {summary['schema_error_count']}",
        f"- missing evidence: {summary['missing_evidence_count']}",
        f"- stop auto-accept violations: {summary['stop_auto_accept_violation_count']}",
        f"- unsafe wrong stops: {summary['unsafe_wrong_stop_count']}",
        f"- uncertain-gold review items: {summary['gold_uncertain_review_required_count']}",
        "",
        "## Field Metrics",
        "",
        (
            f"- load_number: {load.get('correct', 0)} correct / {load.get('wrong', 0)} wrong / "
            f"{load.get('missing', 0)} missing / {load.get('not_applicable_non_rc', 0)} non-RC not applicable"
        ),
        (
            f"- total_carrier_rate: {rate.get('correct', 0)} correct / "
            f"{rate.get('wrong', 0)} wrong / {rate.get('missing', 0)} missing / "
            f"{rate.get('not_applicable_non_rc', 0)} non-RC not applicable"
        ),
        (
            f"- pickup_stops: {pickup.get('exact_complete', 0)} exact / "
            f"{_stop_uncertain_count(pickup)} uncertain-gold review / "
            f"{pickup.get('unsafe_wrong', 0)} unsafe / {pickup.get('missing_review_required', 0)} missing / "
            f"{pickup.get('not_applicable', 0)} non-RC not applicable"
        ),
        (
            f"- delivery_stops: {delivery.get('exact_complete', 0)} exact / "
            f"{_stop_uncertain_count(delivery)} uncertain-gold review / "
            f"{delivery.get('unsafe_wrong', 0)} unsafe / {delivery.get('missing_review_required', 0)} missing / "
            f"{delivery.get('not_applicable', 0)} non-RC not applicable"
        ),
        "",
        "## Interpretation",
        "",
        "- uncertain-gold review items are review-required, not failures",
        "- non-RC/BOL-POD not-applicable scalar fields are filtered/no-action, not accuracy failures",
        "- stops remain review drafts with auto_accept=false",
        "- private benchmark outputs remain local-only",
        "",
        "## Output Files",
        "",
        "- multi_batch_summary.json",
        "- multi_batch_document_coverage.csv",
        "- multi_batch_field_metrics.csv",
        "- multi_batch_review_items.csv",
        "- multi_batch_success_criteria.csv",
    ]
    if write_remaining_plan:
        lines.append("- remaining_manual_batch_plan.csv")
    if write_closeout_report:
        lines.extend(
            [
                "- manual_hybrid_closeout_report.md",
                "- manual_hybrid_closeout_summary.json",
                "- manual_hybrid_closeout_success_criteria.csv",
            ]
        )
    (output_dir / "multi_batch_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_closeout_report(output_dir: Path, summary: dict[str, Any]) -> None:
    load = summary["field_metrics"][FIELD_LOAD_NUMBER]
    rate = summary["field_metrics"][FIELD_TOTAL_CARRIER_RATE]
    pickup = summary["stop_metrics"][FIELD_PICKUP_STOPS]
    delivery = summary["stop_metrics"][FIELD_DELIVERY_STOPS]
    closeout_summary = {
        "schema_version": "ratecon_hybrid_manual_closeout_summary_v1",
        "closeout_verdict": summary.get("closeout_verdict") or classify_closeout_verdict(summary),
        "aggregate_status": summary.get("aggregate_status"),
        "batch_count": summary.get("batch_count", 0),
        "completed_document_count": summary.get("aggregate_document_count", 0),
        "rate_confirmation_document_count": summary.get("rate_confirmation_document_count", 0),
        "non_rc_document_count": summary.get("non_rc_document_count", 0),
        "duplicate_document_count": summary.get("duplicate_document_count", 0),
        "remaining_actionable_document_count": summary.get("remaining_plan_count", 0),
        "uncertain_gold_review_required_count": summary.get("gold_uncertain_review_required_count", 0),
        "schema_error_count": summary.get("schema_error_count", 0),
        "missing_evidence_count": summary.get("missing_evidence_count", 0),
        "stop_auto_accept_violation_count": summary.get("stop_auto_accept_violation_count", 0),
        "unsafe_wrong_stop_count": summary.get("unsafe_wrong_stop_count", 0),
        "load_number": load,
        "total_carrier_rate": rate,
        "pickup_stops": pickup,
        "delivery_stops": delivery,
        "private_values_included": summary.get("private_values_included", False),
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
        "gold_labels_modified": False,
        "filled_hybrid_templates_modified": False,
    }
    _write_json(output_dir / "manual_hybrid_closeout_summary.json", closeout_summary)
    _write_csv(output_dir / "manual_hybrid_closeout_success_criteria.csv", _closeout_success_rows(summary), CLOSEOUT_SUCCESS_FIELDNAMES)
    lines = [
        "# RateCon Manual Hybrid Closeout Report",
        "",
        "This local-only closeout report made no AI, cloud, OCR, model, or PDF processing calls.",
        "",
        "## Final Verdict",
        "",
        f"- closeout verdict: {closeout_summary['closeout_verdict']}",
        f"- aggregate status: {closeout_summary['aggregate_status']}",
        f"- completed documents: {closeout_summary['completed_document_count']}",
        f"- rate confirmations: {closeout_summary['rate_confirmation_document_count']}",
        f"- non-RC/BOL-POD filtered: {closeout_summary['non_rc_document_count']}",
        f"- duplicate aliases excluded: {closeout_summary['duplicate_document_count']}",
        f"- remaining actionable documents: {closeout_summary['remaining_actionable_document_count']}",
        f"- uncertain-gold review items: {closeout_summary['uncertain_gold_review_required_count']}",
        "",
        "## Safety Metrics",
        "",
        f"- schema errors: {closeout_summary['schema_error_count']}",
        f"- missing evidence: {closeout_summary['missing_evidence_count']}",
        f"- stop auto-accept violations: {closeout_summary['stop_auto_accept_violation_count']}",
        f"- unsafe wrong stops: {closeout_summary['unsafe_wrong_stop_count']}",
        "",
        "## Field Metrics",
        "",
        (
            f"- load_number: {load.get('correct', 0)} correct / {load.get('wrong', 0)} wrong / "
            f"{load.get('missing', 0)} missing / {load.get('not_applicable_non_rc', 0)} non-RC not applicable"
        ),
        (
            f"- total_carrier_rate: {rate.get('correct', 0)} correct / {rate.get('wrong', 0)} wrong / "
            f"{rate.get('missing', 0)} missing / {rate.get('not_applicable_non_rc', 0)} non-RC not applicable"
        ),
        (
            f"- pickup_stops: {pickup.get('exact_complete', 0)} exact / {_stop_uncertain_count(pickup)} uncertain-gold review / "
            f"{pickup.get('unsafe_wrong', 0)} unsafe / {pickup.get('missing_review_required', 0)} missing / "
            f"{pickup.get('not_applicable', 0)} non-RC not applicable"
        ),
        (
            f"- delivery_stops: {delivery.get('exact_complete', 0)} exact / {_stop_uncertain_count(delivery)} uncertain-gold review / "
            f"{delivery.get('unsafe_wrong', 0)} unsafe / {delivery.get('missing_review_required', 0)} missing / "
            f"{delivery.get('not_applicable', 0)} non-RC not applicable"
        ),
        "",
        "## Important Limits",
        "",
        "- full manual/hybrid validation does not mean production auto-extraction is ready",
        "- all stops remain review-required",
        "- auto_accept must remain false",
        "- private outputs and filled templates must stay local",
    ]
    (output_dir / "manual_hybrid_closeout_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize multiple local-only RateCon hybrid benchmark batches.")
    parser.add_argument("--benchmark-dir", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--gold-dir", type=Path, default=None)
    parser.add_argument("--write-remaining-plan", action="store_true")
    parser.add_argument("--write-closeout-report", action="store_true")
    parser.add_argument("--max-next-docs", type=int, default=10)
    parser.add_argument("--include-private-values-local-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local multi-batch summary")
    summary = summarize_hybrid_batches(
        benchmark_dirs=args.benchmark_dir,
        output_dir=args.output_dir,
        audit=args.audit,
        gold_dir=args.gold_dir,
        write_remaining_plan=args.write_remaining_plan,
        write_closeout_report=args.write_closeout_report,
        max_next_docs=args.max_next_docs,
        include_private_values_local_only=args.include_private_values_local_only,
    )
    print("RateCon hybrid multi-batch summary")
    print(f"aggregate_status: {summary['aggregate_status']}")
    print(f"aggregate_document_count: {summary['aggregate_document_count']}")
    print(f"remaining_plan_count: {summary['remaining_plan_count']}")
    if args.write_closeout_report:
        print(f"closeout_verdict: {summary.get('closeout_verdict')}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
