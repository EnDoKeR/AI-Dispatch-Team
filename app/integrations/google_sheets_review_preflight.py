"""Safe local preflight checks for Google Sheets review sync inputs."""

import csv
from pathlib import Path

from app.integrations.google_sheets_review import (
    PRIVATE_REVIEW_VALUE_COLUMNS,
    REVIEW_CSV_SPECS,
)


RAW_TEXT_HEADER_TOKENS = {"raw_text", "raw text", "line text", "full text"}


def _safe_header_token(value):
    return str(value or "").strip().lower().replace("-", " ").replace("_", " ")


def _has_raw_text_header(fieldnames):
    for header in fieldnames or []:
        token = _safe_header_token(header)
        if token in RAW_TEXT_HEADER_TOKENS or "raw text" in token:
            return True
    return False


def _inspect_csv(path, expected_columns):
    if not path.exists():
        return {
            "exists": False,
            "row_count": 0,
            "headers_valid": False,
            "missing_headers": list(expected_columns or []),
            "raw_text_column_found": False,
            "private_value_columns_present": False,
        }

    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        row_count = sum(1 for _ in reader)

    missing_headers = [
        column for column in (expected_columns or []) if column not in fieldnames
    ]
    return {
        "exists": True,
        "row_count": row_count,
        "headers_valid": not missing_headers,
        "missing_headers": missing_headers,
        "raw_text_column_found": _has_raw_text_header(fieldnames),
        "private_value_columns_present": bool(
            set(fieldnames) & PRIVATE_REVIEW_VALUE_COLUMNS
        ),
    }


def preflight_google_review_outputs(input_dir):
    """Return safe review CSV readiness counts without exposing cell values."""

    root = Path(input_dir)
    file_summaries = {}
    row_counts = {}
    missing = []
    warning_codes = []
    any_found = False
    all_headers_valid = True
    all_rows_present = True
    raw_text_found = False
    private_value_columns_present = False

    for _sheet_name, (filename, expected_columns) in REVIEW_CSV_SPECS.items():
        summary = _inspect_csv(root / filename, expected_columns)
        file_summaries[filename] = summary
        row_counts[filename] = int(summary["row_count"])
        if summary["exists"]:
            any_found = True
        else:
            missing.append(filename)
        if not summary["headers_valid"]:
            all_headers_valid = False
        if summary["row_count"] <= 0:
            all_rows_present = False
        if summary["raw_text_column_found"]:
            raw_text_found = True
        if summary["private_value_columns_present"]:
            private_value_columns_present = True

    if missing:
        warning_codes.append("missing_review_csv")
    if not all_headers_valid:
        warning_codes.append("invalid_review_csv_headers")
    if not all_rows_present:
        warning_codes.append("empty_review_csv")
    if raw_text_found:
        warning_codes.append("raw_text_column_found")

    return {
        "review_outputs_found": any_found and not missing,
        "rows_per_source_file": row_counts,
        "file_summaries": file_summaries,
        "missing_csv_basenames": missing,
        "headers_valid": all_headers_valid,
        "row_counts_valid": all_rows_present,
        "raw_text_columns_found": raw_text_found,
        "private_value_columns_present": private_value_columns_present,
        "sync_ready": any_found
        and not missing
        and all_headers_valid
        and all_rows_present
        and not raw_text_found,
        "warning_codes": warning_codes,
        "input_path_printed": False,
        "private_values_printed": False,
    }
