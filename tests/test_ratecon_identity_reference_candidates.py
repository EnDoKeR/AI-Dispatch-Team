import json
import unittest
from pathlib import Path

from app.document_ai.ratecon_candidate_generators import (
    generate_identity_reference_candidates,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
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


BROKER_IDENTITY_FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "candidate_coverage"
    / "broker_identity"
)
LOAD_IDENTIFIER_FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "candidate_coverage"
    / "load_identifier"
)


def build_broker_identity_fixture_artifact(name):
    return build_text_extraction_artifact_for_candidates(
        full_text=(BROKER_IDENTITY_FIXTURE_DIR / name).read_text(encoding="utf-8"),
        source_name=name,
    )


def build_load_identifier_fixture_artifact(name):
    return build_text_extraction_artifact_for_candidates(
        full_text=(LOAD_IDENTIFIER_FIXTURE_DIR / name).read_text(encoding="utf-8"),
        source_name=name,
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

    def test_hard_layout_confirmation_references_remain_typed(self):
        artifact = build_fixture_text_artifact("references_near_wrong_stop_ratecon.txt")
        candidates = generate_identity_reference_candidates(artifact)
        reference_types = {
            candidate["value_type"]
            for candidate in candidates
            if candidate["field_name"] == FIELD_REFERENCE
        }

        self.assertIn("po_number", reference_types)
        self.assertIn("bol_number", reference_types)
        self.assertIn("pickup_confirmation", reference_types)
        self.assertIn("delivery_confirmation", reference_types)
        self.assertIn("customer_reference", reference_types)

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

    def test_broker_identity_fixture_manifest_loads(self):
        manifest = json.loads(
            (BROKER_IDENTITY_FIXTURE_DIR / "fixture_manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(manifest["target"], "broker_identity_candidate_generation")
        self.assertGreaterEqual(len(manifest["fixtures"]), 4)
        for fixture in manifest["fixtures"]:
            self.assertTrue((BROKER_IDENTITY_FIXTURE_DIR / fixture["file"]).exists())

    def test_broker_contact_block_generates_broker_candidate(self):
        artifact = build_broker_identity_fixture_artifact("fake_broker_contact_block.txt")
        candidates = generate_identity_reference_candidates(artifact)
        broker_names = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_BROKER_NAME
        ]

        self.assertTrue(broker_names)
        self.assertEqual(
            broker_names[0]["normalized_value"],
            "Pioneer Freight Testing LLC",
        )
        self.assertEqual(broker_names[0]["confidence"], CANDIDATE_CONFIDENCE_MEDIUM)
        self.assertIn("broker_header_context", broker_names[0]["confidence_reasons"])

    def test_broker_logo_header_generates_reviewable_broker_candidate(self):
        artifact = build_broker_identity_fixture_artifact("fake_broker_logo_header.txt")
        candidates = generate_identity_reference_candidates(artifact)
        broker_names = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_BROKER_NAME
        ]

        self.assertTrue(broker_names)
        self.assertEqual(
            broker_names[0]["normalized_value"],
            "Pioneer Freight Testing LLC",
        )
        self.assertIn("broker_identity_review_required", broker_names[0]["warnings"])

    def test_load_tendered_by_label_generates_broker_candidate(self):
        artifact = build_broker_identity_fixture_artifact(
            "fake_load_tendered_by_broker.txt"
        )
        candidates = generate_identity_reference_candidates(artifact)
        broker_names = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_BROKER_NAME
        ]

        self.assertTrue(broker_names)
        self.assertEqual(
            broker_names[0]["normalized_value"],
            "Atlas Freight Testing LLC",
        )
        self.assertEqual(broker_names[0]["confidence"], CANDIDATE_CONFIDENCE_HIGH)

    def test_carrier_context_fixture_does_not_generate_broker_candidate(self):
        artifact = build_broker_identity_fixture_artifact(
            "fake_carrier_name_should_not_be_broker.txt"
        )
        candidates = generate_identity_reference_candidates(artifact)
        broker_names = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_BROKER_NAME
        ]
        carrier_names = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == FIELD_CARRIER_NAME
        ]

        self.assertEqual(broker_names, [])
        self.assertTrue(carrier_names)

    def test_load_identifier_fixtures_generate_expected_types(self):
        manifest = json.loads(
            (LOAD_IDENTIFIER_FIXTURE_DIR / "fixture_manifest.json").read_text(
                encoding="utf-8"
            )
        )

        for fixture in manifest["fixtures"]:
            with self.subTest(fixture=fixture["file"]):
                artifact = build_load_identifier_fixture_artifact(fixture["file"])
                candidates = generate_identity_reference_candidates(artifact)
                matching = [
                    candidate
                    for candidate in candidates
                    if candidate.get("identifier_type")
                    == fixture["expected_identifier_type"]
                ]
                primary_candidates = [
                    candidate
                    for candidate in candidates
                    if candidate.get("primary_load_identifier_candidate")
                    and candidate["field_name"] == FIELD_LOAD_NUMBER
                ]

                self.assertTrue(matching)
                self.assertEqual(
                    bool(primary_candidates),
                    bool(fixture["expected_primary_candidate"]),
                )

    def test_multiple_identifier_fixture_preserves_secondary_references(self):
        artifact = build_load_identifier_fixture_artifact(
            "fake_multiple_identifiers_priority.txt"
        )
        candidates = generate_identity_reference_candidates(artifact)
        primary_types = {
            candidate["identifier_type"]
            for candidate in candidates
            if candidate["field_name"] == FIELD_LOAD_NUMBER
        }
        reference_types = {
            candidate["identifier_type"]
            for candidate in candidates
            if candidate["field_name"] == FIELD_REFERENCE
        }

        self.assertIn("broker_load_number", primary_types)
        self.assertIn("po_number", reference_types)
        self.assertIn("bol_number", reference_types)

    def test_header_reference_no_generates_review_gated_primary_candidate(self):
        artifact = build_load_identifier_fixture_artifact(
            "fake_header_reference_no_review_candidate.txt"
        )
        candidates = generate_identity_reference_candidates(artifact)
        primary = [
            candidate
            for candidate in candidates
            if candidate.get("identifier_type") == "primary_reference"
            and candidate.get("primary_load_identifier_candidate")
        ]

        self.assertTrue(primary)
        self.assertEqual(primary[0]["field_name"], FIELD_LOAD_NUMBER)
        self.assertIn("generic_identifier_requires_review", primary[0]["warnings"])

    def test_stop_reference_no_remains_non_primary(self):
        artifact = build_load_identifier_fixture_artifact(
            "fake_stop_ref_not_primary_even_with_header.txt"
        )
        candidates = generate_identity_reference_candidates(artifact)
        primary = [
            candidate
            for candidate in candidates
            if candidate.get("primary_load_identifier_candidate")
        ]
        references = [
            candidate
            for candidate in candidates
            if candidate.get("identifier_type") == "unknown_reference"
            and candidate["field_name"] == FIELD_REFERENCE
        ]

        self.assertEqual(primary, [])
        self.assertTrue(references)


if __name__ == "__main__":
    unittest.main()
