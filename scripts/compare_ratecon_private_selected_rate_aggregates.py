"""Compare local private RateCon selected-rate aggregate outputs.

This script reads existing local evaluation artifacts only. It does not run
measurement, process PDFs, invoke OCR, call Google, or call model/cloud
services. Default outputs redact selected private values.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SYSTEM_SHADOW = "shadow"
total_carrier_rate_field = "total_carrier_rate"

SUMMARY_FILE_NAME = "ratecon_gold_evaluation_summary.json"
ERROR_CASE_FILE_NAMES = (
    "ratecon_gold_error_cases.csv",
    "ratecon_gold_evaluation_error_cases.csv",
)
SELECTED_RATE_ROW_FILE_NAMES = (
    "private_selected_rate_selected_rows.csv",
    "ratecon_selected_rate_comparison_rows.csv",
    "selected_rate_comparison_rows.csv",
    "ratecon_gold_selected_rate_rows.csv",
    "selected_rate_rows.csv",
)
REDACTED = "[redacted]"

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare local private RateCon selected-rate aggregate evaluation "
            "outputs without printing private values by default."
        )
    )
    parser.add_argument("--baseline-eval-dir", required=True)
    parser.add_argument("--experiment-eval-dir", required=True)
    parser.add_argument("--baseline-label", default="baseline")
    parser.add_argument("--experiment-label", default="experiment")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--fail-on-selected-rate-regression", action="store_true")
    parser.add_argument("--allow-review-only-differences", action="store_true")
    parser.add_argument("--require-private-selected-values-local-only", action="store_true")
    parser.add_argument("--max-allowed-total-rate-wrong-delta", type=int, default=0)
    parser.add_argument("--max-allowed-high-confidence-wrong-delta", type=int, default=0)
    parser.add_argument("--max-allowed-selected-value-changes", type=int, default=0)
    return parser.parse_args(argv)


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _require_output_under_local_outputs(path: Path) -> Path:
    if ".local_outputs" not in path.parts:
        raise ValueError("output-dir must be inside .local_outputs")
    return path


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object at {path}")
    return data


def _find_first_existing(directory: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = directory / name
        if path.exists():
            return path
    return None


def _to_number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    return int(round(_to_number(value, float(default))))


def _nested_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _metric(summary: dict[str, Any]) -> dict[str, Any]:
    field_metrics = _nested_dict(summary.get("field_metrics"))
    shadow_metrics = _nested_dict(field_metrics.get(SYSTEM_SHADOW))
    metric = _nested_dict(shadow_metrics.get(total_carrier_rate_field))
    if metric:
        return metric
    return _nested_dict(field_metrics.get(total_carrier_rate_field))


def _lookup_count(source: dict[str, Any], *keys: str) -> int:
    for key in keys:
        if key in source:
            return _to_int(source.get(key))
    return 0


def _diagnosis_counts(summary: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    rate_errors = _nested_dict(summary.get("rate_error_analysis"))
    for container_key in (
        "wrong_reason_counts",
        "diagnosis_counts",
        "wrong_by_money_context",
        "wrong_by_rate_safety",
    ):
        for key, value in _nested_dict(rate_errors.get(container_key)).items():
            counts[str(key)] += _to_int(value)
    for key in (
        "selected_wrong_money_context",
        "selected_wrong_money_context_count",
        "gold_total_in_candidates_not_selected",
        "gold_total_in_candidates_not_selected_count",
        "selected_safe_total_but_gold_differs",
        "selected_safe_total_but_gold_differs_count",
        "unknown_wrong",
        "unknown_wrong_count",
        "review_required_count",
        "uncertain_gold_count",
    ):
        if key in rate_errors:
            counts[key.replace("_count", "")] += _to_int(rate_errors.get(key))
    for container_key in (
        "residual_wrong_rate_forensics",
        "rate_candidate_forensics",
        "rate_conflict_audit",
    ):
        container = _nested_dict(summary.get(container_key))
        for key, value in _nested_dict(container.get("diagnosis_counts")).items():
            counts[str(key)] += _to_int(value)
        for key, value in _nested_dict(container.get("status_counts")).items():
            counts[str(key)] += _to_int(value)
    return counts


def _read_error_reason_counts(eval_dir: Path) -> Counter[str]:
    path = _find_first_existing(eval_dir, ERROR_CASE_FILE_NAMES)
    if path is None:
        return Counter()
    counts: Counter[str] = Counter()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("field") and row.get("field") != total_carrier_rate_field:
                continue
            reason = (
                row.get("error_reason")
                or row.get("reason")
                or row.get("diagnosis")
                or row.get("status")
                or "unknown"
            )
            counts[reason] += 1
    return counts


def _field_summary(summary: dict[str, Any], eval_dir: Path) -> dict[str, Any]:
    metric = _metric(summary)
    diagnoses = _diagnosis_counts(summary)
    error_reasons = _read_error_reason_counts(eval_dir)

    exact = _lookup_count(metric, "exact_match_count", "exact_count")
    normalized = _lookup_count(metric, "normalized_match_count", "normalized_count")
    correct = _lookup_count(metric, "correct_count", "correct")
    if not correct:
        correct = exact + normalized
    wrong = _lookup_count(metric, "wrong_value_count", "wrong_count", "wrong")
    missing = _lookup_count(metric, "missing_count", "missing")
    high_conf_wrong = _lookup_count(
        metric,
        "high_confidence_but_wrong_count",
        "high_confidence_wrong_count",
        "high_conf_wrong_count",
    )
    review_required = _lookup_count(
        metric,
        "review_required_count",
        "uncertain_count",
        "uncertain_gold_count",
    )
    if "review_required" in error_reasons:
        review_required += error_reasons["review_required"]
    selected_wrong_money_context = (
        diagnoses["selected_wrong_money_context"]
        or diagnoses["wrong_money_context"]
        or diagnoses["wrong_selected_count"]
    )

    return {
        "evaluated_document_count": _lookup_count(
            summary,
            "labels_evaluated",
            "evaluated_document_count",
            "evaluated_docs",
        ),
        "labeled_count": _lookup_count(metric, "labeled_count", "evaluated_count"),
        "correct_count": correct,
        "wrong_count": wrong,
        "missing_count": missing,
        "precision": _to_number(metric.get("precision")),
        "recall": _to_number(metric.get("recall")),
        "high_confidence_wrong_count": high_conf_wrong,
        "selected_wrong_money_context_count": selected_wrong_money_context,
        "gold_total_in_candidates_not_selected_count": diagnoses[
            "gold_total_in_candidates_not_selected"
        ],
        "selected_safe_total_but_gold_differs_count": diagnoses[
            "selected_safe_total_but_gold_differs"
        ],
        "unknown_wrong_count": diagnoses["unknown_wrong"] or error_reasons["unknown"],
        "review_required_count": review_required,
        "uncertain_gold_count": diagnoses["uncertain_gold"],
        "source_not_available_count": _lookup_count(metric, "source_not_available_count"),
        "serialized_gap_count": _lookup_count(
            metric,
            "field_not_serialized_count",
            "serialized_gap_count",
        ),
        "error_reason_counts": dict(sorted(error_reasons.items())),
    }


def _load_selected_rows(eval_dir: Path) -> tuple[str, dict[str, dict[str, str]]]:
    path = _find_first_existing(eval_dir, SELECTED_RATE_ROW_FILE_NAMES)
    if path is None:
        return "private_values_unavailable", {}
    rows: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            field = row.get("field") or row.get("field_name")
            if field and field != total_carrier_rate_field:
                continue
            document_id = (
                row.get("document_id")
                or row.get("file_hash")
                or row.get("case_id")
                or f"row_{index}"
            )
            rows[str(document_id)] = {
                "document_id": str(document_id),
                "selected_value": row.get("selected_value") or row.get("value") or "",
                "selected_source": row.get("selected_source") or row.get("source") or "",
                "selected_confidence": row.get("selected_confidence")
                or row.get("confidence")
                or "",
                "selected_confidence_bucket": row.get("selected_confidence_bucket")
                or row.get("confidence_bucket")
                or _confidence_bucket(row.get("selected_confidence") or row.get("confidence")),
                "selected_money_context": row.get("selected_money_context")
                or row.get("money_context")
                or "",
                "selected_status": row.get("selected_status") or row.get("status") or "",
            }
    if not rows:
        return "private_values_unavailable", {}
    return "available", rows


def _confidence_bucket(value: Any) -> str:
    if value in (None, ""):
        return ""
    confidence = _to_number(value, default=-1.0)
    if confidence < 0:
        return ""
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"


def _compare_selected_rows(
    baseline_rows: dict[str, dict[str, str]],
    experiment_rows: dict[str, dict[str, str]],
    *,
    include_private_values: bool,
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    changed_docs: list[dict[str, Any]] = []
    changed_value_count = 0
    changed_source_count = 0
    changed_confidence_bucket_count = 0
    changed_money_context_count = 0

    for document_id in sorted(set(baseline_rows) | set(experiment_rows)):
        base = baseline_rows.get(document_id, {})
        exp = experiment_rows.get(document_id, {})
        value_changed = base.get("selected_value", "") != exp.get("selected_value", "")
        source_changed = base.get("selected_source", "") != exp.get("selected_source", "")
        confidence_changed = base.get("selected_confidence_bucket", "") != exp.get(
            "selected_confidence_bucket",
            "",
        )
        money_context_changed = base.get("selected_money_context", "") != exp.get(
            "selected_money_context",
            "",
        )
        status_changed = base.get("selected_status", "") != exp.get("selected_status", "")
        if not any(
            (
                value_changed,
                source_changed,
                confidence_changed,
                money_context_changed,
                status_changed,
            )
        ):
            continue
        changed_value_count += int(value_changed)
        changed_source_count += int(source_changed)
        changed_confidence_bucket_count += int(confidence_changed)
        changed_money_context_count += int(money_context_changed)
        row = {
            "document_id": document_id,
            "selected_value_changed": value_changed,
            "selected_source_changed": source_changed,
            "selected_confidence_bucket_changed": confidence_changed,
            "selected_money_context_changed": money_context_changed,
            "selected_status_changed": status_changed,
            "baseline_selected_source": base.get("selected_source", ""),
            "experiment_selected_source": exp.get("selected_source", ""),
            "baseline_selected_confidence_bucket": base.get(
                "selected_confidence_bucket",
                "",
            ),
            "experiment_selected_confidence_bucket": exp.get(
                "selected_confidence_bucket",
                "",
            ),
            "baseline_selected_money_context": base.get("selected_money_context", ""),
            "experiment_selected_money_context": exp.get("selected_money_context", ""),
            "baseline_selected_status": base.get("selected_status", ""),
            "experiment_selected_status": exp.get("selected_status", ""),
            "private_values_included": include_private_values,
        }
        if include_private_values:
            row["baseline_selected_value"] = base.get("selected_value", "")
            row["experiment_selected_value"] = exp.get("selected_value", "")
        else:
            row["baseline_selected_value"] = REDACTED if value_changed else ""
            row["experiment_selected_value"] = REDACTED if value_changed else ""
        changed_docs.append(row)

    counts = {
        "selected_value_changed_count": changed_value_count,
        "selected_source_changed_count": changed_source_count,
        "selected_confidence_bucket_changed_count": changed_confidence_bucket_count,
        "selected_money_context_changed_count": changed_money_context_count,
        "changed_document_count": len(changed_docs),
    }
    return counts, changed_docs


def _delta(baseline: dict[str, Any], experiment: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "evaluated_document_count",
        "labeled_count",
        "correct_count",
        "wrong_count",
        "missing_count",
        "precision",
        "recall",
        "high_confidence_wrong_count",
        "selected_wrong_money_context_count",
        "gold_total_in_candidates_not_selected_count",
        "selected_safe_total_but_gold_differs_count",
        "unknown_wrong_count",
        "review_required_count",
        "uncertain_gold_count",
        "source_not_available_count",
        "serialized_gap_count",
    ]
    payload: dict[str, Any] = {}
    for key in keys:
        value = _to_number(experiment.get(key)) - _to_number(baseline.get(key))
        payload[key] = round(value, 6) if key in {"precision", "recall"} else int(round(value))
    return payload


def _reason_delta(
    baseline: dict[str, Any],
    experiment: dict[str, Any],
) -> list[dict[str, Any]]:
    base_counts = Counter(baseline.get("error_reason_counts", {}) or {})
    exp_counts = Counter(experiment.get("error_reason_counts", {}) or {})
    rows = []
    for reason in sorted(set(base_counts) | set(exp_counts)):
        rows.append(
            {
                "reason": reason,
                "baseline_count": base_counts[reason],
                "experiment_count": exp_counts[reason],
                "delta": exp_counts[reason] - base_counts[reason],
            }
        )
    return rows


def _gate_result(
    *,
    baseline: dict[str, Any],
    experiment: dict[str, Any],
    delta: dict[str, Any],
    selected_counts: dict[str, int],
    selected_status: str,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, detail: str, severity: str = "fail") -> None:
        checks.append(
            {
                "check": name,
                "passed": passed,
                "severity": severity,
                "detail": detail,
            }
        )

    add_check(
        "evaluated_document_count_compatible",
        baseline["evaluated_document_count"] == experiment["evaluated_document_count"],
        (
            f"baseline={baseline['evaluated_document_count']} "
            f"experiment={experiment['evaluated_document_count']}"
        ),
    )
    add_check(
        "wrong_count_not_increased",
        delta["wrong_count"] <= args.max_allowed_total_rate_wrong_delta,
        (
            f"delta={delta['wrong_count']} "
            f"max_allowed={args.max_allowed_total_rate_wrong_delta}"
        ),
    )
    add_check(
        "high_confidence_wrong_not_increased",
        delta["high_confidence_wrong_count"]
        <= args.max_allowed_high_confidence_wrong_delta,
        (
            f"delta={delta['high_confidence_wrong_count']} "
            f"max_allowed={args.max_allowed_high_confidence_wrong_delta}"
        ),
    )
    add_check(
        "selected_wrong_money_context_not_increased",
        delta["selected_wrong_money_context_count"] <= 0,
        f"delta={delta['selected_wrong_money_context_count']}",
    )
    missing_allowed = args.allow_review_only_differences and delta["wrong_count"] <= 0
    add_check(
        "missing_count_not_increased",
        delta["missing_count"] <= 0 or missing_allowed,
        f"delta={delta['missing_count']}",
    )
    selected_available = selected_status == "available"
    if args.require_private_selected_values_local_only:
        add_check(
            "private_selected_values_available",
            selected_available,
            f"selected_value_comparison_status={selected_status}",
        )
    selected_value_change_count = selected_counts["selected_value_changed_count"]
    if args.fail_on_selected_rate_regression and selected_available:
        add_check(
            "selected_values_unchanged",
            selected_value_change_count <= args.max_allowed_selected_value_changes,
            (
                f"changed={selected_value_change_count} "
                f"max_allowed={args.max_allowed_selected_value_changes}"
            ),
        )
    else:
        add_check(
            "selected_values_compared",
            selected_available,
            f"selected_value_comparison_status={selected_status}",
            severity="warn",
        )

    failed_checks = [
        check for check in checks if check["severity"] == "fail" and not check["passed"]
    ]
    gate = {
        "passed": not failed_checks,
        "failed_check_count": len(failed_checks),
        "warning_count": len(
            [check for check in checks if check["severity"] == "warn" and not check["passed"]]
        ),
        "selected_value_comparison_status": selected_status,
        "private_values_included": bool(args.include_private_values_local_only),
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }
    return gate, checks


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_dict_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _write_field_delta_csv(path: Path, baseline: dict, experiment: dict, delta: dict) -> None:
    rows = []
    for metric in delta:
        rows.append(
            {
                "metric": metric,
                "baseline": baseline.get(metric, ""),
                "experiment": experiment.get(metric, ""),
                "delta": delta.get(metric, ""),
            }
        )
    _write_dict_csv(path, rows, ["metric", "baseline", "experiment", "delta"])


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    gate = payload["gate"]
    lines = [
        "# RateCon Private Selected-Rate Aggregate Compare",
        "",
        "This local-only gate compares existing evaluation outputs for `total_carrier_rate`.",
        "Selected private values are redacted unless explicitly included with a local-only flag.",
        "",
        f"- baseline_label: {summary['baseline_label']}",
        f"- experiment_label: {summary['experiment_label']}",
        f"- gate_passed: {gate['passed']}",
        f"- selected_value_comparison_status: {gate['selected_value_comparison_status']}",
        f"- private_values_included: {gate['private_values_included']}",
        f"- selected_value_changed_count: {summary['selected_value_changed_count']}",
        f"- wrong_count_delta: {summary['delta']['wrong_count']}",
        f"- high_confidence_wrong_delta: {summary['delta']['high_confidence_wrong_count']}",
        (
            "- selected_wrong_money_context_delta: "
            f"{summary['delta']['selected_wrong_money_context_count']}"
        ),
        f"- missing_count_delta: {summary['delta']['missing_count']}",
        f"- pdf_processing_attempted: {gate['pdf_processing_attempted']}",
        f"- ocr_attempted: {gate['ocr_attempted']}",
        f"- google_called: {gate['google_called']}",
        f"- model_or_cloud_called: {gate['model_or_cloud_called']}",
        "",
        "## Gate Checks",
        "",
        "| check | passed | severity | detail |",
        "| --- | --- | --- | --- |",
    ]
    for check in payload["gate_checks"]:
        lines.append(
            f"| {check['check']} | {str(check['passed']).lower()} | "
            f"{check['severity']} | {check['detail']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compare_private_selected_rate_aggregates(args: argparse.Namespace) -> dict[str, Any]:
    baseline_dir = _resolve(args.baseline_eval_dir)
    experiment_dir = _resolve(args.experiment_eval_dir)
    baseline_summary = _load_json(baseline_dir / SUMMARY_FILE_NAME)
    experiment_summary = _load_json(experiment_dir / SUMMARY_FILE_NAME)

    baseline = _field_summary(baseline_summary, baseline_dir)
    experiment = _field_summary(experiment_summary, experiment_dir)
    delta = _delta(baseline, experiment)
    reason_delta = _reason_delta(baseline, experiment)

    baseline_row_status, baseline_rows = _load_selected_rows(baseline_dir)
    experiment_row_status, experiment_rows = _load_selected_rows(experiment_dir)
    if baseline_row_status == "available" and experiment_row_status == "available":
        selected_status = "available"
        selected_counts, changed_documents = _compare_selected_rows(
            baseline_rows,
            experiment_rows,
            include_private_values=args.include_private_values_local_only,
        )
    else:
        selected_status = "private_values_unavailable"
        selected_counts = {
            "selected_value_changed_count": 0,
            "selected_source_changed_count": 0,
            "selected_confidence_bucket_changed_count": 0,
            "selected_money_context_changed_count": 0,
            "changed_document_count": 0,
        }
        changed_documents = []

    gate, checks = _gate_result(
        baseline=baseline,
        experiment=experiment,
        delta=delta,
        selected_counts=selected_counts,
        selected_status=selected_status,
        args=args,
    )

    summary = {
        "schema_version": "ratecon_private_selected_rate_aggregate_compare_v1",
        "field": total_carrier_rate_field,
        "baseline_label": args.baseline_label,
        "experiment_label": args.experiment_label,
        "baseline_eval_dir": str(baseline_dir),
        "experiment_eval_dir": str(experiment_dir),
        "baseline": baseline,
        "experiment": experiment,
        "delta": delta,
        **selected_counts,
        "gate_passed": gate["passed"],
        "selected_value_comparison_status": gate["selected_value_comparison_status"],
        "private_values_included": gate["private_values_included"],
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }
    review_items = [
        {
            "item": check["check"],
            "severity": check["severity"],
            "passed": check["passed"],
            "detail": check["detail"],
        }
        for check in checks
        if not check["passed"]
    ]
    return {
        "summary": summary,
        "gate": gate,
        "gate_checks": checks,
        "error_reason_delta": reason_delta,
        "changed_documents": changed_documents,
        "review_items": review_items,
    }


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "private_selected_rate_aggregate_compare_summary.json",
        payload,
    )
    _write_report(
        output_dir / "private_selected_rate_aggregate_compare_report.md",
        payload,
    )
    _write_field_delta_csv(
        output_dir / "private_selected_rate_field_metrics_delta.csv",
        payload["summary"]["baseline"],
        payload["summary"]["experiment"],
        payload["summary"]["delta"],
    )
    _write_dict_csv(
        output_dir / "private_selected_rate_error_reason_delta.csv",
        payload["error_reason_delta"],
        ["reason", "baseline_count", "experiment_count", "delta"],
    )
    _write_dict_csv(
        output_dir / "private_selected_rate_changed_documents.csv",
        payload["changed_documents"],
        [
            "document_id",
            "selected_value_changed",
            "selected_source_changed",
            "selected_confidence_bucket_changed",
            "selected_money_context_changed",
            "selected_status_changed",
            "baseline_selected_value",
            "experiment_selected_value",
            "baseline_selected_source",
            "experiment_selected_source",
            "baseline_selected_confidence_bucket",
            "experiment_selected_confidence_bucket",
            "baseline_selected_money_context",
            "experiment_selected_money_context",
            "baseline_selected_status",
            "experiment_selected_status",
            "private_values_included",
        ],
    )
    _write_dict_csv(
        output_dir / "private_selected_rate_gate_result.csv",
        payload["gate_checks"],
        ["check", "passed", "severity", "detail"],
    )
    _write_dict_csv(
        output_dir / "private_selected_rate_review_items.csv",
        payload["review_items"],
        ["item", "severity", "passed", "detail"],
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_private_local_run:
        print("--confirm-private-local-run is required", file=sys.stderr)
        return 2
    try:
        output_dir = _require_output_under_local_outputs(_resolve(args.output_dir))
        payload = compare_private_selected_rate_aggregates(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"private_selected_rate_aggregate_compare_error: {exc}", file=sys.stderr)
        return 1 if args.confirm_private_local_run else 2

    write_outputs(output_dir, payload)
    summary = payload["summary"]
    print("RateCon private selected-rate aggregate compare")
    print(f"field: {summary['field']}")
    print(f"gate_passed: {payload['gate']['passed']}")
    print(f"wrong_count_delta: {summary['delta']['wrong_count']}")
    print(f"high_confidence_wrong_delta: {summary['delta']['high_confidence_wrong_count']}")
    print(
        "selected_wrong_money_context_delta: "
        f"{summary['delta']['selected_wrong_money_context_count']}"
    )
    print(f"selected_value_comparison_status: {summary['selected_value_comparison_status']}")
    print(f"selected_value_changed_count: {summary['selected_value_changed_count']}")
    print(f"private_values_included: {summary['private_values_included']}")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    print(f"output_dir: {output_dir}")
    return 0 if payload["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
