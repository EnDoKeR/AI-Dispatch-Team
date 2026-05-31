import unittest

from app.document_ai.ratecon_candidate_generators import (
    build_money_rate_candidate_result,
    generate_money_rate_candidates,
)
from app.document_ai.rate_fusion import fuse_rate_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_ACCESSORIAL_TERM,
    FIELD_RATE,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


class RateConMoneyCandidatesTests(unittest.TestCase):
    def test_simple_clean_rate_produces_high_confidence_rate_candidate(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        candidates = generate_money_rate_candidates(artifact)
        rate_candidates = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_RATE
        ]

        self.assertTrue(rate_candidates)
        self.assertEqual(rate_candidates[0]["normalized_value"], "2850.00")
        self.assertEqual(rate_candidates[0]["confidence"], CANDIDATE_CONFIDENCE_HIGH)
        self.assertIn("strong_rate_label", rate_candidates[0]["confidence_reasons"])
        self.assertEqual(rate_candidates[0]["value_type"], "total_carrier_pay")

    def test_accessorial_amounts_are_lower_confidence_or_accessorial_candidates(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")

        candidates = generate_money_rate_candidates(artifact)
        accessorial_candidates = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_ACCESSORIAL_TERM
        ]

        self.assertGreaterEqual(len(accessorial_candidates), 3)
        self.assertTrue(
            all(candidate["confidence"] == CANDIDATE_CONFIDENCE_LOW for candidate in accessorial_candidates)
        )
        self.assertTrue(
            all(candidate["warnings"] for candidate in accessorial_candidates)
        )
        self.assertTrue(
            all(candidate["value_type"] != "money" for candidate in accessorial_candidates)
        )

    def test_rate_source_priority_fixture_preserves_typed_money_candidates(self):
        artifact = build_text_extraction_artifact_for_candidates(
            full_text="\n".join(
                [
                    "FAKE RATE CONFIRMATION",
                    "Total Carrier Pay: USD 4100.00",
                    "Detention: USD 150.00 after two free hours",
                    "Quick Pay Discount: USD 40.00 optional",
                ]
            ),
            source_name="fake_rate_source_priority.txt",
        )

        candidates = generate_money_rate_candidates(artifact)
        rate_types = {
            candidate["value_type"]
            for candidate in candidates
            if candidate["field_name"] == FIELD_RATE
        }
        accessorial_types = {
            candidate["value_type"]
            for candidate in candidates
            if candidate["field_name"] == FIELD_ACCESSORIAL_TERM
        }

        self.assertIn("total_carrier_pay", rate_types)
        self.assertIn("detention_pay", accessorial_types)
        self.assertIn("quick_pay_discount", accessorial_types)

    def test_rate_fusion_uses_typed_total_and_excludes_accessorial_noise(self):
        artifact = build_text_extraction_artifact_for_candidates(
            full_text="\n".join(
                [
                    "FAKE RATE CONFIRMATION",
                    "Carrier Pay: USD 4100.00",
                    "Layover Fee: USD 250.00",
                    "Quick Pay: USD 40.00",
                ]
            ),
            source_name="fake_rate_fusion_priority.txt",
        )
        candidates = generate_money_rate_candidates(artifact)

        result = fuse_rate_candidates(
            text_candidates=candidates,
            baseline_status="missing",
        )

        self.assertEqual(result["fused_status"], "resolved")
        self.assertTrue(result["selected_candidate_id"])
        self.assertTrue(result["excluded_candidate_ids"])

    def test_multiple_dollar_amounts_produce_multiple_candidates(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")

        candidates = generate_money_rate_candidates(artifact)

        self.assertGreaterEqual(len(candidates), 5)

    def test_no_money_found_produces_warning(self):
        artifact = build_text_extraction_artifact_for_candidates(
            full_text="Broker: FAKE BROKER LLC\nPickup: Fake City, ST",
            source_name="no_money_fake.txt",
        )

        result = build_money_rate_candidate_result(artifact)

        self.assertEqual(result["candidates"], [])
        self.assertIn("no_money_candidates_found", result["warnings"])
        self.assertIn(FIELD_RATE, result["missing_candidate_fields"])

    def test_conflict_rate_fixture_produces_multiple_plausible_rate_candidates(self):
        artifact = build_fixture_text_artifact("conflict_rate_ratecon.txt")

        candidates = [
            candidate
            for candidate in generate_money_rate_candidates(artifact)
            if candidate["field_name"] == FIELD_RATE
        ]

        self.assertGreaterEqual(len(candidates), 2)
        self.assertTrue(
            any(candidate["normalized_value"] == "2900.00" for candidate in candidates)
        )
        self.assertTrue(
            any(candidate["normalized_value"] == "3050.00" for candidate in candidates)
        )

    def test_no_dispatch_recommendation_literals_emitted(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")
        result = build_money_rate_candidate_result(artifact)
        text = str(result)

        for literal in ["ACCEPT", "REJECT"]:
            with self.subTest(literal=literal):
                self.assertNotIn(literal, text)


if __name__ == "__main__":
    unittest.main()
