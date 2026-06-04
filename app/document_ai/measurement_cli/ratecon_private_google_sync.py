"""Google Sheets sync orchestration for private RateCon measurement CLI."""

from dataclasses import dataclass
from pathlib import Path

from app.integrations import google_sheets_review as sheets_review


GoogleSheetsReviewConfigError = sheets_review.GoogleSheetsReviewConfigError
GoogleSheetsReviewClientError = sheets_review.GoogleSheetsReviewClientError


@dataclass(frozen=True)
class PrivateRateconGoogleSyncPlan:
    """Google sync plan derived from already-validated CLI config."""

    enabled: bool
    output_dir: Path | None = None
    message_label: str = "google_sheet_sync"


@dataclass(frozen=True)
class PrivateRateconGoogleSyncResult:
    """Console-safe Google sync result."""

    message_label: str
    payload: dict
    sync_result: dict


def build_private_ratecon_google_sync_plan(config, output_paths=None):
    """Return whether the existing Google sync task should run."""
    enabled = bool(
        getattr(config, "sync_review_google_sheet", False)
        and not getattr(config, "dry_run", False)
    )
    return PrivateRateconGoogleSyncPlan(
        enabled=enabled,
        output_dir=getattr(output_paths, "output_dir", None),
    )


def load_private_ratecon_google_review_config(config, *, sheets_module=sheets_review):
    """Load Google review config using the historical override precedence."""
    loaded = sheets_module.load_google_sheets_review_config(config.google_config)
    return sheets_module.GoogleSheetsReviewConfig(
        spreadsheet_id=getattr(config, "google_spreadsheet_id", "") or loaded.spreadsheet_id,
        credentials_json_path=(
            getattr(config, "google_credentials_json", "")
            or loaded.credentials_json_path
        ),
        worksheet_prefix=getattr(config, "google_worksheet_prefix", "") or loaded.worksheet_prefix,
        service_account_email=loaded.service_account_email,
        default_sync_mode=loaded.default_sync_mode,
        allow_private_review_value_sync=getattr(
            loaded,
            "allow_private_review_value_sync",
            False,
        ),
    )


def sync_private_ratecon_google_review_tabs(
    report,
    config,
    *,
    sheets_module=sheets_review,
):
    """Run the existing Google review tab sync without changing semantics."""
    mode = (
        sheets_module.SYNC_MODE_PRIVATE_VALUES_TEST_ONLY
        if getattr(config, "include_private_review_values_google_test_only", False)
        else sheets_module.SYNC_MODE_STATUS_ONLY
    )
    if getattr(config, "include_private_review_values_google_test_only", False):
        google_config = load_private_ratecon_google_review_config(
            config,
            sheets_module=sheets_module,
        )
        if not google_config.allow_private_review_value_sync:
            raise sheets_module.GoogleSheetsReviewConfigError(
                "private review value sync requires allow_private_review_value_sync=true in local config"
            )
    rows_by_tab = sheets_module.build_google_review_tab_rows(
        report["rows"],
        local_document_names_by_alias=report.get("local_document_names_by_alias", {}),
        sync_mode=mode,
        include_private_values=getattr(
            config,
            "include_private_review_values_google_test_only",
            False,
        ),
        worksheet_prefix=getattr(config, "google_worksheet_prefix", ""),
    )
    google_config = load_private_ratecon_google_review_config(
        config,
        sheets_module=sheets_module,
    )
    client = sheets_module.connect_to_google_sheet(google_config)
    result = client.batch_update_review_tabs(rows_by_tab)
    result["sync_mode"] = mode
    return result


def private_ratecon_google_sync_labels(sync_result):
    """Return the historical console-safe Google sync label payload."""
    return {
        "google_sheet_sync": "completed",
        "tabs_updated": sync_result.get("tabs_updated", []),
        "row_counts": sync_result.get("row_counts", {}),
        "sync_mode": sync_result.get("sync_mode", "status_only"),
        "private_values_printed": sync_result.get("private_values_printed", False),
        "credentials_printed": sync_result.get("credentials_printed", False),
        "spreadsheet_id_printed": sync_result.get("spreadsheet_id_printed", False),
    }


def run_private_ratecon_google_sync_if_enabled(
    report,
    config,
    output_paths,
    *,
    sync_callable=sync_private_ratecon_google_review_tabs,
):
    """Run Google sync when requested, otherwise return no-op."""
    plan = build_private_ratecon_google_sync_plan(config, output_paths)
    if not plan.enabled:
        return None

    sync_result = sync_callable(report, config)
    return PrivateRateconGoogleSyncResult(
        message_label=plan.message_label,
        payload=private_ratecon_google_sync_labels(sync_result),
        sync_result=sync_result,
    )
