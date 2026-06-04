"""CLI for RateCon model provider registry and dry-run planning.

This script never executes a real provider. It lists descriptors, validates
safe configs, and writes dry-run plans under `.local_outputs`.
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
from app.document_ai.ratecon_model_provider_contract import RateConModelProviderError  # noqa: E402
from app.document_ai.ratecon_model_provider_registry import (  # noqa: E402
    dry_run_provider_plan,
    list_available_providers,
    validate_provider_selection,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_model_provider_dry_run")


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


def _template_count(templates_dir: Path) -> int:
    resolved = _repo_relative(templates_dir)
    if not resolved.exists():
        raise RateConModelProviderError("Templates directory does not exist.")
    return len(list(resolved.glob("*.hybrid_result.json")))


def list_providers_command() -> int:
    providers = list_available_providers()
    print(json.dumps({"providers": providers}, indent=2, sort_keys=True))
    return 0


def validate_config_command(config_path: Path) -> int:
    config = _read_json(config_path)
    validation = validate_provider_selection(config)
    print("RateCon model provider config validation")
    print(f"valid: {validation.valid}")
    if validation.errors:
        print("errors:")
        for error in validation.errors:
            print(f"- {error}")
    return 0 if validation.valid else 2


def dry_run_command(config_path: Path, templates_dir: Path, output_dir: Path) -> int:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise RateConModelProviderError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)
    config = _read_json(config_path)
    template_count = _template_count(templates_dir)
    plan = dry_run_provider_plan(config, template_count=template_count, output_dir=output_dir)
    _write_json(resolved_output / "provider_dry_run_plan.json", plan)
    _write_csv(
        resolved_output / "provider_safety_gates.csv",
        plan.get("safety_gate_results", []),
        ["gate", "status", "reason"],
    )
    lines = [
        "# RateCon Model Provider Dry Run",
        "",
        "No provider/model execution occurred.",
        "",
        f"- provider: {plan.get('provider', {}).get('provider_name')}",
        f"- config valid: {plan.get('config_valid')}",
        f"- template count: {template_count}",
        "- external API calls attempted: false",
        "- PDF processing attempted: false",
        "- OCR attempted: false",
        "- AI/model invocation attempted: false",
    ]
    (resolved_output / "provider_dry_run_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("RateCon model provider dry run")
    print(f"provider: {plan.get('provider', {}).get('provider_name')}")
    print(f"config_valid: {plan.get('config_valid')}")
    print(f"template_count: {template_count}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0 if plan.get("config_valid") else 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RateCon model provider registry CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-providers")
    validate = subparsers.add_parser("validate-config")
    validate.add_argument("--config", type=Path, required=True)
    validate.add_argument("--confirm-private-local-run", action="store_true")
    dry_run = subparsers.add_parser("dry-run")
    dry_run.add_argument("--config", type=Path, required=True)
    dry_run.add_argument("--templates-dir", type=Path, required=True)
    dry_run.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    dry_run.add_argument("--confirm-private-local-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "list-providers":
        return list_providers_command()
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for provider config validation and dry-run")
    if args.command == "validate-config":
        return validate_config_command(args.config)
    if args.command == "dry-run":
        return dry_run_command(args.config, args.templates_dir, args.output_dir)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
