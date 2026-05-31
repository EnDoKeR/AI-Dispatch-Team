import csv
import tempfile
import unittest
from pathlib import Path

from app.document_ai.private_measurement_inputs import natural_sort_key
from app.document_ai.ratecon_review_workbook import (
    REVIEW_DOCUMENT_SUMMARY_CSV,
    REVIEW_FIELD_REVIEW_CSV,
    REVIEW_RATE_REVIEW_CSV,
    REVIEW_STOP_REVIEW_CSV,
    REVIEW_V2_CORE_FIELDS_CSV,
    REVIEW_V2_DOCUMENT_SUMMARY_CSV,
    REVIEW_V2_LOAD_IDS_CSV,
    REVIEW_V2_RATES_CSV,
    REVIEW_V2_STOPS_CSV,
    REVIEW_V2_WORKBOOK_XLSX,
    REVIEW_WORKBOOK_XLSX,
    write_ratecon_review_artifacts,
    write_ratecon_review_csvs,
    write_ratecon_review_v2_artifacts,
    write_ratecon_review_workbook,
)


def _fake_row():
    return {
        "document_alias": "RATECON_001",
        "document_type": "LOAD_CONFIRMATION",
        "classification_status": "classified",
        "extraction_relevant": True,
        "normal_load_movement": True,
        "extraction_status": "TEXT_EXTRACTED",
        "layout_provider_status": "success",
        "old_raw_stop_groups": 8,
        "old_normalized_stops": 8,
        "span_anchor_count": 2,
        "stop_span_count": 2,
        "span_normalized_stop_count": 2,
        "span_pickup_count": 1,
        "span_delivery_count": 1,
        "span_unknown_count": 0,
        "span_date_resolved_count": 1,
        "span_date_missing_count": 1,
        "span_time_resolved_count": 0,
        "span_time_missing_count": 2,
        "span_review_required_count": 1,
        "span_normalized_stop_set": {
            "document_alias": "RATECON_001",
            "stops": [
                {
                    "stop_id": "span_stop_001",
                    "sequence": 1,
                    "stop_type": "pickup",
                    "review_required": True,
                    "fields": [
                        {
                            "field_name": "location",
                            "status": "resolved",
                            "confidence": "high",
                            "selected_value": "Fake Pickup City",
                            "evidence_refs": [
                                {"evidence_type": "layout_line", "page_number": 1}
                            ],
                        }
                    ],
                }
            ],
        },
        "load_identifier_coverage_metrics": {
            "primary_identifier_candidate_count": 1,
            "primary_identifier_type_counts": {"broker_load_number": 1},
            "typed_reference_candidate_count": 1,
            "rejected_reference_as_load_id_count": 1,
            "core_load_number_mapping_count": 1,
            "private_values_included": False,
            "raw_text_included": False,
        },
        "rate_forensics_records": [
            {
                "measurement_alias": "RATECON_001",
                "main_rate_candidate_count": 2,
                "category_counts": {"main_total_carrier_pay": 1, "linehaul": 1},
                "private_values_included": False,
                "raw_text_included": False,
                "money_values_included": False,
            }
        ],
        "rate_conflict_audit_records": [
            {
                "measurement_alias": "RATECON_001",
                "main_rate_candidate_count": 2,
                "equivalent_candidate_group_count": 1,
                "different_strong_total_count": 0,
                "selected_rate_present": True,
                "core_rate_mapped": True,
                "review_required": False,
                "conflict_reason": "same_amount_multiple_sources",
                "private_values_included": False,
                "raw_text_included": False,
                "money_values_included": False,
            }
        ],
        "field_statuses": [
            {
                "field_name": "rate",
                "status": "resolved",
                "selected_value": "$1234",
                "evidence_type": "layout_table",
            },
            {"field_name": "broker_name", "status": "needs_review"},
            {"field_name": "load_number", "status": "resolved"},
            {"field_name": "pickup_location", "status": "resolved"},
            {"field_name": "pickup_date", "status": "needs_review"},
            {"field_name": "delivery_location", "status": "resolved"},
            {"field_name": "delivery_date", "status": "resolved"},
        ],
    }


def _output_dir(tmp):
    return Path(tmp) / ".local_outputs" / "private_ratecon_measurement"


class RateConReviewWorkbookExportTests(unittest.TestCase):
    def test_natural_sort_orders_load_confirmations(self):
        names = ["LoadConfirmation1.pdf", "LoadConfirmation12.pdf", "LoadConfirmation2.pdf"]
        self.assertEqual(
            sorted(names, key=natural_sort_key),
            ["LoadConfirmation1.pdf", "LoadConfirmation2.pdf", "LoadConfirmation12.pdf"],
        )

    def test_writes_review_csvs_without_private_values_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_ratecon_review_csvs(
                [_fake_row()],
                output_dir=_output_dir(tmp),
                allow_custom_output_dir=True,
            )
            paths = output["paths"]
            self.assertEqual(paths["document_summary_csv"].name, REVIEW_DOCUMENT_SUMMARY_CSV)
            self.assertEqual(paths["stop_review_csv"].name, REVIEW_STOP_REVIEW_CSV)
            self.assertEqual(paths["field_review_csv"].name, REVIEW_FIELD_REVIEW_CSV)
            self.assertEqual(paths["rate_review_csv"].name, REVIEW_RATE_REVIEW_CSV)

            with paths["stop_review_csv"].open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["Predicted Value LOCAL ONLY"], "")
            with paths["field_review_csv"].open(encoding="utf-8", newline="") as handle:
                field_rows = list(csv.DictReader(handle))
            self.assertIn("Intake Core Blocker", field_rows[0])
            self.assertIn("Policy Gap Reason", field_rows[0])
            load_row = next(row for row in field_rows if row["Field Name"] == "load_number")
            self.assertEqual(load_row["Load Identifier Candidate Count"], "1")
            self.assertEqual(
                load_row["Primary Load Identifier Candidate Type"],
                "broker_load_number=1",
            )

    def test_private_values_written_only_when_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_ratecon_review_csvs(
                [_fake_row()],
                output_dir=_output_dir(tmp),
                include_private_values=True,
                allow_custom_output_dir=True,
            )

            with output["paths"]["stop_review_csv"].open(
                encoding="utf-8",
                newline="",
            ) as handle:
                stop_rows = list(csv.DictReader(handle))
            with output["paths"]["rate_review_csv"].open(
                encoding="utf-8",
                newline="",
            ) as handle:
                rate_rows = list(csv.DictReader(handle))

            self.assertEqual(stop_rows[0]["Predicted Value LOCAL ONLY"], "Fake Pickup City")
            self.assertEqual(rate_rows[0]["Predicted Value LOCAL ONLY"], "$1234")
            self.assertEqual(
                rate_rows[0]["Rate Conflict Reason"],
                "same_amount_multiple_sources",
            )
            self.assertEqual(rate_rows[0]["Main Rate Candidate Count"], "2")
            self.assertEqual(rate_rows[0]["Equivalent Rate Group Count"], "1")
            self.assertEqual(rate_rows[0]["Rate Core Mapped? yes/no"], "yes")
            self.assertTrue(output["include_private_values_local_only"])
            self.assertFalse(output["private_values_printed"])

    def test_writes_xlsx_if_available_or_skips_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_ratecon_review_workbook(
                [_fake_row()],
                output_dir=_output_dir(tmp),
                allow_custom_output_dir=True,
            )
            if output["xlsx"]:
                self.assertEqual(output["xlsx"].name, REVIEW_WORKBOOK_XLSX)
                self.assertTrue(output["xlsx"].exists())
            else:
                self.assertIsNone(output["xlsx"])
            self.assertFalse(output["raw_text_included"])

    def test_combined_artifact_writer_returns_safe_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_ratecon_review_artifacts(
                [_fake_row()],
                output_dir=_output_dir(tmp),
                write_workbook=True,
                write_csvs=True,
                allow_custom_output_dir=True,
            )

            self.assertIn("document_summary_csv", output["paths"])
            self.assertEqual(output["summary"]["document_rows"], 1)
            self.assertEqual(output["summary"]["stop_review_rows"], 1)
            self.assertEqual(output["summary"]["rate_review_rows"], 1)
            self.assertFalse(output["private_values_printed"])

    def test_writes_v2_packet_with_priority_rows_and_no_private_values_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_ratecon_review_v2_artifacts(
                [_fake_row()],
                output_dir=_output_dir(tmp),
                allow_custom_output_dir=True,
            )

            paths = output["paths"]
            self.assertEqual(
                paths["document_summary_csv"].name,
                REVIEW_V2_DOCUMENT_SUMMARY_CSV,
            )
            self.assertEqual(paths["core_fields_csv"].name, REVIEW_V2_CORE_FIELDS_CSV)
            self.assertEqual(paths["stops_csv"].name, REVIEW_V2_STOPS_CSV)
            self.assertEqual(paths["rates_csv"].name, REVIEW_V2_RATES_CSV)
            self.assertEqual(paths["load_ids_csv"].name, REVIEW_V2_LOAD_IDS_CSV)
            if output["xlsx_written"]:
                self.assertEqual(
                    paths["review_v2_workbook_xlsx"].name,
                    REVIEW_V2_WORKBOOK_XLSX,
                )

            with paths["core_fields_csv"].open(encoding="utf-8", newline="") as handle:
                core_rows = list(csv.DictReader(handle))
            with paths["stops_csv"].open(encoding="utf-8", newline="") as handle:
                stop_rows = list(csv.DictReader(handle))

            self.assertEqual(len(core_rows), 7)
            self.assertEqual(core_rows[0]["Predicted Value LOCAL ONLY"], "")
            self.assertIn("User Issue Type", core_rows[0])
            self.assertEqual(len(stop_rows), 1)
            self.assertLess(
                output["summary"]["core_field_rows"]
                + output["summary"]["stop_rows"]
                + output["summary"]["rate_rows"]
                + output["summary"]["load_id_rows"],
                20,
            )
            self.assertFalse(output["private_values_printed"])

    def test_v2_packet_includes_private_values_only_when_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_ratecon_review_v2_artifacts(
                [_fake_row()],
                output_dir=_output_dir(tmp),
                include_private_values=True,
                allow_custom_output_dir=True,
            )

            with output["paths"]["core_fields_csv"].open(
                encoding="utf-8",
                newline="",
            ) as handle:
                core_rows = list(csv.DictReader(handle))
            rate_row = next(row for row in core_rows if row["Field Name"] == "rate")

            self.assertEqual(rate_row["Predicted Value LOCAL ONLY"], "$1234")
            self.assertTrue(output["include_private_values_local_only"])
            self.assertFalse(output["private_values_printed"])


if __name__ == "__main__":
    unittest.main()
