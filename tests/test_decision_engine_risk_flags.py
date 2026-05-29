import inspect
import unittest

from app.market_intelligence.decision_engine import risk_flags
from app.market_intelligence.decision_engine.risk_flags import (
    ACTION_BLOCK,
    ACTION_INFO,
    ACTION_REVIEW,
    FLAG_GROUPS,
    RISK_FLAGS,
    dedupe_risk_flags,
    is_known_risk_flag,
    normalize_risk_flag,
    risk_flag_action,
    risk_flag_category,
    risk_flag_metadata,
)


class DecisionEngineRiskFlagsTest(unittest.TestCase):
    def test_key_flags_exist(self):
        for flag_name in [
            "MISSING_WEIGHT",
            "NO_CONESTOGA",
            "CONESTOGA_VERIFY",
            "RATE_CHECK_REQUIRED",
            "WEAK_EXIT_MARKET",
            "BROKER_MC_MISSING",
            "HAZMAT_REQUIRED",
            "TRACKING_REQUIRED",
            "LOW_CONFIDENCE_PARSER_FIELD",
        ]:
            with self.subTest(flag_name=flag_name):
                self.assertIn(flag_name, RISK_FLAGS)
                self.assertTrue(is_known_risk_flag(flag_name))

    def test_normalize_flag_text(self):
        self.assertEqual(normalize_risk_flag(" missing rate "), "MISSING_RATE")
        self.assertEqual(normalize_risk_flag("rate-check-required"), "RATE_CHECK_REQUIRED")
        self.assertEqual(normalize_risk_flag("weak exit market"), "WEAK_EXIT_MARKET")
        self.assertEqual(normalize_risk_flag("broker/mc/missing"), "BROKER_MC_MISSING")

    def test_dedupe_preserves_order(self):
        self.assertEqual(
            dedupe_risk_flags(
                [
                    "missing rate",
                    "MISSING_RATE",
                    "no-conestoga",
                    "",
                    None,
                    "NO_CONESTOGA",
                    "weak exit market",
                ]
            ),
            [
                "MISSING_RATE",
                "NO_CONESTOGA",
                "WEAK_EXIT_MARKET",
            ],
        )

    def test_unknown_flag_handled_safely(self):
        self.assertFalse(is_known_risk_flag("future unknown flag"))

        metadata = risk_flag_metadata("future unknown flag")

        self.assertEqual(metadata["name"], "FUTURE_UNKNOWN_FLAG")
        self.assertEqual(metadata["category"], "unknown")
        self.assertEqual(metadata["usual_action"], ACTION_REVIEW)
        self.assertEqual(metadata["meaning"], "")

    def test_flag_groups_are_stable(self):
        self.assertIn("missing_data", FLAG_GROUPS)
        self.assertIn("conestoga_compatibility", FLAG_GROUPS)
        self.assertIn("parser_confidence", FLAG_GROUPS)
        self.assertIn("MISSING_RATE", FLAG_GROUPS["missing_data"])
        self.assertIn("NO_CONESTOGA", FLAG_GROUPS["conestoga_compatibility"])
        self.assertIn("LOW_CONFIDENCE_PARSER_FIELD", FLAG_GROUPS["parser_confidence"])

    def test_metadata_category_and_action_helpers(self):
        self.assertEqual(risk_flag_category("NO_CONESTOGA"), "conestoga_compatibility")
        self.assertEqual(risk_flag_action("NO_CONESTOGA"), ACTION_BLOCK)
        self.assertEqual(risk_flag_action("CONESTOGA_COVERS_TARP"), ACTION_INFO)
        self.assertEqual(risk_flag_action("RATE_CHECK_REQUIRED"), ACTION_REVIEW)

    def test_no_forbidden_imports(self):
        source = inspect.getsource(risk_flags).lower()

        forbidden_terms = [
            "telegram",
            "dispatch_case",
            "case_event_builder",
            "event_logger",
            "pypdf",
            "gspread",
            "googlemaps",
            "dat_api",
            "apscheduler",
            "threading",
            "sqlite",
            "jsonl",
            "parser_contract",
            "pasted_text_parser",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
