import csv
import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.private_measurement import (
    BLOCKER_OCR_NEEDED,
    build_private_ratecon_measurement_row,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    PrivateMeasurementOutputError,
    write_private_measurement_outputs,
    write_safe_aggregate_md,
    write_safe_summary_csv,
    write_safe_summary_json,
    write_value_review_template_csv,
)
from app.document_ai.private_measurement_reports import (
    build_private_ratecon_measurement_aggregate,
)


class PrivateMeasurementOutputTests(unittest.TestCase):
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

    def test_default_output_path_is_local_outputs(self):
        self.assertEqual(
            DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR.as_posix(),
            ".local_outputs/private_ratecon_measurement",
        )

    def test_json_writer_excludes_raw_text_and_private_values(self):
        rows, aggregate = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_safe_summary_json(
                rows,
                aggregate,
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        serialized = json.dumps(payload)
        self.assertTrue(payload["local_only"])
        self.assertNotIn("TRUCKLOAD RATE CONFIRMATION", serialized)
        self.assertNotIn("FAKE BROKER LLC", serialized)
        self.assertNotIn("raw_text\":", serialized)

    def test_csv_writer_excludes_raw_text_and_values(self):
        rows, _ = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_safe_summary_csv(
                rows,
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            text = path.read_text(encoding="utf-8")

        self.assertIn("document_alias", text)
        self.assertIn("extraction_relevant", text)
        self.assertIn("normal_load_movement", text)
        self.assertIn("skipped_by_scope", text)
        self.assertNotIn("raw_text", text)
        self.assertNotIn("FAKE BROKER LLC", text)

    def test_custom_path_guard_requires_explicit_allow(self):
        rows, aggregate = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(PrivateMeasurementOutputError):
                write_safe_summary_json(rows, aggregate, output_dir=temp_dir)

    def test_markdown_aggregate_contains_safe_statuses_only(self):
        rows, aggregate = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_safe_aggregate_md(
                aggregate,
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            text = path.read_text(encoding="utf-8")

        self.assertIn("blocker_category_counts", text)
        self.assertIn("normal_load_critical_field_denominator", text)
        self.assertIn("classification_status_counts", text)
        self.assertNotIn("FAKE BROKER LLC", text)
        self.assertIn("no raw text or private values included", text.lower())

    def test_value_review_template_has_blank_private_note_column(self):
        rows, _ = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_value_review_template_csv(
                rows,
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            with path.open(newline="", encoding="utf-8") as handle:
                records = list(csv.DictReader(handle))

        self.assertEqual(records[0]["document_alias"], "RATECON_001")
        self.assertEqual(records[0]["private_note_do_not_share"], "")

    def test_combined_writer_returns_paths(self):
        rows, aggregate = self._rows_and_aggregate()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = write_private_measurement_outputs(
                rows,
                aggregate,
                output_dir=temp_dir,
                write_json=True,
                write_csv=True,
                write_md=True,
                write_value_review_template=True,
                allow_custom_output_dir=True,
            )

        self.assertTrue(result["local_only"])
        self.assertIn("safe_summary_json", result["paths"])


if __name__ == "__main__":
    unittest.main()
