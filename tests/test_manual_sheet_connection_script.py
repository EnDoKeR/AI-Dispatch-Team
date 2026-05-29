import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts import manual_test_sheet_connection


class TestManualSheetConnectionScript(unittest.TestCase):
    def test_load_settings_uses_environment_values(self):
        with patch.dict(
            "os.environ",
            {
                "GOOGLE_CREDENTIALS_FILE": "custom-creds.json",
                "GOOGLE_SPREADSHEET_ID": "sheet-123",
                "GOOGLE_SHEET_NAME": "Loads",
            },
        ):
            settings = manual_test_sheet_connection.load_settings()

        self.assertEqual(settings["credentials_file"], "custom-creds.json")
        self.assertEqual(settings["spreadsheet_id"], "sheet-123")
        self.assertEqual(settings["sheet_name"], "Loads")

    def test_append_test_row_stops_before_external_imports_without_sheet_id(self):
        settings = {
            "credentials_file": "missing-creds.json",
            "spreadsheet_id": "",
            "sheet_name": "Sheet1",
        }

        output = io.StringIO()

        with redirect_stdout(output):
            result = manual_test_sheet_connection.append_test_row(settings)

        self.assertFalse(result)
        self.assertIn("GOOGLE_SPREADSHEET_ID is missing.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
