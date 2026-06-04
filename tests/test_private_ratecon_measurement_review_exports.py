import inspect
import tempfile
import unittest

from app.document_ai.measurement_cli import ratecon_private_review_exports
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    STOP_REVIEW_PACKET_CSV,
    STOP_REVIEW_PACKET_MD,
    review_google_sheet_csv_path,
    review_workbook_path,
    stop_review_packet_csv_path,
    stop_review_packet_md_path,
)
from app.document_ai.measurement_cli.ratecon_private_report_writers import (
    PrivateMeasurementOutputError,
)
from app.document_ai.measurement_cli.ratecon_private_review_exports import (
    private_ratecon_review_export_labels,
    private_ratecon_review_packet_export_labels,
    stop_review_rows,
    write_private_ratecon_review_packet_exports,
    write_private_ratecon_value_review_exports,
)
from app.document_ai import stop_review_packet as legacy_stop_review_packet


def _measurement_rows_with_stop_set():
    return [
        {
            "document_alias": "RATECON_001",
            "normalized_stop_set": {
                "document_alias": "RATECON_001",
                "stops": [
                    {
                        "stop_id": "stop_1",
                        "stop_type": "pickup",
                        "sequence": 1,
                        "fields": [
                            {
                                "field_name": "date",
                                "status": "resolved",
                                "confidence": "high",
                                "selected_value": "2026-01-01",
                                "evidence_refs": [
                                    {
                                        "evidence_type": "fixture",
                                        "page_number": 1,
                                    }
                                ],
                                "warning_codes": [],
                            }
                        ],
                    }
                ],
            },
        }
    ]


class PrivateRateconMeasurementReviewExportTests(unittest.TestCase):
    def test_review_packet_uses_centralized_output_paths_and_existing_names(self):
        rows = _measurement_rows_with_stop_set()

        with tempfile.TemporaryDirectory() as temp_dir:
            packet = write_private_ratecon_review_packet_exports(
                rows,
                output_dir=temp_dir,
            )

            self.assertEqual(packet["csv"], stop_review_packet_csv_path(temp_dir))
            self.assertEqual(packet["md"], stop_review_packet_md_path(temp_dir))
            self.assertEqual(packet["csv"].name, STOP_REVIEW_PACKET_CSV)
            self.assertEqual(packet["md"].name, STOP_REVIEW_PACKET_MD)
            self.assertTrue(packet["csv"].exists())
            self.assertTrue(packet["md"].exists())

    def test_review_packet_exports_are_sanitized_by_default(self):
        rows = _measurement_rows_with_stop_set()

        with tempfile.TemporaryDirectory() as temp_dir:
            packet = write_private_ratecon_review_packet_exports(
                rows,
                output_dir=temp_dir,
            )
            csv_text = packet["csv"].read_text(encoding="utf-8")
            md_text = packet["md"].read_text(encoding="utf-8")

        self.assertEqual(packet["row_count"], 1)
        self.assertFalse(packet["include_private_values_local_only"])
        self.assertFalse(packet["raw_text_included"])
        self.assertIn("No private values included.", md_text)
        self.assertNotIn("selected_value_local_only", csv_text)
        self.assertNotIn("2026-01-01", csv_text + md_text)

    def test_review_packet_labels_keep_existing_shape(self):
        rows = _measurement_rows_with_stop_set()

        with tempfile.TemporaryDirectory() as temp_dir:
            packet = write_private_ratecon_review_packet_exports(
                rows,
                output_dir=temp_dir,
            )

        self.assertEqual(
            private_ratecon_review_packet_export_labels(packet),
            {
                "csv": "stop_review_packet.csv",
                "md": "stop_review_packet.md",
                "row_count": 1,
                "include_private_values_local_only": False,
            },
        )

    def test_review_export_labels_keep_existing_csv_and_optional_xlsx_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            export = {
                "csv": review_google_sheet_csv_path(temp_dir),
                "xlsx": review_workbook_path(temp_dir),
                "row_count": 3,
            }

            labels = private_ratecon_review_export_labels(export)

        self.assertEqual(
            labels,
            {
                "csv": "ratecon_review_google_sheet.csv",
                "row_count": 3,
                "xlsx": "ratecon_review_workbook.xlsx",
            },
        )

    def test_value_review_export_uses_report_writer_validation(self):
        rows = _measurement_rows_with_stop_set()

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(PrivateMeasurementOutputError):
                write_private_ratecon_value_review_exports(rows, output_dir=temp_dir)

    def test_legacy_stop_review_packet_surface_delegates_to_review_export_owner(self):
        self.assertIs(
            legacy_stop_review_packet.write_stop_review_packet,
            ratecon_private_review_exports.write_stop_review_packet,
        )
        self.assertIs(
            legacy_stop_review_packet.stop_review_rows,
            ratecon_private_review_exports.stop_review_rows,
        )

    def test_stop_review_rows_can_include_private_values_only_when_explicit(self):
        rows = stop_review_rows(
            [row["normalized_stop_set"] for row in _measurement_rows_with_stop_set()],
            include_private_values_local_only=True,
        )

        self.assertEqual(rows[0]["selected_value_local_only"], "2026-01-01")

    def test_module_does_not_process_documents_call_services_or_generate_workbooks(self):
        source = inspect.getsource(ratecon_private_review_exports)
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
