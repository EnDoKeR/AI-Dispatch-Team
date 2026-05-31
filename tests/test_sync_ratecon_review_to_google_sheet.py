import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from app.document_ai.ratecon_review_workbook import (
    DOCUMENT_SUMMARY_COLUMNS,
    FIELD_REVIEW_COLUMNS,
    RATE_REVIEW_COLUMNS,
    REVIEW_DOCUMENT_SUMMARY_CSV,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_RATE_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    STOP_REVIEW_COLUMNS,
)
from scripts import sync_ratecon_review_to_google_sheet as sync_script


def _write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_fake_review_csvs(root):
    _write_csv(
        root / REVIEW_DOCUMENT_SUMMARY_CSV,
        DOCUMENT_SUMMARY_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Readiness Level": "extraction_review_ready",
            }
        ],
    )
    _write_csv(
        root / REVIEW_STOP_REVIEW_CSV,
        STOP_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Stop ID": "span_stop_001",
                "Field Name": "location",
                "Predicted Value LOCAL ONLY": "Fake Private Stop Value",
                "Status": "resolved",
            }
        ],
    )
    _write_csv(
        root / REVIEW_FIELD_REVIEW_CSV,
        FIELD_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Field Name": "rate",
                "Predicted Value LOCAL ONLY": "Fake Private Rate Value",
                "Status": "resolved",
            }
        ],
    )
    _write_csv(
        root / REVIEW_RATE_REVIEW_CSV,
        RATE_REVIEW_COLUMNS,
        [
            {
                "Measurement Alias": "RATECON_001",
                "Rate Field Type": "rate",
                "Predicted Value LOCAL ONLY": "Fake Private Rate Value",
                "Status": "resolved",
            }
        ],
    )


def _write_fake_config(root):
    path = root / "google_sheets_review_config.json"
    path.write_text(
        json.dumps(
            {
                "spreadsheet_id": "fake-spreadsheet",
                "credentials_json_path": "fake-credentials.json",
                "worksheet_prefix": "RC_",
            }
        ),
        encoding="utf-8",
    )
    return path


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


class SyncRateConReviewToGoogleSheetTests(unittest.TestCase):
    def test_refuses_without_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_review_csvs(Path(tmp))
            with self.assertRaises(Exception) as ctx:
                sync_script.run_sync(
                    sync_script._build_parser().parse_args(
                        ["--input-dir", tmp, "--dry-run"]
                    )
                )

        self.assertIn("confirm-google-review-sync", str(ctx.exception))

    def test_dry_run_outputs_safe_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_review_csvs(Path(tmp))
            result = sync_script.run_sync(
                sync_script._build_parser().parse_args(
                    [
                        "--input-dir",
                        tmp,
                        "--confirm-google-review-sync",
                        "--dry-run",
                    ]
                )
            )

        self.assertEqual(result["sync_mode"], "status_only")
        self.assertIn("RC_Stop_Review", result["row_counts"])
        self.assertFalse(result["private_values_printed"])

    def test_dry_run_lists_only_allowed_review_tabs(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_review_csvs(Path(tmp))
            result = sync_script.run_sync(
                sync_script._build_parser().parse_args(
                    [
                        "--input-dir",
                        tmp,
                        "--confirm-google-review-sync",
                        "--dry-run",
                    ]
                )
            )

        self.assertEqual(
            set(result["tabs_updated"]),
            {
                "RC_Document_Summary",
                "RC_Stop_Review",
                "RC_Field_Review",
                "RC_Rate_Review",
                "RC_Instructions",
                "RC_Feedback_Summary",
            },
        )

    def test_refuses_unexpected_worksheet_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_review_csvs(Path(tmp))
            with self.assertRaises(Exception) as ctx:
                sync_script.run_sync(
                    sync_script._build_parser().parse_args(
                        [
                            "--input-dir",
                            tmp,
                            "--confirm-google-review-sync",
                            "--dry-run",
                            "--worksheet-prefix",
                            "OPS_",
                        ]
                    )
                )

        self.assertIn("dedicated RC_* review tabs", str(ctx.exception))

    def test_status_only_redacts_private_values_from_upload_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_review_csvs(root)
            result = sync_script.run_sync(
                sync_script._build_parser().parse_args(
                    [
                        "--input-dir",
                        tmp,
                        "--confirm-google-review-sync",
                        "--dry-run",
                    ]
                )
            )

            rows_by_tab = sync_script.sheets.build_google_review_tab_rows_from_review_csvs(
                root
            )
        payload = "\n".join(str(cell) for rows in rows_by_tab.values() for row in rows for cell in row)
        self.assertNotIn("Fake Private Stop Value", payload)
        self.assertNotIn("Fake Private Rate Value", payload)
        self.assertEqual(result["row_counts"]["RC_Field_Review"], 3)

    def test_private_value_mode_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_review_csvs(root)
            rows_by_tab = sync_script.sheets.build_google_review_tab_rows_from_review_csvs(
                root,
                sync_mode="private_values_test_only",
                include_private_values=False,
            )

        payload = "\n".join(str(cell) for rows in rows_by_tab.values() for row in rows for cell in row)
        self.assertNotIn("Fake Private Stop Value", payload)

    def test_mock_client_receives_expected_tabs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fake_review_csvs(root)
            config_path = _write_fake_config(root)
            fake_client = FakeClient()
            with patch.object(
                sync_script.sheets,
                "connect_to_google_sheet",
                return_value=fake_client,
            ):
                result = sync_script.run_sync(
                    sync_script._build_parser().parse_args(
                        [
                            "--input-dir",
                            tmp,
                            "--google-config",
                            str(config_path),
                            "--confirm-google-review-sync",
                        ]
                    )
                )

        self.assertIn("RC_Document_Summary", result["tabs_updated"])
        self.assertEqual(set(fake_client.rows_by_tab), set(result["tabs_updated"]))

    def test_main_does_not_print_values_or_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_review_csvs(Path(tmp))
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = sync_script.main(
                    [
                        "--input-dir",
                        tmp,
                        "--confirm-google-review-sync",
                        "--dry-run",
                    ]
                )

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn("Fake Private", output)
        self.assertNotIn("credentials", output.lower().replace("credentials_printed", ""))


if __name__ == "__main__":
    unittest.main()
