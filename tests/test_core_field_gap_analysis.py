import json
import unittest

from app.document_ai.core_field_gap_analysis import (
    CORE_FIELD_BROKER_MC,
    CORE_FIELD_BROKER_NAME,
    CORE_FIELD_COMMODITY,
    CORE_FIELD_DELIVERY_DATE,
    CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
    CORE_FIELD_GAP_CONFLICT,
    CORE_FIELD_GAP_NO_CANDIDATE,
    CORE_FIELD_GAP_OCR_NEEDED,
    CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
    CORE_FIELD_PICKUP_DATE,
    CORE_FIELD_PICKUP_TIME,
    CORE_FIELD_RATE,
    analyze_core_field_gaps_from_rows,
    build_core_field_gap_aggregate,
    build_core_field_gap_record,
)


class CoreFieldGapAnalysisTests(unittest.TestCase):
    def test_builds_missing_no_candidate_record(self):
        record = build_core_field_gap_record(
            measurement_alias="RATECON_001",
            field_name=CORE_FIELD_BROKER_NAME,
            status="missing",
            gap_reason=CORE_FIELD_GAP_NO_CANDIDATE,
            candidate_count=0,
            intake_core_blocker=True,
        )

        self.assertEqual(record["field_name"], CORE_FIELD_BROKER_NAME)
        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_NO_CANDIDATE)
        self.assertTrue(record["intake_core_blocker"])
        self.assertEqual(record["recommended_fix_bucket"], "broker_load_identity_extraction")

    def test_builds_unresolved_record(self):
        record = build_core_field_gap_record(
            measurement_alias="RATECON_001",
            field_name=CORE_FIELD_RATE,
            status="needs_review",
            gap_reason=CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
            candidate_count=2,
        )

        self.assertEqual(record["candidate_count"], 2)
        self.assertEqual(
            record["gap_reason"],
            CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
        )
        self.assertEqual(record["recommended_fix_bucket"], "rate_resolution_hardening")

    def test_builds_conflict_record(self):
        record = build_core_field_gap_record(
            measurement_alias="RATECON_001",
            field_name=CORE_FIELD_RATE,
            status="conflict",
            gap_reason=CORE_FIELD_GAP_CONFLICT,
            candidate_count=3,
            conflict_count=2,
        )

        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_CONFLICT)
        self.assertEqual(record["conflict_count"], 2)

    def test_optional_misclassified_record_is_not_intake_blocker(self):
        record = build_core_field_gap_record(
            measurement_alias="RATECON_001",
            field_name=CORE_FIELD_BROKER_MC,
            status="missing",
            gap_reason=CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
            intake_core_blocker=False,
            dispatch_decision_blocker=True,
        )

        self.assertFalse(record["intake_core_blocker"])
        self.assertTrue(record["dispatch_decision_blocker"])

    def test_aggregate_selects_top_field_and_target(self):
        aggregate = build_core_field_gap_aggregate(
            [
                build_core_field_gap_record(
                    measurement_alias="RATECON_001",
                    field_name=CORE_FIELD_BROKER_NAME,
                    status="missing",
                    gap_reason=CORE_FIELD_GAP_NO_CANDIDATE,
                ),
                build_core_field_gap_record(
                    measurement_alias="RATECON_002",
                    field_name=CORE_FIELD_BROKER_NAME,
                    status="missing",
                    gap_reason=CORE_FIELD_GAP_NO_CANDIDATE,
                ),
                build_core_field_gap_record(
                    measurement_alias="RATECON_003",
                    field_name=CORE_FIELD_RATE,
                    status="conflict",
                    gap_reason=CORE_FIELD_GAP_CONFLICT,
                ),
            ],
            document_count=3,
        )

        self.assertEqual(aggregate["document_count"], 3)
        self.assertEqual(aggregate["gap_counts_by_field"][CORE_FIELD_BROKER_NAME], 2)
        self.assertEqual(aggregate["top_core_field_gaps"][0], CORE_FIELD_BROKER_NAME)
        self.assertEqual(
            aggregate["recommended_next_target"],
            "broker_load_identity_extraction",
        )

    def test_optional_records_do_not_drive_next_target(self):
        aggregate = build_core_field_gap_aggregate(
            [
                build_core_field_gap_record(
                    measurement_alias=f"RATECON_OPT_{index}",
                    field_name=CORE_FIELD_BROKER_MC,
                    status="missing",
                    gap_reason=CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED,
                    intake_core_blocker=False,
                    dispatch_decision_blocker=True,
                )
                for index in range(5)
            ]
            + [
                build_core_field_gap_record(
                    measurement_alias="RATECON_RATE",
                    field_name=CORE_FIELD_RATE,
                    status="conflict",
                    gap_reason=CORE_FIELD_GAP_CONFLICT,
                    intake_core_blocker=True,
                )
            ],
            document_count=6,
        )

        self.assertEqual(
            aggregate["recommended_next_target"],
            "rate_resolution_hardening",
        )

    def test_serialization_contains_no_private_values(self):
        aggregate = build_core_field_gap_aggregate(
            [
                build_core_field_gap_record(
                    measurement_alias="RATECON_001",
                    field_name=CORE_FIELD_BROKER_NAME,
                    status="missing",
                    gap_reason=CORE_FIELD_GAP_NO_CANDIDATE,
                )
            ],
            document_count=1,
        )

        payload = json.dumps(aggregate)
        self.assertIn("RATECON_001", payload)
        self.assertNotIn("Fake Broker", payload)

    def test_analyzer_classifies_missing_with_zero_candidates(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[{"Measurement Alias": "RATECON_001"}],
            field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": CORE_FIELD_BROKER_NAME,
                    "Status": "missing",
                    "Predicted Value LOCAL ONLY": "Fake Broker",
                }
            ],
            safe_summary_rows=[
                {
                    "document_alias": "RATECON_001",
                    "field_statuses": [
                        {
                            "field_name": CORE_FIELD_BROKER_NAME,
                            "status": "missing",
                            "candidate_count": 0,
                        }
                    ],
                }
            ],
        )

        record = analysis["records"][0]
        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_NO_CANDIDATE)
        self.assertTrue(record["intake_core_blocker"])
        self.assertNotIn("Fake Broker", json.dumps(analysis))

    def test_analyzer_classifies_missing_with_candidates_as_unresolved(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[{"Measurement Alias": "RATECON_001"}],
            field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": CORE_FIELD_PICKUP_DATE,
                    "Status": "missing",
                }
            ],
            safe_summary_rows=[
                {
                    "document_alias": "RATECON_001",
                    "field_statuses": [
                        {
                            "field_name": CORE_FIELD_PICKUP_DATE,
                            "status": "missing",
                            "candidate_count": 2,
                        }
                    ],
                }
            ],
        )

        self.assertEqual(
            analysis["records"][0]["gap_reason"],
            CORE_FIELD_GAP_CANDIDATE_EXISTS_BUT_UNRESOLVED,
        )

    def test_analyzer_classifies_conflict(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[{"Measurement Alias": "RATECON_001"}],
            field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": CORE_FIELD_RATE,
                    "Status": "conflict",
                }
            ],
            safe_summary_rows=[
                {
                    "document_alias": "RATECON_001",
                    "field_statuses": [
                        {
                            "field_name": CORE_FIELD_RATE,
                            "status": "conflict",
                            "candidate_count": 3,
                        }
                    ],
                }
            ],
        )

        self.assertEqual(analysis["records"][0]["gap_reason"], CORE_FIELD_GAP_CONFLICT)
        self.assertEqual(analysis["records"][0]["conflict_count"], 1)

    def test_optional_field_missing_is_not_intake_blocker(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[{"Measurement Alias": "RATECON_001"}],
            field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": CORE_FIELD_BROKER_MC,
                    "Status": "missing",
                }
            ],
        )

        record = analysis["records"][0]
        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_OPTIONAL_MISCLASSIFIED)
        self.assertFalse(record["intake_core_blocker"])
        self.assertTrue(record["dispatch_decision_blocker"])

    def test_ocr_document_is_not_digital_intake_blocker(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "OCR Needed": "yes",
                }
            ],
            field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": CORE_FIELD_BROKER_NAME,
                    "Status": "missing",
                }
            ],
        )

        record = analysis["records"][0]
        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_OCR_NEEDED)
        self.assertFalse(record["intake_core_blocker"])

    def test_stop_review_gap_maps_to_pickup_or_delivery_field(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[{"Measurement Alias": "RATECON_001"}],
            stop_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Stop Type": "delivery",
                    "Field Name": "date",
                    "Status": "missing",
                }
            ],
        )

        record = analysis["records"][0]
        self.assertEqual(record["field_name"], CORE_FIELD_DELIVERY_DATE)
        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_NO_CANDIDATE)

    def test_missing_stop_review_appointment_window_does_not_double_count_time_gap(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[{"Measurement Alias": "RATECON_001"}],
            stop_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Stop Type": "pickup",
                    "Field Name": "appointment_window",
                    "Status": "missing",
                }
            ],
        )

        self.assertEqual(analysis["records"], [])

    def test_conflicting_stop_review_appointment_window_maps_to_stop_time(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[{"Measurement Alias": "RATECON_001"}],
            stop_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Stop Type": "pickup",
                    "Field Name": "appointment_window",
                    "Status": "conflict",
                }
            ],
        )

        record = analysis["records"][0]
        self.assertEqual(record["field_name"], CORE_FIELD_PICKUP_TIME)
        self.assertEqual(record["gap_reason"], CORE_FIELD_GAP_CONFLICT)

    def test_analyzer_omits_resolved_and_non_core_rows(self):
        analysis = analyze_core_field_gaps_from_rows(
            document_rows=[{"Measurement Alias": "RATECON_001"}],
            field_rows=[
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": CORE_FIELD_COMMODITY,
                    "Status": "resolved",
                },
                {
                    "Measurement Alias": "RATECON_001",
                    "Field Name": "accessorial_term",
                    "Status": "missing",
                },
            ],
        )

        self.assertEqual(analysis["records"], [])


if __name__ == "__main__":
    unittest.main()
