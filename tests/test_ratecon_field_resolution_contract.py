import json
import unittest

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_RATE,
    build_field_candidate,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
    FIELD_RESOLUTION_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_RESOLVED,
    build_field_resolution,
    build_ratecon_field_resolution_result,
)


class RateConFieldResolutionContractTests(unittest.TestCase):
    def test_resolved_field_with_one_good_candidate(self):
        candidate = build_field_candidate(
            field_name=FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            evidence_ref="p1-l4",
        )

        resolution = build_field_resolution(
            field_name=FIELD_RATE,
            status=FIELD_RESOLUTION_STATUS_RESOLVED,
            selected_candidate=candidate,
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            reasons=["single_high_confidence_candidate"],
            evidence_refs=["p1-l4"],
        )

        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(resolution["selected_candidate"]["normalized_value"], "2850.00")
        self.assertIn("p1-l4", resolution["evidence_refs"])

    def test_missing_field_resolution(self):
        resolution = build_field_resolution(
            field_name=FIELD_RATE,
            status=FIELD_RESOLUTION_STATUS_MISSING,
            reasons=["no_candidate"],
        )

        self.assertEqual(resolution["selected_candidate"], {})
        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_MISSING)

    def test_conflict_field_with_rejected_candidates(self):
        selected = build_field_candidate(
            field_name=FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
        )
        rejected = build_field_candidate(
            field_name=FIELD_RATE,
            raw_value="$3,050.00",
            normalized_value="3050.00",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
        )

        resolution = build_field_resolution(
            field_name=FIELD_RATE,
            status=FIELD_RESOLUTION_STATUS_CONFLICT,
            selected_candidate=selected,
            rejected_candidates=[rejected],
            reasons=["multiple_strong_candidates"],
        )

        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_CONFLICT)
        self.assertEqual(len(resolution["rejected_candidates"]), 1)

    def test_low_confidence_field(self):
        candidate = build_field_candidate(
            field_name=FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=CANDIDATE_CONFIDENCE_LOW,
        )

        resolution = build_field_resolution(
            field_name=FIELD_RATE,
            status=FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
            selected_candidate=candidate,
            confidence=CANDIDATE_CONFIDENCE_LOW,
            warnings=["review_required"],
        )

        self.assertEqual(resolution["status"], FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE)
        self.assertIn("review_required", resolution["warnings"])

    def test_resolution_result_serializes(self):
        result = build_ratecon_field_resolution_result(
            document_id="doc-fake-1",
            artifact_id="artifact-fake-1",
            missing_fields=[FIELD_RATE],
            needs_check_fields=["pickup_date"],
            conflict_fields=["load_number"],
            warnings=["fake_warning"],
        )

        json.dumps(result)
        self.assertIn(FIELD_RATE, result["missing_fields"])
        self.assertIn("pickup_date", result["needs_check_fields"])
        self.assertIn("load_number", result["conflict_fields"])


if __name__ == "__main__":
    unittest.main()
