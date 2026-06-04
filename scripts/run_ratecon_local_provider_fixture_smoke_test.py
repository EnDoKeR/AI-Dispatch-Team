"""Run a sanitized fixture-only local-provider readiness smoke test.

The workflow exercises provider listing, config validation, readiness gates,
stub submission generation, and model-assisted benchmarking without executing
models, reading PDFs, OCR, or private files.
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

from app.document_ai.ratecon_hybrid_contract import is_under_local_outputs  # noqa: E402
from app.document_ai.ratecon_local_provider_readiness import RateConLocalProviderReadinessError  # noqa: E402
from app.document_ai.ratecon_model_provider_registry import (  # noqa: E402
    list_available_providers,
    validate_provider_selection,
)
from scripts.create_ratecon_model_assisted_stub_outputs import create_model_assisted_stub_outputs  # noqa: E402
from scripts.ratecon_local_provider_readiness_cli import dry_run_report_command  # noqa: E402
from scripts.run_ratecon_model_assisted_benchmark import run_model_assisted_benchmark  # noqa: E402


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_local_provider_fixture_smoke_test")
READINESS_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_readiness"
PROVIDER_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_provider"
MODEL_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_assisted"
HYBRID_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_hybrid"


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _fixture_baseline(path: Path) -> Path:
    payload = {
        "schema_version": "ratecon_hybrid_manual_closeout_summary_v1",
        "completed_document_count": 1,
        "load_number": {"correct": 1, "wrong": 0, "missing": 0, "not_applicable_non_rc": 0},
        "total_carrier_rate": {"correct": 1, "wrong": 0, "missing": 0, "not_applicable_non_rc": 0},
        "pickup_stops": {
            "exact_complete": 1,
            "matches_uncertain_gold_review_required": 0,
            "unsafe_wrong": 0,
            "missing_review_required": 0,
            "not_applicable": 0,
        },
        "delivery_stops": {
            "exact_complete": 1,
            "matches_uncertain_gold_review_required": 0,
            "unsafe_wrong": 0,
            "missing_review_required": 0,
            "not_applicable": 0,
        },
    }
    _write_json(path, payload)
    return path


def run_fixture_smoke_test(*, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise RateConLocalProviderReadinessError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)
    provider_config = PROVIDER_FIXTURES / "valid_stub_provider_config.json"
    readiness_file = READINESS_FIXTURES / "valid_fixture_only_readiness.json"
    config_payload = json.loads(provider_config.read_text(encoding="utf-8"))
    providers = list_available_providers()
    config_validation = validate_provider_selection(config_payload)
    readiness_output = resolved_output / "readiness_dry_run"
    dry_run_report_command(readiness_file, provider_config, readiness_output)
    stub_output = resolved_output / "stub_outputs"
    stub_summary = create_model_assisted_stub_outputs(
        templates_dir=MODEL_FIXTURES,
        output_dir=stub_output,
        fixture_mode=False,
        provider_config=provider_config,
        copy_manual_template_shape=True,
        max_docs=1,
    )
    baseline = _fixture_baseline(resolved_output / "fixture_manual_baseline.json")
    benchmark_summary = run_model_assisted_benchmark(
        model_submissions_dir=stub_output,
        gold_dir=HYBRID_FIXTURES / "gold_labels_sanitized",
        audit=HYBRID_FIXTURES / "audit_sanitized" / "ratecon_shadow_document_pipeline_audit.jsonl",
        manual_baseline_summary=baseline,
        output_dir=resolved_output / "model_assisted_benchmark",
        allow_unfilled_manual_templates=True,
        write_review_packets=False,
    )
    gate_rows = json.loads((readiness_output / "readiness_summary.json").read_text(encoding="utf-8"))
    artifacts = [
        {"artifact": "readiness_report.md", "path": str(readiness_output / "readiness_report.md")},
        {"artifact": "model_assisted_stub_summary.json", "path": str(stub_output / "model_assisted_stub_summary.json")},
        {"artifact": "model_assisted_benchmark_summary.json", "path": str(resolved_output / "model_assisted_benchmark" / "model_assisted_benchmark_summary.json")},
    ]
    summary = {
        "schema_version": "ratecon_local_provider_fixture_smoke_summary_v1",
        "status": "fixture_smoke_passed_no_model_execution",
        "provider_count": len(providers),
        "providers_listed_count": len(providers),
        "provider_config_valid": config_validation.valid,
        "provider_config_status": "valid" if config_validation.valid else "invalid",
        "readiness_status": gate_rows.get("status"),
        "provider_readiness_status": gate_rows.get("provider_readiness_status"),
        "stub_submission_count": stub_summary.get("submission_count", 0),
        "benchmark_model_status": benchmark_summary.get("model_status"),
        "benchmark_status": benchmark_summary.get("model_status"),
        "safety_violation_count": benchmark_summary.get("safety_violation_count", 0),
        "model_execution_attempted": False,
        "external_api_calls_attempted": False,
        "external_call_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
        "private_data_used": False,
        "production_output_changed": False,
        "gold_labels_edited": False,
        "hybrid_templates_edited": False,
    }
    _write_json(resolved_output / "fixture_smoke_summary.json", summary)
    report = [
        "# RateCon Local Provider Fixture Smoke Test",
        "",
        "Status: fixture_smoke_passed_no_model_execution",
        "",
        "This sanitized fixture workflow made no model call, processed no PDFs, ran no OCR, and changed no production output.",
        "",
        f"- providers listed: {len(providers)}",
        f"- provider config valid: {config_validation.valid}",
        f"- readiness status: {summary['readiness_status']}",
        f"- provider readiness status: {summary['provider_readiness_status']}",
        f"- stub submissions: {summary['stub_submission_count']}",
        f"- benchmark model status: {summary['benchmark_model_status']}",
    ]
    (resolved_output / "fixture_smoke_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    gate_source = readiness_output / "readiness_gate_results.csv"
    (resolved_output / "fixture_smoke_gate_results.csv").write_text(gate_source.read_text(encoding="utf-8"), encoding="utf-8")
    _write_csv(resolved_output / "fixture_smoke_artifacts_index.csv", artifacts, ["artifact", "path"])
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run sanitized RateCon local provider fixture smoke test.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for fixture smoke testing")
    summary = run_fixture_smoke_test(output_dir=args.output_dir)
    print("RateCon local provider fixture smoke test")
    print(f"status: {summary['status']}")
    print(f"provider_config_valid: {summary['provider_config_valid']}")
    print(f"readiness_status: {summary['readiness_status']}")
    print("ai_model_invocation_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
