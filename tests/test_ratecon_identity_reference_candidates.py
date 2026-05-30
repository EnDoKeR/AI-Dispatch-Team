import unittest

from app.document_ai.ratecon_candidate_generators import (
    generate_identity_reference_candidates,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_BROKER_MC,
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_LOAD_NUMBER,
    FIELD_REFERENCE,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


class RateConIdentityReferenceCandidatesTests(unittest.TestCase):
    def test_fake_broker_name_candidate(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")
        candidates = generate_identity_reference_candidates(artifact)

        broker_names = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_BROKER_NAME
        ]

        self.assertTrue(broker_names)
        self.assertEqual(broker_names[0]["normalized_value"], "FAKE BROKER LLC")
        self.assertEqual(broker_names[0]["confidence"], CANDIDATE_CONFIDENCE_HIGH)

    def test_fake_broker_mc_candidate(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")
        candidates = generate_identity_reference_candidates(artifact)

        broker_mcs = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_BROKER_MC
        ]

        self.assertTrue(broker_mcs)
        self.assertEqual(broker_mcs[0]["normalized_value"], "MC000000")

    def test_load_number_candidate(self):
        artifact = build_fixture_text_artifact("ambiguous_references_ratecon.txt")
        candidates = generate_identity_reference_candidates(artifact)

        load_numbers = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_LOAD_NUMBER
        ]

        self.assertGreaterEqual(len(load_numbers), 2)
        self.assertTrue(
            any(candidate["normalized_value"] == "FAKE-LOAD-003" for candidate in load_numbers)
        )

    def test_multiple_typed_reference_candidates(self):
        artifact = build_fixture_text_artifact("ambiguous_references_ratecon.txt")
        candidates = generate_identity_reference_candidates(artifact)
        references = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_REFERENCE
        ]
        reference_types = {candidate["value_type"] for candidate in references}

        self.assertIn("po_number", reference_types)
        self.assertIn("bol_number", reference_types)
        self.assertIn("pickup_number", reference_types)
        self.assertIn("delivery_number", reference_types)
        self.assertIn("customer_reference", reference_types)
        self.assertIn("appointment_number", reference_types)

    def test_ambiguous_reference_candidate_is_lower_confidence(self):
        artifact = build_text_extraction_artifact_for_candidates(
            full_text="Reference: FAKE-REF-999",
            source_name="ambiguous_reference_fake.txt",
        )

        candidates = generate_identity_reference_candidates(artifact)

        self.assertEqual(candidates[0]["field_name"], FIELD_REFERENCE)
        self.assertEqual(candidates[0]["value_type"], "unknown_reference")
        self.assertEqual(candidates[0]["confidence"], CANDIDATE_CONFIDENCE_LOW)
        self.assertIn("ambiguous_reference_label", candidates[0]["warnings"])

    def test_carrier_name_not_confused_with_broker_name(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")
        candidates = generate_identity_reference_candidates(artifact)

        carrier_names = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_CARRIER_NAME
        ]
        broker_names = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_BROKER_NAME
        ]

        self.assertTrue(carrier_names)
        self.assertEqual(carrier_names[0]["normalized_value"], "FAKE CARRIER LLC")
        self.assertTrue(
            all(candidate["normalized_value"] != "FAKE CARRIER LLC" for candidate in broker_names)
        )


if __name__ == "__main__":
    unittest.main()
