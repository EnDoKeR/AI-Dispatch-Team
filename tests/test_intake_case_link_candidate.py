import copy
import inspect
import json
import unittest

from app.market_intelligence.intake import case_link_candidate
from app.market_intelligence.intake.case_link_candidate import (
    CREATE_CASE_REVIEW,
    KEEP_UNLINKED,
    LINK_EXISTING,
    NEEDS_REVIEW,
    build_intake_case_link_candidate,
)
from app.market_intelligence.intake.record import build_intake_record


def clean_intake(overrides=None):
    record = build_intake_record(
        {
            "intake_id": "INTAKE-1",
            "source_type": "manual_json",
            "source_file_name": "synthetic-ratecon.json",
            "broker_name": "Synthetic Logistics",
            "broker_mc": "000000",
            "rate": 3200,
            "pickup_location": "Dallas, TX",
            "pickup_date": "2026-06-01",
            "delivery_location": "Denver, CO",
            "delivery_date": "2026-06-02",
            "commodity": "Synthetic steel",
            "weight": 42000,
            "reference_id": "SYN-REF-1",
            "equipment": "Conestoga",
            "field_confidence": {"reference_id": "HIGH"},
        }
    )
    record.update(overrides or {})
    return record


def matching_case(overrides=None):
    record = {
        "case_id": "CASE-1",
        "reference_id": "SYN-REF-1",
        "broker_name": "Synthetic Logistics",
        "broker_mc": "000000",
        "pickup": "Dallas, TX",
        "delivery": "Denver, CO",
        "rate": 3200,
    }
    record.update(overrides or {})
    return record


class TestIntakeCaseLinkCandidate(unittest.TestCase):
    def test_clean_intake_matching_case_recommends_link_existing(self):
        candidate = build_intake_case_link_candidate(clean_intake(), matching_case())

        self.assertEqual(candidate["recommended_action"], LINK_EXISTING)
        self.assertTrue(candidate["approval_required"])
        self.assertEqual(candidate["candidate_case_id"], "CASE-1")
        self.assertIn("reference_id_match", candidate["match_reasons"])
        self.assertIn("lane_match", candidate["match_reasons"])
        self.assertEqual(candidate["mismatch_reasons"], [])

    def test_clean_intake_without_case_recommends_create_case_review(self):
        candidate = build_intake_case_link_candidate(clean_intake())

        self.assertEqual(candidate["recommended_action"], CREATE_CASE_REVIEW)
        self.assertTrue(candidate["approval_required"])
        self.assertEqual(candidate["candidate_case_id"], "")

    def test_missing_mandatory_fields_recommends_needs_review(self):
        intake = build_intake_record({"intake_id": "INTAKE-MISSING"})

        candidate = build_intake_case_link_candidate(intake, matching_case())

        self.assertEqual(candidate["recommended_action"], NEEDS_REVIEW)
        self.assertIn("broker_name", candidate["missing_fields"])
        self.assertIn("reference_id", candidate["missing_fields"])

    def test_low_confidence_critical_field_recommends_needs_review(self):
        intake = clean_intake(
            {
                "field_confidence": {
                    "reference_id": "LOW",
                    "pickup_location": "HIGH",
                }
            }
        )

        candidate = build_intake_case_link_candidate(intake, matching_case())

        self.assertEqual(candidate["recommended_action"], NEEDS_REVIEW)
        self.assertIn("low_confidence_reference_id", candidate["mismatch_reasons"])
        self.assertEqual(candidate["confidence"], "LOW")

    def test_weak_identity_evidence_recommends_keep_unlinked(self):
        intake = clean_intake(
            {
                "reference_id": "",
                "missing_fields": [],
                "needs_check_fields": [],
            }
        )

        candidate = build_intake_case_link_candidate(intake)

        self.assertEqual(candidate["recommended_action"], KEEP_UNLINKED)
        self.assertIn("missing_identity_evidence", candidate["mismatch_reasons"])

    def test_mismatch_lane_broker_and_reference_create_mismatch_reasons(self):
        candidate = build_intake_case_link_candidate(
            clean_intake(),
            matching_case(
                {
                    "reference_id": "OTHER-REF",
                    "broker_mc": "999999",
                    "pickup": "Austin, TX",
                    "delivery": "Phoenix, AZ",
                }
            ),
        )

        self.assertEqual(candidate["recommended_action"], NEEDS_REVIEW)
        self.assertIn("reference_id_mismatch", candidate["mismatch_reasons"])
        self.assertIn("broker_mc_mismatch", candidate["mismatch_reasons"])
        self.assertIn("lane_mismatch", candidate["mismatch_reasons"])

    def test_missing_fields_are_preserved(self):
        intake = clean_intake({"missing_fields": ["broker_mc", "weight"]})

        candidate = build_intake_case_link_candidate(intake, matching_case())

        self.assertEqual(candidate["missing_fields"], ["broker_mc", "weight"])
        self.assertEqual(candidate["recommended_action"], NEEDS_REVIEW)

    def test_needs_check_fields_are_preserved(self):
        intake = clean_intake({"needs_check_fields": ["pickup_date"]})

        candidate = build_intake_case_link_candidate(intake, matching_case())

        self.assertEqual(candidate["needs_check_fields"], ["pickup_date"])
        self.assertEqual(candidate["recommended_action"], NEEDS_REVIEW)

    def test_candidate_is_json_serializable(self):
        candidate = build_intake_case_link_candidate(clean_intake(), matching_case())

        json.dumps(candidate)

    def test_helper_does_not_mutate_inputs(self):
        intake = clean_intake()
        case = matching_case()
        intake_before = copy.deepcopy(intake)
        case_before = copy.deepcopy(case)

        build_intake_case_link_candidate(intake, case)

        self.assertEqual(intake, intake_before)
        self.assertEqual(case, case_before)
        self.assertEqual(intake.get("linked_dispatch_case_id", ""), "")

    def test_helper_does_not_import_forbidden_runtime_layers(self):
        source = inspect.getsource(case_link_candidate)

        forbidden = [
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "telegram_sender",
            "telegram_notifier",
            "pypdf",
            "pytesseract",
            "gspread",
            "google.oauth",
            "googlemaps",
            "dat_api",
            "load_intake",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
