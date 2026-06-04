"""Create a local-only RateCon provider readiness evidence pack.

The evidence pack bundles readiness validation, provider config validation,
registry blockers, fixture smoke status, and artifact references. It never
executes models, processes PDFs, performs OCR, edits gold labels, or edits
hybrid templates.
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
from app.document_ai.ratecon_local_provider_evidence_pack import (  # noqa: E402
    RateConLocalProviderEvidencePackError,
    build_artifact_index,
    build_evidence_pack,
    validate_evidence_pack,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_local_provider_evidence_pack")


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


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


def _require_local_output(output_dir: Path) -> Path:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise RateConLocalProviderEvidencePackError("Output directory must be under .local_outputs.")
    resolved = _repo_relative(output_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _report_lines(pack: dict[str, Any]) -> list[str]:
    return [
        "# RateCon Local Provider Evidence Pack",
        "",
        "This fixture-only evidence pack made no model, cloud, PDF, OCR, gold-label, or template-edit calls.",
        "",
        f"- recommendation: {pack.get('recommendation')}",
        f"- readiness status: {pack.get('readiness_status')}",
        f"- provider registry status: {pack.get('provider_registry_status')}",
        f"- provider config status: {pack.get('provider_config_status')}",
        f"- fixture smoke status: {pack.get('fixture_smoke_status')}",
        f"- blockers: {len(pack.get('blockers', []))}",
        f"- warnings: {len(pack.get('warnings', []))}",
        "",
        "Recommendation note: this does not approve model implementation. It only supports proposing a separate local-provider design PR.",
        "",
        "Safety flags:",
        f"- model execution attempted: {pack.get('model_execution_attempted')}",
        f"- PDF processing attempted: {pack.get('pdf_processing_attempted')}",
        f"- OCR attempted: {pack.get('ocr_attempted')}",
        f"- external call attempted: {pack.get('external_call_attempted')}",
        f"- private data used: {pack.get('private_data_used')}",
    ]


def create_evidence_pack_outputs(
    *,
    readiness_file: Path,
    provider_config: Path,
    smoke_dir: Path,
    readiness_report_dir: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_fixture_benchmark: bool = False,
    provider_name: str | None = None,
    fail_on_warning: bool = False,
    redact_default: bool = True,
) -> dict[str, Any]:
    if not redact_default:
        raise RateConLocalProviderEvidencePackError("redact-default must remain true.")
    resolved_output = _require_local_output(output_dir)
    readiness_payload = _read_json(readiness_file)
    provider_payload = _read_json(provider_config)
    if provider_name:
        provider_payload = dict(provider_payload)
        provider_payload["provider_name"] = provider_name
    resolved_smoke_dir = _repo_relative(smoke_dir)
    resolved_readiness_report_dir = _repo_relative(readiness_report_dir)
    smoke_summary = _read_json(resolved_smoke_dir / "fixture_smoke_summary.json")
    readiness_summary = _read_json(resolved_readiness_report_dir / "readiness_summary.json")
    artifacts = build_artifact_index(
        readiness_file=readiness_file,
        provider_config=provider_config,
        smoke_dir=smoke_dir,
        readiness_report_dir=readiness_report_dir,
        include_fixture_benchmark=include_fixture_benchmark,
    )
    pack = build_evidence_pack(
        readiness_payload=readiness_payload,
        provider_config=provider_payload,
        smoke_summary=smoke_summary if smoke_summary else None,
        readiness_report_summary=readiness_summary if readiness_summary else None,
        artifact_index=artifacts,
        fail_on_warning=fail_on_warning,
    )
    validation = validate_evidence_pack(pack)
    if validation.errors and pack["recommendation"] != "reject":
        pack["blockers"] = list(dict.fromkeys(list(pack.get("blockers", [])) + list(validation.errors)))
        pack["recommendation"] = "reject"
    _write_json(resolved_output / "local_provider_evidence_pack_summary.json", pack)
    (resolved_output / "local_provider_evidence_pack_report.md").write_text("\n".join(_report_lines(pack)) + "\n", encoding="utf-8")
    _write_csv(
        resolved_output / "local_provider_evidence_gate_results.csv",
        pack.get("gate_results", []),
        ["gate", "status", "reason"],
    )
    _write_csv(
        resolved_output / "local_provider_evidence_blockers.csv",
        [{"blocker": blocker} for blocker in pack.get("blockers", [])],
        ["blocker"],
    )
    _write_csv(
        resolved_output / "local_provider_evidence_next_actions.csv",
        [{"next_action": action} for action in pack.get("required_next_actions", [])],
        ["next_action"],
    )
    _write_csv(
        resolved_output / "local_provider_evidence_artifact_index.csv",
        pack.get("artifact_index", []),
        [
            "artifact_name",
            "artifact_type",
            "path",
            "exists",
            "safe_to_commit",
            "contains_private_values",
            "generated_from_fixtures_only",
            "required_for_review",
            "notes",
        ],
    )
    return pack


def _bool_text(value: str) -> bool:
    return str(value).strip().lower() not in {"false", "0", "no"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a RateCon local-provider evidence pack.")
    parser.add_argument("--readiness-file", type=Path, required=True)
    parser.add_argument("--provider-config", type=Path, required=True)
    parser.add_argument("--smoke-dir", type=Path, required=True)
    parser.add_argument("--readiness-report-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-fixture-benchmark", action="store_true")
    parser.add_argument("--provider-name", default=None)
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--redact-default", default="true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required")
    pack = create_evidence_pack_outputs(
        readiness_file=args.readiness_file,
        provider_config=args.provider_config,
        smoke_dir=args.smoke_dir,
        readiness_report_dir=args.readiness_report_dir,
        output_dir=args.output_dir,
        include_fixture_benchmark=args.include_fixture_benchmark,
        provider_name=args.provider_name,
        fail_on_warning=args.fail_on_warning,
        redact_default=_bool_text(args.redact_default),
    )
    print("RateCon local provider evidence pack")
    print(f"recommendation: {pack['recommendation']}")
    print(f"gate_count: {len(pack.get('gate_results', []))}")
    print(f"blocker_count: {len(pack.get('blockers', []))}")
    print(f"next_action_count: {len(pack.get('required_next_actions', []))}")
    print(f"artifact_count: {len(pack.get('artifact_index', []))}")
    print("ai_model_invocation_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    return 0 if pack["recommendation"] != "reject" else 2


if __name__ == "__main__":
    raise SystemExit(main())
