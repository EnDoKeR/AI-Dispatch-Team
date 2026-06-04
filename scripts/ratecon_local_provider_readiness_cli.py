"""CLI for RateCon local-provider readiness gates.

The CLI writes templates and dry-run reports only. It never executes models,
reads PDFs, performs OCR, edits gold labels, or edits hybrid templates.
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
from app.document_ai.ratecon_local_provider_readiness import (  # noqa: E402
    RateConLocalProviderReadinessError,
    default_readiness_template,
    readiness_summary,
    validate_readiness_payload,
)
from app.document_ai.ratecon_model_provider_registry import evaluate_provider_readiness  # noqa: E402


DEFAULT_TEMPLATE_OUTPUT = Path(".local_outputs/ratecon_local_provider_readiness_template.json")
DEFAULT_DRY_RUN_OUTPUT = Path(".local_outputs/ratecon_local_provider_readiness_dry_run")


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(_repo_relative(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _require_local_output(path: Path) -> Path:
    if not is_under_local_outputs(path, REPO_ROOT):
        raise RateConLocalProviderReadinessError("Output path must be under .local_outputs.")
    resolved = _repo_relative(path)
    if resolved.suffix:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    else:
        resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def create_template_command(output: Path) -> int:
    resolved = _require_local_output(output)
    payload = default_readiness_template()
    _write_json(resolved, payload)
    print("RateCon local provider readiness template")
    print(f"output: {output}")
    print("ai_model_invocation_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    return 0


def validate_command(readiness_file: Path) -> int:
    payload = _read_json(readiness_file)
    validation = validate_readiness_payload(payload)
    print("RateCon local provider readiness validation")
    print(f"status: {validation.status}")
    print(f"valid: {validation.valid}")
    if validation.errors:
        print("blocking_reasons:")
        for error in validation.errors:
            print(f"- {error}")
    return 0 if validation.valid else 2


def _report_lines(summary: dict[str, Any], evaluation: dict[str, Any]) -> list[str]:
    return [
        "# RateCon Local Provider Readiness Dry Run",
        "",
        "No model, cloud API, PDF processing, OCR, gold edit, or template edit occurred.",
        "",
        f"- readiness status: {summary.get('status')}",
        f"- provider readiness status: {evaluation.get('provider_readiness_status')}",
        f"- provider execution allowed: {evaluation.get('provider_execution_allowed')}",
        f"- provider config valid: {evaluation.get('provider_config_valid')}",
        f"- readiness valid: {evaluation.get('readiness_valid')}",
        "- local model placeholder executable: false",
        "- cloud model placeholder executable: false",
        "",
        "This branch only defines approval gates. A future local provider implementation requires a separate PR.",
    ]


def dry_run_report_command(readiness_file: Path, provider_config: Path, output_dir: Path) -> int:
    resolved = _require_local_output(output_dir)
    readiness_payload = _read_json(readiness_file)
    provider_payload = _read_json(provider_config)
    provider_name = str(provider_payload.get("provider_name") or readiness_payload.get("provider_name") or "").strip()
    evaluation = evaluate_provider_readiness(provider_name, readiness_payload, provider_payload)
    summary = readiness_summary(readiness_payload)
    summary.update(
        {
            "provider_readiness_status": evaluation["provider_readiness_status"],
            "provider_execution_allowed": evaluation["provider_execution_allowed"],
            "provider_config_valid": evaluation["provider_config_valid"],
            "provider_name": provider_name,
            "future_local_provider_requires_separate_pr": True,
        }
    )
    _write_json(resolved / "readiness_summary.json", summary)
    (resolved / "readiness_report.md").write_text("\n".join(_report_lines(summary, evaluation)) + "\n", encoding="utf-8")
    _write_csv(
        resolved / "readiness_gate_results.csv",
        evaluation.get("readiness_gate_results", []) + evaluation.get("provider_config_gate_results", []),
        ["gate", "status", "reason"],
    )
    _write_csv(
        resolved / "readiness_next_actions.csv",
        [{"next_action": action} for action in evaluation.get("required_next_actions", [])],
        ["next_action"],
    )
    print("RateCon local provider readiness dry run")
    print(f"readiness_status: {summary['status']}")
    print(f"provider_readiness_status: {summary['provider_readiness_status']}")
    print(f"provider_execution_allowed: {summary['provider_execution_allowed']}")
    print("ai_model_invocation_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    return 0 if summary["status"] == "fixture_only_plan_valid" and not summary["provider_execution_allowed"] else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RateCon local provider readiness CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-template")
    create.add_argument("--output", type=Path, default=DEFAULT_TEMPLATE_OUTPUT)
    create.add_argument("--confirm-private-local-run", action="store_true")
    validate = subparsers.add_parser("validate")
    validate.add_argument("--readiness-file", type=Path, required=True)
    validate.add_argument("--confirm-private-local-run", action="store_true")
    dry_run = subparsers.add_parser("dry-run-report")
    dry_run.add_argument("--readiness-file", type=Path, required=True)
    dry_run.add_argument("--provider-config", type=Path, required=True)
    dry_run.add_argument("--output-dir", type=Path, default=DEFAULT_DRY_RUN_OUTPUT)
    dry_run.add_argument("--confirm-private-local-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required")
    if args.command == "create-template":
        return create_template_command(args.output)
    if args.command == "validate":
        return validate_command(args.readiness_file)
    if args.command == "dry-run-report":
        return dry_run_report_command(args.readiness_file, args.provider_config, args.output_dir)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
