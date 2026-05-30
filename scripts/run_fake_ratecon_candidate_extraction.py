"""Run candidate-based RateCon extraction on fake/anonymized fixtures only."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_RESOLVED,
    resolve_ratecon_fields,
)
from app.document_ai.ratecon_intake_draft import build_ratecon_intake_from_resolution
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates


DEFAULT_FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "document_ai" / "ratecon_text"


def _candidate_counts(candidates):
    return dict(sorted(Counter(candidate["field_name"] for candidate in candidates).items()))


def _safe_fixture_summary(path):
    text = path.read_text(encoding="utf-8")
    artifact = build_text_extraction_artifact_for_candidates(
        artifact_id=f"ART-{path.stem.upper()}",
        document_id=f"DOC-{path.stem.upper()}",
        source_name=path.name,
        full_text=text,
        source_method="synthetic_fixture",
    )
    candidate_result = extract_ratecon_candidates(artifact)
    resolution_result = resolve_ratecon_fields(candidate_result)
    intake = build_ratecon_intake_from_resolution(resolution_result)
    resolved_fields = [
        resolution["field_name"]
        for resolution in resolution_result["resolutions"]
        if resolution["status"] == FIELD_RESOLUTION_STATUS_RESOLVED
    ]

    return {
        "fixture": path.name,
        "candidate_counts_by_field": _candidate_counts(candidate_result["candidates"]),
        "resolved_fields": resolved_fields,
        "missing_fields": resolution_result["missing_fields"],
        "needs_check_fields": resolution_result["needs_check_fields"],
        "conflict_fields": resolution_result["conflict_fields"],
        "intake_status": intake["status"],
        "warnings": sorted(set(candidate_result["warnings"] + resolution_result["warnings"])),
    }


def build_fake_candidate_extraction_summary(input_dir=DEFAULT_FIXTURE_DIR):
    fixture_dir = Path(input_dir)
    summaries = [
        _safe_fixture_summary(path)
        for path in sorted(fixture_dir.glob("*.txt"))
    ]

    return {
        "fixture_dir": str(fixture_dir),
        "total_fixtures": len(summaries),
        "summaries": summaries,
        "dry_run_only": True,
        "raw_text_printed": False,
    }


def format_summary_lines(summary):
    lines = [
        "Fake RateCon candidate extraction dry run",
        f"Total fixtures: {summary['total_fixtures']}",
    ]

    for item in summary["summaries"]:
        lines.extend(
            [
                "",
                item["fixture"],
                f"  candidate_counts_by_field: {item['candidate_counts_by_field']}",
                f"  resolved_fields: {item['resolved_fields']}",
                f"  missing_fields: {item['missing_fields']}",
                f"  needs_check_fields: {item['needs_check_fields']}",
                f"  conflict_fields: {item['conflict_fields']}",
                f"  intake_status: {item['intake_status']}",
                f"  warnings: {item['warnings']}",
            ]
        )

    lines.append("")
    lines.append("DRY RUN ONLY - fake/anonymized fixtures, no raw text printed")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run fake/anonymized RateCon candidate extraction.",
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Directory of fake/anonymized .txt fixtures.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path for safe summary JSON with no raw fixture text.",
    )
    args = parser.parse_args(argv)

    summary = build_fake_candidate_extraction_summary(args.input_dir)

    for line in format_summary_lines(summary):
        print(line)

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
