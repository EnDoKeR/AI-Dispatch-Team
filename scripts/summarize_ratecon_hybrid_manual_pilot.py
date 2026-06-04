"""Summarize a local-only RateCon hybrid manual pilot benchmark.

This script turns an existing benchmark output folder into a concise pilot
outcome report and optional next-batch plan. It does not call AI models, cloud
APIs, OCR, local model runtimes, PDF processing, or modify gold/template files.
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

from app.document_ai.ratecon_gold_labels import load_gold_labels  # noqa: E402
from app.document_ai.ratecon_hybrid_contract import is_under_local_outputs  # noqa: E402
from scripts.create_ratecon_hybrid_private_manual_pilot import infer_document_pattern  # noqa: E402


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_manual_pilot_summary")
PILOT_STATUSES = {
    "pilot_passed",
    "pilot_passed_with_review_items",
    "pilot_failed_schema",
    "pilot_failed_safety",
    "pilot_failed_accuracy",
    "pilot_inconclusive",
}
NEXT_ACTIONS = [
    (
        "keep_hybrid_result_contract_unchanged",
        "The manual pilot succeeded without requiring contract changes.",
        "continue",
    ),
    (
        "keep_stops_review_required",
        "Stops are still review drafts even when the pilot is clean.",
        "required_policy",
    ),
    (
        "keep_auto_accept_false",
        "Phase 1 does not support stop auto-accept.",
        "required_policy",
    ),
    (
        "do_not_build_ai_integration_yet",
        "Expand manual coverage before introducing model-assisted filling.",
        "defer",
    ),
    (
        "expand_manual_pilot_to_next_5_to_10_documents",
        "The first batch is too small to decide production architecture.",
        "next_step",
    ),
    (
        "prioritize_diverse_document_patterns",
        "Include compact rows, pickup/drop blocks, PU/SO blocks, structured shipper/consignee blocks, city-level-only, and non-RC/BOL/POD.",
        "next_step",
    ),
    (
        "run_benchmark_after_each_batch",
        "Keep safety, evidence, scalar, and stop-review metrics visible after every batch.",
        "next_step",
    ),
    (
        "do_not_commit_private_outputs",
        "Manual templates, benchmark outputs, review packets, and private source files remain local only.",
        "required_policy",
    ),
]


class ManualPilotSummaryError(ValueError):
    """Raised when manual pilot summary generation would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    resolved = _repo_relative(path)
    if not resolved.exists():
        raise ManualPilotSummaryError(f"Required input does not exist: {path}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ManualPilotSummaryError(f"Expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    resolved = _repo_relative(path)
    if not resolved.exists():
        return []
    with resolved.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def _safe_int(value: Any) -> int:
    try:
        if value in [None, ""]:
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _metric(summary: dict[str, Any], *keys: str) -> int:
    current: Any = summary
    for key in keys:
        if not isinstance(current, dict):
            return 0
        current = current.get(key)
    return _safe_int(current)


def _scalar_wrong_count(summary: dict[str, Any]) -> int:
    return _metric(summary, "field_metrics", "load_number", "wrong") + _metric(
        summary, "field_metrics", "total_carrier_rate", "wrong"
    )


def _gold_uncertain_review_count(summary: dict[str, Any]) -> int:
    return _metric(summary, "one_screen_summary", "gold_uncertain_review_required") or _metric(
        summary, "gold_uncertain_metrics", "review_required"
    )


def classify_pilot_outcome(summary: dict[str, Any]) -> str:
    if not summary:
        return "pilot_inconclusive"
    if _metric(summary, "schema_error_count") or _metric(summary, "one_screen_summary", "schema_errors"):
        return "pilot_failed_schema"
    auto_accept = _metric(summary, "one_screen_summary", "stop_auto_accept_violations") or _metric(
        summary, "review_policy", "stop_auto_accept_violation"
    )
    missing_evidence = _metric(summary, "one_screen_summary", "missing_evidence")
    if auto_accept or missing_evidence:
        return "pilot_failed_safety"
    if _metric(summary, "one_screen_summary", "unsafe_wrong_stops") or _scalar_wrong_count(summary):
        return "pilot_failed_accuracy"
    if _gold_uncertain_review_count(summary):
        return "pilot_passed_with_review_items"
    return "pilot_passed"


def _success_criteria_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    scalar_wrong = _scalar_wrong_count(summary)
    rows = [
        {
            "criterion": "schema_errors",
            "value": _metric(summary, "schema_error_count") or _metric(summary, "one_screen_summary", "schema_errors"),
            "passes": (_metric(summary, "schema_error_count") or _metric(summary, "one_screen_summary", "schema_errors")) == 0,
            "failure_status": "pilot_failed_schema",
            "notes": "Schema errors block pilot acceptance.",
        },
        {
            "criterion": "auto_accept_violations",
            "value": _metric(summary, "one_screen_summary", "stop_auto_accept_violations"),
            "passes": _metric(summary, "one_screen_summary", "stop_auto_accept_violations") == 0,
            "failure_status": "pilot_failed_safety",
            "notes": "Stop auto_accept must remain false.",
        },
        {
            "criterion": "missing_evidence",
            "value": _metric(summary, "one_screen_summary", "missing_evidence"),
            "passes": _metric(summary, "one_screen_summary", "missing_evidence") == 0,
            "failure_status": "pilot_failed_safety",
            "notes": "Every filled field needs evidence.",
        },
        {
            "criterion": "unsafe_wrong_stops",
            "value": _metric(summary, "one_screen_summary", "unsafe_wrong_stops"),
            "passes": _metric(summary, "one_screen_summary", "unsafe_wrong_stops") == 0,
            "failure_status": "pilot_failed_accuracy",
            "notes": "Unsafe wrong stops are pilot failures.",
        },
        {
            "criterion": "load_or_rate_wrong",
            "value": scalar_wrong,
            "passes": scalar_wrong == 0,
            "failure_status": "pilot_failed_accuracy",
            "notes": "Wrong scalar fields must be resolved before success.",
        },
        {
            "criterion": "uncertain_gold_review_required",
            "value": _gold_uncertain_review_count(summary),
            "passes": True,
            "failure_status": "",
            "notes": "Uncertain gold review items are expected review work, not failures.",
        },
    ]
    for row in rows:
        row["passes"] = "true" if row["passes"] else "false"
    return rows


def _next_action_rows(pilot_status: str) -> list[dict[str, Any]]:
    rows = []
    for priority, (action, rationale, action_type) in enumerate(NEXT_ACTIONS, start=1):
        rows.append(
            {
                "priority": priority,
                "pilot_status": pilot_status,
                "recommended_action": action,
                "action_type": action_type,
                "rationale": rationale,
            }
        )
    return rows


def _current_pilot_document_ids(benchmark_dir: Path) -> set[str]:
    rows = _read_csv(_repo_relative(benchmark_dir) / "hybrid_document_metrics.csv")
    return {_text(row.get("document_id")) for row in rows if _text(row.get("document_id"))}


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
    if difficulty == "classification":
        return "include non-RC/BOL/POD classification coverage"
    if difficulty == "hard":
        return "include hard scanned/OCR or ambiguous stop pattern"
    if "compact" in pattern or "table" in pattern:
        return "include clean table or compact-row coverage"
    if "structured" in pattern:
        return "include structured shipper/consignee block coverage"
    return "expand representative manual pilot coverage"


def _expected_fields(document_type: str) -> str:
    if document_type == "bol_pod":
        return "document_type"
    return "document_type; load_number; total_carrier_rate; pickup_stops; delivery_stops; evidence"


def build_next_batch_plan(
    *,
    benchmark_dir: Path,
    audit: Path | None,
    gold_dir: Path | None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    audit_records = _read_audit(audit)
    labels = load_gold_labels(_repo_relative(gold_dir)) if gold_dir and _repo_relative(gold_dir).exists() else []
    current_doc_ids = _current_pilot_document_ids(benchmark_dir)
    audit_by_key = _audit_index(audit_records)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for label in labels:
        audit_record = _match_audit(label, audit_by_key)
        document_id = _text(label.get("document_id")) or _text(audit_record.get("document_id"))
        if not document_id or document_id in current_doc_ids or document_id in seen:
            continue
        document_type = _text((label.get("gold") or {}).get("document_type")) or _text(audit_record.get("document_type")) or "unknown"
        pattern = infer_document_pattern(audit_record, label)
        difficulty = _difficulty(pattern, document_type)
        candidates.append(
            {
                "document_id": document_id,
                "file_name": _text(label.get("file_name")) or _text(audit_record.get("file_name")),
                "suggested_pattern": pattern,
                "difficulty": difficulty,
                "reason_selected": _reason_selected(pattern, difficulty),
                "expected_fields_to_fill": _expected_fields(document_type),
                "notes_for_reviewer": "keep stops review_required=true and auto_accept=false",
            }
        )
        seen.add(document_id)

    for record in audit_records:
        document_id = _record_key(record)
        if not document_id or document_id in current_doc_ids or document_id in seen:
            continue
        document_type = _text(record.get("document_type")) or "unknown"
        pattern = infer_document_pattern(record, {})
        difficulty = _difficulty(pattern, document_type)
        candidates.append(
            {
                "document_id": document_id,
                "file_name": _text(record.get("file_name")),
                "suggested_pattern": pattern,
                "difficulty": difficulty,
                "reason_selected": _reason_selected(pattern, difficulty),
                "expected_fields_to_fill": _expected_fields(document_type),
                "notes_for_reviewer": "keep stops review_required=true and auto_accept=false",
            }
        )
        seen.add(document_id)

    def sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
        difficulty_priority = {"hard": 0, "medium": 1, "classification": 2, "unknown": 3}
        return (difficulty_priority.get(row["difficulty"], 9), row["suggested_pattern"], row["document_id"])

    return sorted(candidates, key=sort_key)[:limit]


def summarize_manual_pilot(
    *,
    benchmark_dir: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_private_values_local_only: bool = False,
    write_next_batch_plan: bool = False,
    audit: Path | None = None,
    gold_dir: Path | None = None,
) -> dict[str, Any]:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise ManualPilotSummaryError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)

    resolved_benchmark = _repo_relative(benchmark_dir)
    benchmark_summary = _read_json(resolved_benchmark / "hybrid_benchmark_summary.json")
    pilot_status = classify_pilot_outcome(benchmark_summary)
    success_rows = _success_criteria_rows(benchmark_summary)
    action_rows = _next_action_rows(pilot_status)
    next_batch_rows = (
        build_next_batch_plan(benchmark_dir=resolved_benchmark, audit=audit, gold_dir=gold_dir)
        if write_next_batch_plan
        else []
    )

    summary = {
        "schema_version": "ratecon_hybrid_manual_pilot_summary_report_v1",
        "pilot_status": pilot_status,
        "hybrid_result_count": _metric(benchmark_summary, "hybrid_result_count")
        or _metric(benchmark_summary, "one_screen_summary", "results"),
        "schema_error_count": _metric(benchmark_summary, "schema_error_count")
        or _metric(benchmark_summary, "one_screen_summary", "schema_errors"),
        "error_case_count": _metric(benchmark_summary, "one_screen_summary", "error_cases"),
        "missing_evidence_count": _metric(benchmark_summary, "one_screen_summary", "missing_evidence"),
        "stop_auto_accept_violation_count": _metric(benchmark_summary, "one_screen_summary", "stop_auto_accept_violations"),
        "unsafe_wrong_stop_count": _metric(benchmark_summary, "one_screen_summary", "unsafe_wrong_stops"),
        "gold_uncertain_review_required_count": _gold_uncertain_review_count(benchmark_summary),
        "load_number": benchmark_summary.get("field_metrics", {}).get("load_number", {}),
        "total_carrier_rate": benchmark_summary.get("field_metrics", {}).get("total_carrier_rate", {}),
        "pickup_stops": benchmark_summary.get("stop_metrics", {}).get("pickup_stops", {}),
        "delivery_stops": benchmark_summary.get("stop_metrics", {}).get("delivery_stops", {}),
        "success_criteria_count": len(success_rows),
        "next_action_count": len(action_rows),
        "next_batch_plan_count": len(next_batch_rows),
        "private_values_included": bool(include_private_values_local_only),
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ai_model_invocation_attempted": False,
    }

    _write_outputs(
        resolved_output,
        summary=summary,
        success_rows=success_rows,
        action_rows=action_rows,
        next_batch_rows=next_batch_rows,
        write_next_batch_plan=write_next_batch_plan,
    )
    return summary


SUCCESS_FIELDNAMES = ["criterion", "value", "passes", "failure_status", "notes"]
ACTION_FIELDNAMES = ["priority", "pilot_status", "recommended_action", "action_type", "rationale"]
NEXT_BATCH_FIELDNAMES = [
    "document_id",
    "file_name",
    "suggested_pattern",
    "difficulty",
    "reason_selected",
    "expected_fields_to_fill",
    "notes_for_reviewer",
]


def _write_outputs(
    output_dir: Path,
    *,
    summary: dict[str, Any],
    success_rows: list[dict[str, Any]],
    action_rows: list[dict[str, Any]],
    next_batch_rows: list[dict[str, Any]],
    write_next_batch_plan: bool,
) -> None:
    _write_json(output_dir / "manual_pilot_summary.json", summary)
    _write_csv(output_dir / "manual_pilot_success_criteria.csv", success_rows, SUCCESS_FIELDNAMES)
    _write_csv(output_dir / "manual_pilot_next_actions.csv", action_rows, ACTION_FIELDNAMES)
    if write_next_batch_plan:
        _write_csv(output_dir / "manual_pilot_next_batch_plan.csv", next_batch_rows, NEXT_BATCH_FIELDNAMES)
    lines = [
        "# RateCon Hybrid Manual Pilot Summary",
        "",
        "This local-only summary made no AI, cloud, OCR, model, or PDF processing calls.",
        "",
        "## Outcome",
        "",
        f"- pilot status: {summary['pilot_status']}",
        f"- hybrid results: {summary['hybrid_result_count']}",
        f"- schema errors: {summary['schema_error_count']}",
        f"- error cases: {summary['error_case_count']}",
        f"- missing evidence: {summary['missing_evidence_count']}",
        f"- stop auto-accept violations: {summary['stop_auto_accept_violation_count']}",
        f"- unsafe wrong stops: {summary['unsafe_wrong_stop_count']}",
        f"- uncertain-gold review items: {summary['gold_uncertain_review_required_count']}",
        "",
        "## Field Metrics",
        "",
        (
            f"- load_number: {summary['load_number'].get('correct', 0)} correct / "
            f"{summary['load_number'].get('wrong', 0)} wrong / "
            f"{summary['load_number'].get('missing', 0)} missing"
        ),
        (
            f"- total_carrier_rate: {summary['total_carrier_rate'].get('correct', 0)} correct / "
            f"{summary['total_carrier_rate'].get('wrong', 0)} wrong / "
            f"{summary['total_carrier_rate'].get('missing', 0)} missing"
        ),
        (
            f"- pickup_stops: {summary['pickup_stops'].get('exact_complete', 0)} exact / "
            f"{summary['pickup_stops'].get('unsafe_wrong', 0)} unsafe / "
            f"{summary['pickup_stops'].get('missing_review_required', 0)} missing"
        ),
        (
            f"- delivery_stops: {summary['delivery_stops'].get('exact_complete', 0)} exact / "
            f"{summary['delivery_stops'].get('unsafe_wrong', 0)} unsafe / "
            f"{summary['delivery_stops'].get('matches_uncertain_gold_review_required', 0)} uncertain-gold review / "
            f"{summary['delivery_stops'].get('missing_review_required', 0)} missing"
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
        "- manual_pilot_summary.json",
        "- manual_pilot_success_criteria.csv",
        "- manual_pilot_next_actions.csv",
    ]
    if write_next_batch_plan:
        lines.append("- manual_pilot_next_batch_plan.csv")
    (output_dir / "manual_pilot_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize a local-only RateCon hybrid manual pilot benchmark.")
    parser.add_argument("--benchmark-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--write-next-batch-plan", action="store_true")
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--gold-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local private pilot summary")
    summary = summarize_manual_pilot(
        benchmark_dir=args.benchmark_dir,
        output_dir=args.output_dir,
        include_private_values_local_only=args.include_private_values_local_only,
        write_next_batch_plan=args.write_next_batch_plan,
        audit=args.audit,
        gold_dir=args.gold_dir,
    )
    print("RateCon hybrid manual pilot summary")
    print(f"pilot_status: {summary['pilot_status']}")
    print(f"next_action_count: {summary['next_action_count']}")
    print(f"next_batch_plan_count: {summary['next_batch_plan_count']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
