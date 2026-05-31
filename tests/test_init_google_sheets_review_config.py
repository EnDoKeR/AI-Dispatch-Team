import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from app.integrations.google_sheets_review import (
    EXPECTED_SERVICE_ACCOUNT_EMAIL,
    GoogleSheetsReviewConfigError,
    build_google_sheets_review_config,
    validate_google_sheets_review_config,
)
from scripts import init_google_sheets_review_config as init_script


class InitGoogleSheetsReviewConfigTests(unittest.TestCase):
    def test_writes_fake_temp_config_without_printing_paths_or_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            creds = root / "fake-service-account.json"
            config = root / "google_sheets_review_config.json"
            creds.write_text("{}", encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = init_script.main(
                    [
                        "--spreadsheet-id",
                        "fake-spreadsheet-id",
                        "--credentials-json",
                        str(creds),
                        "--config-output",
                        str(config),
                    ]
                )
            payload = json.loads(config.read_text(encoding="utf-8"))
            output = stdout.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["spreadsheet_id"], "fake-spreadsheet-id")
        self.assertEqual(payload["service_account_email"], EXPECTED_SERVICE_ACCOUNT_EMAIL)
        self.assertIn("config_written: yes", output)
        self.assertIn("credentials_file_exists: yes", output)
        self.assertNotIn("fake-spreadsheet-id", output)
        self.assertNotIn(str(creds), output)
        self.assertNotIn("BEGIN PRIVATE KEY", output)

    def test_refuses_missing_credentials_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = init_script.main(
                    [
                        "--spreadsheet-id",
                        "fake-spreadsheet-id",
                        "--credentials-json",
                        str(Path(tmp) / "missing.json"),
                        "--config-output",
                        str(Path(tmp) / "config.json"),
                    ]
                )

        self.assertEqual(exit_code, 2)
        self.assertIn("credentials file not found", stderr.getvalue())

    def test_refuses_overwrite_without_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            creds = root / "fake-service-account.json"
            config = root / "google_sheets_review_config.json"
            creds.write_text("{}", encoding="utf-8")
            config.write_text("{}", encoding="utf-8")

            with self.assertRaises(GoogleSheetsReviewConfigError):
                init_script.write_google_sheets_review_config(
                    spreadsheet_id="fake-spreadsheet-id",
                    credentials_json=str(creds),
                    config_output=config,
                )

    def test_overwrite_allows_private_value_sync_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            creds = root / "fake-service-account.json"
            config = root / "google_sheets_review_config.json"
            creds.write_text("{}", encoding="utf-8")
            config.write_text("{}", encoding="utf-8")

            result = init_script.write_google_sheets_review_config(
                spreadsheet_id="fake-spreadsheet-id",
                credentials_json=str(creds),
                allow_private_review_value_sync=True,
                config_output=config,
                overwrite=True,
            )
            payload = json.loads(config.read_text(encoding="utf-8"))

        self.assertTrue(result["private_value_sync_allowed"])
        self.assertTrue(payload["allow_private_review_value_sync"])

    def test_config_validation_reports_fake_fields_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            creds = Path(tmp) / "fake-service-account.json"
            creds.write_text("{}", encoding="utf-8")
            config = build_google_sheets_review_config(
                {
                    "spreadsheet_id": "fake-spreadsheet-id",
                    "credentials_json_path": str(creds),
                    "service_account_email": EXPECTED_SERVICE_ACCOUNT_EMAIL,
                    "allow_private_review_value_sync": True,
                }
            )
            validation = validate_google_sheets_review_config(config)

        self.assertTrue(validation["sync_ready"])
        self.assertTrue(validation["private_value_sync_allowed"])
        self.assertFalse(validation["credentials_path_printed"])
        self.assertFalse(validation["spreadsheet_id_printed"])

    def test_local_private_path_is_ignored(self):
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        self.assertIn(".local_private/", gitignore)


if __name__ == "__main__":
    unittest.main()
