import json
import unittest
from pathlib import Path

from app.document_ai.layout_rate_candidates import generate_layout_rate_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    FIELD_ACCESSORIAL_TERM,
    FIELD_RATE,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_artifacts")


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class LayoutRateCandidateTests(unittest.TestCase):
    def test_blue_table_rate_table_produces_main_rate_and_bonus_candidates(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")

        candidates = generate_layout_rate_candidates(artifact)
        rate_candidates = [candidate for candidate in candidates if candidate["field_name"] == FIELD_RATE]
        accessorial_candidates = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_ACCESSORIAL_TERM
        ]

        self.assertTrue(any(candidate["normalized_value"] == "2800.00" for candidate in rate_candidates))
        self.assertTrue(any(candidate["value_type"] == "tracking_bonus" for candidate in accessorial_candidates))
        self.assertTrue(any(candidate["layout_table_id"] == "P1_T_RATE" for candidate in rate_candidates))

    def test_mcleod_payment_summary_produces_carrier_freight_pay_candidate(self):
        artifact = _load_fixture("fake_mcleod_pu_so_layout.json")

        candidates = generate_layout_rate_candidates(artifact)
        rate_candidates = [candidate for candidate in candidates if candidate["field_name"] == FIELD_RATE]

        self.assertTrue(any(candidate["value_type"] == "carrier_freight_pay" for candidate in rate_candidates))
        self.assertTrue(any(candidate["confidence"] == CANDIDATE_CONFIDENCE_HIGH for candidate in rate_candidates))

    def test_carrier_tender_agreed_rate_table_produces_rate_candidate(self):
        artifact = _load_fixture("fake_carrier_tender_route_details_layout.json")

        candidates = generate_layout_rate_candidates(artifact)

        self.assertTrue(any(candidate["value_type"] == "total_charge" for candidate in candidates))
        self.assertTrue(any(candidate["normalized_value"] == "3500.00" for candidate in candidates))
        self.assertFalse(any(candidate["raw_value"] == "300" for candidate in candidates))

    def test_terms_page_money_is_not_main_rate(self):
        artifact = _load_fixture("fake_terms_billing_signature_layout.json")

        candidates = generate_layout_rate_candidates(artifact)
        rate_candidates = [candidate for candidate in candidates if candidate["field_name"] == FIELD_RATE]
        accessorial_candidates = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_ACCESSORIAL_TERM
        ]

        self.assertFalse(rate_candidates)
        self.assertTrue(accessorial_candidates)
        self.assertTrue(all("not_final_rate_candidate" in candidate["warnings"] or "payment_terms_not_main_rate" in candidate["warnings"] for candidate in accessorial_candidates))

    def test_quickpay_discount_is_not_main_rate(self):
        artifact = _load_fixture("fake_terms_billing_signature_layout.json")

        candidates = generate_layout_rate_candidates(artifact)

        self.assertTrue(any(candidate["value_type"] == "quick_pay_discount" for candidate in candidates))
        self.assertFalse(
            any(candidate["field_name"] == FIELD_RATE and candidate["normalized_value"] == "25.00" for candidate in candidates)
        )

    def test_tonu_amount_classified_separately(self):
        artifact = _load_fixture("fake_tonu_payment_layout.json")

        candidates = generate_layout_rate_candidates(artifact)

        self.assertTrue(any(candidate["value_type"] == "TONU_pay" for candidate in candidates))
        self.assertFalse(any(candidate["field_name"] == FIELD_RATE for candidate in candidates))
        self.assertTrue(any("tonu_payment_not_normal_linehaul" in candidate["warnings"] for candidate in candidates))

    def test_multiple_money_values_preserved(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")

        candidates = generate_layout_rate_candidates(artifact)
        values = {candidate["normalized_value"] for candidate in candidates}

        self.assertIn("2800.00", values)
        self.assertIn("100.00", values)


if __name__ == "__main__":
    unittest.main()
