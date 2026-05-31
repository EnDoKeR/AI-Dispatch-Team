"""Google Sheets review sync adapter contracts and config loading.

The adapter is for explicit RateCon review sync only. It must not own business
decisions, create DispatchCases, or print credentials/private values.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path


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


class GoogleSheetsReviewConfigError(ValueError):
    """Raised when review sync config is missing or unsafe."""


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

    def safe_summary(self):
        return {
            "spreadsheet_configured": bool(self.spreadsheet_id),
            "credentials_configured": bool(self.credentials_json_path),
            "worksheet_prefix": self.worksheet_prefix,
            "service_account_email": self.service_account_email,
            "default_sync_mode": self.default_sync_mode,
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
