"""Create an ignored local Google Sheets review sync config."""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.integrations.google_sheets_review import (
    DEFAULT_GOOGLE_SHEETS_REVIEW_CONFIG,
    DEFAULT_WORKSHEET_PREFIX,
    EXPECTED_SERVICE_ACCOUNT_EMAIL,
    GoogleSheetsReviewConfigError,
    build_google_sheets_review_config,
    validate_google_sheets_review_config,
)


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Initialize ignored local Google Sheets review sync config."
    )
    parser.add_argument("--spreadsheet-id", required=True)
    parser.add_argument("--credentials-json", required=True)
    parser.add_argument("--worksheet-prefix", default=DEFAULT_WORKSHEET_PREFIX)
    parser.add_argument(
        "--service-account-email",
        default=EXPECTED_SERVICE_ACCOUNT_EMAIL,
    )
    parser.add_argument("--allow-private-review-value-sync", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--config-output",
        default=str(DEFAULT_GOOGLE_SHEETS_REVIEW_CONFIG),
        help="Ignored local config path. Defaults to .local_private/google_sheets_review_config.json.",
    )
    return parser


def write_google_sheets_review_config(
    spreadsheet_id,
    credentials_json,
    worksheet_prefix=DEFAULT_WORKSHEET_PREFIX,
    service_account_email=EXPECTED_SERVICE_ACCOUNT_EMAIL,
    allow_private_review_value_sync=False,
    config_output=DEFAULT_GOOGLE_SHEETS_REVIEW_CONFIG,
    overwrite=False,
):
    output_path = Path(config_output)
    credentials_path = Path(credentials_json)

    if output_path.exists() and not overwrite:
        raise GoogleSheetsReviewConfigError(
            "google sheets review config already exists; pass --overwrite"
        )
    if not credentials_path.exists():
        raise GoogleSheetsReviewConfigError("google sheets credentials file not found")

    payload = {
        "spreadsheet_id": str(spreadsheet_id or "").strip(),
        "credentials_json_path": str(credentials_path),
        "worksheet_prefix": str(worksheet_prefix or DEFAULT_WORKSHEET_PREFIX).strip(),
        "service_account_email": str(
            service_account_email or EXPECTED_SERVICE_ACCOUNT_EMAIL
        ).strip(),
        "default_sync_mode": "status_only",
        "allow_private_review_value_sync": bool(allow_private_review_value_sync),
    }
    config = build_google_sheets_review_config(payload)
    validation = validate_google_sheets_review_config(config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "config_written": True,
        "spreadsheet_id_present": validation["spreadsheet_id_present"],
        "credentials_file_exists": validation["credentials_file_exists"],
        "worksheet_prefix": config.worksheet_prefix,
        "service_account_email_expected": validation["service_account_email_expected"],
        "private_value_sync_allowed": validation["private_value_sync_allowed"],
        "warning_codes": validation["warning_codes"],
        "config_path_printed": False,
        "credential_path_printed": False,
        "private_key_printed": False,
    }


def _safe_summary_lines(result):
    return [
        f"config_written: {'yes' if result.get('config_written') else 'no'}",
        f"spreadsheet_id_present: {'yes' if result.get('spreadsheet_id_present') else 'no'}",
        f"credentials_file_exists: {'yes' if result.get('credentials_file_exists') else 'no'}",
        f"worksheet_prefix: {result.get('worksheet_prefix', DEFAULT_WORKSHEET_PREFIX)}",
        f"service_account_email_expected: {'yes' if result.get('service_account_email_expected') else 'no'}",
        f"private_value_sync_allowed: {'yes' if result.get('private_value_sync_allowed') else 'no'}",
        f"warning_codes: {result.get('warning_codes', [])}",
        f"config_path_printed: {result.get('config_path_printed', False)}",
        f"credential_path_printed: {result.get('credential_path_printed', False)}",
        f"private_key_printed: {result.get('private_key_printed', False)}",
    ]


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = write_google_sheets_review_config(
            spreadsheet_id=args.spreadsheet_id,
            credentials_json=args.credentials_json,
            worksheet_prefix=args.worksheet_prefix,
            service_account_email=args.service_account_email,
            allow_private_review_value_sync=args.allow_private_review_value_sync,
            config_output=args.config_output,
            overwrite=args.overwrite,
        )
    except GoogleSheetsReviewConfigError as exc:
        print("Google Sheets review config was not written.", file=sys.stderr)
        print(f"Reason: {exc}.", file=sys.stderr)
        return 2

    for line in _safe_summary_lines(result):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
