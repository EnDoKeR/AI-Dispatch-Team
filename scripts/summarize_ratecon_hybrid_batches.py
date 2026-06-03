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
    "unsafe_wrong",
    "missing_review_required",
)
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
]


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


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).lower() in {"true", "1", "yes", "y"}


def _empty_scalar_metrics() -> dict[str, dict[str, int]]:
    return {
        FIELD_LOAD_NUMBER: {"correct": 0, "wrong": 0, "missing": 0, "high_confidence_wrong": 0},
        FIELD_TOTAL_CARRIER_RATE: {"correct": 0, "wrong": 0, "missing": 0, "high_confidence_wrong": 0},
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
) -> tuple[list[dict[str, Any]], set[str]]:
    seen: dict[str, dict[str, Any]] = {}
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
    return coverage_rows, set(seen)


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
                if _is_correct_scalar_status(status):
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
            "Wrong scalar fields must be resolved by review.",
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
    max_next_docs: int = 10,
    include_private_values_local_only: bool = False,
) -> list[dict[str, Any]]:
    audit_records = _read_audit(audit)
    labels = load_gold_labels(_repo_relative(gold_dir)) if gold_dir and _repo_relative(gold_dir).exists() else []
    audit_by_key = _audit_index(audit_records)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for label in labels:
        audit_record = _match_audit(label, audit_by_key)
        document_id = _text(label.get("document_id")) or _text(audit_record.get("document_id"))
        if not document_id or document_id in seen or document_id in completed_document_ids:
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
            }
        )
        seen.add(document_id)

    for record in audit_records:
        document_id = _record_key(record)
        if not document_id or document_id in seen or document_id in completed_document_ids:
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
            }
        )
        seen.add(document_id)

    def sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
        priority = {"hard": 0, "medium": 1, "unknown": 2, "classification": 3}
        return (priority.get(row["difficulty"], 9), row["suggested_pattern"], row["document_id"])

    return sorted(rows, key=sort_key)[:max_next_docs]


def summarize_hybrid_batches(
    *,
    benchmark_dirs: list[Path],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    audit: Path | None = None,
    gold_dir: Path | None = None,
    write_remaining_plan: bool = False,
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
    coverage_rows, completed_document_ids = _completed_documents(
        batches,
        include_private_values_local_only=include_private_values_local_only,
    )
    scalar_metrics, stop_metrics, field_rows, review_policy = _aggregate_metrics(batches, completed_document_ids)
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
        "duplicate_document_count": sum(1 for row in coverage_rows if row["included_in_aggregate"] == "false"),
        "completed_document_ids": sorted(completed_document_ids),
        "schema_error_count": summary_counts.get("schema_errors", 0),
        "unfilled_manual_template_count": summary_counts.get("unfilled_manual_templates", 0),
        "missing_evidence_count": summary_counts.get("missing_evidence", 0) or review_policy.get("missing_evidence", 0),
        "stop_auto_accept_violation_count": summary_counts.get("stop_auto_accept_violations", 0)
        or review_policy.get("stop_auto_accept_violation", 0),
        "unsafe_wrong_stop_count": summary_counts.get("unsafe_wrong_stops", 0) or unsafe_wrong,
        "gold_uncertain_review_required_count": pickup_uncertain + delivery_uncertain,
        "field_metrics": scalar_metrics,
        "stop_metrics": stop_metrics,
        "remaining_plan_count": len(remaining_rows),
        "private_values_included": bool(include_private_values_local_only),
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
        "gold_labels_modified": False,
        "filled_hybrid_templates_modified": False,
    }
    summary["aggregate_status"] = classify_multi_batch_status(summary)
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
) -> None:
    _write_json(output_dir / "multi_batch_summary.json", summary)
    _write_csv(output_dir / "multi_batch_document_coverage.csv", coverage_rows, COVERAGE_FIELDNAMES)
    _write_csv(output_dir / "multi_batch_field_metrics.csv", field_metric_rows, FIELD_METRIC_FIELDNAMES)
    _write_csv(output_dir / "multi_batch_review_items.csv", review_rows, REVIEW_ITEM_FIELDNAMES)
    _write_csv(output_dir / "multi_batch_success_criteria.csv", success_rows, SUCCESS_FIELDNAMES)
    if write_remaining_plan:
        _write_csv(output_dir / "remaining_manual_batch_plan.csv", remaining_rows, REMAINING_PLAN_FIELDNAMES)

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
        f"- duplicate documents excluded: {summary['duplicate_document_count']}",
        f"- schema errors: {summary['schema_error_count']}",
        f"- missing evidence: {summary['missing_evidence_count']}",
        f"- stop auto-accept violations: {summary['stop_auto_accept_violation_count']}",
        f"- unsafe wrong stops: {summary['unsafe_wrong_stop_count']}",
        f"- uncertain-gold review items: {summary['gold_uncertain_review_required_count']}",
        "",
        "## Field Metrics",
        "",
        f"- load_number: {load.get('correct', 0)} correct / {load.get('wrong', 0)} wrong / {load.get('missing', 0)} missing",
        (
            f"- total_carrier_rate: {rate.get('correct', 0)} correct / "
            f"{rate.get('wrong', 0)} wrong / {rate.get('missing', 0)} missing"
        ),
        (
            f"- pickup_stops: {pickup.get('exact_complete', 0)} exact / "
            f"{_stop_uncertain_count(pickup)} uncertain-gold review / "
            f"{pickup.get('unsafe_wrong', 0)} unsafe / {pickup.get('missing_review_required', 0)} missing"
        ),
        (
            f"- delivery_stops: {delivery.get('exact_complete', 0)} exact / "
            f"{_stop_uncertain_count(delivery)} uncertain-gold review / "
            f"{delivery.get('unsafe_wrong', 0)} unsafe / {delivery.get('missing_review_required', 0)} missing"
        ),
        "",
        "## Interpretation",
        "",
        "- uncertain-gold review items are review-required, not failures",
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
    (output_dir / "multi_batch_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize multiple local-only RateCon hybrid benchmark batches.")
    parser.add_argument("--benchmark-dir", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--gold-dir", type=Path, default=None)
    parser.add_argument("--write-remaining-plan", action="store_true")
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
        max_next_docs=args.max_next_docs,
        include_private_values_local_only=args.include_private_values_local_only,
    )
    print("RateCon hybrid multi-batch summary")
    print(f"aggregate_status: {summary['aggregate_status']}")
    print(f"aggregate_document_count: {summary['aggregate_document_count']}")
    print(f"remaining_plan_count: {summary['remaining_plan_count']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
