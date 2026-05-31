import csv
import tempfile
import unittest
from pathlib import Path

from app.document_ai.private_measurement_inputs import build_safe_aliases, natural_sort_key
from app.document_ai.private_measurement_review_export import (
    REVIEW_EXPORT_COLUMNS,
    REVIEW_GOOGLE_SHEET_CSV,
    build_review_export_rows,
    write_ratecon_review_export,
)


def _fake_row(alias="RATECON_001"):
    return {
        "document_alias": alias,
        "document_type": "LOAD_CONFIRMATION",
        "classification_status": "classified",
        "extraction_relevant": True,
        "normal_load_movement": True,
        "extraction_status": "TEXT_EXTRACTED",
        "layout_provider_status": "success",
        "raw_stop_group_count": 8,
        "premerge_stop_group_count": 8,
        "post_single_line_cluster_stop_group_count": 1,
        "post_row_merge_stop_group_count": 1,
        "post_section_merge_stop_group_count": 1,
        "post_noise_filter_stop_group_count": 1,
        "post_dedupe_stop_group_count": 1,
        "normalized_stop_count": 1,
        "stop_duplicate_removed_count": 0,
        "stop_noise_removed_count": 0,
        "pickup_count": 1,
        "delivery_count": 0,
        "unknown_stop_count": 0,
        "stop_field_status_counts": {
            "date": {"resolved": 1},
            "time": {"missing": 1},
        },
        "field_statuses": [
            {"field_name": "rate", "status": "resolved"},
            {"field_name": "broker_name", "status": "missing"},
            {"field_name": "broker_mc", "status": "missing"},
            {"field_name": "equipment", "status": "resolved"},
            {"field_name": "weight", "status": "missing"},
        ],
        "blocker_categories": ["LAYOUT_EXTRACTION_GAP"],
        "stop_pipeline_trace": {
            "passthrough_detected": False,
            "first_stage_that_changed": "post_single_line_cluster",
        },
    }


class PrivateMeasurementReviewExportTests(unittest.TestCase):
    def test_natural_sort_orders_local_document_names(self):
        names = ["LoadConfirmation1.pdf", "LoadConfirmation10.pdf", "LoadConfirmation2.pdf"]
        sorted_names = sorted(names, key=natural_sort_key)

        self.assertEqual(
            sorted_names,
            ["LoadConfirmation1.pdf", "LoadConfirmation2.pdf", "LoadConfirmation10.pdf"],
        )

    def test_build_safe_aliases_supports_natural_sort(self):
        paths = [
            Path("LoadConfirmation10.pdf"),
            Path("LoadConfirmation1.pdf"),
            Path("LoadConfirmation2.pdf"),
        ]

        aliases = build_safe_aliases(paths, natural_sort=True)

        self.assertEqual(aliases[Path("LoadConfirmation1.pdf")], "RATECON_001")
        self.assertEqual(aliases[Path("LoadConfirmation2.pdf")], "RATECON_002")
        self.assertEqual(aliases[Path("LoadConfirmation10.pdf")], "RATECON_003")

    def test_export_rows_include_expected_columns(self):
        rows = build_review_export_rows(
            [_fake_row()],
            local_document_names_by_alias={"RATECON_001": "LoadConfirmation1"},
        )

        self.assertEqual(set(rows[0]), set(REVIEW_EXPORT_COLUMNS))
        self.assertEqual(rows[0]["Local Document Name / File Stem"], "LoadConfirmation1")
        self.assertEqual(rows[0]["Post Single-Line Cluster"], 1)
        self.assertEqual(rows[0]["Root Cause Bucket"], "post_single_line_cluster")

    def test_csv_export_written_under_local_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_ratecon_review_export(
                [_fake_row()],
                output_dir=Path(tmp) / ".local_outputs" / "private_ratecon_measurement",
                allow_custom_output_dir=True,
            )
            csv_path = Path(output["csv"])

            self.assertEqual(csv_path.name, REVIEW_GOOGLE_SHEET_CSV)
            self.assertTrue(csv_path.exists())
            with csv_path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)

            self.assertEqual(rows[0]["Measurement Alias"], "RATECON_001")
            self.assertNotIn("raw_text", csv_path.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
