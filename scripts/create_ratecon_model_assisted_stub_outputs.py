"""Create local-only stub RateCon model-assisted submission wrappers.

The script does not call AI models, cloud APIs, local model runtimes, OCR, PDF
readers, or production extraction. It wraps blank/stub hybrid results in the
model-assisted submission contract for future benchmark testing.
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

from app.document_ai.ratecon_hybrid_contract import (  # noqa: E402
    build_hybrid_result_template,
    build_stop_template,
    is_under_local_outputs,
)
from app.document_ai.ratecon_model_assisted_contract import (  # noqa: E402
    build_model_assisted_submission,
    validate_model_assisted_submission,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_model_assisted_stub_outputs")


class ModelAssistedStubOutputError(ValueError):
    """Raised when stub generation would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_file_stem(document_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in document_id)
    return safe or "MODEL_ASSISTED_STUB"


def _blank_field(field: Any) -> dict[str, Any]:
    if isinstance(field, dict):
        blank = dict(field)
    else:
        blank = {"value": None, "confidence": 0.0, "requires_human_review": True, "evidence_ids": []}
    blank["value"] = None
    blank["confidence"] = 0.0
    blank["requires_human_review"] = True
    blank["evidence_ids"] = []
    return blank


def _blank_stop(stop: dict[str, Any], role: str, stop_index: int) -> dict[str, Any]:
    blank = build_stop_template(role, stop_index)
    if isinstance(stop, dict):
        blank["role"] = stop.get("role") or role
        blank["stop_index"] = stop.get("stop_index") if isinstance(stop.get("stop_index"), int) else stop_index
    blank["requires_human_review"] = True
    blank["auto_accept"] = False
    return blank


def _stub_result_from_template(
    template: dict[str, Any],
    *,
    copy_manual_template_shape: bool,
    include_private_values_local_only: bool,
) -> dict[str, Any]:
    document_id = _text(template.get("document_id")) or "MODEL_ASSISTED_STUB"
    result = build_hybrid_result_template(document_id)
    result["model_provider"] = "local_stub"
    result["model_name"] = "model_assisted_no_model_stub_v1"
    result["document_type"] = _text(template.get("document_type")) or "unknown"
    result["private_local_only"] = True
    result["review_reasons"] = ["model_assisted_stub_unfilled", "phase_1_no_auto_accept"]
    if include_private_values_local_only:
        for key in ("file_name", "file_name_or_label", "file_hash", "file_hash_prefix"):
            if _text(template.get(key)):
                result[key] = template[key]
    if not copy_manual_template_shape:
        result["fields"]["pickup_stops"] = []
        result["fields"]["delivery_stops"] = []
        return result
    fields = template.get("fields") if isinstance(template.get("fields"), dict) else {}
    result["fields"]["load_number"] = _blank_field(fields.get("load_number"))
    result["fields"]["total_carrier_rate"] = _blank_field(fields.get("total_carrier_rate"))
    for field_name, role in (("pickup_stops", "pickup"), ("delivery_stops", "delivery")):
        stops = fields.get(field_name) or []
        if isinstance(stops, list) and stops:
            result["fields"][field_name] = [
                _blank_stop(stop if isinstance(stop, dict) else {}, role, index)
                for index, stop in enumerate(stops, start=1)
            ]
        else:
            result["fields"][field_name] = [] if result["document_type"] in {"bol_pod", "non_rate_confirmation"} else [build_stop_template(role, 1)]
    result["evidence"] = []
    return result


def _template_paths(templates_dir: Path, fixture_mode: bool) -> list[Path]:
    resolved = _repo_relative(templates_dir)
    if not resolved.exists():
        raise ModelAssistedStubOutputError("Templates directory does not exist.")
    patterns = ["*.hybrid_result.json"]
    if fixture_mode:
        patterns.append("*.json")
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(resolved.glob(pattern)))
    return sorted(set(paths))


def create_model_assisted_stub_outputs(
    *,
    templates_dir: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    fixture_mode: bool = False,
    provider_type: str = "stub",
    copy_manual_template_shape: bool = False,
    include_private_values_local_only: bool = False,
    max_docs: int | None = None,
) -> dict[str, Any]:
    if provider_type != "stub":
        raise ModelAssistedStubOutputError("Only provider-type stub is supported in this scaffold.")
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise ModelAssistedStubOutputError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)
    paths = _template_paths(templates_dir, fixture_mode)
    if max_docs is not None:
        paths = paths[:max_docs]
    index_rows: list[dict[str, Any]] = []
    invalid_count = 0
    for path in paths:
        template = _read_json(path)
        result = _stub_result_from_template(
            template,
            copy_manual_template_shape=copy_manual_template_shape,
            include_private_values_local_only=include_private_values_local_only,
        )
        document_id = _text(result.get("document_id")) or path.stem
        submission = build_model_assisted_submission(
            result,
            submission_id=f"stub_{_safe_file_stem(document_id)}",
            run_id="model_assisted_stub_run_v1",
            provider_type="stub",
            provider_name="local_no_model_stub",
        )
        validation = validate_model_assisted_submission(submission, strict_hybrid=False)
        if not validation.valid:
            invalid_count += 1
        output_name = f"{_safe_file_stem(document_id)}.model_assisted_submission.json"
        _write_json(resolved_output / output_name, submission)
        index_rows.append(
            {
                "document_id": document_id,
                "submission_file": output_name,
                "provider_type": "stub",
                "external_call_made": "false",
                "pdf_processing_attempted": "false",
                "ocr_attempted": "false",
                "private_values_included": str(bool(include_private_values_local_only)).lower(),
                "valid_contract": str(validation.valid).lower(),
            }
        )
    with (resolved_output / "model_assisted_stub_index.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(index_rows[0]) if index_rows else ["document_id"])
        writer.writeheader()
        writer.writerows(index_rows)
    summary = {
        "schema_version": "ratecon_model_assisted_stub_summary_v1",
        "submission_count": len(index_rows),
        "valid_submission_count": len(index_rows) - invalid_count,
        "invalid_submission_count": invalid_count,
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
        "private_values_included": bool(include_private_values_local_only),
    }
    _write_json(resolved_output / "model_assisted_stub_summary.json", summary)
    readme = """# RateCon Model-Assisted Stub Outputs

These local-only files are scaffold submissions for testing the model-assisted
benchmark harness. No model, cloud API, OCR, PDF reader, or private document
processing was invoked.

The embedded hybrid results are intentionally unfilled by default. Benchmark
them with `scripts/run_ratecon_model_assisted_benchmark.py`.
"""
    (resolved_output / "model_assisted_stub_readme.md").write_text(readme, encoding="utf-8")
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create local-only RateCon model-assisted stub submissions.")
    parser.add_argument("--templates-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--provider-type", default="stub")
    parser.add_argument("--copy-manual-template-shape", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--max-docs", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local model-assisted stub generation")
    summary = create_model_assisted_stub_outputs(
        templates_dir=args.templates_dir,
        output_dir=args.output_dir,
        fixture_mode=args.fixture_mode,
        provider_type=args.provider_type,
        copy_manual_template_shape=args.copy_manual_template_shape,
        include_private_values_local_only=args.include_private_values_local_only,
        max_docs=args.max_docs,
    )
    print("RateCon model-assisted stub summary")
    print(f"submission_count: {summary['submission_count']}")
    print(f"valid_submission_count: {summary['valid_submission_count']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
