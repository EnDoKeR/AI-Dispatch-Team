import sys
import types
import unittest
from unittest.mock import patch

from app.integrations.google_sheets_review import (
    GoogleSheetsReviewClient,
    GoogleSheetsReviewClientError,
    GoogleSheetsReviewConfig,
    allowed_google_review_tab_titles,
    batch_update_review_tabs,
    clear_and_update_worksheet,
    connect_to_google_sheet,
    download_worksheet_rows,
    ensure_worksheet,
    validate_google_review_tab_titles,
)


class WorksheetNotFound(Exception):
    pass


class FakeWorksheet:
    def __init__(self, title, values=None):
        self.title = title
        self.values = values or []
        self.cleared = False
        self.updated = []

    def clear(self):
        self.cleared = True

    def update(self, rows, value_input_option=None):
        self.updated = rows

    def get_all_values(self):
        return self.values


class FakeSpreadsheet:
    def __init__(self):
        self.worksheets = {}
        self.created = []

    def worksheet(self, title):
        if title not in self.worksheets:
            raise WorksheetNotFound()
        return self.worksheets[title]

    def add_worksheet(self, title, rows, cols):
        worksheet = FakeWorksheet(title)
        self.worksheets[title] = worksheet
        self.created.append({"title": title, "rows": rows, "cols": cols})
        return worksheet


class GoogleSheetsReviewClientTests(unittest.TestCase):
    def test_ensure_worksheet_returns_existing_sheet(self):
        spreadsheet = FakeSpreadsheet()
        spreadsheet.worksheets["RC_Document_Summary"] = FakeWorksheet(
            "RC_Document_Summary"
        )

        worksheet = ensure_worksheet(spreadsheet, "RC_Document_Summary")

        self.assertEqual(worksheet.title, "RC_Document_Summary")
        self.assertEqual(spreadsheet.created, [])

    def test_ensure_worksheet_creates_missing_sheet(self):
        spreadsheet = FakeSpreadsheet()

        worksheet = ensure_worksheet(spreadsheet, "RC_Stop_Review", rows=5, cols=3)

        self.assertEqual(worksheet.title, "RC_Stop_Review")
        self.assertEqual(
            spreadsheet.created,
            [{"title": "RC_Stop_Review", "rows": "5", "cols": "3"}],
        )

    def test_clear_and_update_worksheet_replaces_rows(self):
        worksheet = FakeWorksheet("RC_Field_Review")

        result = clear_and_update_worksheet(
            worksheet,
            [["Measurement Alias", "Status"], ["RATECON_001", "resolved"]],
        )

        self.assertTrue(worksheet.cleared)
        self.assertEqual(len(worksheet.updated), 2)
        self.assertEqual(result["row_count"], 2)
        self.assertFalse(result["private_values_printed"])

    def test_batch_update_review_tabs_uses_fake_client(self):
        spreadsheet = FakeSpreadsheet()
        rows_by_tab = {
            "RC_Document_Summary": [["alias"], ["RATECON_001"]],
            "RC_Stop_Review": [["stop_id"]],
        }

        result = batch_update_review_tabs(spreadsheet, rows_by_tab)

        self.assertEqual(
            result["row_counts"],
            {"RC_Document_Summary": 2, "RC_Stop_Review": 1},
        )
        self.assertEqual(set(result["tabs_updated"]), set(rows_by_tab))
        self.assertFalse(result["credentials_printed"])

    def test_batch_update_refuses_non_review_tab(self):
        spreadsheet = FakeSpreadsheet()
        with self.assertRaises(GoogleSheetsReviewClientError) as ctx:
            batch_update_review_tabs(
                spreadsheet,
                {"Operational_Dispatch": [["must not update"]]},
            )

        self.assertIn("dedicated RC_* review tabs", str(ctx.exception))
        self.assertEqual(spreadsheet.created, [])

    def test_tab_validator_allows_only_dedicated_review_tabs(self):
        tabs = allowed_google_review_tab_titles()

        result = validate_google_review_tab_titles({title: [["ok"]] for title in tabs})

        self.assertTrue(result["tabs_allowed"])
        self.assertIn("RC_Document_Summary", result["tabs_checked"])

    def test_existing_operational_tab_is_ignored(self):
        spreadsheet = FakeSpreadsheet()
        spreadsheet.worksheets["Operational_Dispatch"] = FakeWorksheet(
            "Operational_Dispatch",
            values=[["existing"]],
        )

        batch_update_review_tabs(
            spreadsheet,
            {"RC_Document_Summary": [["alias"], ["RATECON_001"]]},
        )

        self.assertFalse(spreadsheet.worksheets["Operational_Dispatch"].cleared)

    def test_download_worksheet_rows_returns_counts_only(self):
        spreadsheet = FakeSpreadsheet()
        spreadsheet.worksheets["RC_Rate_Review"] = FakeWorksheet(
            "RC_Rate_Review",
            values=[["field"], ["rate"]],
        )

        result = download_worksheet_rows(spreadsheet, "RC_Rate_Review")

        self.assertEqual(result["row_count"], 2)
        self.assertFalse(result["private_values_printed"])

    def test_client_methods_delegate_to_helpers(self):
        spreadsheet = FakeSpreadsheet()
        client = GoogleSheetsReviewClient(spreadsheet)

        result = client.batch_update_review_tabs({"RC_Document_Summary": [["alias"]]})

        self.assertEqual(result["row_counts"]["RC_Document_Summary"], 1)

    def test_connect_missing_dependency_gives_safe_error(self):
        config = GoogleSheetsReviewConfig(
            spreadsheet_id="fake-spreadsheet",
            credentials_json_path="fake-credentials.json",
        )
        with patch.dict(sys.modules, {"gspread": None}):
            with self.assertRaises(GoogleSheetsReviewClientError) as ctx:
                connect_to_google_sheet(config)

        self.assertNotIn("fake-credentials", str(ctx.exception))
        self.assertNotIn("fake-spreadsheet", str(ctx.exception))

    def test_connect_uses_google_client_when_dependencies_exist(self):
        opened = {}

        class FakeCredentials:
            @staticmethod
            def from_service_account_file(path, scopes=None):
                opened["credentials_path"] = path
                opened["scopes"] = scopes
                return "credentials"

        class FakeGspread(types.SimpleNamespace):
            @staticmethod
            def authorize(credentials):
                opened["credentials"] = credentials
                return types.SimpleNamespace(
                    open_by_key=lambda spreadsheet_id: f"spreadsheet:{spreadsheet_id}"
                )

        google_module = types.ModuleType("google")
        oauth2_module = types.ModuleType("google.oauth2")
        service_account_module = types.ModuleType("google.oauth2.service_account")
        service_account_module.Credentials = FakeCredentials

        with patch.dict(
            sys.modules,
            {
                "gspread": FakeGspread(),
                "google": google_module,
                "google.oauth2": oauth2_module,
                "google.oauth2.service_account": service_account_module,
            },
        ):
            client = connect_to_google_sheet(
                GoogleSheetsReviewConfig(
                    spreadsheet_id="fake-spreadsheet",
                    credentials_json_path="fake-credentials.json",
                )
            )

        self.assertIsInstance(client, GoogleSheetsReviewClient)
        self.assertEqual(client.spreadsheet, "spreadsheet:fake-spreadsheet")
        self.assertEqual(opened["credentials"], "credentials")


if __name__ == "__main__":
    unittest.main()
