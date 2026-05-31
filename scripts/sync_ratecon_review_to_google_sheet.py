"""Sync local RateCon review CSVs into dedicated Google Sheets tabs."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.integrations import google_sheets_review as sheets
from app.integrations.google_sheets_review_preflight import (
    preflight_google_review_outputs,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Sync local-only RateCon review CSVs to dedicated Google Sheet tabs."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
        help="Local ignored review output directory.",
    )
    parser.add_argument("--google-config", default="")
    parser.add_argument("--spreadsheet-id", default="")
    parser.add_argument("--credentials-json", default="")
    parser.add_argument("--worksheet-prefix", default=sheets.DEFAULT_WORKSHEET_PREFIX)
    parser.add_argument("--confirm-google-review-sync", action="store_true")
    parser.add_argument(
        "--include-private-review-values-google-test-only",
        action="store_true",
    )
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
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


def _sync_mode(args):
    if args.status_only and args.include_private_review_values_google_test_only:
        raise sheets.GoogleSheetsReviewConfigError(
            "choose status-only or private-values test mode, not both"
        )
    if args.include_private_review_values_google_test_only:
        config = sheets.load_google_sheets_review_config(args.google_config)
        if not config.allow_private_review_value_sync:
            raise sheets.GoogleSheetsReviewConfigError(
                "private review value sync requires allow_private_review_value_sync=true in local config"
            )
        return sheets.SYNC_MODE_PRIVATE_VALUES_TEST_ONLY
    return sheets.SYNC_MODE_STATUS_ONLY


def _safe_summary_lines(result, dry_run=False):
    if result.get("preflight_only"):
        return [
            "Google Sheets RateCon review sync preflight",
            f"review_outputs_found: {result.get('review_outputs_found', False)}",
            f"rows_per_source_file: {result.get('rows_per_source_file', {})}",
            f"headers_valid: {result.get('headers_valid', False)}",
            f"sync_ready: {result.get('sync_ready', False)}",
            f"missing_csv_basenames: {result.get('missing_csv_basenames', [])}",
            f"warning_codes: {result.get('warning_codes', [])}",
            f"private_values_printed: {result.get('private_values_printed', False)}",
            f"input_path_printed: {result.get('input_path_printed', False)}",
        ]
    lines = [
        "Google Sheets RateCon review sync summary",
        f"dry_run: {bool(dry_run)}",
        f"sync_mode: {result.get('sync_mode', sheets.SYNC_MODE_STATUS_ONLY)}",
        f"tabs_updated: {result.get('tabs_updated', [])}",
        f"row_counts: {result.get('row_counts', {})}",
        f"missing_csv_basenames: {result.get('missing_csv_basenames', [])}",
        f"private_values_printed: {result.get('private_values_printed', False)}",
        f"credentials_printed: {result.get('credentials_printed', False)}",
        f"spreadsheet_id_printed: {result.get('spreadsheet_id_printed', False)}",
    ]
    return lines


def run_sync(args):
    if args.preflight_only:
        result = preflight_google_review_outputs(args.input_dir)
        result["preflight_only"] = True
        return result

    if not args.confirm_google_review_sync:
        raise sheets.GoogleSheetsReviewConfigError(
            "--confirm-google-review-sync is required"
        )

    mode = _sync_mode(args)
    include_values = bool(
        mode == sheets.SYNC_MODE_PRIVATE_VALUES_TEST_ONLY
        and args.include_private_review_values_google_test_only
    )
    loaded = sheets.read_local_review_csv_rows(args.input_dir)
    rows_by_tab = sheets.build_google_review_tab_rows_from_review_csvs(
        args.input_dir,
        sync_mode=mode,
        include_private_values=include_values,
        worksheet_prefix=args.worksheet_prefix,
    )
    sheets.validate_google_review_tab_titles(rows_by_tab)
    row_counts = {title: len(rows) for title, rows in rows_by_tab.items()}
    if args.dry_run:
        return {
            "sync_mode": mode,
            "tabs_updated": list(rows_by_tab),
            "row_counts": row_counts,
            "missing_csv_basenames": loaded.get("missing_csv_basenames", []),
            "private_values_printed": False,
            "credentials_printed": False,
            "spreadsheet_id_printed": False,
        }

    config = _config_with_overrides(args)
    client = sheets.connect_to_google_sheet(config)
    result = client.batch_update_review_tabs(rows_by_tab)
    result["sync_mode"] = mode
    result["missing_csv_basenames"] = loaded.get("missing_csv_basenames", [])
    return result


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_sync(args)
    except (sheets.GoogleSheetsReviewConfigError, sheets.GoogleSheetsReviewClientError) as exc:
        print("Google Sheets review sync skipped.", file=sys.stderr)
        print(f"Reason: {exc}.", file=sys.stderr)
        return 2

    for line in _safe_summary_lines(result, dry_run=args.dry_run):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
