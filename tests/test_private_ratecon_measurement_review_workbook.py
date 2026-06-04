import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.document_ai.measurement_cli import ratecon_private_review_workbook
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    build_private_ratecon_output_paths,
    review_document_summary_csv_path,
    review_workbook_path,
)
from app.document_ai.measurement_cli.ratecon_private_review_workbook import (
    PrivateRateconReviewWorkbookResult,
    build_private_ratecon_review_workbook_plan,
    private_ratecon_review_workbook_labels,
    write_private_ratecon_review_workbook_if_enabled,
)


def _config(**overrides):
    values = {
        "allow_custom_output_dir": False,
        "dry_run": False,
        "include_private_review_values_local_only": False,
        "write_review_workbook": False,
        "write_review_csvs": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _report():
    return {
        "rows": [{"document_alias": "RATECON_001"}],
        "local_document_names_by_alias": {"RATECON_001": "FixtureLoad001"},
    }


def _fake_review(output_dir):
    return {
        "paths": {
            "review_workbook_xlsx": review_workbook_path(output_dir),
            "document_summary_csv": review_document_summary_csv_path(output_dir),
        },
        "rows_by_sheet": {"Document_Summary": [{"Measurement Alias": "RATECON_001"}]},
        "summary": {
            "document_rows": 1,
            "stop_review_rows": 2,
            "field_review_rows": 3,
            "rate_review_rows": 4,
            "readiness_level_counts": {"review_required": 1},
            "integrity_issue_counts": {"missing_stop": 1},
        },
        "xlsx_written": True,
        "csvs_written": True,
        "include_private_values_local_only": True,
        "local_only": True,
        "raw_text_included": False,
        "private_values_printed": False,
    }


class PrivateRateconMeasurementReviewWorkbookTests(unittest.TestCase):
    def test_workbook_plan_enables_existing_workbook_flags(self):
        self.assertEqual(
            build_private_ratecon_review_workbook_plan(
                _config(write_review_workbook=True)
            ),
            ["review_workbook"],
        )
        self.assertEqual(
            build_private_ratecon_review_workbook_plan(_config(write_review_csvs=True)),
            ["review_workbook"],
        )

    def test_workbook_plan_disables_when_flags_absent_or_dry_run(self):
        self.assertEqual(build_private_ratecon_review_workbook_plan(_config()), [])
        self.assertEqual(
            build_private_ratecon_review_workbook_plan(
                _config(write_review_workbook=True, dry_run=True)
            ),
            [],
        )

    def test_workbook_wrapper_uses_centralized_paths_and_existing_flags(self):
        calls = {}
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_review_workbook"
        )

        def writer(
            rows,
            output_dir=None,
            local_document_names_by_alias=None,
            include_private_values=False,
            write_workbook=True,
            write_csvs=True,
            allow_custom_output_dir=False,
        ):
            calls.update(
                {
                    "rows": rows,
                    "output_dir": output_dir,
                    "local_document_names_by_alias": local_document_names_by_alias,
                    "include_private_values": include_private_values,
                    "write_workbook": write_workbook,
                    "write_csvs": write_csvs,
                    "allow_custom_output_dir": allow_custom_output_dir,
                }
            )
            return _fake_review(output_dir)

        result = write_private_ratecon_review_workbook_if_enabled(
            _report(),
            _config(
                write_review_workbook=True,
                write_review_csvs=True,
                include_private_review_values_local_only=True,
            ),
            output_paths,
            writer=writer,
        )

        self.assertIsInstance(result, PrivateRateconReviewWorkbookResult)
        self.assertEqual(result.message_label, "review_workbook_export_written")
        self.assertEqual(calls["rows"], _report()["rows"])
        self.assertEqual(calls["output_dir"], output_paths.output_dir)
        self.assertEqual(
            calls["local_document_names_by_alias"],
            {"RATECON_001": "FixtureLoad001"},
        )
        self.assertTrue(calls["include_private_values"])
        self.assertTrue(calls["write_workbook"])
        self.assertTrue(calls["write_csvs"])
        self.assertFalse(calls["allow_custom_output_dir"])
        self.assertEqual(
            result.review_rows_by_sheet,
            {"Document_Summary": [{"Measurement Alias": "RATECON_001"}]},
        )

    def test_workbook_labels_preserve_existing_console_shape_and_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            labels = private_ratecon_review_workbook_labels(_fake_review(temp_dir))

        self.assertEqual(
            labels,
            {
                "files": {
                    "review_workbook_xlsx": "ratecon_review_workbook.xlsx",
                    "document_summary_csv": "ratecon_review_document_summary.csv",
                },
                "document_rows": 1,
                "stop_review_rows": 2,
                "field_review_rows": 3,
                "rate_review_rows": 4,
                "readiness_level_counts": {"review_required": 1},
                "integrity_issue_counts": {"missing_stop": 1},
                "include_private_values_local_only": True,
                "xlsx_written": True,
                "csvs_written": True,
            },
        )

    def test_workbook_wrapper_returns_none_when_disabled(self):
        output_paths = build_private_ratecon_output_paths(
            output_dir=".local_outputs/test_review_workbook"
        )

        result = write_private_ratecon_review_workbook_if_enabled(
            _report(),
            _config(),
            output_paths,
            writer=lambda *args, **kwargs: self.fail("writer should not run"),
        )

        self.assertIsNone(result)

    def test_workbook_wrapper_preserves_writer_path_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_paths = build_private_ratecon_output_paths(output_dir=temp_dir)

            with self.assertRaises(ValueError):
                write_private_ratecon_review_workbook_if_enabled(
                    _report(),
                    _config(write_review_workbook=True),
                    output_paths,
                )

    def test_workbook_wrapper_does_not_process_documents_call_services_or_sync_google(self):
        source = inspect.getsource(ratecon_private_review_workbook)
        forbidden = [
            "discover_private_pdfs",
            "measure_private_ratecon_pdf",
            "pytesseract",
            "easyocr",
            "openai",
            "anthropic",
            "gemini",
            "google_sheets_review",
            "googleapiclient",
            "google.oauth",
            "requests.",
            "urllib.",
        ]

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
