"""Local-only scaffold for future RateCon hybrid document understanding eval.

This script intentionally does not call AI models, cloud APIs, OCR providers, or
PDF processing. It writes a template under .local_outputs so future branches can
evaluate hybrid document-understanding outputs without changing production
extraction behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.ratecon_hybrid_contract import (  # noqa: E402
    HybridContractError,
    build_hybrid_result_template,
    build_stop_template,
    require_valid_hybrid_result,
    validate_hybrid_result,
    validate_stop,
)

DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_eval_stub")
SAFE_EVAL_SUMMARY_KEYS = {
    "load_number_summary",
    "total_carrier_rate_summary",
    "stop_metrics_consistent_summary",
    "stop_usability_summary",
    "stop_candidate_group_metrics",
}

class HybridEvalStubError(HybridContractError):
    """Raised when the local-only scaffold would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _is_under_local_outputs(path: Path) -> bool:
    resolved = _repo_relative(path)
    local_outputs = (REPO_ROOT / ".local_outputs").resolve()
    return resolved == local_outputs or local_outputs in resolved.parents


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _count_jsonl_lines(path: Path | None) -> int | None:
    if not path:
        return None
    resolved = _repo_relative(path)
    if not resolved.exists():
        return None
    count = 0
    with resolved.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _count_gold_files(gold_dir: Path | None) -> int | None:
    if not gold_dir:
        return None
    resolved = _repo_relative(gold_dir)
    if not resolved.exists() or not resolved.is_dir():
        return None
    return len(list(resolved.glob("*.gold.json")))


def _redact_string_values(value):
    if isinstance(value, dict):
        return {str(key): _redact_string_values(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_redact_string_values(child) for child in value]
    if isinstance(value, str):
        return "<redacted_string>"
    return value


def _safe_eval_summary(eval_dir: Path | None) -> dict:
    if not eval_dir:
        return {}
    summary_path = _repo_relative(eval_dir) / "ratecon_gold_evaluation_summary.json"
    if not summary_path.exists():
        return {}
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    safe = {
        key: _redact_string_values(payload[key])
        for key in sorted(SAFE_EVAL_SUMMARY_KEYS)
        if key in payload
    }
    return safe


def validate_stop_contract(stop: dict) -> None:
    errors = validate_stop(stop, require_evidence_for_values=False)
    if errors:
        raise HybridEvalStubError("; ".join(errors))


def validate_hybrid_result_contract(result: dict) -> None:
    validation = validate_hybrid_result(result, strict=False)
    if not validation.valid:
        raise HybridEvalStubError("; ".join(validation.errors))


def build_plan_summary(
    *,
    gold_dir: Path | None,
    audit: Path | None,
    eval_dir: Path | None,
    include_private_values_local_only: bool,
) -> dict:
    safe_eval = _safe_eval_summary(eval_dir)
    return {
        "schema_version": "ratecon_hybrid_eval_plan_summary_v1",
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ai_model_invocation_attempted": False,
        "private_values_included": bool(include_private_values_local_only),
        "private_values_printed": False,
        "gold_label_file_count": _count_gold_files(gold_dir),
        "audit_jsonl_record_count": _count_jsonl_lines(audit),
        "safe_eval_summary_loaded": bool(safe_eval),
        "safe_eval_summary_keys_loaded": sorted(safe_eval.keys()),
        "current_baseline": {
            "load_number": "25 correct / 1 wrong / 5 missing",
            "total_carrier_rate": "26 correct / 3 wrong / 2 missing",
            "pickup_selected_stops": "0 exact / 17 partial / 5 wrong / 3 missing",
            "delivery_selected_stops": "0 exact / 12 partial / 5 wrong / 4 missing",
        },
        "phase_1_policy": {
            "stops_review_required": True,
            "stop_auto_accept_allowed": False,
            "production_output_changed": False,
            "selected_stop_output_changed": False,
        },
        "next_steps": [
            "validate hybrid result JSON against contract",
            "compare review-only stop drafts separately from selected output",
            "require page/source evidence for every proposed field",
            "keep all stop drafts review-required in phase 1",
        ],
    }


def write_stub_outputs(
    *,
    output_dir: Path,
    gold_dir: Path | None = None,
    audit: Path | None = None,
    eval_dir: Path | None = None,
    include_private_values_local_only: bool = False,
) -> dict:
    if not _is_under_local_outputs(output_dir):
        raise HybridEvalStubError("Output directory must be under .local_outputs.")
    resolved_output_dir = _repo_relative(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    template = build_hybrid_result_template()
    require_valid_hybrid_result(template, strict=False)
    summary = build_plan_summary(
        gold_dir=gold_dir,
        audit=audit,
        eval_dir=eval_dir,
        include_private_values_local_only=include_private_values_local_only,
    )
    readme = """# RateCon Hybrid Eval Stub

This is a local-only scaffold. It does not call external APIs, run OCR, process
PDFs, or change production extraction behavior.

Files:

- `hybrid_eval_plan_summary.json`: safe aggregate scaffold metadata.
- `hybrid_result_template.json`: contract-shaped template for future hybrid
  extraction results.
- `hybrid_eval_readme.md`: this explanation.

All future private model outputs must remain under ignored local-only paths.
"""

    _write_json(resolved_output_dir / "hybrid_eval_plan_summary.json", summary)
    _write_json(resolved_output_dir / "hybrid_result_template.json", template)
    (resolved_output_dir / "hybrid_eval_readme.md").write_text(readme, encoding="utf-8")
    return {
        "output_dir": str(output_dir),
        "files_written": [
            "hybrid_eval_plan_summary.json",
            "hybrid_result_template.json",
            "hybrid_eval_readme.md",
        ],
        "external_api_calls_attempted": False,
        "private_values_printed": False,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write a local-only RateCon hybrid document-understanding eval scaffold."
    )
    parser.add_argument("--gold-dir", type=Path, default=None)
    parser.add_argument("--audit", type=Path, default=None)
    parser.add_argument("--eval-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local private scaffolds")
    result = write_stub_outputs(
        output_dir=args.output_dir,
        gold_dir=args.gold_dir,
        audit=args.audit,
        eval_dir=args.eval_dir,
        include_private_values_local_only=args.include_private_values_local_only,
    )
    print("RateCon hybrid eval stub summary")
    print(f"output_dir: {result['output_dir']}")
    print(f"files_written: {result['files_written']}")
    print("external_api_calls_attempted: False")
    print("private_values_printed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
