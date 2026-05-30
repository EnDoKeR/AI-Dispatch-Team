import unittest

from app.document_ai.rate_fusion import RATE_FUSION_VERSION, fuse_rate_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_ACCESSORIAL_TERM,
    FIELD_RATE,
    SOURCE_REGEX,
    SOURCE_TABLE_PATTERN_FUTURE,
    build_field_candidate,
)


class RateFusionTests(unittest.TestCase):
    def _candidate(
        self,
        candidate_id,
        value,
        confidence=CANDIDATE_CONFIDENCE_HIGH,
        field_name=FIELD_RATE,
        value_type="total_carrier_pay",
        section_role="RATE_SUMMARY",
        warnings=None,
        source=SOURCE_TABLE_PATTERN_FUTURE,
    ):
        candidate = build_field_candidate(
            field_name=field_name,
            raw_value=value,
            normalized_value=value,
            confidence=confidence,
            source=source,
            candidate_id=candidate_id,
            value_type=value_type,
            warnings=warnings,
        )
        candidate["layout_section_role"] = section_role
        return candidate

    def test_layout_rate_improves_text_conflict(self):
        layout = self._candidate("layout_rate", "2400.00")

        result = fuse_rate_candidates(
            text_candidates=[],
            layout_candidates=[layout],
            baseline_status="conflict",
        )

        self.assertEqual(result["fused_status"], "resolved")
        self.assertEqual(result["selected_candidate_id"], "layout_rate")
        self.assertTrue(result["did_improve_baseline"])

    def test_quickpay_amount_is_not_main_rate(self):
        quickpay = self._candidate(
            "quickpay",
            "25.00",
            field_name=FIELD_ACCESSORIAL_TERM,
            value_type="quick_pay_discount",
            section_role="QUICK_PAY",
            warnings=["payment_terms_not_main_rate"],
        )

        result = fuse_rate_candidates(layout_candidates=[quickpay], baseline_status="missing")

        self.assertEqual(result["fused_status"], "missing")
        self.assertIn("quickpay", result["excluded_candidate_ids"])

    def test_terms_penalty_is_not_main_rate(self):
        penalty = self._candidate(
            "terms_penalty",
            "250.00",
            field_name=FIELD_ACCESSORIAL_TERM,
            value_type="deduction",
            section_role="LEGAL_TERMS",
            warnings=["not_final_rate_candidate"],
        )

        result = fuse_rate_candidates(layout_candidates=[penalty], baseline_status="missing")

        self.assertEqual(result["fused_status"], "missing")
        self.assertIn("terms_penalty", result["excluded_candidate_ids"])

    def test_matching_text_and_layout_reinforces_resolved_baseline(self):
        text = self._candidate(
            "text_rate",
            "2400.00",
            source=SOURCE_REGEX,
            section_role="",
        )
        layout = self._candidate("layout_rate", "2400.00")

        result = fuse_rate_candidates(
            text_candidates=[text],
            layout_candidates=[layout],
            baseline_status="resolved",
        )

        self.assertEqual(result["fused_status"], "resolved")
        self.assertFalse(result["did_worsen_baseline"])
        self.assertIn("rate_fusion_reinforced_baseline", result["warning_codes"])

    def test_conflicting_totals_route_review(self):
        first = self._candidate("layout_total_1", "2400.00")
        second = self._candidate("layout_total_2", "2600.00")

        result = fuse_rate_candidates(
            layout_candidates=[first, second],
            baseline_status="needs_review",
        )

        self.assertEqual(result["fused_status"], "conflict")
        self.assertTrue(result["review_required"])
        self.assertIn("rate_fusion_conflicting_strong_totals", result["warning_codes"])

    def test_conflicting_layout_rate_does_not_mark_resolved_baseline_worsened(self):
        text = self._candidate("text_rate", "2400.00", source=SOURCE_REGEX, section_role="")
        layout = self._candidate("layout_rate", "2600.00")

        result = fuse_rate_candidates(
            text_candidates=[text],
            layout_candidates=[layout],
            baseline_status="resolved",
        )

        self.assertEqual(result["fused_status"], "conflict")
        self.assertFalse(result["did_worsen_baseline"])
        self.assertIn(
            "layout_candidate_rejected_to_prevent_regression",
            result["warning_codes"],
        )

    def test_tonu_payment_is_separate_from_normal_linehaul(self):
        tonu = self._candidate(
            "tonu_amount",
            "300.00",
            field_name=FIELD_ACCESSORIAL_TERM,
            value_type="TONU_pay",
            section_role="TONU_PAYMENT",
            warnings=["tonu_payment_not_normal_linehaul"],
        )

        result = fuse_rate_candidates(
            layout_candidates=[tonu],
            baseline_status="missing",
            document_type="RATE_CONFIRMATION",
        )

        self.assertEqual(result["fused_status"], "missing")
        self.assertIn("tonu_amount", result["excluded_candidate_ids"])
        self.assertEqual(result["fusion_version"], RATE_FUSION_VERSION)

    def test_resolved_baseline_is_not_silently_downgraded_to_missing(self):
        weak_layout = self._candidate(
            "weak_layout",
            "2400.00",
            confidence=CANDIDATE_CONFIDENCE_LOW,
        )

        result = fuse_rate_candidates(
            layout_candidates=[weak_layout],
            baseline_status="resolved",
        )

        self.assertEqual(result["fused_status"], "resolved")
        self.assertFalse(result["did_worsen_baseline"])


if __name__ == "__main__":
    unittest.main()
