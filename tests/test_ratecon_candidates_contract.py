import json
import unittest

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_RATE,
    SOURCE_LABEL_PATTERN,
    build_candidate_extraction_result,
    build_field_candidate,
)


class RateConCandidatesContractTests(unittest.TestCase):
    def test_create_candidate(self):
        candidate = build_field_candidate(
            field_name=FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
            confidence_reasons=["strong total rate label"],
            page_number=1,
            line_number=4,
            label="Total Rate",
            source=SOURCE_LABEL_PATTERN,
            evidence_ref="EVIDENCE-001",
        )

        self.assertEqual(candidate["field_name"], FIELD_RATE)
        self.assertEqual(candidate["raw_value"], "$2,850.00")
        self.assertEqual(candidate["normalized_value"], "2850.00")
        self.assertEqual(candidate["confidence"], CANDIDATE_CONFIDENCE_HIGH)
        self.assertEqual(candidate["source"], SOURCE_LABEL_PATTERN)

    def test_candidate_serializes(self):
        candidate = build_field_candidate(field_name=FIELD_RATE, raw_value="$2,850.00")

        json.dumps(candidate)

    def test_multiple_rate_candidates_supported(self):
        result = build_candidate_extraction_result(
            document_id="DOC-001",
            artifact_id="ART-001",
            candidates=[
                build_field_candidate(field_name=FIELD_RATE, raw_value="$2,850.00"),
                build_field_candidate(field_name=FIELD_RATE, raw_value="$150.00"),
            ],
        )

        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["candidates"][0]["field_name"], FIELD_RATE)

    def test_low_confidence_candidate_supported(self):
        candidate = build_field_candidate(
            field_name=FIELD_RATE,
            raw_value="$150.00",
            confidence=CANDIDATE_CONFIDENCE_LOW,
            confidence_reasons=["accessorial-like label"],
            warnings=["not_final_assignment"],
        )

        self.assertEqual(candidate["confidence"], CANDIDATE_CONFIDENCE_LOW)
        self.assertIn("accessorial-like label", candidate["confidence_reasons"])
        self.assertIn("not_final_assignment", candidate["warnings"])

    def test_result_does_not_require_final_assignment(self):
        result = build_candidate_extraction_result(
            candidates=[
                build_field_candidate(field_name=FIELD_RATE, raw_value="$2,850.00"),
            ],
            missing_candidate_fields=["pickup_date"],
            warnings=["candidate_extraction_only"],
        )

        self.assertNotIn("resolved_fields", result)
        self.assertIn("pickup_date", result["missing_candidate_fields"])
        self.assertIn("candidate_extraction_only", result["warnings"])


if __name__ == "__main__":
    unittest.main()
