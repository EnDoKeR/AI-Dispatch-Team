import csv
import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.dispatcher_review_table import (
    DISPATCHER_REVIEW_COLUMNS,
    DISPATCHER_REVIEW_V3_AUDIT_CSV,
    DISPATCHER_REVIEW_V3_REVIEW_CSV,
    DISPATCHER_REVIEW_V3_WORKBOOK_XLSX,
    aggregate_dispatcher_feedback,
    build_dispatcher_review_table_from_rows,
    build_dispatcher_audit_row,
    build_dispatcher_feedback_row,
    build_dispatcher_review_row,
    infer_dispatcher_issue_type,
    write_dispatcher_review_v3_artifacts,
)


class DispatcherReviewTableTests(unittest.TestCase):
    def test_creates_dispatcher_review_row(self):
        row = build_dispatcher_review_row(
            folder_order=1,
            measurement_alias="RATECON_001",
            broker="Fake Broker",
            pickup="Fake Pickup",
            final_rate="Fake Rate",
            top_blockers="rate;load_number",
        )

        self.assertEqual(row["Measurement Alias"], "RATECON_001")
        self.assertEqual(row["Broker"], "Fake Broker")
        self.assertEqual(row["Pickup"], "Fake Pickup")
        self.assertEqual(row["Top Blockers"], "rate;load_number")
        self.assertIn("User Corrected Broker", row)

    def test_creates_audit_row(self):
        row = build_dispatcher_audit_row(
            measurement_alias="RATECON_002",
            field_name="Load No",
            predicted_status="missing",
            candidate_count=0,
            gap_reason="no_candidate",
            source_sheet="Core_Field_Review",
        )

        self.assertEqual(row["Field Name"], "load_no")
        self.assertEqual(row["Predicted Status"], "missing")
        self.assertEqual(row["Gap Reason"], "no_candidate")

    def test_infers_changed_value_issue_type(self):
        self.assertEqual(
            infer_dispatcher_issue_type("final_rate", "Fake Old", "Fake New"),
            "wrong_rate",
        )
        self.assertEqual(
            infer_dispatcher_issue_type("load_number", "", "Fake Load"),
            "load_id_missing",
        )
        self.assertEqual(
            infer_dispatcher_issue_type("broker", "", "Fake Broker"),
            "broker_missing",
        )

    def test_feedback_aggregate_counts_without_values(self):
        rows = [
            build_dispatcher_feedback_row(
                measurement_alias="RATECON_001",
                field_name="final_rate",
                original_predicted_value="Fake Old Rate",
                user_corrected_value="Fake New Rate",
            ),
            build_dispatcher_feedback_row(
                measurement_alias="RATECON_002",
                field_name="pickup",
                original_predicted_value="Fake Pickup",
                user_corrected_value="Fake Pickup",
            ),
        ]

        aggregate = aggregate_dispatcher_feedback(rows)

        self.assertEqual(aggregate["rows_loaded"], 2)
        self.assertEqual(aggregate["documents_reviewed"], 2)
        self.assertEqual(aggregate["changed_field_count"], 1)
        self.assertEqual(aggregate["issue_type_counts"], {"wrong_rate": 1})
        self.assertEqual(
            aggregate["recommended_next_repair_target"],
            "rate_resolution",
        )
        encoded = json.dumps(aggregate)
        self.assertNotIn("Fake Old Rate", encoded)
        self.assertNotIn("Fake New Rate", encoded)
        self.assertFalse(aggregate["private_values_included"])

    def test_builds_one_row_per_document_from_review_rows(self):
        result = build_dispatcher_review_table_from_rows(
            [
                {
                    "Folder Order": "1",
                    "Measurement Alias": "RATECON_001",
                    "Document Type": "LOAD_CONFIRMATION",
                    "OCR Needed": "no",
                    "Extraction Relevant": "yes",
                    "Readiness Level": "not_ready",
                    "Review Priority": "high",
                    "Top Blockers": "rate;load_number",
                }
            ],
            core_field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": "broker_name",
                    "Predicted Value LOCAL ONLY": "Fake Broker",
                    "Predicted Status": "resolved",
                },
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": "load_number",
                    "Predicted Value LOCAL ONLY": "Fake Load",
                    "Predicted Status": "missing",
                    "Gap Reason": "no_candidate",
                },
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": "rate",
                    "Predicted Value LOCAL ONLY": "Fake Rate",
                    "Predicted Status": "conflict",
                    "Gap Reason": "conflict",
                },
            ],
            stop_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Stop Type": "pickup",
                    "Field Name": "location",
                    "Predicted Value LOCAL ONLY": "Fake Pickup",
                    "Status": "resolved",
                }
            ],
            detailed_field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": "commodity",
                    "Predicted Value LOCAL ONLY": "Fake Commodity",
                    "Status": "resolved",
                }
            ],
            include_private_values=True,
        )

        row = result["dispatcher_rows"][0]
        self.assertEqual(row["Broker"], "Fake Broker")
        self.assertEqual(row["Pickup"], "Fake Pickup")
        self.assertEqual(row["Commodity"], "Fake Commodity")
        self.assertEqual(row["Load No"], "")
        self.assertEqual(row["Final Rate"], "")
        self.assertEqual(result["summary"]["document_rows"], 1)
        self.assertEqual(result["summary"]["audit_rows"], 12)

    def test_status_only_mode_excludes_values(self):
        result = build_dispatcher_review_table_from_rows(
            [{"Measurement Alias": "RATECON_002", "Extraction Relevant": "yes"}],
            core_field_rows=[
                {
                    "Measurement Alias": "RATECON_002",
                    "Field Name": "broker_name",
                    "Predicted Value LOCAL ONLY": "Fake Broker",
                    "Predicted Status": "resolved",
                }
            ],
            include_private_values=False,
        )

        self.assertEqual(result["dispatcher_rows"][0]["Broker"], "")
        self.assertEqual(result["audit_rows"][0]["Predicted Value LOCAL ONLY"], "")

    def test_exports_v3_csvs_and_workbook_if_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            dispatcher_rows = [
                build_dispatcher_review_row(
                    measurement_alias="RATECON_003",
                    broker="Fake Broker",
                    pickup="Fake Pickup",
                )
            ]
            audit_rows = [
                build_dispatcher_audit_row(
                    measurement_alias="RATECON_003",
                    field_name="broker",
                    predicted_value_local_only="Fake Broker",
                    predicted_status="resolved",
                )
            ]
            output = write_dispatcher_review_v3_artifacts(
                dispatcher_rows,
                audit_rows,
                output_dir=Path(tmp),
                include_private_values=True,
                allow_custom_output_dir=True,
            )

            self.assertEqual(
                output["paths"]["dispatcher_review_csv"].name,
                DISPATCHER_REVIEW_V3_REVIEW_CSV,
            )
            self.assertEqual(
                output["paths"]["extraction_audit_csv"].name,
                DISPATCHER_REVIEW_V3_AUDIT_CSV,
            )
            if output["xlsx_written"]:
                self.assertEqual(
                    output["paths"]["dispatcher_review_workbook_xlsx"].name,
                    DISPATCHER_REVIEW_V3_WORKBOOK_XLSX,
                )

            with output["paths"]["dispatcher_review_csv"].open(
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(list(rows[0].keys()), DISPATCHER_REVIEW_COLUMNS)
            self.assertEqual(rows[0]["Broker"], "Fake Broker")
            self.assertFalse(output["private_values_printed"])

    def test_exporter_can_write_status_only_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_dispatcher_review_v3_artifacts(
                [build_dispatcher_review_row(measurement_alias="RATECON_004")],
                [build_dispatcher_audit_row(measurement_alias="RATECON_004")],
                output_dir=Path(tmp),
                include_private_values=False,
                allow_custom_output_dir=True,
            )

            with output["paths"]["dispatcher_review_csv"].open(
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["Broker"], "")
            self.assertFalse(output["private_values_printed"])


if __name__ == "__main__":
    unittest.main()
