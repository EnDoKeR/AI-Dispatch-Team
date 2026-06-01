import unittest

from app.document_ai.review_feedback_target_selector import (
    REVIEW_TARGET_HUMAN_REVIEW_CONTINUE,
    REVIEW_TARGET_LOAD_IDENTIFIER_EXTRACTION,
    REVIEW_TARGET_OCR_DESIGN,
    REVIEW_TARGET_RATE_RESOLUTION,
    REVIEW_TARGET_STOP_LOCATION_EXTRACTION,
    REVIEW_TARGET_STOP_DATE_EXTRACTION,
    select_repair_target_from_dispatcher_feedback,
    select_repair_target_from_feedback,
)
from app.document_ai.target_disposition import (
    TARGET_DISPOSITION_STATUS_NEEDS_HUMAN_REVIEW,
    build_target_disposition_registry,
    mark_target_deferred,
)


def _aggregate(issue_counts, reviewed=3, incorrect=3):
    return {
        "reviewed_count": reviewed,
        "incorrect_count": incorrect,
        "issue_type_counts": issue_counts,
    }


class ReviewFeedbackTargetSelectorTests(unittest.TestCase):
    def test_no_feedback_continues_human_review(self):
        decision = select_repair_target_from_feedback(
            _aggregate({}, reviewed=0, incorrect=0)
        )

        self.assertEqual(
            decision["selected_target"],
            REVIEW_TARGET_HUMAN_REVIEW_CONTINUE,
        )
        self.assertIn("no_completed_feedback", decision["warning_codes"])

    def test_wrong_rate_selects_rate_resolution(self):
        decision = select_repair_target_from_feedback(
            _aggregate({"wrong_rate": 2, "wrong_date": 1})
        )

        self.assertEqual(decision["selected_target"], REVIEW_TARGET_RATE_RESOLUTION)
        self.assertEqual(decision["supporting_issue_types"], {"wrong_rate": 2})

    def test_wrong_date_selects_stop_date(self):
        decision = select_repair_target_from_feedback(
            _aggregate({"wrong_date": 4, "wrong_rate": 1})
        )

        self.assertEqual(
            decision["selected_target"],
            REVIEW_TARGET_STOP_DATE_EXTRACTION,
        )

    def test_load_id_missing_reopens_deferred_target_with_feedback(self):
        registry = mark_target_deferred(
            build_target_disposition_registry(),
            "load_identifier_candidate_generation",
            status=TARGET_DISPOSITION_STATUS_NEEDS_HUMAN_REVIEW,
            reason="fake review gate",
        )

        decision = select_repair_target_from_feedback(
            _aggregate({"load_id_missing": 3}),
            target_disposition_registry=registry,
        )

        self.assertEqual(
            decision["selected_target"],
            REVIEW_TARGET_LOAD_IDENTIFIER_EXTRACTION,
        )
        self.assertIn(
            "deferred_target_reopened_by_feedback",
            decision["warning_codes"],
        )

    def test_ocr_needed_selects_ocr_design_later(self):
        decision = select_repair_target_from_feedback(
            _aggregate({"OCR_needed": 3})
        )

        self.assertEqual(decision["selected_target"], REVIEW_TARGET_OCR_DESIGN)

    def test_dispatcher_feedback_wrong_pickup_selects_stop_location(self):
        decision = select_repair_target_from_dispatcher_feedback(
            {
                "rows_loaded": 2,
                "changed_field_count": 2,
                "issue_type_counts": {"wrong_pickup": 2},
            }
        )

        self.assertEqual(
            decision["selected_target"],
            REVIEW_TARGET_STOP_LOCATION_EXTRACTION,
        )
        self.assertEqual(decision["dispatcher_changed_field_count"], 2)

    def test_dispatcher_feedback_no_changes_continues_review(self):
        decision = select_repair_target_from_dispatcher_feedback(
            {"rows_loaded": 0, "changed_field_count": 0, "issue_type_counts": {}}
        )

        self.assertEqual(
            decision["selected_target"],
            REVIEW_TARGET_HUMAN_REVIEW_CONTINUE,
        )


if __name__ == "__main__":
    unittest.main()
