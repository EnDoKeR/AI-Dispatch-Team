import json
import unittest

from app.document_ai.candidate_fusion import (
    FUSION_STATUS_CONFLICT,
    FUSION_STATUS_RESOLVED,
    SOURCE_PRIORITY_LAYOUT_TABLE,
    SOURCE_PRIORITY_TEXT_REGEX,
    build_candidate_fusion_result,
    classify_candidate_source_priority,
    fuse_candidates_by_field,
)
from app.document_ai.layout_candidate_adapter import attach_layout_evidence_to_candidate
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_RATE,
    SOURCE_REGEX,
    SOURCE_TABLE_PATTERN_FUTURE,
    build_field_candidate,
)


class CandidateFusionTests(unittest.TestCase):
    def _candidate(self, candidate_id, value, confidence, source=SOURCE_REGEX):
        return build_field_candidate(
            field_name=FIELD_RATE,
            raw_value=value,
            normalized_value=value,
            confidence=confidence,
            source=source,
            candidate_id=candidate_id,
        )

    def test_selects_stronger_layout_candidate_over_weak_text_candidate(self):
        text_candidate = self._candidate("text_rate", "1000", CANDIDATE_CONFIDENCE_LOW)
        layout_candidate = attach_layout_evidence_to_candidate(
            self._candidate(
                "layout_rate",
                "1000",
                CANDIDATE_CONFIDENCE_HIGH,
                source=SOURCE_TABLE_PATTERN_FUTURE,
            ),
            layout_evidence_ref={"evidence_type": "table_cell", "page_number": 1},
        )

        result = fuse_candidates_by_field(
            [text_candidate, layout_candidate],
            baseline_statuses={FIELD_RATE: "missing"},
        )

        decision = result["decisions"][0]
        self.assertEqual(decision["selected_candidate_id"], "layout_rate")
        self.assertEqual(decision["selected_source"], SOURCE_PRIORITY_LAYOUT_TABLE)
        self.assertEqual(decision["fused_status"], FUSION_STATUS_RESOLVED)
        self.assertIn(FIELD_RATE, result["improved_fields"])

    def test_keeps_strong_text_candidate_when_layout_evidence_is_weaker(self):
        text_candidate = self._candidate("text_rate", "1000", CANDIDATE_CONFIDENCE_HIGH)
        layout_candidate = attach_layout_evidence_to_candidate(
            self._candidate(
                "layout_rate",
                "1000",
                CANDIDATE_CONFIDENCE_LOW,
                source=SOURCE_TABLE_PATTERN_FUTURE,
            ),
            layout_evidence_ref={"evidence_type": "table_cell", "page_number": 1},
        )

        result = fuse_candidates_by_field(
            [text_candidate, layout_candidate],
            baseline_statuses={FIELD_RATE: "resolved"},
        )

        decision = result["decisions"][0]
        self.assertEqual(decision["selected_candidate_id"], "text_rate")
        self.assertEqual(decision["selected_source"], SOURCE_PRIORITY_TEXT_REGEX)
        self.assertFalse(decision["did_worsen_baseline"])

    def test_conflicts_when_two_strong_sources_disagree(self):
        text_candidate = self._candidate("text_rate", "1000", CANDIDATE_CONFIDENCE_HIGH)
        layout_candidate = attach_layout_evidence_to_candidate(
            self._candidate(
                "layout_rate",
                "1200",
                CANDIDATE_CONFIDENCE_HIGH,
                source=SOURCE_TABLE_PATTERN_FUTURE,
            ),
            layout_evidence_ref={"evidence_type": "table_cell", "page_number": 1},
        )

        result = fuse_candidates_by_field(
            [text_candidate, layout_candidate],
            baseline_statuses={FIELD_RATE: "needs_review"},
        )

        decision = result["decisions"][0]
        self.assertEqual(decision["fused_status"], FUSION_STATUS_CONFLICT)
        self.assertTrue(decision["review_required"])
        self.assertIn(FIELD_RATE, result["conflict_fields"])

    def test_source_priority_classification_handles_layout_and_text(self):
        self.assertEqual(
            classify_candidate_source_priority(self._candidate("text", "1000", "HIGH")),
            SOURCE_PRIORITY_TEXT_REGEX,
        )
        layout_candidate = attach_layout_evidence_to_candidate(
            self._candidate("layout", "1000", "HIGH", source=SOURCE_TABLE_PATTERN_FUTURE),
            layout_evidence_ref={"evidence_type": "table_cell"},
        )
        self.assertEqual(
            classify_candidate_source_priority(layout_candidate),
            SOURCE_PRIORITY_LAYOUT_TABLE,
        )

    def test_fusion_result_serializes(self):
        payload = build_candidate_fusion_result(
            decisions=[
                {
                    "field_name": FIELD_RATE,
                    "fused_status": FUSION_STATUS_RESOLVED,
                }
            ],
            fused_candidates=[self._candidate("text_rate", "1000", "HIGH")],
        )

        text = json.dumps(payload, sort_keys=True)

        self.assertIn("candidate_fusion_v1", text)
        self.assertIn(FIELD_RATE, text)


if __name__ == "__main__":
    unittest.main()
