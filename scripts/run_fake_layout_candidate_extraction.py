"""Run layout-aware candidate extraction on synthetic layout fixtures only."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.layout_candidate_extraction import extract_ratecon_layout_candidates


DEFAULT_FIXTURE_DIR = (
    REPO_ROOT / "tests" / "fixtures" / "document_ai" / "layout_artifacts"
)


def _fixture_paths(input_dir):
    return sorted(Path(input_dir).glob("*.json"))


def _load_layout_fixture(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _counter(values):
    return dict(sorted(Counter(value for value in values if value).items()))


def _safe_fixture_summary(path):
    artifact = _load_layout_fixture(path)
    result = extract_ratecon_layout_candidates(artifact)
    candidates = result["candidates"]

    return {
        "fixture": path.name,
        "candidate_counts_by_field": result.get("candidate_counts_by_field", {}),
        "evidence_type_counts": _counter(
            (candidate.get("layout_evidence_ref") or {}).get("evidence_type", "")
            for candidate in candidates
        ),
        "section_role_counts": _counter(
            candidate.get("layout_section_role", "")
            for candidate in candidates
        ),
        "proximity_type_counts": _counter(
            candidate.get("layout_proximity_type", "")
            for candidate in candidates
        ),
        "warnings": sorted(
            {
                warning
                for candidate in candidates
                for warning in candidate.get("warnings", [])
            }
            | set(result.get("warnings", []))
        ),
    }


def build_fake_layout_candidate_extraction_summary(
    input_dir=DEFAULT_FIXTURE_DIR,
    limit=None,
):
    paths = _fixture_paths(input_dir)
    if limit is not None:
        paths = paths[: int(limit)]

    summaries = [_safe_fixture_summary(path) for path in paths]

    return {
        "fake_only": True,
        "raw_text_printed": False,
        "private_values_printed": False,
        "total_fixtures": len(summaries),
        "summaries": summaries,
    }


def format_summary_lines(summary):
    lines = [
        "Fake layout candidate extraction dry run",
        f"Total fixtures: {summary['total_fixtures']}",
    ]

    for item in summary["summaries"]:
        lines.extend(
            [
                "",
                item["fixture"],
                f"  candidate_counts_by_field: {item['candidate_counts_by_field']}",
                f"  evidence_type_counts: {item['evidence_type_counts']}",
                f"  section_role_counts: {item['section_role_counts']}",
                f"  proximity_type_counts: {item['proximity_type_counts']}",
                f"  warnings: {item['warnings']}",
            ]
        )

    lines.append("")
    lines.append("DRY RUN ONLY - synthetic layout fixtures, no PDFs, no raw text printed")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Run fake-only layout-aware candidate extraction on synthetic JSON "
            "fixtures. This does not read private PDFs or private directories."
        ),
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Directory of synthetic layout JSON fixtures.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path for safe summary JSON with no raw fixture text.",
    )
    args = parser.parse_args(argv)

    summary = build_fake_layout_candidate_extraction_summary(
        input_dir=args.input_dir,
        limit=args.limit,
    )

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
