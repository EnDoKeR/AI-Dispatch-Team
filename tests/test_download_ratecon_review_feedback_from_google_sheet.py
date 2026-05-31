import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import download_ratecon_review_feedback_from_google_sheet as download_script


class FakeClient:
    def __init__(self):
        self.rows_by_title = {
            "RC_Stop_Review": [
                ["LOCAL/TEST REVIEW DATA - DO NOT USE AS FINAL TRUTH", ""],
                [
                    "Measurement Alias",
                    "Field Name",
                    "User Correct? yes/no/unknown",
                    "User Expected Value LOCAL ONLY",
                    "User Issue Type",
                ],
                ["RATECON_001", "location", "no", "Fake Expected Stop", "wrong_value"],
            ],
            "RC_Field_Review": [
                ["LOCAL/TEST REVIEW DATA - DO NOT USE AS FINAL TRUTH", ""],
                [
                    "Measurement Alias",
                    "Field Name",
                    "User Correct? yes/no/unknown",
                    "User Expected Value LOCAL ONLY",
                    "User Issue Type",
                ],
                ["RATECON_001", "rate", "yes", "Fake Expected Rate", ""],
            ],
            "RC_Rate_Review": [
                ["LOCAL/TEST REVIEW DATA - DO NOT USE AS FINAL TRUTH", ""],
                [
                    "Measurement Alias",
                    "Rate Field Type",
                    "User Correct? yes/no/unknown",
                    "User Issue Type",
                ],
                ["RATECON_002", "rate", "unknown", ""],
            ],
        }

    def download_worksheet_rows(self, title):
        return {"title": title, "rows": self.rows_by_title[title], "row_count": 3}


def _fake_config():
    return type(
        "Config",
        (),
        {
            "spreadsheet_id": "fake-spreadsheet",
            "credentials_json_path": "fake-credentials.json",
            "worksheet_prefix": "RC_",
            "service_account_email": "ai-dispatch-sheet@ai-dispatch-team.iam.gserviceaccount.com",
            "default_sync_mode": "status_only",
        },
    )()


class DownloadRateConReviewFeedbackTests(unittest.TestCase):
    def test_refuses_without_confirm_flag(self):
        with self.assertRaises(Exception) as ctx:
            download_script.run_download(download_script._build_parser().parse_args([]))

        self.assertIn("confirm-google-feedback-download", str(ctx.exception))

    def test_mock_download_writes_feedback_csvs_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_client = FakeClient()
            with patch.object(
                download_script.sheets,
                "load_google_sheets_review_config",
                return_value=_fake_config(),
            ), patch.object(
                download_script.sheets,
                "connect_to_google_sheet",
                return_value=fake_client,
            ):
                result = download_script.run_download(
                    download_script._build_parser().parse_args(
                        [
                            "--output-dir",
                            tmp,
                            "--confirm-google-feedback-download",
                        ]
                    )
                )

            self.assertTrue(
                (Path(tmp) / download_script.GOOGLE_FEEDBACK_STOP_REVIEW_CSV).exists()
            )
            stop_text = (
                Path(tmp) / download_script.GOOGLE_FEEDBACK_STOP_REVIEW_CSV
            ).read_text(encoding="utf-8")

        self.assertIn("Fake Expected Stop", stop_text)
        self.assertEqual(result["feedback_summary"]["reviewed_field_count"], 3)
        self.assertEqual(result["feedback_summary"]["incorrect_count"], 1)
        self.assertEqual(
            result["feedback_summary"]["issue_type_counts"],
            {"wrong_value": 1},
        )
        self.assertIn("RC_Stop_Review", result["tabs_downloaded"])

    def test_main_prints_safe_summary_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                download_script.sheets,
                "load_google_sheets_review_config",
                return_value=_fake_config(),
            ), patch.object(
                download_script.sheets,
                "connect_to_google_sheet",
                return_value=FakeClient(),
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = download_script.main(
                    [
                        "--output-dir",
                        tmp,
                        "--confirm-google-feedback-download",
                    ]
                )

        output = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("incorrect_count: 1", output)
        self.assertNotIn("Fake Expected Stop", output)
        self.assertNotIn("Fake Expected Rate", output)
        self.assertNotIn("fake-credentials", output)
        self.assertNotIn("fake-spreadsheet", output)


if __name__ == "__main__":
    unittest.main()
