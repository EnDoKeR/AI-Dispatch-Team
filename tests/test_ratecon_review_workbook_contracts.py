import unittest

from app.document_ai.ratecon_review_workbook import (
    DOCUMENT_SUMMARY_COLUMNS,
    FIELD_REVIEW_COLUMNS,
    LOCAL_PRIVATE_REVIEW_WARNING,
    RATE_REVIEW_COLUMNS,
    REVIEW_WORKBOOK_COLUMNS_BY_SHEET,
    SHEET_DOCUMENT_SUMMARY,
    SHEET_FIELD_REVIEW,
    SHEET_INSTRUCTIONS,
    SHEET_RATE_REVIEW,
    SHEET_STOP_REVIEW,
    STOP_REVIEW_COLUMNS,
    build_ratecon_review_rows,
    summarize_ratecon_review_workbook_rows,
)


def _fake_stop_set():
    return {
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
                    },
                    {
                        "field_name": "date",
                        "status": "missing",
                        "confidence": "unknown",
                        "evidence_refs": [],
                    },
                ],
            }
        ],
        "pickup_count": 1,
        "delivery_count": 0,
        "unknown_count": 0,
    }


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
        "span_normalized_stop_set": _fake_stop_set(),
        "load_identifier_coverage_metrics": {
            "primary_identifier_candidate_count": 1,
            "primary_identifier_type_counts": {"broker_load_number": 1},
            "typed_reference_candidate_count": 2,
            "rejected_reference_as_load_id_count": 2,
            "core_load_number_mapping_count": 1,
            "private_values_included": False,
            "raw_text_included": False,
        },
        "field_statuses": [
            {
                "field_name": "broker_name",
                "status": "needs_review",
                "confidence": "medium",
                "selected_value": "Fake Broker",
                "evidence_type": "text_regex",
            },
            {"field_name": "load_number", "status": "resolved"},
            {
                "field_name": "rate",
                "status": "resolved",
                "selected_value": "$1234",
                "evidence_type": "layout_table",
            },
            {"field_name": "pickup_location", "status": "resolved"},
            {"field_name": "pickup_date", "status": "needs_review"},
            {"field_name": "delivery_location", "status": "resolved"},
            {"field_name": "delivery_date", "status": "resolved"},
        ],
        "blocker_categories": ["VALUE_REVIEW_NEEDED"],
    }


class RateConReviewWorkbookContractTests(unittest.TestCase):
    def test_columns_registered_for_expected_sheets(self):
        self.assertEqual(
            REVIEW_WORKBOOK_COLUMNS_BY_SHEET[SHEET_DOCUMENT_SUMMARY],
            DOCUMENT_SUMMARY_COLUMNS,
        )
        self.assertEqual(
            REVIEW_WORKBOOK_COLUMNS_BY_SHEET[SHEET_STOP_REVIEW],
            STOP_REVIEW_COLUMNS,
        )
        self.assertEqual(
            REVIEW_WORKBOOK_COLUMNS_BY_SHEET[SHEET_FIELD_REVIEW],
            FIELD_REVIEW_COLUMNS,
        )
        self.assertEqual(
            REVIEW_WORKBOOK_COLUMNS_BY_SHEET[SHEET_RATE_REVIEW],
            RATE_REVIEW_COLUMNS,
        )
        for column in [
            "Extraction Review Blocker",
            "Intake Core Blocker",
            "Dispatch Decision Blocker",
            "Review Field",
            "Optional Missing Field",
            "Non Applicable Field",
            "Field Requirement Level",
            "Policy Gap Reason",
            "Load Identifier Status",
            "Load Identifier Candidate Count",
            "Primary Load Identifier Candidate Type",
            "Typed Reference Count",
            "Rejected Non-primary Reference Count",
            "Load Identifier Gap Reason",
            "Load Identifier Needs Review",
        ]:
            self.assertIn(column, FIELD_REVIEW_COLUMNS)
        for column in [
            "Extraction Review Blockers",
            "Intake Core Blockers",
            "Dispatch Decision Blockers",
            "Optional Missing Fields",
            "Non Applicable Fields",
        ]:
            self.assertIn(column, DOCUMENT_SUMMARY_COLUMNS)

    def test_build_rows_excludes_private_values_by_default(self):
        rows_by_sheet = build_ratecon_review_rows(
            [_fake_row()],
            local_document_names_by_alias={"RATECON_001": "LoadConfirmation1"},
        )

        stop_row = rows_by_sheet[SHEET_STOP_REVIEW][0]
        field_row = rows_by_sheet[SHEET_FIELD_REVIEW][0]
        self.assertEqual(stop_row["Predicted Value LOCAL ONLY"], "")
        self.assertEqual(field_row["Predicted Value LOCAL ONLY"], "")
        self.assertEqual(stop_row["Local Document Name / File Stem"], "LoadConfirmation1")
        self.assertEqual(stop_row["Needs Review"], "yes")
        self.assertIn("Intake Core Blocker", field_row)
        self.assertIn("Policy Gap Reason", field_row)

    def test_load_identifier_columns_are_populated_for_load_number(self):
        rows_by_sheet = build_ratecon_review_rows([_fake_row()])
        load_row = next(
            row
            for row in rows_by_sheet[SHEET_FIELD_REVIEW]
            if row["Field Name"] == "load_number"
        )

        self.assertEqual(load_row["Load Identifier Status"], "resolved")
        self.assertEqual(load_row["Load Identifier Candidate Count"], 1)
        self.assertEqual(
            load_row["Primary Load Identifier Candidate Type"],
            "broker_load_number=1",
        )
        self.assertEqual(load_row["Typed Reference Count"], 2)
        self.assertEqual(load_row["Rejected Non-primary Reference Count"], 2)
        self.assertEqual(load_row["Load Identifier Needs Review"], "no")

    def test_build_rows_includes_fake_private_values_only_when_explicit(self):
        rows_by_sheet = build_ratecon_review_rows(
            [_fake_row()],
            include_private_values=True,
        )

        stop_values = [
            row["Predicted Value LOCAL ONLY"]
            for row in rows_by_sheet[SHEET_STOP_REVIEW]
        ]
        field_values = [
            row["Predicted Value LOCAL ONLY"]
            for row in rows_by_sheet[SHEET_FIELD_REVIEW]
        ]
        self.assertIn("Fake Pickup City", stop_values)
        self.assertIn("Fake Broker", field_values)

    def test_summary_reports_readiness_and_integrity_counts(self):
        bad_row = _fake_row()
        bad_row["span_unknown_count"] = 2
        rows_by_sheet = build_ratecon_review_rows([bad_row])
        summary = summarize_ratecon_review_workbook_rows(rows_by_sheet)

        self.assertEqual(summary["document_rows"], 1)
        self.assertEqual(summary["stop_review_rows"], 2)
        self.assertIn("intake_core_ready", summary["readiness_level_counts"])
        self.assertIn("SPAN_TYPE_COUNT_MISMATCH", summary["integrity_issue_counts"])
        self.assertIn("intake_core_blocker_counts", summary)
        self.assertIn("optional_missing_field_counts", summary)
        self.assertEqual(summary["policy_misclassification_count"], 0)
        self.assertFalse(summary["raw_text_included"])

    def test_instructions_include_local_only_warning(self):
        rows_by_sheet = build_ratecon_review_rows([_fake_row()])
        instructions = rows_by_sheet[SHEET_INSTRUCTIONS]

        self.assertTrue(
            any(row["Instruction"] == LOCAL_PRIVATE_REVIEW_WARNING for row in instructions)
        )


if __name__ == "__main__":
    unittest.main()
