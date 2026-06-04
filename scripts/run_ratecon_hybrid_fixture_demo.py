"""Run the sanitized RateCon hybrid fixture benchmark demo.

This script intentionally reads only committed sanitized fixtures. It does not
call AI models, cloud APIs, OCR, local model runtimes, or PDF processing.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_ratecon_hybrid_benchmark import run_hybrid_benchmark  # noqa: E402


FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ratecon_hybrid"
DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_hybrid_fixture_demo")


def run_fixture_demo(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Run the sanitized fixture benchmark and return its aggregate summary."""

    return run_hybrid_benchmark(
        hybrid_results_dir=FIXTURE_ROOT / "hybrid_results_sanitized",
        gold_dir=FIXTURE_ROOT / "gold_labels_sanitized",
        audit=FIXTURE_ROOT / "audit_sanitized" / "ratecon_shadow_document_pipeline_audit.jsonl",
        output_dir=output_dir,
        include_private_values_local_only=False,
        strict_schema=False,
        allow_missing_hybrid_results=False,
        write_review_packets=True,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the sanitized RateCon hybrid fixture benchmark demo.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = run_fixture_demo(args.output_dir)
    one_screen = summary.get("one_screen_summary", {})
    print("RateCon hybrid fixture demo")
    print(f"hybrid results: {summary['hybrid_result_count']}")
    print(f"schema errors: {summary['schema_error_count']}")
    print(f"missing evidence: {one_screen.get('missing_evidence', 0)}")
    print(f"unsafe wrong stops: {one_screen.get('unsafe_wrong_stops', 0)}")
    print(f"auto-accept violations: {one_screen.get('stop_auto_accept_violations', 0)}")
    print(f"non-RC filtered: {one_screen.get('non_rc_bol_pod_filtered', 0)}")
    print(f"output_dir: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
