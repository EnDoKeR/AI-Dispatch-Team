import unittest

from app.document_ai.private_measurement import (
    BLOCKER_CONFLICTING_CRITICAL_FIELD,
    BLOCKER_DIGITAL_TEXT_EXTRACTION_GAP,
    BLOCKER_LAYOUT_EXTRACTION_GAP,
    BLOCKER_MANUAL_REVIEW_REQUIRED,
    BLOCKER_MISSING_CRITICAL_FIELD,
    BLOCKER_OCR_NEEDED,
    BLOCKER_PARSED_HIGH_CONFIDENCE_CANDIDATE,
    BLOCKER_RESOLVER_GAP,
    BLOCKER_TEMPLATE_GAP,
    BLOCKER_UNSUPPORTED_OR_BROKEN_PDF,
    EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED,
    EXTRACTION_STATUS_EMPTY_TEXT,
    EXTRACTION_STATUS_TEXT_EXTRACTED,
)
from app.document_ai.private_measurement_blockers import (
    classify_private_ratecon_measurement_blockers,
)


class PrivateMeasurementBlockerTests(unittest.TestCase):
    def test_empty_text_routes_to_ocr_needed(self):
        blockers = classify_private_ratecon_measurement_blockers(
            triage_route="OCR_NEEDED",
            extraction_status=EXTRACTION_STATUS_EMPTY_TEXT,
            likely_image_based=True,
        )

        self.assertIn(BLOCKER_OCR_NEEDED, blockers)

    def test_broken_routes_to_unsupported(self):
        blockers = classify_private_ratecon_measurement_blockers(
            triage_route="UNSUPPORTED",
            extraction_status=EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED,
            broken=True,
        )

        self.assertIn(BLOCKER_UNSUPPORTED_OR_BROKEN_PDF, blockers)

    def test_text_exists_but_missing_rate_marks_missing_and_layout_gap(self):
        blockers = classify_private_ratecon_measurement_blockers(
            triage_route="DIGITAL_TEXT",
            extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
            template_status="matched",
            missing_fields=["rate"],
            candidate_counts_by_field={},
            review_required=True,
        )

        self.assertIn(BLOCKER_MISSING_CRITICAL_FIELD, blockers)
        self.assertIn(BLOCKER_DIGITAL_TEXT_EXTRACTION_GAP, blockers)
        self.assertIn(BLOCKER_LAYOUT_EXTRACTION_GAP, blockers)

    def test_missing_field_with_candidates_marks_resolver_gap(self):
        blockers = classify_private_ratecon_measurement_blockers(
            triage_route="DIGITAL_TEXT",
            extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
            template_status="matched",
            missing_fields=["rate"],
            candidate_counts_by_field={"rate": 2},
        )

        self.assertIn(BLOCKER_RESOLVER_GAP, blockers)

    def test_unknown_template_with_weak_fields_marks_template_gap(self):
        blockers = classify_private_ratecon_measurement_blockers(
            triage_route="DIGITAL_TEXT",
            extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
            template_status="unknown",
            missing_fields=["pickup_location"],
        )

        self.assertIn(BLOCKER_TEMPLATE_GAP, blockers)

    def test_conflicting_rate_marks_conflict_and_manual_review(self):
        blockers = classify_private_ratecon_measurement_blockers(
            triage_route="DIGITAL_TEXT",
            extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
            template_status="matched",
            conflict_fields=["rate"],
            review_required=True,
            candidate_counts_by_field={"rate": 3},
        )

        self.assertIn(BLOCKER_CONFLICTING_CRITICAL_FIELD, blockers)
        self.assertIn(BLOCKER_MANUAL_REVIEW_REQUIRED, blockers)
        self.assertIn(BLOCKER_RESOLVER_GAP, blockers)

    def test_high_confidence_candidate_does_not_claim_dispatch_readiness(self):
        blockers = classify_private_ratecon_measurement_blockers(
            triage_route="DIGITAL_TEXT",
            extraction_status=EXTRACTION_STATUS_TEXT_EXTRACTED,
            template_status="matched",
            review_required=False,
            candidate_counts_by_field={"rate": 1, "pickup_location": 1},
        )

        self.assertEqual(blockers, [BLOCKER_PARSED_HIGH_CONFIDENCE_CANDIDATE])


if __name__ == "__main__":
    unittest.main()
