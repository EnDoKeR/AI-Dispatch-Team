import json
import unittest

from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_RATE,
    build_candidate_extraction_result,
    build_field_candidate,
)
from app.document_ai.ratecon_field_resolution import resolve_ratecon_fields
from app.document_ai.ratecon_intake_draft import build_ratecon_intake_from_resolution
from app.market_intelligence.intake.rate_confirmation_intake import (
    STATUS_MISSING_FIELDS,
    STATUS_READY_FOR_REVIEW,
)
from app.market_intelligence.intake.rate_confirmation_validation import (
    validate_rate_confirmation_intake,
)
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


class RateConIntakeDraftTests(unittest.TestCase):
    def _build_draft_from_fixture(self, fixture_name, field_names=None):
        artifact = build_fixture_text_artifact(fixture_name)
        candidate_result = extract_ratecon_candidates(artifact)
        resolution_result = resolve_ratecon_fields(candidate_result, field_names=field_names)
        return build_ratecon_intake_from_resolution(resolution_result)

    def test_simple_fixture_produces_intake_draft_with_resolved_fields(self):
        intake = self._build_draft_from_fixture("simple_clean_ratecon.txt")

        self.assertEqual(intake["status"], STATUS_READY_FOR_REVIEW)
        self.assertEqual(intake["broker_name"], "FAKE BROKER LLC")
        self.assertEqual(intake["load_number"], "FAKE-LOAD-001")
        self.assertEqual(intake["rate"]["amount"], "2850.00")
        self.assertEqual(intake["commodity"], "FAKE STEEL PARTS")
        self.assertEqual(intake["weight"], "42500")
        self.assertFalse(intake["cases_created"])
        self.assertFalse(intake["cases_linked"])

    def test_missing_rate_produces_missing_fields(self):
        intake = self._build_draft_from_fixture(
            "missing_core_fields_ratecon.txt",
            field_names=[FIELD_RATE],
        )

        self.assertEqual(intake["status"], STATUS_MISSING_FIELDS)
        self.assertIn("rate", intake["missing_fields"])

    def test_conflict_rate_preserves_needs_check_marker(self):
        intake = self._build_draft_from_fixture(
            "conflict_rate_ratecon.txt",
            field_names=[FIELD_RATE],
        )

        self.assertIn("rate", intake["needs_check_fields"])
        self.assertTrue(intake["review_required"])

    def test_low_confidence_critical_field_does_not_become_ready(self):
        candidate_result = build_candidate_extraction_result(
            document_id="DOC-LOW-CONFIDENCE",
            candidates=[
                build_field_candidate(
                    field_name=FIELD_RATE,
                    raw_value="$2,850.00",
                    normalized_value="2850.00",
                    confidence=CANDIDATE_CONFIDENCE_LOW,
                )
            ],
        )
        resolution_result = resolve_ratecon_fields(candidate_result, field_names=[FIELD_RATE])

        intake = build_ratecon_intake_from_resolution(resolution_result)

        self.assertNotEqual(intake["status"], STATUS_READY_FOR_REVIEW)
        self.assertIn("rate", intake["needs_check_fields"])
        self.assertIn("rate", intake["missing_fields"])

    def test_serialization_round_trip(self):
        intake = self._build_draft_from_fixture("simple_clean_ratecon.txt")

        payload = json.loads(json.dumps(intake))

        self.assertEqual(payload["document_id"], intake["document_id"])
        self.assertFalse(payload["raw_text_included"])

    def test_validation_catches_missing_fields_from_draft(self):
        intake = self._build_draft_from_fixture(
            "missing_core_fields_ratecon.txt",
            field_names=[FIELD_RATE],
        )

        validation = validate_rate_confirmation_intake(intake)

        self.assertEqual(validation["status"], STATUS_MISSING_FIELDS)
        self.assertIn("rate", validation["missing_fields"])


if __name__ == "__main__":
    unittest.main()
