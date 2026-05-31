import json
import unittest

from app.document_ai.rate_candidate_equivalence import (
    classify_rate_candidate_equivalence_group,
    group_equivalent_rate_candidates,
    summarize_rate_candidate_groups,
)
from app.document_ai.rate_conflict_audit import (
    RATE_EQUIVALENT_DIFFERENT_LABEL_SAME_AMOUNT,
    RATE_EQUIVALENT_DIFFERENT_SOURCE_SAME_AMOUNT,
    RATE_EQUIVALENT_SAME_LABEL_DUPLICATE,
)
from app.document_ai.ratecon_candidates import FIELD_ACCESSORIAL_TERM, FIELD_RATE


class RateCandidateEquivalenceTests(unittest.TestCase):
    def _candidate(
        self,
        value,
        candidate_id="rate_1",
        field_name=FIELD_RATE,
        value_type="total_carrier_pay",
        source="TEXT",
        label="Total Carrier Pay",
    ):
        return {
            "candidate_id": candidate_id,
            "field_name": field_name,
            "normalized_value": value,
            "raw_value": value,
            "value_type": value_type,
            "source": source,
            "label": label,
        }

    def test_same_amount_different_sources_equivalent(self):
        groups = group_equivalent_rate_candidates(
            [
                self._candidate("1200.00", candidate_id="text", source="TEXT"),
                self._candidate("1,200.00", candidate_id="layout", source="LAYOUT"),
            ]
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(
            classify_rate_candidate_equivalence_group(groups[0]),
            RATE_EQUIVALENT_DIFFERENT_SOURCE_SAME_AMOUNT,
        )

    def test_same_amount_same_label_duplicate(self):
        groups = group_equivalent_rate_candidates(
            [
                self._candidate("1200.00", candidate_id="a"),
                self._candidate("1200.00", candidate_id="b"),
            ]
        )

        self.assertEqual(
            classify_rate_candidate_equivalence_group(groups[0]),
            RATE_EQUIVALENT_SAME_LABEL_DUPLICATE,
        )

    def test_different_amount_strong_totals_are_separate_groups(self):
        groups = group_equivalent_rate_candidates(
            [
                self._candidate("1200.00", candidate_id="a"),
                self._candidate("1300.00", candidate_id="b"),
            ]
        )

        summary = summarize_rate_candidate_groups(groups)

        self.assertEqual(summary["main_rate_group_count"], 2)
        self.assertEqual(summary["equivalent_group_count"], 0)

    def test_accessorial_same_amount_stays_separate_category(self):
        groups = group_equivalent_rate_candidates(
            [
                self._candidate("1200.00", candidate_id="main"),
                self._candidate(
                    "1200.00",
                    candidate_id="accessorial",
                    field_name=FIELD_ACCESSORIAL_TERM,
                    value_type="detention_pay",
                    label="Detention",
                ),
            ]
        )

        summary = summarize_rate_candidate_groups(groups)

        self.assertEqual(summary["group_count"], 2)
        self.assertEqual(summary["main_rate_group_count"], 1)
        self.assertEqual(summary["accessorial_group_count"], 1)

    def test_same_amount_different_labels_equivalent(self):
        groups = group_equivalent_rate_candidates(
            [
                self._candidate(
                    "1200.00",
                    candidate_id="total",
                    label="Total Carrier Pay",
                ),
                self._candidate(
                    "1200.00",
                    candidate_id="agreed",
                    value_type="agreed_amount",
                    label="Agreed Amount",
                ),
            ]
        )

        self.assertEqual(
            classify_rate_candidate_equivalence_group(groups[0]),
            RATE_EQUIVALENT_DIFFERENT_LABEL_SAME_AMOUNT,
        )

    def test_safe_summary_excludes_money_values(self):
        groups = group_equivalent_rate_candidates(
            [self._candidate("1200.00"), self._candidate("1200.00")]
        )
        payload = json.dumps(summarize_rate_candidate_groups(groups))

        self.assertNotIn("1200", payload)
        self.assertNotIn("$", payload)


if __name__ == "__main__":
    unittest.main()
