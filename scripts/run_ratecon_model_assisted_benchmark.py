"""Benchmark local-only RateCon model-assisted submissions.

This wrapper validates model-assisted submission JSON files, extracts embedded
hybrid results into a local-only output folder, runs the existing hybrid
benchmark, and compares aggregate metrics to the validated manual baseline. It
does not call AI models, cloud APIs, OCR, PDF readers, or production extraction.
"""

from __future__ import annotations

import argparse
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
)
from app.document_ai.ratecon_hybrid_contract import is_under_local_outputs  # noqa: E402
from app.document_ai.ratecon_model_assisted_contract import (  # noqa: E402
    safe_submission_shape,
    validate_model_assisted_submission,
)
from scripts.run_ratecon_hybrid_benchmark import run_hybrid_benchmark  # noqa: E402


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_model_assisted_benchmark")
MODEL_STATUSES = {
    "model_output_not_ready",
    "model_output_schema_failed",
    "model_output_safety_failed",
    "model_output_below_manual_baseline",
    "model_output_matches_manual_baseline",
    "model_output_exceeds_manual_baseline_review_only",
}


class ModelAssistedBenchmarkError(ValueError):
    """Raised when model-assisted benchmarking would be unsafe or invalid."""


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


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _safe_file_stem(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in value)
    return safe or "MODEL_ASSISTED_RESULT"


def _submission_paths(model_submissions_dir: Path) -> list[Path]:
    resolved = _repo_relative(model_submissions_dir)
    if not resolved.exists():
        raise ModelAssistedBenchmarkError("Model submissions directory does not exist.")
    return sorted(resolved.glob("*.model_assisted_submission.json"))


def _extract_results(
    *,
    paths: list[Path],
    extracted_dir: Path,
    allow_unfilled_manual_templates: bool,
    include_private_values_local_only: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    extracted_dir.mkdir(parents=True, exist_ok=True)
    validation_rows: list[dict[str, Any]] = []
    safety_rows: list[dict[str, Any]] = []
    extracted_count = 0
    for path in paths:
        submission = _read_json(path)
        validation = validate_model_assisted_submission(
            submission,
            strict_hybrid=not allow_unfilled_manual_templates,
            include_private_values_local_only=include_private_values_local_only,
        )
        shape = safe_submission_shape(submission if isinstance(submission, dict) else {})
        validation_rows.append(
            {
                "submission_file": path.name,
                "submission_id": shape.get("submission_id"),
                "document_id": shape.get("document_id"),
                "provider_type": shape.get("provider_type"),
                "valid": str(validation.valid).lower(),
                "errors": "; ".join(validation.errors),
            }
        )
        for error in validation.errors:
            if any(token in error for token in ("external_call_made", "offline_only", "auto_accept", "requires_human_review", "private_local_only")):
                safety_rows.append(
                    {
                        "submission_file": path.name,
                        "submission_id": shape.get("submission_id"),
                        "document_id": shape.get("document_id"),
                        "violation": error,
                        "recommended_action": "reject_submission",
                    }
                )
        if not validation.valid:
            continue
        result = submission.get("result") if isinstance(submission, dict) else None
        if not isinstance(result, dict):
            continue
        if not include_private_values_local_only:
            result = dict(result)
            for key in ("file_name", "file_name_or_label", "file_hash", "file_hash_prefix", "document_label"):
                result.pop(key, None)
        document_id = _text(result.get("document_id")) or path.stem
        _write_json(extracted_dir / f"{_safe_file_stem(document_id)}.hybrid_result.json", result)
        extracted_count += 1
    return validation_rows, safety_rows, extracted_count


def _manual_metric(summary: dict[str, Any], field_name: str, metric: str) -> int:
    field = summary.get(field_name) if isinstance(summary.get(field_name), dict) else {}
    if not field and isinstance(summary.get("field_metrics"), dict):
        field = summary.get("field_metrics", {}).get(field_name, {})
    return _safe_int(field.get(metric) if isinstance(field, dict) else 0)


def _manual_stop_metric(summary: dict[str, Any], field_name: str, metric: str) -> int:
    field = summary.get(field_name) if isinstance(summary.get(field_name), dict) else {}
    if not field and isinstance(summary.get("stop_metrics"), dict):
        field = summary.get("stop_metrics", {}).get(field_name, {})
    return _safe_int(field.get(metric) if isinstance(field, dict) else 0)


def _benchmark_metric(summary: dict[str, Any], field_name: str, metric: str) -> int:
    return _safe_int((summary.get("field_metrics", {}).get(field_name, {}) or {}).get(metric))


def _benchmark_stop_metric(summary: dict[str, Any], field_name: str, metric: str) -> int:
    return _safe_int((summary.get("stop_metrics", {}).get(field_name, {}) or {}).get(metric))


def _baseline_rows(benchmark_summary: dict[str, Any], manual_baseline: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in (FIELD_LOAD_NUMBER, FIELD_TOTAL_CARRIER_RATE):
        for metric in ("correct", "wrong", "missing", "not_applicable_non_rc"):
            rows.append(
                {
                    "field": field,
                    "metric": metric,
                    "model_value": _benchmark_metric(benchmark_summary, field, metric),
                    "manual_baseline_value": _manual_metric(manual_baseline, field, metric),
                    "delta": _benchmark_metric(benchmark_summary, field, metric) - _manual_metric(manual_baseline, field, metric),
                }
            )
    for field in (FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS):
        for metric in ("exact_complete", "matches_uncertain_gold_review_required", "unsafe_wrong", "missing_review_required", "not_applicable"):
            rows.append(
                {
                    "field": field,
                    "metric": metric,
                    "model_value": _benchmark_stop_metric(benchmark_summary, field, metric),
                    "manual_baseline_value": _manual_stop_metric(manual_baseline, field, metric),
                    "delta": _benchmark_stop_metric(benchmark_summary, field, metric) - _manual_stop_metric(manual_baseline, field, metric),
                }
            )
    return rows


def _classify_model_status(
    *,
    benchmark_summary: dict[str, Any],
    valid_submission_count: int,
    invalid_submission_count: int,
    safety_violation_count: int,
    manual_baseline: dict[str, Any],
) -> str:
    one_screen = benchmark_summary.get("one_screen_summary", {}) if isinstance(benchmark_summary, dict) else {}
    if invalid_submission_count:
        return "model_output_schema_failed"
    if safety_violation_count or _safe_int(one_screen.get("stop_auto_accept_violations")) or _safe_int(one_screen.get("missing_evidence")):
        return "model_output_safety_failed"
    if not valid_submission_count or _safe_int(benchmark_summary.get("unfilled_manual_template_count")):
        return "model_output_not_ready"
    if _safe_int(one_screen.get("unsafe_wrong_stops")):
        return "model_output_below_manual_baseline"
    model_docs = _safe_int(benchmark_summary.get("hybrid_result_count"))
    baseline_docs = _safe_int(manual_baseline.get("completed_document_count") or manual_baseline.get("aggregate_document_count"))
    model_load_correct = _benchmark_metric(benchmark_summary, FIELD_LOAD_NUMBER, "correct")
    baseline_load_correct = _manual_metric(manual_baseline, FIELD_LOAD_NUMBER, "correct")
    model_rate_correct = _benchmark_metric(benchmark_summary, FIELD_TOTAL_CARRIER_RATE, "correct")
    baseline_rate_correct = _manual_metric(manual_baseline, FIELD_TOTAL_CARRIER_RATE, "correct")
    if baseline_docs and model_docs < baseline_docs:
        return "model_output_below_manual_baseline"
    if model_load_correct < baseline_load_correct or model_rate_correct < baseline_rate_correct:
        return "model_output_below_manual_baseline"
    if model_load_correct == baseline_load_correct and model_rate_correct == baseline_rate_correct:
        return "model_output_matches_manual_baseline"
    return "model_output_exceeds_manual_baseline_review_only"


def run_model_assisted_benchmark(
    *,
    model_submissions_dir: Path,
    gold_dir: Path,
    audit: Path | None,
    manual_baseline_summary: Path | None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    allow_unfilled_manual_templates: bool = False,
    write_review_packets: bool = False,
    include_private_values_local_only: bool = False,
) -> dict[str, Any]:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise ModelAssistedBenchmarkError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)
    extracted_dir = resolved_output / "extracted_hybrid_results_local_only"
    paths = _submission_paths(model_submissions_dir)
    validation_rows, safety_rows, extracted_count = _extract_results(
        paths=paths,
        extracted_dir=extracted_dir,
        allow_unfilled_manual_templates=allow_unfilled_manual_templates,
        include_private_values_local_only=include_private_values_local_only,
    )
    benchmark_output_dir = resolved_output / "hybrid_benchmark"
    if extracted_count:
        benchmark_summary = run_hybrid_benchmark(
            hybrid_results_dir=extracted_dir,
            gold_dir=gold_dir,
            audit=audit,
            output_dir=benchmark_output_dir,
            allow_unfilled_manual_templates=allow_unfilled_manual_templates,
            write_review_packets=write_review_packets,
            include_private_values_local_only=include_private_values_local_only,
        )
    else:
        benchmark_summary = {
            "hybrid_result_count": 0,
            "schema_error_count": 0,
            "unfilled_manual_template_count": 0,
            "field_metrics": {},
            "stop_metrics": {},
            "one_screen_summary": {
                "missing_evidence": 0,
                "stop_auto_accept_violations": 0,
                "unsafe_wrong_stops": 0,
            },
        }
    manual_baseline = _read_json(manual_baseline_summary) if manual_baseline_summary else {}
    baseline_rows = _baseline_rows(benchmark_summary, manual_baseline) if manual_baseline else []
    invalid_count = sum(1 for row in validation_rows if row["valid"] != "true")
    model_status = _classify_model_status(
        benchmark_summary=benchmark_summary,
        valid_submission_count=extracted_count,
        invalid_submission_count=invalid_count,
        safety_violation_count=len(safety_rows),
        manual_baseline=manual_baseline,
    )
    summary = {
        "schema_version": "ratecon_model_assisted_benchmark_summary_v1",
        "model_status": model_status,
        "submission_count": len(paths),
        "valid_submission_count": extracted_count,
        "invalid_submission_count": invalid_count,
        "safety_violation_count": len(safety_rows),
        "manual_baseline_supplied": bool(manual_baseline),
        "benchmark_summary": benchmark_summary,
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
        "private_values_included": bool(include_private_values_local_only),
    }
    _write_json(resolved_output / "model_assisted_benchmark_summary.json", summary)
    _write_csv(
        resolved_output / "model_assisted_safety_violations.csv",
        safety_rows,
        ["submission_file", "submission_id", "document_id", "violation", "recommended_action"],
    )
    _write_csv(
        resolved_output / "model_assisted_submission_validation.csv",
        validation_rows,
        ["submission_file", "submission_id", "document_id", "provider_type", "valid", "errors"],
    )
    if baseline_rows:
        _write_csv(
            resolved_output / "model_assisted_baseline_comparison.csv",
            baseline_rows,
            ["field", "metric", "model_value", "manual_baseline_value", "delta"],
        )
    for source_name, target_name in (
        ("hybrid_field_metrics.csv", "model_assisted_field_metrics.csv"),
        ("hybrid_document_metrics.csv", "model_assisted_document_metrics.csv"),
    ):
        source = benchmark_output_dir / source_name
        if source.exists():
            (resolved_output / target_name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            (resolved_output / target_name).write_text("", encoding="utf-8")
    report = [
        "# RateCon Model-Assisted Benchmark Report",
        "",
        "This local-only benchmark made no AI, cloud, OCR, model, or PDF processing calls.",
        "",
        f"- model status: {model_status}",
        f"- submissions: {len(paths)}",
        f"- valid submissions: {extracted_count}",
        f"- invalid submissions: {invalid_count}",
        f"- safety violations: {len(safety_rows)}",
        f"- manual baseline supplied: {bool(manual_baseline)}",
        "",
        "Model output cannot be production auto-accepted in this phase, even if it matches the manual baseline.",
    ]
    (resolved_output / "model_assisted_benchmark_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark local-only RateCon model-assisted submissions.")
    parser.add_argument("--model-submissions-dir", type=Path, required=True)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--manual-baseline-summary", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--allow-unfilled-manual-templates", action="store_true")
    parser.add_argument("--write-review-packets", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local model-assisted benchmark")
    summary = run_model_assisted_benchmark(
        model_submissions_dir=args.model_submissions_dir,
        gold_dir=args.gold_dir,
        audit=args.audit,
        manual_baseline_summary=args.manual_baseline_summary,
        output_dir=args.output_dir,
        allow_unfilled_manual_templates=args.allow_unfilled_manual_templates,
        write_review_packets=args.write_review_packets,
        include_private_values_local_only=args.include_private_values_local_only,
    )
    print("RateCon model-assisted benchmark summary")
    print(f"submission_count: {summary['submission_count']}")
    print(f"valid_submission_count: {summary['valid_submission_count']}")
    print(f"model_status: {summary['model_status']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
