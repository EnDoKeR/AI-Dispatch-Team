import inspect
import unittest
from types import SimpleNamespace

from app.document_ai.measurement_cli import ratecon_private_google_sync
from app.document_ai.measurement_cli.ratecon_private_google_sync import (
    GoogleSheetsReviewConfigError,
    PrivateRateconGoogleSyncResult,
    build_private_ratecon_google_sync_plan,
    private_ratecon_google_sync_labels,
    run_private_ratecon_google_sync_if_enabled,
    sync_private_ratecon_google_review_tabs,
)
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    build_private_ratecon_output_paths,
)
from app.integrations import google_sheets_review


def _config(**overrides):
    values = {
        "dry_run": False,
        "google_config": "",
        "google_credentials_json": "",
        "google_spreadsheet_id": "",
        "google_worksheet_prefix": "",
        "include_private_review_values_google_test_only": False,
        "sync_review_google_sheet": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _report():
    return {
        "rows": [{"document_alias": "RATECON_001"}],
        "local_document_names_by_alias": {"RATECON_001": "FixtureLoad001"},
    }


class FakeClient:
    def __init__(self):
        self.rows_by_tab = None

    def batch_update_review_tabs(self, rows_by_tab):
        self.rows_by_tab = rows_by_tab
        return {
            "tabs_updated": list(rows_by_tab),
            "row_counts": {title: len(rows) for title, rows in rows_by_tab.items()},
            "private_values_printed": False,
            "credentials_printed": False,
            "spreadsheet_id_printed": False,
        }


class FakeSheetsModule:
    SYNC_MODE_STATUS_ONLY = google_sheets_review.SYNC_MODE_STATUS_ONLY
    SYNC_MODE_PRIVATE_VALUES_TEST_ONLY = (
        google_sheets_review.SYNC_MODE_PRIVATE_VALUES_TEST_ONLY
    )
    GoogleSheetsReviewConfig = google_sheets_review.GoogleSheetsReviewConfig
    GoogleSheetsReviewConfigError = google_sheets_review.GoogleSheetsReviewConfigError

    def __init__(self, *, allow_private_review_value_sync=False):
        self.allow_private_review_value_sync = allow_private_review_value_sync
        self.loaded_config_path = None
        self.rows_call = None
        self.connected_config = None
        self.client = FakeClient()

    def load_google_sheets_review_config(self, config_path=""):
        self.loaded_config_path = config_path
        return self.GoogleSheetsReviewConfig(
            spreadsheet_id="config-spreadsheet",
            credentials_json_path="config-credentials.json",
            worksheet_prefix="RC_",
            service_account_email=(
                "ai-dispatch-sheet@ai-dispatch-team.iam.gserviceaccount.com"
            ),
            default_sync_mode=self.SYNC_MODE_STATUS_ONLY,
            allow_private_review_value_sync=self.allow_private_review_value_sync,
        )

    def build_google_review_tab_rows(
        self,
        rows,
        local_document_names_by_alias=None,
        sync_mode=None,
        include_private_values=False,
        worksheet_prefix="",
    ):
        self.rows_call = {
            "rows": rows,
            "local_document_names_by_alias": local_document_names_by_alias,
            "sync_mode": sync_mode,
            "include_private_values": include_private_values,
            "worksheet_prefix": worksheet_prefix,
        }
        prefix = worksheet_prefix or "RC_"
        return {f"{prefix}Document_Summary": [["Measurement Alias"], ["RATECON_001"]]}

    def connect_to_google_sheet(self, config):
        self.connected_config = config
        return self.client


class PrivateRateconMeasurementGoogleSyncTests(unittest.TestCase):
    def test_google_sync_plan_enables_existing_sync_flag(self):
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_google_sync"
        )

        plan = build_private_ratecon_google_sync_plan(
            _config(sync_review_google_sheet=True),
            output_paths,
        )

        self.assertTrue(plan.enabled)
        self.assertEqual(plan.output_dir, output_paths.output_dir)
        self.assertEqual(plan.message_label, "google_sheet_sync")

    def test_google_sync_plan_disables_when_flag_absent_or_dry_run(self):
        self.assertFalse(build_private_ratecon_google_sync_plan(_config()).enabled)
        self.assertFalse(
            build_private_ratecon_google_sync_plan(
                _config(sync_review_google_sheet=True, dry_run=True)
            ).enabled
        )

    def test_google_sync_wrapper_noops_when_disabled(self):
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_google_sync"
        )

        result = run_private_ratecon_google_sync_if_enabled(
            _report(),
            _config(),
            output_paths,
            sync_callable=lambda report, config: self.fail("sync should not run"),
        )

        self.assertIsNone(result)

    def test_google_sync_wrapper_uses_fake_sync_callable_and_preserves_labels(self):
        calls = {}
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_google_sync"
        )

        def sync_callable(report, config):
            calls["report"] = report
            calls["config"] = config
            return {
                "tabs_updated": ["RC_Document_Summary"],
                "row_counts": {"RC_Document_Summary": 2},
                "sync_mode": "status_only",
                "private_values_printed": False,
                "credentials_printed": False,
                "spreadsheet_id_printed": False,
            }

        config = _config(sync_review_google_sheet=True)
        result = run_private_ratecon_google_sync_if_enabled(
            _report(),
            config,
            output_paths,
            sync_callable=sync_callable,
        )

        self.assertIsInstance(result, PrivateRateconGoogleSyncResult)
        self.assertEqual(calls["report"], _report())
        self.assertIs(calls["config"], config)
        self.assertEqual(result.message_label, "google_sheet_sync")
        self.assertEqual(
            result.payload,
            {
                "google_sheet_sync": "completed",
                "tabs_updated": ["RC_Document_Summary"],
                "row_counts": {"RC_Document_Summary": 2},
                "sync_mode": "status_only",
                "private_values_printed": False,
                "credentials_printed": False,
                "spreadsheet_id_printed": False,
            },
        )

    def test_sync_delegation_preserves_config_overrides_and_upload_rows(self):
        sheets = FakeSheetsModule()
        config = _config(
            google_config="config.local.json",
            google_credentials_json="override-credentials.json",
            google_spreadsheet_id="override-spreadsheet",
            google_worksheet_prefix="TEST_",
        )

        result = sync_private_ratecon_google_review_tabs(
            _report(),
            config,
            sheets_module=sheets,
        )

        self.assertEqual(sheets.loaded_config_path, "config.local.json")
        self.assertEqual(sheets.connected_config.spreadsheet_id, "override-spreadsheet")
        self.assertEqual(
            sheets.connected_config.credentials_json_path,
            "override-credentials.json",
        )
        self.assertEqual(sheets.connected_config.worksheet_prefix, "TEST_")
        self.assertEqual(
            sheets.rows_call,
            {
                "rows": _report()["rows"],
                "local_document_names_by_alias": {"RATECON_001": "FixtureLoad001"},
                "sync_mode": "status_only",
                "include_private_values": False,
                "worksheet_prefix": "TEST_",
            },
        )
        self.assertEqual(result["tabs_updated"], ["TEST_Document_Summary"])
        self.assertEqual(result["sync_mode"], "status_only")
        self.assertFalse(result["private_values_printed"])
        self.assertFalse(result["credentials_printed"])
        self.assertFalse(result["spreadsheet_id_printed"])

    def test_private_value_sync_still_requires_local_config_permission(self):
        sheets = FakeSheetsModule(allow_private_review_value_sync=False)

        with self.assertRaises(GoogleSheetsReviewConfigError):
            sync_private_ratecon_google_review_tabs(
                _report(),
                _config(include_private_review_values_google_test_only=True),
                sheets_module=sheets,
            )

    def test_private_value_sync_uses_existing_mode_when_allowed(self):
        sheets = FakeSheetsModule(allow_private_review_value_sync=True)

        result = sync_private_ratecon_google_review_tabs(
            _report(),
            _config(include_private_review_values_google_test_only=True),
            sheets_module=sheets,
        )

        self.assertEqual(result["sync_mode"], "private_values_test_only")
        self.assertTrue(sheets.rows_call["include_private_values"])

    def test_label_defaults_match_existing_console_shape(self):
        self.assertEqual(
            private_ratecon_google_sync_labels({}),
            {
                "google_sheet_sync": "completed",
                "tabs_updated": [],
                "row_counts": {},
                "sync_mode": "status_only",
                "private_values_printed": False,
                "credentials_printed": False,
                "spreadsheet_id_printed": False,
            },
        )

    def test_module_does_not_process_documents_call_models_or_generate_workbooks(self):
        source = inspect.getsource(ratecon_private_google_sync)
        forbidden = [
            "discover_private_pdfs",
            "measure_private_ratecon_pdf",
            "pytesseract",
            "easyocr",
            "openai",
            "anthropic",
            "gemini",
            "googleapiclient",
            "google.oauth",
            "Workbook",
            "openpyxl",
            "workbook.save",
            "requests.",
            "urllib.",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
