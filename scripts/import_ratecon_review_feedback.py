"""Import completed local RateCon review feedback safely."""

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.review_issue_taxonomy import (
    build_review_feedback_aggregate,
    review_feedback_row_from_csv,
)
from app.document_ai.review_feedback_target_selector import (
    select_repair_target_from_feedback,
)
from app.document_ai.target_disposition import load_target_dispositions


REVIEW_FEEDBACK_SUMMARY_JSON = "review_feedback_summary.json"
REVIEW_FEEDBACK_SUMMARY_MD = "review_feedback_summary.md"

_COMPLETED_CSVS = [
    ("ratecon_review_v2_core_fields_completed.csv", "Core_Field_Review", "field"),
    ("ratecon_review_v2_stops_completed.csv", "Stop_Review", "stop"),
    ("ratecon_review_v2_rates_completed.csv", "Rate_Review", "rate"),
    ("ratecon_review_v2_load_ids_completed.csv", "Load_ID_Review", "load_identifier"),
]

_EDITED_IN_PLACE_CSVS = [
    ("ratecon_review_v2_core_fields.csv", "Core_Field_Review", "field"),
    ("ratecon_review_v2_stops.csv", "Stop_Review", "stop"),
    ("ratecon_review_v2_rates.csv", "Rate_Review", "rate"),
    ("ratecon_review_v2_load_ids.csv", "Load_ID_Review", "load_identifier"),
]


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Import completed local RateCon review feedback CSVs safely."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
    )
    return parser


def _text(value):
    return str(value or "").strip()


def _read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _has_completed_feedback(rows):
    for row in rows or []:
        if _text(row.get("User Correct? yes/no/unknown")) or _text(
            row.get("User Correct?")
        ):
            return True
        if _text(row.get("User Issue Type")):
            return True
    return False


def _load_feedback_records(input_dir):
    root = Path(input_dir)
    loaded = []
    used_files = []
    for filename, sheet_name, row_type in _COMPLETED_CSVS:
        path = root / filename
        if not path.exists():
            continue
        rows = _read_csv(path)
        used_files.append(filename)
        loaded.extend(
            review_feedback_row_from_csv(row, sheet_name=sheet_name, row_type=row_type)
            for row in rows
        )

    if loaded:
        return loaded, used_files

    for filename, sheet_name, row_type in _EDITED_IN_PLACE_CSVS:
        path = root / filename
        if not path.exists():
            continue
        rows = _read_csv(path)
        if not _has_completed_feedback(rows):
            continue
        used_files.append(filename)
        loaded.extend(
            review_feedback_row_from_csv(row, sheet_name=sheet_name, row_type=row_type)
            for row in rows
        )
    return loaded, used_files


def _empty_result():
    aggregate = build_review_feedback_aggregate([])
    aggregate["warning_codes"] = ["no_completed_feedback_found"]
    aggregate["recommended_next_repair_target"] = "human_review_continue"
    return aggregate


def _write_json(path, aggregate, used_files):
    payload = {
        "aggregate": aggregate,
        "completed_feedback_files": sorted(used_files),
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path.name


def _write_md(path, aggregate, used_files):
    lines = [
        "# Review Feedback Summary",
        "",
        "Local-only safe summary. Expected values and private notes are not included.",
        "",
        f"- rows_loaded: {aggregate.get('rows_loaded', 0)}",
        f"- reviewed_count: {aggregate.get('reviewed_count', 0)}",
        f"- correct_count: {aggregate.get('correct_count', 0)}",
        f"- incorrect_count: {aggregate.get('incorrect_count', 0)}",
        f"- unknown_count: {aggregate.get('unknown_count', 0)}",
        f"- not_applicable_count: {aggregate.get('not_applicable_count', 0)}",
        f"- issue_type_counts: {aggregate.get('issue_type_counts', {})}",
        f"- top_issue_types: {aggregate.get('top_issue_types', [])}",
        f"- top_fields_by_incorrect: {aggregate.get('top_fields_by_incorrect', [])}",
        f"- recommended_next_repair_target: {aggregate.get('recommended_next_repair_target')}",
        f"- completed_feedback_files: {sorted(used_files)}",
        "- private_values_included: False",
        "- raw_text_included: False",
        "- money_values_included: False",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path.name


def import_feedback(input_dir, output_dir):
    records, used_files = _load_feedback_records(input_dir)
    aggregate = (
        build_review_feedback_aggregate(records)
        if records
        else _empty_result()
    )
    target_decision = select_repair_target_from_feedback(
        aggregate,
        target_disposition_registry=load_target_dispositions(input_dir),
    )
    aggregate["recommended_next_repair_target"] = target_decision["selected_target"]
    aggregate["target_selection"] = target_decision
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    written = {
        "json": _write_json(output_root / REVIEW_FEEDBACK_SUMMARY_JSON, aggregate, used_files),
        "md": _write_md(output_root / REVIEW_FEEDBACK_SUMMARY_MD, aggregate, used_files),
    }
    return aggregate, used_files, written


def main(argv=None):
    args = _build_parser().parse_args(argv)
    aggregate, used_files, written = import_feedback(args.input_dir, args.output_dir)
    if not used_files:
        print("no_completed_feedback_found")
    print("Review feedback summary")
    print(f"rows_loaded: {aggregate.get('rows_loaded', 0)}")
    print(f"reviewed_count: {aggregate.get('reviewed_count', 0)}")
    print(f"correct_count: {aggregate.get('correct_count', 0)}")
    print(f"incorrect_count: {aggregate.get('incorrect_count', 0)}")
    print(f"unknown_count: {aggregate.get('unknown_count', 0)}")
    print(f"not_applicable_count: {aggregate.get('not_applicable_count', 0)}")
    print(f"issue_type_counts: {aggregate.get('issue_type_counts', {})}")
    print(
        "recommended_next_repair_target: "
        f"{aggregate.get('recommended_next_repair_target')}"
    )
    print(f"outputs_written: {sorted(written.values())}")
    print("expected_values_printed: False")
    print("private_notes_printed: False")
    print("private_values_printed: False")
    print("raw_text_printed: False")
    print("local_paths_printed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
