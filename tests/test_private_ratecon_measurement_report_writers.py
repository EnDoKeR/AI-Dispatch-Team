import csv
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.private_measurement import (
    BLOCKER_OCR_NEEDED,
    build_private_ratecon_measurement_row,
)
from app.document_ai.private_measurement_reports import (
    build_private_ratecon_measurement_aggregate,
)
from app.document_ai import private_measurement_outputs as legacy_outputs
from app.document_ai.measurement_cli import ratecon_private_report_writers
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    private_measurement_aggregate_path,
    private_measurement_report_path,
    private_measurement_rows_path,
    private_measurement_summary_path,
    value_review_template_path,
)
from app.document_ai.measurement_cli.ratecon_private_report_writers import (
    PrivateMeasurementOutputError,
    write_private_ratecon_safe_outputs,
    write_private_ratecon_safe_summary_json,
)


class PrivateRateconMeasurementReportWriterTests(unittest.TestCase):
    def _rows_and_aggregate(self):
        rows = [
            build_private_ratecon_measurement_row(
                document_alias="RATECON_001",
                triage_route="OCR_NEEDED",
                extraction_status="EMPTY_TEXT",
                candidate_counts_by_field={"rate": 0},
                missing_fields=["rate"],
                blocker_categories=[BLOCKER_OCR_NEEDED],
                warning_codes=["no_extractable_text"],
                review_required=True,
            )
        ]
        return rows, build_private_ratecon_measurement_aggregate(rows)

    def test_safe_outputs_use_centralized_output_paths_and_existing_names(self):
        rows, aggregate = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            output = write_private_ratecon_safe_outputs(
                rows,
                aggregate,
                output_dir=temp_dir,
                write_json=True,
                write_csv=True,
                write_md=True,
                write_value_review_template=True,
                allow_custom_output_dir=True,
            )

            expected = {
                "safe_summary_json": private_measurement_summary_path(temp_dir),
                "safe_aggregate_json": private_measurement_aggregate_path(temp_dir),
                "safe_summary_csv": private_measurement_rows_path(temp_dir),
                "safe_aggregate_md": private_measurement_report_path(temp_dir),
                "value_review_template_csv": value_review_template_path(temp_dir),
            }

            self.assertEqual(output["output_dir"], temp_dir)
            self.assertTrue(output["local_only"])
            self.assertTrue(output["private_values_redacted"])
            self.assertFalse(output["raw_text_saved"])
            self.assertEqual(output["paths"], {key: str(path) for key, path in expected.items()})
            for path in expected.values():
                self.assertTrue(path.exists())

    def test_json_csv_markdown_and_template_metadata_remain_sanitized(self):
        rows, aggregate = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            output = write_private_ratecon_safe_outputs(
                rows,
                aggregate,
                output_dir=temp_dir,
                write_json=True,
                write_csv=True,
                write_md=True,
                write_value_review_template=True,
                allow_custom_output_dir=True,
            )

            summary = json.loads(Path(output["paths"]["safe_summary_json"]).read_text(encoding="utf-8"))
            aggregate_payload = json.loads(
                Path(output["paths"]["safe_aggregate_json"]).read_text(encoding="utf-8")
            )
            summary_csv = Path(output["paths"]["safe_summary_csv"]).read_text(encoding="utf-8")
            aggregate_md = Path(output["paths"]["safe_aggregate_md"]).read_text(encoding="utf-8")
            with Path(output["paths"]["value_review_template_csv"]).open(
                newline="",
                encoding="utf-8",
            ) as handle:
                template_rows = list(csv.DictReader(handle))

        serialized = json.dumps(summary) + json.dumps(aggregate_payload) + summary_csv + aggregate_md
        self.assertTrue(summary["local_only"])
        self.assertTrue(summary["private_values_redacted"])
        self.assertFalse(summary["raw_text_saved"])
        self.assertTrue(aggregate_payload["local_only"])
        self.assertIn("document_alias", summary_csv)
        self.assertIn("no raw text or private values included", aggregate_md.lower())
        self.assertEqual(template_rows[0]["private_note_do_not_share"], "")
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", serialized)
        self.assertNotIn("FAKE BROKER LLC", serialized)
        self.assertNotIn('"raw_text":', serialized)

    def test_writer_rejects_unsafe_payload_fields(self):
        rows, aggregate = self._rows_and_aggregate()
        rows[0]["raw_text"] = "PRIVATE TEXT"

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(PrivateMeasurementOutputError):
                write_private_ratecon_safe_summary_json(
                    rows,
                    aggregate,
                    output_dir=temp_dir,
                    allow_custom_output_dir=True,
                )

    def test_writer_rejects_custom_output_path_without_explicit_allow(self):
        rows, aggregate = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(PrivateMeasurementOutputError):
                write_private_ratecon_safe_outputs(
                    rows,
                    aggregate,
                    output_dir=temp_dir,
                    write_json=True,
                )

    def test_legacy_import_surface_delegates_to_report_writer_owner(self):
        self.assertIs(
            legacy_outputs.write_private_measurement_outputs,
            ratecon_private_report_writers.write_private_measurement_outputs,
        )
        self.assertIs(
            legacy_outputs.write_safe_summary_json,
            ratecon_private_report_writers.write_safe_summary_json,
        )

    def test_module_does_not_process_documents_or_call_cloud_model_ocr_or_google_sync(self):
        source = inspect.getsource(ratecon_private_report_writers)
        forbidden = [
            "discover_private_pdfs",
            "measure_private_ratecon_pdf",
            "pytesseract",
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
