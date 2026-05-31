import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.integrations.google_sheets_review import (
    DEFAULT_WORKSHEET_PREFIX,
    EXPECTED_SERVICE_ACCOUNT_EMAIL,
    GoogleSheetsReviewConfigError,
    load_google_sheets_review_config,
)


class GoogleSheetsReviewConfigTests(unittest.TestCase):
    def test_loads_config_from_fake_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "google_sheets_review_config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "spreadsheet_id": "fake-sheet-id",
                        "credentials_json_path": str(Path(tmp) / "fake-creds.json"),
                        "worksheet_prefix": "RC_TEST_",
                        "default_sync_mode": "status_only",
                    }
                ),
                encoding="utf-8",
            )

            config = load_google_sheets_review_config(config_path)

        self.assertEqual(config.spreadsheet_id, "fake-sheet-id")
        self.assertEqual(config.worksheet_prefix, "RC_TEST_")
        self.assertEqual(config.service_account_email, EXPECTED_SERVICE_ACCOUNT_EMAIL)
        self.assertFalse(config.safe_summary()["spreadsheet_id_printed"])
        self.assertFalse(config.safe_summary()["credentials_path_printed"])

    def test_env_vars_override_missing_file_config(self):
        with patch.dict(
            os.environ,
            {
                "AI_DISPATCH_GOOGLE_SPREADSHEET_ID": "env-sheet",
                "AI_DISPATCH_GOOGLE_CREDENTIALS_JSON": "env-creds.json",
            },
            clear=False,
        ):
            config = load_google_sheets_review_config()

        self.assertEqual(config.spreadsheet_id, "env-sheet")
        self.assertEqual(config.credentials_json_path, "env-creds.json")
        self.assertEqual(config.worksheet_prefix, DEFAULT_WORKSHEET_PREFIX)

    def test_missing_config_gives_friendly_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GoogleSheetsReviewConfigError) as raised:
                load_google_sheets_review_config()

        self.assertIn("spreadsheet_id is missing", str(raised.exception))

    def test_explicit_missing_config_path_gives_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"
            with self.assertRaises(GoogleSheetsReviewConfigError) as raised:
                load_google_sheets_review_config(missing)

        self.assertIn("config file not found", str(raised.exception))

    def test_sample_config_contains_fake_placeholders_only(self):
        path = Path("docs/examples/google_sheets_review_config.example.json")
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("FAKE", payload["spreadsheet_id"])
        self.assertIn("fake", payload["credentials_json_path"])
        self.assertEqual(
            payload["service_account_email"],
            EXPECTED_SERVICE_ACCOUNT_EMAIL,
        )
        self.assertNotIn("private_key", json.dumps(payload).lower())

    def test_local_private_config_path_is_ignored(self):
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        self.assertIn(".local_private/", gitignore)
        self.assertIn("data/credentials/", gitignore)


if __name__ == "__main__":
    unittest.main()
