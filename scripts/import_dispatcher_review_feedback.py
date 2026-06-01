"""Import edited dispatcher review table v3 feedback safely."""

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.dispatcher_review_table import (
    DISPATCHER_EDITABLE_FIELDS,
    DISPATCHER_REVIEW_V3_AUDIT_CSV,
    DISPATCHER_REVIEW_V3_REVIEW_CSV,
    FIELD_TO_CORRECTION_COLUMN,
    FIELD_TO_REVIEW_COLUMN,
    aggregate_dispatcher_feedback,
    build_dispatcher_feedback_row,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.review_issue_taxonomy import normalize_review_issue_type


DISPATCHER_FEEDBACK_SUMMARY_JSON = "dispatcher_review_feedback_summary.json"
DISPATCHER_FEEDBACK_SUMMARY_MD = "dispatcher_review_feedback_summary.md"
DISPATCHER_COMPLETED_REVIEW_CSV = "ratecon_review_v3_dispatcher_review_completed.csv"


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Import edited dispatcher review table v3 feedback safely."
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


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _audit_index(audit_rows):
    index = {}
    for row in audit_rows or []:
        alias = _text(row.get("Measurement Alias"))
        field = _token(row.get("Field Name"))
        if alias and field:
            index[(alias, field)] = row
    return index


def _feedback_input_path(input_dir):
    root = Path(input_dir)
    completed = root / DISPATCHER_COMPLETED_REVIEW_CSV
    if completed.exists():
        return completed, True
    return root / DISPATCHER_REVIEW_V3_REVIEW_CSV, False


def _row_has_feedback(row):
    if _text(row.get("User Review Status")) or _text(row.get("User Notes Local Only")):
        return True
    if _text(row.get("User Issue Type")):
        return True
    for field_name in DISPATCHER_EDITABLE_FIELDS:
        correction_column = FIELD_TO_CORRECTION_COLUMN.get(field_name, "")
        if correction_column and _text(row.get(correction_column)):
            return True
    return False


def _changed(value, baseline):
    return " ".join(_text(value).split()).casefold() != " ".join(
        _text(baseline).split()
    ).casefold()


def build_dispatcher_feedback_rows(review_rows, audit_rows, completed_file=False):
    audit = _audit_index(audit_rows)
    feedback_rows = []
    for row in review_rows or []:
        alias = _text(row.get("Measurement Alias"))
        if not alias:
            continue
        if not completed_file and not _row_has_feedback(row):
            continue
        user_issue_type = normalize_review_issue_type(row.get("User Issue Type"))
        for field_name in DISPATCHER_EDITABLE_FIELDS:
            review_column = FIELD_TO_REVIEW_COLUMN[field_name]
            correction_column = FIELD_TO_CORRECTION_COLUMN[field_name]
            audit_row = audit.get((alias, field_name), {})
            original_predicted = _text(audit_row.get("Predicted Value LOCAL ONLY"))
            exported_value = _text(
                audit_row.get("Dispatcher Value At Export LOCAL ONLY")
            )
            direct_value = _text(row.get(review_column))
            correction_value = _text(row.get(correction_column))
            if correction_value:
                user_value = correction_value
                changed = _changed(user_value, original_predicted)
            else:
                if review_column not in row:
                    continue
                user_value = direct_value
                changed = _changed(user_value, exported_value)
            if not changed:
                continue
            feedback_rows.append(
                build_dispatcher_feedback_row(
                    measurement_alias=alias,
                    field_name=field_name,
                    original_predicted_value=original_predicted,
                    user_corrected_value=user_value,
                    user_issue_type=user_issue_type,
                    user_review_status=row.get("User Review Status"),
                    user_notes_local_only=row.get("User Notes Local Only"),
                )
            )
    return feedback_rows


def _write_json(path, aggregate):
    payload = {
        "aggregate": aggregate,
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path.name


def _write_md(path, aggregate):
    lines = [
        "# Dispatcher Review Feedback Summary",
        "",
        "Local-only safe summary. Corrected values and private notes are not included.",
        "",
        f"- rows_loaded: {aggregate.get('rows_loaded', 0)}",
        f"- documents_reviewed: {aggregate.get('documents_reviewed', 0)}",
        f"- changed_field_count: {aggregate.get('changed_field_count', 0)}",
        f"- issue_type_counts: {aggregate.get('issue_type_counts', {})}",
        f"- changed_fields_by_name: {aggregate.get('changed_fields_by_name', {})}",
        f"- recommended_next_repair_target: {aggregate.get('recommended_next_repair_target')}",
        "- private_values_included: False",
        "- raw_text_included: False",
        "- money_values_included: False",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path.name


def import_dispatcher_feedback(input_dir, output_dir):
    review_path, completed_file = _feedback_input_path(input_dir)
    audit_path = Path(input_dir) / DISPATCHER_REVIEW_V3_AUDIT_CSV
    review_rows = _read_csv(review_path)
    audit_rows = _read_csv(audit_path)
    feedback_rows = build_dispatcher_feedback_rows(
        review_rows,
        audit_rows,
        completed_file=completed_file,
    )
    aggregate = aggregate_dispatcher_feedback(feedback_rows)
    if not feedback_rows:
        aggregate["warning_codes"] = ["no_completed_dispatcher_feedback_found"]
        aggregate["recommended_next_repair_target"] = "human_review_continue"
    output_root = Path(output_dir)
    written = {
        "json": _write_json(output_root / DISPATCHER_FEEDBACK_SUMMARY_JSON, aggregate),
        "md": _write_md(output_root / DISPATCHER_FEEDBACK_SUMMARY_MD, aggregate),
    }
    return aggregate, written


def main(argv=None):
    args = _build_parser().parse_args(argv)
    aggregate, written = import_dispatcher_feedback(args.input_dir, args.output_dir)
    if not aggregate.get("changed_field_count"):
        print("no_completed_dispatcher_feedback_found")
    print("Dispatcher review feedback summary")
    print(f"rows_loaded: {aggregate.get('rows_loaded', 0)}")
    print(f"documents_reviewed: {aggregate.get('documents_reviewed', 0)}")
    print(f"changed_field_count: {aggregate.get('changed_field_count', 0)}")
    print(f"issue_type_counts: {aggregate.get('issue_type_counts', {})}")
    print(f"changed_fields_by_name: {aggregate.get('changed_fields_by_name', {})}")
    print(
        "recommended_next_repair_target: "
        f"{aggregate.get('recommended_next_repair_target')}"
    )
    print(f"outputs_written: {sorted(written.values())}")
    print("corrected_values_printed: False")
    print("private_notes_printed: False")
    print("private_values_printed: False")
    print("money_values_printed: False")
    print("raw_text_printed: False")
    print("local_paths_printed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
