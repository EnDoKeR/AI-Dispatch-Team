import importlib
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


LOAD_INTAKE_MODULES = [
    "app.load_intake.broker_engine",
    "app.load_intake.decision_engine",
    "app.load_intake.importer",
    "app.load_intake.market_models",
    "app.load_intake.mileage",
    "app.load_intake.parser",
    "app.load_intake.reload_engine",
    "app.load_intake.sheet_writer",
    "app.load_intake.zone_engine",
]


class TestLoadIntakeImports(unittest.TestCase):
    def test_load_intake_modules_import_without_external_side_effects(self):
        for module_name in LOAD_INTAKE_MODULES:
            with self.subTest(module_name=module_name):
                importlib.import_module(module_name)

    def test_sheet_writer_uses_environment_settings(self):
        sheet_writer = importlib.import_module("app.load_intake.sheet_writer")

        with patch.dict(
            "os.environ",
            {
                "GOOGLE_CREDENTIALS_FILE": "custom-creds.json",
                "GOOGLE_SPREADSHEET_ID": "sheet-123",
                "GOOGLE_SHEET_NAME": "Loads",
            },
        ):
            settings = sheet_writer.load_settings()

        self.assertEqual(settings["credentials_file"], "custom-creds.json")
        self.assertEqual(settings["spreadsheet_id"], "sheet-123")
        self.assertEqual(settings["sheet_name"], "Loads")

    def test_sheet_writer_stops_before_external_imports_without_sheet_id(self):
        sheet_writer = importlib.import_module("app.load_intake.sheet_writer")
        output = io.StringIO()

        with redirect_stdout(output):
            result = sheet_writer.append_load(load=object(), settings={
                "credentials_file": "missing-creds.json",
                "spreadsheet_id": "",
                "sheet_name": "Sheet1",
            })

        self.assertFalse(result)
        self.assertIn("GOOGLE_SPREADSHEET_ID is missing.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
