import json
import unittest
from pathlib import Path

from app.document_ai.layout_candidate_extraction import extract_ratecon_layout_candidates
from app.document_ai.ratecon_candidates import (
    FIELD_DELIVERY_LOCATION,
    FIELD_EQUIPMENT,
    FIELD_PICKUP_LOCATION,
    FIELD_RATE,
    FIELD_WEIGHT,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_artifacts")


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _classification_for_pages(page_roles_by_number, ratecon_eligible=True, document_type="RATE_CONFIRMATION"):
    page_results = []
    for page_number, roles in page_roles_by_number.items():
        page_results.append(
            {
                "page_number": page_number,
                "page_roles": roles,
                "primary_page_role": roles[0] if roles else "UNKNOWN",
                "section_summaries": [
                    {"section_role": section}
                    for section in [
                        "RATE_SUMMARY",
                        "RATE_BREAKDOWN",
                        "STOP_TABLE",
                        "PICKUP_SECTION",
                        "DELIVERY_SECTION",
                        "SPECIAL_INSTRUCTIONS",
                        "TONU_PAYMENT",
                    ]
                ],
            }
        )
    return {
        "document_type": document_type,
        "ratecon_eligible": ratecon_eligible,
        "supplemental_only": not ratecon_eligible,
        "classification_status": "ratecon_eligible" if ratecon_eligible else "supplemental_only",
        "page_results": page_results,
    }


class LayoutCandidateExtractionTests(unittest.TestCase):
    def test_blue_table_layout_produces_rate_stops_and_operational_candidates(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")

        result = extract_ratecon_layout_candidates(artifact)
        counts = result["candidate_counts_by_field"]

        self.assertGreaterEqual(counts[FIELD_RATE], 1)
        self.assertGreaterEqual(counts[FIELD_PICKUP_LOCATION], 1)
        self.assertGreaterEqual(counts[FIELD_DELIVERY_LOCATION], 1)
        self.assertGreaterEqual(counts[FIELD_EQUIPMENT], 1)
        self.assertGreaterEqual(counts[FIELD_WEIGHT], 1)

    def test_mcleod_layout_produces_pu_so_and_payment_candidates(self):
        artifact = _load_fixture("fake_mcleod_pu_so_layout.json")

        result = extract_ratecon_layout_candidates(artifact)
        fields = {candidate["field_name"] for candidate in result["candidates"]}

        self.assertIn(FIELD_RATE, fields)
        self.assertIn(FIELD_PICKUP_LOCATION, fields)
        self.assertIn(FIELD_DELIVERY_LOCATION, fields)
        self.assertIn(FIELD_EQUIPMENT, fields)

    def test_terms_billing_signature_layout_skipped_when_classified_supplemental(self):
        artifact = _load_fixture("fake_terms_billing_signature_layout.json")
        classification = _classification_for_pages({1: ["TERMS", "BILLING", "SIGNATURE"]}, ratecon_eligible=False)

        result = extract_ratecon_layout_candidates(artifact, classification)

        self.assertEqual(result["candidates"], [])
        self.assertIn("layout_extraction_skipped_by_classification", result["warnings"])

    def test_tonu_layout_produces_tonu_payment_candidate(self):
        artifact = _load_fixture("fake_tonu_payment_layout.json")
        classification = _classification_for_pages(
            {1: ["MAIN_LOAD_CONFIRMATION", "PAYMENT_SUMMARY"]},
            ratecon_eligible=True,
            document_type="TRUCK_ORDER_NOT_USED",
        )

        result = extract_ratecon_layout_candidates(artifact, classification)

        self.assertTrue(any(candidate["value_type"] == "TONU_pay" for candidate in result["candidates"]))
        self.assertNotIn(FIELD_PICKUP_LOCATION, result["candidate_counts_by_field"])

    def test_output_serializes(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")
        result = extract_ratecon_layout_candidates(artifact)

        json.dumps(result)

    def test_no_accept_reject_recommendation_emitted(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")

        text = str(extract_ratecon_layout_candidates(artifact))

        self.assertNotIn("ACCEPT", text)
        self.assertNotIn("REJECT", text)


if __name__ == "__main__":
    unittest.main()
