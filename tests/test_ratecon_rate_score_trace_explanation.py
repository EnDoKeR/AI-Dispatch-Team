import unittest

from app.document_ai import field_candidate_resolver as resolver
from tests.helpers.ratecon_selected_rate_regression import (
    load_selected_rate_cases,
    run_selected_rate_case,
)


def _candidate(label, *, value="100.00", confidence=0.82, source="native_layout", metadata=None):
    return {
        "field": resolver.FIELD_TOTAL_CARRIER_RATE,
        "label": label,
        "evidence_text": label,
        "value": value,
        "normalized_value": value,
        "confidence": confidence,
        "source": source,
        "parser_name": "sanitized_trace_fixture",
        "metadata": dict(metadata or {}),
    }


class RateconRateScoreTraceExplanationTests(unittest.TestCase):
    def test_score_trace_adjustment_reason_strings_are_pinned(self):
        candidate = _candidate(
            "Total Carrier Pay: $100.00",
            metadata={"money_context": "total_carrier_pay"},
        )

        score = resolver._score(
            resolver.FIELD_TOTAL_CARRIER_RATE,
            candidate,
            {},
            resolver.RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
        )

        self.assertEqual(1.0, score)
        self.assertEqual(
            {
                "money_context": "total_carrier_pay",
                "ranking_profile": "money_abstain_v1",
                "ranking_adjustment_total": 0.08,
                "ranking_adjustments": [
                    {"reason": "total_carrier_pay_context", "amount": 0.08},
                ],
            },
            candidate["metadata"],
        )

    def test_abstention_trace_reason_strings_are_pinned(self):
        candidate = _candidate(
            "Quick Pay 3%",
            value="3",
            confidence=0.95,
            metadata={
                "money_context": "quickpay",
                "rate_abstained": True,
                "rate_abstention_reason": "quickpay_unsafe",
            },
        )

        score = resolver._score(
            resolver.FIELD_TOTAL_CARRIER_RATE,
            candidate,
            {},
            resolver.RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
        )

        self.assertEqual(0.0, score)
        self.assertEqual(-1.02, candidate["metadata"]["ranking_adjustment_total"])
        self.assertEqual(
            [
                {"reason": "quickpay_money_context_penalty", "amount": -0.42},
                {"reason": "quickpay_unsafe", "amount": -0.6},
            ],
            candidate["metadata"]["ranking_adjustments"],
        )

    def test_selected_candidate_trace_fields_are_stable(self):
        result = resolver.resolve_candidates(
            [
                _candidate(
                    "Total Carrier Pay: $100.00",
                    metadata={"money_context": "total_carrier_pay"},
                )
            ],
            field_names=[resolver.FIELD_TOTAL_CARRIER_RATE],
            rate_ranking_profile=resolver.RATE_RANKING_PROFILE_MONEY_ABSTAIN_V1,
        )

        trace = result["resolver_decision_traces"][resolver.FIELD_TOTAL_CARRIER_RATE]
        selected = trace["selected_candidate"]
        metadata = selected["metadata_summary"]

        self.assertEqual("selected", trace["decision_status"])
        self.assertEqual("money_abstain_v1", trace["ranking_profile"])
        self.assertEqual(1, trace["candidate_count_seen"])
        self.assertEqual(1, trace["candidate_count_eligible"])
        self.assertEqual([], trace["top_rejected_or_not_selected"])
        self.assertEqual("total_carrier_rate:candidate:1", selected["candidate_id"])
        self.assertEqual("native_layout", selected["source"])
        self.assertEqual("sanitized_trace_fixture", selected["parser_name"])
        self.assertEqual(1.0, selected["score"])
        self.assertEqual("total_carrier_pay", metadata["money_context"])
        self.assertEqual("safe", metadata["rate_safety"])
        self.assertEqual(
            [{"reason": "total_carrier_pay_context", "amount": 0.08}],
            metadata["ranking_adjustments"],
        )

    def test_conflict_not_selected_trace_reason_is_stable(self):
        result = resolver.resolve_candidates(
            [
                _candidate(
                    "Total Carrier Pay: $100.00",
                    value="100.00",
                    confidence=0.82,
                    metadata={"money_context": "total_carrier_pay"},
                ),
                _candidate(
                    "Total Carrier Pay: $90.00",
                    value="90.00",
                    confidence=0.70,
                    metadata={"money_context": "total_carrier_pay"},
                ),
            ],
            field_names=[resolver.FIELD_TOTAL_CARRIER_RATE],
        )

        trace = result["resolver_decision_traces"][resolver.FIELD_TOTAL_CARRIER_RATE]

        self.assertEqual("conflict", trace["decision_status"])
        self.assertEqual(["CONFLICTING_CANDIDATES"], trace["review_reasons"])
        self.assertEqual(2, trace["candidate_count_seen"])
        self.assertEqual(2, trace["candidate_count_eligible"])
        self.assertEqual("total_carrier_rate:candidate:2", trace["selected_candidate"]["candidate_id"])
        self.assertEqual(
            [
                {
                    "candidate_id": "total_carrier_rate:candidate:1",
                    "reason": "conflict",
                    "score": 1.0,
                }
            ],
            [
                {
                    "candidate_id": row["candidate_id"],
                    "reason": row["reason"],
                    "score": row["score"],
                }
                for row in trace["top_rejected_or_not_selected"]
            ],
        )

    def test_selected_rate_fixture_outputs_remain_unchanged(self):
        for case in load_selected_rate_cases():
            with self.subTest(case=case["id"]):
                actual = run_selected_rate_case(case)
                expected = dict(case["expected"])
                expected["case_id"] = case["id"]
                expected["known_debt"] = bool(case.get("known_debt"))
                self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
