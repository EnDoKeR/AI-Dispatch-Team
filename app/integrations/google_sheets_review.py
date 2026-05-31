"""Google Sheets review sync adapter contracts and config loading.

The adapter is for explicit RateCon review sync only. It must not own business
decisions, create case records, or print credentials/private values.
"""

from dataclasses import dataclass
import csv
import json
import os
from pathlib import Path

from app.document_ai.ratecon_review_workbook import (
    DOCUMENT_SUMMARY_COLUMNS,
    FIELD_REVIEW_COLUMNS,
    INSTRUCTIONS_COLUMNS,
    RATE_REVIEW_COLUMNS,
    REVIEW_DOCUMENT_SUMMARY_CSV,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_RATE_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    SHEET_DOCUMENT_SUMMARY,
    SHEET_FIELD_REVIEW,
    SHEET_INSTRUCTIONS,
    SHEET_RATE_REVIEW,
    SHEET_STOP_REVIEW,
    STOP_REVIEW_COLUMNS,
    build_ratecon_review_rows,
)


DEFAULT_GOOGLE_SHEETS_REVIEW_CONFIG = Path(
    ".local_private/google_sheets_review_config.json"
)
EXPECTED_SERVICE_ACCOUNT_EMAIL = (
    "ai-dispatch-sheet@ai-dispatch-team.iam.gserviceaccount.com"
)
DEFAULT_WORKSHEET_PREFIX = "RC_"
SYNC_MODE_STATUS_ONLY = "status_only"
SYNC_MODE_PRIVATE_VALUES_TEST_ONLY = "private_values_test_only"
SYNC_MODES = {SYNC_MODE_STATUS_ONLY, SYNC_MODE_PRIVATE_VALUES_TEST_ONLY}
REVIEW_SYNC_WARNING = "LOCAL/TEST REVIEW DATA - DO NOT USE AS FINAL TRUTH"
SHEET_FEEDBACK_SUMMARY = "Feedback_Summary"
FEEDBACK_SUMMARY_COLUMNS = ["Metric", "Value"]
PRIVATE_REVIEW_VALUE_COLUMNS = {
    "Predicted Value LOCAL ONLY",
    "User Expected Value LOCAL ONLY",
}
REVIEW_SYNC_ALLOWED_BASE_SHEETS = {
    SHEET_DOCUMENT_SUMMARY,
    SHEET_STOP_REVIEW,
    SHEET_FIELD_REVIEW,
    SHEET_RATE_REVIEW,
    SHEET_INSTRUCTIONS,
    SHEET_FEEDBACK_SUMMARY,
}
REVIEW_CSV_SPECS = {
    SHEET_DOCUMENT_SUMMARY: (REVIEW_DOCUMENT_SUMMARY_CSV, DOCUMENT_SUMMARY_COLUMNS),
    SHEET_STOP_REVIEW: (REVIEW_STOP_REVIEW_CSV, STOP_REVIEW_COLUMNS),
    SHEET_FIELD_REVIEW: (REVIEW_FIELD_REVIEW_CSV, FIELD_REVIEW_COLUMNS),
    SHEET_RATE_REVIEW: (REVIEW_RATE_REVIEW_CSV, RATE_REVIEW_COLUMNS),
}


class GoogleSheetsReviewConfigError(ValueError):
    """Raised when review sync config is missing or unsafe."""


class GoogleSheetsReviewClientError(RuntimeError):
    """Raised when Google Sheets review sync cannot connect or update."""


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


@dataclass(frozen=True)
class GoogleSheetsReviewConfig:
    spreadsheet_id: str
    credentials_json_path: str
    worksheet_prefix: str = DEFAULT_WORKSHEET_PREFIX
    service_account_email: str = EXPECTED_SERVICE_ACCOUNT_EMAIL
    default_sync_mode: str = SYNC_MODE_STATUS_ONLY
    allow_private_review_value_sync: bool = False

    def safe_summary(self):
        return {
            "spreadsheet_configured": bool(self.spreadsheet_id),
            "credentials_configured": bool(self.credentials_json_path),
            "credentials_file_exists": Path(self.credentials_json_path).exists()
            if self.credentials_json_path
            else False,
            "worksheet_prefix": self.worksheet_prefix,
            "service_account_email": self.service_account_email,
            "default_sync_mode": self.default_sync_mode,
            "private_value_sync_allowed": bool(self.allow_private_review_value_sync),
            "credentials_path_printed": False,
            "spreadsheet_id_printed": False,
        }


def _load_json_config(path):
    config_path = Path(path)
    if not config_path.exists():
        raise GoogleSheetsReviewConfigError("google sheets review config file not found")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GoogleSheetsReviewConfigError("google sheets review config is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise GoogleSheetsReviewConfigError("google sheets review config must be a JSON object")
    return payload


def _config_path(explicit_path=""):
    if explicit_path:
        return Path(explicit_path)
    env_path = _text(os.environ.get("AI_DISPATCH_GOOGLE_SHEETS_CONFIG"))
    if env_path:
        return Path(env_path)
    return DEFAULT_GOOGLE_SHEETS_REVIEW_CONFIG


def _normalize_sync_mode(value):
    token = _token(value) or SYNC_MODE_STATUS_ONLY
    if token not in SYNC_MODES:
        raise GoogleSheetsReviewConfigError("unsupported google sheets review sync mode")
    return token


def build_google_sheets_review_config(payload=None):
    data = payload or {}
    spreadsheet_id = _text(data.get("spreadsheet_id")) or _text(
        os.environ.get("AI_DISPATCH_GOOGLE_SPREADSHEET_ID")
    )
    credentials_json_path = _text(data.get("credentials_json_path")) or _text(
        os.environ.get("AI_DISPATCH_GOOGLE_CREDENTIALS_JSON")
    )
    worksheet_prefix = _text(data.get("worksheet_prefix")) or DEFAULT_WORKSHEET_PREFIX
    service_account_email = _text(data.get("service_account_email")) or EXPECTED_SERVICE_ACCOUNT_EMAIL
    default_sync_mode = _normalize_sync_mode(data.get("default_sync_mode"))
    allow_private_review_value_sync = bool(data.get("allow_private_review_value_sync"))

    if not spreadsheet_id:
        raise GoogleSheetsReviewConfigError("google sheets spreadsheet_id is missing")
    if not credentials_json_path:
        raise GoogleSheetsReviewConfigError("google sheets credentials_json_path is missing")

    return GoogleSheetsReviewConfig(
        spreadsheet_id=spreadsheet_id,
        credentials_json_path=credentials_json_path,
        worksheet_prefix=worksheet_prefix,
        service_account_email=service_account_email,
        default_sync_mode=default_sync_mode,
        allow_private_review_value_sync=allow_private_review_value_sync,
    )


def load_google_sheets_review_config(config_path=""):
    path = _config_path(config_path)
    if path.exists():
        payload = _load_json_config(path)
    else:
        if config_path or os.environ.get("AI_DISPATCH_GOOGLE_SHEETS_CONFIG"):
            raise GoogleSheetsReviewConfigError("google sheets review config file not found")
        payload = {}
    return build_google_sheets_review_config(payload)


def validate_google_sheets_review_config(config, require_credentials_file=True):
    if not isinstance(config, GoogleSheetsReviewConfig):
        config = build_google_sheets_review_config(config)

    credentials_file_exists = (
        Path(config.credentials_json_path).exists()
        if config.credentials_json_path
        else False
    )
    service_account_email_expected = (
        _text(config.service_account_email) == EXPECTED_SERVICE_ACCOUNT_EMAIL
    )
    warning_codes = []
    if not _text(config.spreadsheet_id):
        warning_codes.append("missing_spreadsheet_id")
    if not _text(config.credentials_json_path):
        warning_codes.append("missing_credentials_json_path")
    if require_credentials_file and not credentials_file_exists:
        warning_codes.append("missing_credentials_file")
    if not service_account_email_expected:
        warning_codes.append("service_account_email_mismatch")

    return {
        "spreadsheet_id_present": bool(_text(config.spreadsheet_id)),
        "credentials_path_present": bool(_text(config.credentials_json_path)),
        "credentials_file_exists": credentials_file_exists,
        "worksheet_prefix": config.worksheet_prefix,
        "service_account_email_expected": service_account_email_expected,
        "private_value_sync_allowed": bool(config.allow_private_review_value_sync),
        "sync_ready": not warning_codes,
        "warning_codes": warning_codes,
        "credentials_path_printed": False,
        "spreadsheet_id_printed": False,
        "private_key_printed": False,
    }


def _missing_google_dependency_error(exc):
    return GoogleSheetsReviewClientError(
        "google sheets optional dependency is unavailable; install the existing "
        "manual Google Sheets extras in the local environment"
    )


def _is_worksheet_not_found(exc):
    return exc.__class__.__name__ in {"WorksheetNotFound", "WorksheetNotFoundException"}


def _row_width(rows):
    width = 1
    for row in rows or []:
        if isinstance(row, (list, tuple)):
            width = max(width, len(row))
    return width


def _tab_title(sheet_name, worksheet_prefix=DEFAULT_WORKSHEET_PREFIX):
    prefix = _text(worksheet_prefix) or DEFAULT_WORKSHEET_PREFIX
    name = _text(sheet_name)
    return name if name.startswith(prefix) else f"{prefix}{name}"


def google_review_tab_title(sheet_name, worksheet_prefix=DEFAULT_WORKSHEET_PREFIX):
    return _tab_title(sheet_name, worksheet_prefix)


def allowed_google_review_tab_titles():
    return sorted(
        _tab_title(sheet_name, DEFAULT_WORKSHEET_PREFIX)
        for sheet_name in REVIEW_SYNC_ALLOWED_BASE_SHEETS
    )


def validate_google_review_tab_titles(rows_by_tab):
    allowed = set(allowed_google_review_tab_titles())
    unexpected = sorted(
        title for title in (_text(title) for title in (rows_by_tab or {})) if title not in allowed
    )
    if unexpected:
        raise GoogleSheetsReviewClientError(
            "google sheets review sync can update dedicated RC_* review tabs only"
        )
    return {
        "tabs_allowed": True,
        "tabs_checked": sorted(_text(title) for title in (rows_by_tab or {})),
        "unexpected_tabs": [],
    }


def _sheet_values(columns, dict_rows, note=REVIEW_SYNC_WARNING):
    header = list(columns or [])
    note_row = [note] + [""] * max(len(header) - 1, 0)
    values = [note_row, header]
    for row in dict_rows or []:
        values.append([row.get(column, "") for column in header])
    return values


def _feedback_summary_rows(feedback_summary=None):
    summary = feedback_summary if isinstance(feedback_summary, dict) else {}
    rows = []
    for key, value in sorted(summary.items()):
        if isinstance(value, (dict, list, tuple, set)):
            safe_value = json.dumps(value, sort_keys=True)
        else:
            safe_value = _text(value)
        rows.append({"Metric": _text(key), "Value": safe_value})
    if not rows:
        rows.append({"Metric": "feedback_status", "Value": "not_downloaded"})
    return rows


def _instruction_rows_for_google_sync(include_private_values=False):
    rows = [
        {
            "Section": "Local/test review",
            "Instruction": REVIEW_SYNC_WARNING,
        },
        {
            "Section": "Review flow",
            "Instruction": "Mark correct, incorrect, or unknown; add issue type and local notes when useful.",
        },
        {
            "Section": "Safe sharing",
            "Instruction": "Share aliases, counts, statuses, issue type counts, and field names only.",
        },
        {
            "Section": "Do not share",
            "Instruction": "Do not share service account keys, private values, raw text, local paths, rates, addresses, or references.",
        },
    ]
    if include_private_values:
        rows.append(
            {
                "Section": "Private values",
                "Instruction": "Private predicted values were uploaded for local test review only.",
            }
        )
    return rows


def _sanitize_review_rows(rows, include_private_values=False):
    sanitized = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        clean = dict(row)
        if not include_private_values:
            for column in PRIVATE_REVIEW_VALUE_COLUMNS:
                if column in clean:
                    clean[column] = ""
        sanitized.append(clean)
    return sanitized


def read_local_review_csv_rows(input_dir):
    """Read local review CSVs from ignored output without printing file paths."""

    root = Path(input_dir)
    rows_by_sheet = {}
    missing = []
    for sheet_name, (filename, columns) in REVIEW_CSV_SPECS.items():
        path = root / filename
        if not path.exists():
            missing.append(filename)
            rows_by_sheet[sheet_name] = []
            continue
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows_by_sheet[sheet_name] = [
                {column: row.get(column, "") for column in columns}
                for row in reader
            ]
    return {
        "rows_by_sheet": rows_by_sheet,
        "missing_csv_basenames": missing,
        "input_path_printed": False,
        "private_values_printed": False,
    }


def build_google_review_tab_rows_from_review_csvs(
    input_dir,
    sync_mode=SYNC_MODE_STATUS_ONLY,
    include_private_values=False,
    worksheet_prefix=DEFAULT_WORKSHEET_PREFIX,
    feedback_summary=None,
):
    mode = _normalize_sync_mode(sync_mode)
    include_values = bool(
        include_private_values and mode == SYNC_MODE_PRIVATE_VALUES_TEST_ONLY
    )
    loaded = read_local_review_csv_rows(input_dir)
    rows_by_sheet = loaded["rows_by_sheet"]
    return {
        _tab_title(SHEET_DOCUMENT_SUMMARY, worksheet_prefix): _sheet_values(
            DOCUMENT_SUMMARY_COLUMNS,
            _sanitize_review_rows(
                rows_by_sheet.get(SHEET_DOCUMENT_SUMMARY, []),
                include_private_values=include_values,
            ),
        ),
        _tab_title(SHEET_STOP_REVIEW, worksheet_prefix): _sheet_values(
            STOP_REVIEW_COLUMNS,
            _sanitize_review_rows(
                rows_by_sheet.get(SHEET_STOP_REVIEW, []),
                include_private_values=include_values,
            ),
        ),
        _tab_title(SHEET_FIELD_REVIEW, worksheet_prefix): _sheet_values(
            FIELD_REVIEW_COLUMNS,
            _sanitize_review_rows(
                rows_by_sheet.get(SHEET_FIELD_REVIEW, []),
                include_private_values=include_values,
            ),
        ),
        _tab_title(SHEET_RATE_REVIEW, worksheet_prefix): _sheet_values(
            RATE_REVIEW_COLUMNS,
            _sanitize_review_rows(
                rows_by_sheet.get(SHEET_RATE_REVIEW, []),
                include_private_values=include_values,
            ),
        ),
        _tab_title(SHEET_INSTRUCTIONS, worksheet_prefix): _sheet_values(
            INSTRUCTIONS_COLUMNS,
            _instruction_rows_for_google_sync(include_private_values=include_values),
        ),
        _tab_title(SHEET_FEEDBACK_SUMMARY, worksheet_prefix): _sheet_values(
            FEEDBACK_SUMMARY_COLUMNS,
            _feedback_summary_rows(feedback_summary),
        ),
    }


def build_google_review_tab_rows(
    measurement_rows,
    local_document_names_by_alias=None,
    sync_mode=SYNC_MODE_STATUS_ONLY,
    include_private_values=False,
    worksheet_prefix=DEFAULT_WORKSHEET_PREFIX,
    feedback_summary=None,
):
    """Build dedicated review-tab payloads for Google Sheets sync."""

    mode = _normalize_sync_mode(sync_mode)
    include_values = bool(
        include_private_values and mode == SYNC_MODE_PRIVATE_VALUES_TEST_ONLY
    )
    rows_by_sheet = build_ratecon_review_rows(
        measurement_rows,
        local_document_names_by_alias=local_document_names_by_alias,
        include_private_values=include_values,
    )
    return {
        _tab_title(SHEET_DOCUMENT_SUMMARY, worksheet_prefix): _sheet_values(
            DOCUMENT_SUMMARY_COLUMNS,
            rows_by_sheet.get(SHEET_DOCUMENT_SUMMARY, []),
        ),
        _tab_title(SHEET_STOP_REVIEW, worksheet_prefix): _sheet_values(
            STOP_REVIEW_COLUMNS,
            rows_by_sheet.get(SHEET_STOP_REVIEW, []),
        ),
        _tab_title(SHEET_FIELD_REVIEW, worksheet_prefix): _sheet_values(
            FIELD_REVIEW_COLUMNS,
            rows_by_sheet.get(SHEET_FIELD_REVIEW, []),
        ),
        _tab_title(SHEET_RATE_REVIEW, worksheet_prefix): _sheet_values(
            RATE_REVIEW_COLUMNS,
            rows_by_sheet.get(SHEET_RATE_REVIEW, []),
        ),
        _tab_title(SHEET_INSTRUCTIONS, worksheet_prefix): _sheet_values(
            INSTRUCTIONS_COLUMNS,
            rows_by_sheet.get(SHEET_INSTRUCTIONS, []),
        ),
        _tab_title(SHEET_FEEDBACK_SUMMARY, worksheet_prefix): _sheet_values(
            FEEDBACK_SUMMARY_COLUMNS,
            _feedback_summary_rows(feedback_summary),
        ),
    }


def ensure_worksheet(spreadsheet, title, rows=1000, cols=26):
    """Return an existing worksheet or create a dedicated review worksheet."""

    safe_title = _text(title)
    if not safe_title:
        raise GoogleSheetsReviewClientError("worksheet title is missing")

    try:
        return spreadsheet.worksheet(safe_title)
    except Exception as exc:
        if not _is_worksheet_not_found(exc):
            raise

    return spreadsheet.add_worksheet(
        title=safe_title,
        rows=str(max(int(rows or 1), 1)),
        cols=str(max(int(cols or 1), 1)),
    )


def clear_and_update_worksheet(worksheet, rows):
    """Clear and replace a worksheet with already-redacted review rows."""

    payload = rows or []
    worksheet.clear()
    if not payload:
        return {"row_count": 0, "private_values_printed": False}
    try:
        worksheet.update(payload, value_input_option="USER_ENTERED")
    except TypeError:
        worksheet.update("A1", payload)
    return {"row_count": len(payload), "private_values_printed": False}


def download_worksheet_rows(spreadsheet, title):
    worksheet = spreadsheet.worksheet(_text(title))
    rows = worksheet.get_all_values()
    return {
        "title": _text(title),
        "rows": rows or [],
        "row_count": len(rows or []),
        "private_values_printed": False,
    }


class GoogleSheetsReviewClient:
    """Small adapter for explicit review-tab Google Sheets operations."""

    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet

    def ensure_worksheet(self, title, rows=1000, cols=26):
        return ensure_worksheet(self.spreadsheet, title, rows=rows, cols=cols)

    def clear_and_update_worksheet(self, worksheet, rows):
        return clear_and_update_worksheet(worksheet, rows)

    def batch_update_review_tabs(self, rows_by_tab):
        return batch_update_review_tabs(self, rows_by_tab)

    def download_worksheet_rows(self, title):
        return download_worksheet_rows(self.spreadsheet, title)


def connect_to_google_sheet(config):
    """Connect to a spreadsheet using local-only service account credentials."""

    if not isinstance(config, GoogleSheetsReviewConfig):
        config = build_google_sheets_review_config(config)
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception as exc:
        raise _missing_google_dependency_error(exc) from exc

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_file(
        config.credentials_json_path,
        scopes=scopes,
    )
    client = gspread.authorize(credentials)
    return GoogleSheetsReviewClient(client.open_by_key(config.spreadsheet_id))


def batch_update_review_tabs(client_or_spreadsheet, rows_by_tab):
    """Replace dedicated review tabs and return counts only."""

    validate_google_review_tab_titles(rows_by_tab)

    if isinstance(client_or_spreadsheet, GoogleSheetsReviewClient):
        client = client_or_spreadsheet
    else:
        client = GoogleSheetsReviewClient(client_or_spreadsheet)

    row_counts = {}
    updated = []
    for title, rows in (rows_by_tab or {}).items():
        row_payload = rows or []
        worksheet = client.ensure_worksheet(
            title,
            rows=max(len(row_payload) + 10, 100),
            cols=max(_row_width(row_payload), 1),
        )
        result = client.clear_and_update_worksheet(worksheet, row_payload)
        row_counts[_text(title)] = int(result.get("row_count", 0) or 0)
        updated.append(_text(title))

    return {
        "tabs_updated": updated,
        "row_counts": row_counts,
        "private_values_printed": False,
        "credentials_printed": False,
        "spreadsheet_id_printed": False,
    }
