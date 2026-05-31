"""Local-only review feedback import summaries.

This module reads user-edited review CSV rows and returns safe aggregate
metrics only. It does not apply corrections or persist production data.
"""

import csv
from pathlib import Path

from app.document_ai.ratecon_candidates import normalize_list


REVIEW_FEEDBACK_SUMMARY_VERSION = "review_feedback_summary_v1"

USER_CORRECT_COLUMN = "User Correct? yes/no/unknown"
USER_ISSUE_TYPE_COLUMN = "User Issue Type"
MEASUREMENT_ALIAS_COLUMN = "Measurement Alias"
FIELD_NAME_COLUMN = "Field Name"

REQUIRED_REVIEW_COLUMNS = {
    USER_CORRECT_COLUMN,
    USER_ISSUE_TYPE_COLUMN,
    MEASUREMENT_ALIAS_COLUMN,
    FIELD_NAME_COLUMN,
}


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _normalize_answer(value):
    token = _token(value)
    if token in {"yes", "y", "true", "correct"}:
        return "yes"
    if token in {"no", "n", "false", "incorrect"}:
        return "no"
    if token in {"unknown", "unk", "unsure"}:
        return "unknown"
    return ""


def _empty_summary(warning_codes=None):
    return {
        "rows_loaded": 0,
        "reviewed_field_count": 0,
        "correct_count": 0,
        "incorrect_count": 0,
        "unknown_count": 0,
        "issue_type_counts": {},
        "fields_with_high_error_rate": [],
        "aliases_with_high_error_rate": [],
        "safe_summary_only": True,
        "warning_codes": normalize_list(warning_codes),
        "summary_version": REVIEW_FEEDBACK_SUMMARY_VERSION,
    }


def _high_error_keys(counts_by_key):
    high = []
    for key, counts in counts_by_key.items():
        reviewed = int(counts.get("reviewed", 0) or 0)
        incorrect = int(counts.get("incorrect", 0) or 0)
        if reviewed and incorrect / reviewed >= 0.5:
            high.append(key)
    return sorted(high)


def summarize_review_feedback_rows(rows):
    safe_rows = [row for row in rows or [] if isinstance(row, dict)]
    if not safe_rows:
        return _empty_summary()

    missing_columns = REQUIRED_REVIEW_COLUMNS - set(safe_rows[0])
    if missing_columns:
        return _empty_summary(
            warning_codes=[
                "malformed_review_feedback_csv",
                *[f"missing_column_{_token(column)}" for column in sorted(missing_columns)],
            ]
        )

    correct = 0
    incorrect = 0
    unknown = 0
    reviewed = 0
    issue_type_counts = {}
    field_counts = {}
    alias_counts = {}

    for row in safe_rows:
        answer = _normalize_answer(row.get(USER_CORRECT_COLUMN))
        if not answer:
            continue
        reviewed += 1
        field_name = _token(row.get(FIELD_NAME_COLUMN)) or "unknown"
        alias = _text(row.get(MEASUREMENT_ALIAS_COLUMN)) or "UNKNOWN_ALIAS"
        field_counts.setdefault(field_name, {"reviewed": 0, "incorrect": 0})
        alias_counts.setdefault(alias, {"reviewed": 0, "incorrect": 0})
        field_counts[field_name]["reviewed"] += 1
        alias_counts[alias]["reviewed"] += 1

        if answer == "yes":
            correct += 1
        elif answer == "no":
            incorrect += 1
            field_counts[field_name]["incorrect"] += 1
            alias_counts[alias]["incorrect"] += 1
            issue_type = _token(row.get(USER_ISSUE_TYPE_COLUMN)) or "unspecified"
            issue_type_counts[issue_type] = issue_type_counts.get(issue_type, 0) + 1
        else:
            unknown += 1

    return {
        "rows_loaded": len(safe_rows),
        "reviewed_field_count": reviewed,
        "correct_count": correct,
        "incorrect_count": incorrect,
        "unknown_count": unknown,
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "fields_with_high_error_rate": _high_error_keys(field_counts),
        "aliases_with_high_error_rate": _high_error_keys(alias_counts),
        "safe_summary_only": True,
        "warning_codes": [],
        "summary_version": REVIEW_FEEDBACK_SUMMARY_VERSION,
    }


def import_review_feedback_csv(path):
    csv_path = Path(path)
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return summarize_review_feedback_rows(rows)
