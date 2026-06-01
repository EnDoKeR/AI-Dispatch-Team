"""Analyze safe RateCon shadow audit artifacts."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.document_ai.private_measurement_outputs import (  # noqa: E402
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.ratecon_shadow_audit import (  # noqa: E402
    RATECON_SHADOW_AUDIT_JSONL,
    RATECON_SHADOW_AUDIT_SUMMARY_JSON,
)
from app.document_ai.ratecon_shadow_root_cause_analysis import (  # noqa: E402
    analyze_ratecon_shadow_audit,
    load_shadow_audit_jsonl,
    load_shadow_summary,
    write_ratecon_shadow_root_cause_artifacts,
)


def build_parser():
    default_root = DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR
    parser = argparse.ArgumentParser(
        description="Analyze safe local RateCon shadow pipeline diagnostics."
    )
    parser.add_argument(
        "--summary",
        default=str(default_root / RATECON_SHADOW_AUDIT_SUMMARY_JSON),
        help="Path to ratecon_shadow_document_pipeline_summary.json.",
    )
    parser.add_argument(
        "--audit",
        default=str(default_root / RATECON_SHADOW_AUDIT_JSONL),
        help="Path to ratecon_shadow_document_pipeline_audit.jsonl.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_root),
        help="Local output directory for root-cause reports.",
    )
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--baseline-summary", default="")
    parser.add_argument("--baseline-audit", default="")
    parser.add_argument("--allow-custom-output-dir", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    summary = load_shadow_summary(args.summary)
    records = load_shadow_audit_jsonl(args.audit)
    baseline_analysis = None
    if args.baseline_summary or args.baseline_audit:
        baseline_summary = load_shadow_summary(args.baseline_summary)
        baseline_records = load_shadow_audit_jsonl(args.baseline_audit)
        baseline_analysis = analyze_ratecon_shadow_audit(
            summary=baseline_summary,
            audit_records=baseline_records,
            top_n=args.top_n,
        )
    analysis = analyze_ratecon_shadow_audit(
        summary=summary,
        audit_records=records,
        top_n=args.top_n,
        baseline_analysis=baseline_analysis,
    )
    result = write_ratecon_shadow_root_cause_artifacts(
        analysis,
        output_dir=args.output_dir,
        allow_custom_output_dir=args.allow_custom_output_dir,
        top_n=args.top_n,
    )
    aggregate = result.get("aggregate", {}) or {}
    labels = {
        "files": result.get("files", {}),
        "documents_processed": aggregate.get("documents_processed", 0),
        "shadow_success": aggregate.get("shadow_success", 0),
        "shadow_failed": aggregate.get("shadow_failed", 0),
        "needs_review_count": aggregate.get("needs_review_count", 0),
        "primary_next_move": (
            aggregate.get("recommendation", {}) or {}
        ).get("primary_next_move", ""),
        "private_values_printed": result.get("private_values_printed", False),
        "raw_text_printed": result.get("raw_text_printed", False),
        "money_values_printed": result.get("money_values_printed", False),
    }
    print(f"ratecon_shadow_root_cause_analysis_written: {labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
