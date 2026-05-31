"""Download completed RateCon review feedback from dedicated Google Sheet tabs."""

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.ratecon_review_workbook import (
    SHEET_FIELD_REVIEW,
    SHEET_RATE_REVIEW,
    SHEET_STOP_REVIEW,
)
from app.document_ai.review_feedback_import import summarize_review_feedback_rows
from app.integrations import google_sheets_review as sheets


GOOGLE_FEEDBACK_STOP_REVIEW_CSV = "google_feedback_stop_review.csv"
GOOGLE_FEEDBACK_FIELD_REVIEW_CSV = "google_feedback_field_review.csv"
GOOGLE_FEEDBACK_RATE_REVIEW_CSV = "google_feedback_rate_review.csv"


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Download local-only RateCon review feedback from Google Sheets."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
        help="Ignored local output directory for downloaded feedback CSVs.",
    )
    parser.add_argument("--google-config", default="")
    parser.add_argument("--spreadsheet-id", default="")
    parser.add_argument("--credentials-json", default="")
    parser.add_argument("--worksheet-prefix", default=sheets.DEFAULT_WORKSHEET_PREFIX)
    parser.add_argument("--confirm-google-feedback-download", action="store_true")
    return parser


def _config_with_overrides(args):
    config = sheets.load_google_sheets_review_config(args.google_config)
    return sheets.GoogleSheetsReviewConfig(
        spreadsheet_id=args.spreadsheet_id or config.spreadsheet_id,
        credentials_json_path=args.credentials_json or config.credentials_json_path,
        worksheet_prefix=args.worksheet_prefix or config.worksheet_prefix,
        service_account_email=config.service_account_email,
        default_sync_mode=config.default_sync_mode,
        allow_private_review_value_sync=getattr(
            config,
            "allow_private_review_value_sync",
            False,
        ),
    )


def _rows_from_values(values):
    safe_values = list(values or [])
    if safe_values and safe_values[0] and safe_values[0][0] == sheets.REVIEW_SYNC_WARNING:
        safe_values = safe_values[1:]
    if not safe_values:
        return []
    headers = [str(header or "").strip() for header in safe_values[0]]
    rows = []
    for values_row in safe_values[1:]:
        row = {
            header: values_row[index] if index < len(values_row) else ""
            for index, header in enumerate(headers)
            if header
        }
        if "Field Name" not in row and row.get("Rate Field Type"):
            row["Field Name"] = row.get("Rate Field Type", "")
        rows.append(row)
    return rows


def _write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = []
    for row in rows or []:
        for column in row:
            if column not in columns:
                columns.append(column)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows or []:
            writer.writerow({column: row.get(column, "") for column in columns})


def _safe_summary_lines(result):
    summary = result.get("feedback_summary", {})
    return [
        "Google Sheets RateCon feedback download summary",
        f"tabs_downloaded: {result.get('tabs_downloaded', [])}",
        f"row_counts: {result.get('row_counts', {})}",
        f"files_written: {result.get('files_written', [])}",
        f"reviewed_field_count: {summary.get('reviewed_field_count', 0)}",
        f"correct_count: {summary.get('correct_count', 0)}",
        f"incorrect_count: {summary.get('incorrect_count', 0)}",
        f"unknown_count: {summary.get('unknown_count', 0)}",
        f"issue_type_counts: {summary.get('issue_type_counts', {})}",
        f"fields_with_high_error_rate: {summary.get('fields_with_high_error_rate', [])}",
        f"aliases_with_high_error_rate: {summary.get('aliases_with_high_error_rate', [])}",
        f"private_values_printed: {result.get('private_values_printed', False)}",
        f"credentials_printed: {result.get('credentials_printed', False)}",
        f"spreadsheet_id_printed: {result.get('spreadsheet_id_printed', False)}",
    ]


def run_download(args):
    if not args.confirm_google_feedback_download:
        raise sheets.GoogleSheetsReviewConfigError(
            "--confirm-google-feedback-download is required"
        )

    config = _config_with_overrides(args)
    client = sheets.connect_to_google_sheet(config)
    output_root = Path(args.output_dir)
    tab_specs = {
        SHEET_STOP_REVIEW: GOOGLE_FEEDBACK_STOP_REVIEW_CSV,
        SHEET_FIELD_REVIEW: GOOGLE_FEEDBACK_FIELD_REVIEW_CSV,
        SHEET_RATE_REVIEW: GOOGLE_FEEDBACK_RATE_REVIEW_CSV,
    }
    rows_by_sheet = {}
    row_counts = {}
    files_written = []
    for sheet_name, filename in tab_specs.items():
        title = sheets.google_review_tab_title(sheet_name, args.worksheet_prefix)
        download = client.download_worksheet_rows(title)
        rows = _rows_from_values(download.get("rows", []))
        rows_by_sheet[sheet_name] = rows
        row_counts[title] = len(rows)
        path = output_root / filename
        _write_rows(path, rows)
        files_written.append(path.name)

    feedback_rows = []
    for rows in rows_by_sheet.values():
        feedback_rows.extend(rows)
    return {
        "tabs_downloaded": [
            sheets.google_review_tab_title(sheet_name, args.worksheet_prefix)
            for sheet_name in tab_specs
        ],
        "row_counts": row_counts,
        "files_written": files_written,
        "feedback_summary": summarize_review_feedback_rows(feedback_rows),
        "private_values_printed": False,
        "credentials_printed": False,
        "spreadsheet_id_printed": False,
    }


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_download(args)
    except (sheets.GoogleSheetsReviewConfigError, sheets.GoogleSheetsReviewClientError) as exc:
        print("Google Sheets review feedback download skipped.", file=sys.stderr)
        print(f"Reason: {exc}.", file=sys.stderr)
        return 2

    for line in _safe_summary_lines(result):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
