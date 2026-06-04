"""Create a local-only RateCon local-provider design review packet.

The packet is checklist scaffolding only. It reads a fixture-only evidence-pack
summary and never calls models, reads PDFs, performs OCR, edits gold labels, or
edits hybrid templates.
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
from app.document_ai.ratecon_local_provider_design_review import (  # noqa: E402
    RateConLocalProviderDesignReviewError,
    build_design_review,
    checklist_markdown,
    report_markdown,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_local_provider_design_review")


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    resolved = _repo_relative(path)
    if not resolved.exists():
        return None
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
        raise RateConLocalProviderDesignReviewError("Output directory must be under .local_outputs.")
    resolved = _repo_relative(output_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _bool_text(value: str) -> bool:
    return str(value).strip().lower() not in {"false", "0", "no"}


def create_design_review_outputs(
    *,
    evidence_pack_summary: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    provider_name: str = "local_model_placeholder_v1",
    design_id: str = "local_provider_design_v1",
    fixture_only: bool = True,
    redact_default: bool = True,
) -> dict[str, Any]:
    if not fixture_only:
        raise RateConLocalProviderDesignReviewError("fixture-only mode is required for design review generation.")
    if not redact_default:
        raise RateConLocalProviderDesignReviewError("redact-default must remain true.")
    resolved_output = _require_local_output(output_dir)
    evidence_payload = _read_json_if_exists(evidence_pack_summary)
    review = build_design_review(
        evidence_pack_summary=evidence_payload,
        provider_name=provider_name,
        design_review_id=design_id,
    )
    _write_json(resolved_output / "local_provider_design_review_summary.json", review)
    (resolved_output / "local_provider_design_review_report.md").write_text(report_markdown(review), encoding="utf-8")
    _write_csv(
        resolved_output / "local_provider_design_acceptance_criteria.csv",
        review.get("acceptance_criteria", []),
        ["id", "section", "criterion", "required", "status"],
    )
    _write_csv(
        resolved_output / "local_provider_design_blockers.csv",
        [{"blocker": blocker} for blocker in review.get("blockers", [])],
        ["blocker"],
    )
    _write_csv(
        resolved_output / "local_provider_design_next_actions.csv",
        [{"next_action": action} for action in review.get("required_next_actions", [])],
        ["next_action"],
    )
    (resolved_output / "local_provider_design_pr_checklist.md").write_text(checklist_markdown(review), encoding="utf-8")
    return review


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a RateCon local-provider design review packet.")
    parser.add_argument("--evidence-pack-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--provider-name", default="local_model_placeholder_v1")
    parser.add_argument("--design-id", default="local_provider_design_v1")
    parser.add_argument("--fixture-only", action="store_true")
    parser.add_argument("--redact-default", default="true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required")
    review = create_design_review_outputs(
        evidence_pack_summary=args.evidence_pack_summary,
        output_dir=args.output_dir,
        provider_name=args.provider_name,
        design_id=args.design_id,
        fixture_only=True if not args.fixture_only else args.fixture_only,
        redact_default=_bool_text(args.redact_default),
    )
    output_dir = _repo_relative(args.output_dir)
    print("RateCon local provider design review")
    print(f"recommendation: {review['recommendation']}")
    print(f"acceptance_criteria_count: {len(review.get('acceptance_criteria', []))}")
    print(f"blocker_count: {len(review.get('blockers', []))}")
    print(f"next_action_count: {len(review.get('required_next_actions', []))}")
    print(f"checklist_path: {output_dir / 'local_provider_design_pr_checklist.md'}")
    print("provider_execution_allowed: False")
    print("ai_model_invocation_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("external_api_calls_attempted: False")
    return 2 if review["recommendation"] == "reject" else 0


if __name__ == "__main__":
    raise SystemExit(main())
