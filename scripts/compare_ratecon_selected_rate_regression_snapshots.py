"""Compare sanitized RateCon selected-rate regression snapshots."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


COMPARE_FIELDS = (
    "selected_value",
    "selected_source",
    "selected_confidence",
    "selected_score",
    "selected_money_context",
    "selected_rate_safety",
    "selected_rate_safety_reason",
    "needs_review",
    "review_reasons",
    "global_needs_review",
    "global_review_reasons",
    "resolved_candidate_count",
)

FORBIDDEN_PRIVATE_MARKERS = (
    "data/private_ratecons",
    ".pdf",
    ".gold.json",
    "api_key",
    "secret",
    "token",
    "service account",
    "private_ratecon",
    "raw text",
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare sanitized selected-rate regression snapshots."
    )
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _is_under_local_outputs(path: Path) -> bool:
    return ".local_outputs" in path.parts


def _load_snapshot(path: Path) -> dict:
    payload = path.read_text(encoding="utf-8")
    lower_payload = payload.lower()
    hits = [marker for marker in FORBIDDEN_PRIVATE_MARKERS if marker in lower_payload]
    if hits:
        raise ValueError(f"snapshot contains forbidden private markers: {hits}")
    return json.loads(payload)


def _actual_by_case(snapshot: dict) -> dict[str, dict]:
    return {
        str(case.get("case_id")): dict(case.get("actual") or {})
        for case in snapshot.get("cases", [])
    }


def compare_snapshots(before: dict, after: dict) -> dict:
    before_cases = _actual_by_case(before)
    after_cases = _actual_by_case(after)
    before_ids = set(before_cases)
    after_ids = set(after_cases)
    changes = []

    for case_id in sorted(before_ids | after_ids):
        if case_id not in before_cases:
            changes.append(
                {
                    "case_id": case_id,
                    "field": "__case__",
                    "before": "",
                    "after": "added",
                }
            )
            continue
        if case_id not in after_cases:
            changes.append(
                {
                    "case_id": case_id,
                    "field": "__case__",
                    "before": "present",
                    "after": "removed",
                }
            )
            continue
        before_actual = before_cases[case_id]
        after_actual = after_cases[case_id]
        for field in COMPARE_FIELDS:
            if before_actual.get(field) != after_actual.get(field):
                changes.append(
                    {
                        "case_id": case_id,
                        "field": field,
                        "before": before_actual.get(field),
                        "after": after_actual.get(field),
                    }
                )

    return {
        "summary": {
            "case_count_before": len(before_cases),
            "case_count_after": len(after_cases),
            "changed_field_count": len(changes),
            "selected_rate_outputs_unchanged": not changes,
            "private_values_used": False,
            "pdf_processing_attempted": False,
            "ocr_attempted": False,
            "google_called": False,
            "model_or_cloud_called": False,
        },
        "changes": changes,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, changes: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "field", "before", "after"])
        writer.writeheader()
        for row in changes:
            writer.writerow(row)


def _write_md(path: Path, comparison: dict) -> None:
    summary = comparison["summary"]
    lines = [
        "# RateCon Selected-Rate Regression Snapshot Compare",
        "",
        f"- case_count_before: {summary['case_count_before']}",
        f"- case_count_after: {summary['case_count_after']}",
        f"- changed_field_count: {summary['changed_field_count']}",
        f"- selected_rate_outputs_unchanged: {summary['selected_rate_outputs_unchanged']}",
        f"- private_values_used: {summary['private_values_used']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
    ]
    if comparison["changes"]:
        lines.extend(["", "## Changes", ""])
        for row in comparison["changes"]:
            lines.append(f"- {row['case_id']} {row['field']}: {row['before']} -> {row['after']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.confirm_local_audit_run:
        print("--confirm-local-audit-run is required", file=sys.stderr)
        return 2

    before_path = _resolve(args.before)
    after_path = _resolve(args.after)
    output_dir = _resolve(args.output_dir)
    if not _is_under_local_outputs(output_dir):
        print("output-dir must be inside .local_outputs", file=sys.stderr)
        return 2

    try:
        before = _load_snapshot(before_path)
        after = _load_snapshot(after_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"snapshot_compare_error: {exc}", file=sys.stderr)
        return 1

    comparison = compare_snapshots(before, after)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "selected_rate_regression_snapshot_compare.json", comparison)
    _write_md(output_dir / "selected_rate_regression_snapshot_compare.md", comparison)
    _write_csv(output_dir / "selected_rate_regression_snapshot_compare.csv", comparison["changes"])

    summary = comparison["summary"]
    print("RateCon selected-rate regression snapshot compare")
    print(f"case_count_before: {summary['case_count_before']}")
    print(f"case_count_after: {summary['case_count_after']}")
    print(f"changed_field_count: {summary['changed_field_count']}")
    print(f"selected_rate_outputs_unchanged: {summary['selected_rate_outputs_unchanged']}")
    print(f"output_dir: {output_dir}")
    return 0 if summary["selected_rate_outputs_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
