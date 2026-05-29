import inspect
import unittest

from app.market_intelligence.decision_engine import approval_modes
from app.market_intelligence.decision_engine.approval_modes import (
    MODE_AUTOPILOT,
    MODE_COPILOT,
    MODE_SUPERVISED,
    approval_required_for_action,
    is_autonomous_action_allowed,
    normalize_action_type,
    normalize_approval_mode,
)


class DecisionEngineApprovalModesTest(unittest.TestCase):
    def test_defaults_to_copilot(self):
        self.assertEqual(normalize_approval_mode(""), MODE_COPILOT)
        self.assertEqual(normalize_approval_mode(None), MODE_COPILOT)
        self.assertEqual(normalize_approval_mode("unknown"), MODE_COPILOT)

    def test_normalizes_valid_modes(self):
        self.assertEqual(normalize_approval_mode("copilot"), MODE_COPILOT)
        self.assertEqual(normalize_approval_mode(" supervised "), MODE_SUPERVISED)
        self.assertEqual(normalize_approval_mode("auto-pilot"), MODE_AUTOPILOT)

    def test_unknown_mode_falls_back_safely(self):
        self.assertEqual(normalize_approval_mode("hands free"), MODE_COPILOT)

    def test_action_type_normalization(self):
        self.assertEqual(normalize_action_type("book load"), "BOOK_LOAD")
        self.assertEqual(normalize_action_type("rate-commitment"), "RATE_COMMITMENT")
        self.assertEqual(normalize_action_type(""), "NO_ACTION")

    def test_booking_and_rate_commitments_require_approval_in_all_modes(self):
        for mode in [MODE_COPILOT, MODE_SUPERVISED, MODE_AUTOPILOT]:
            with self.subTest(mode=mode):
                self.assertTrue(approval_required_for_action(mode, "BOOK_LOAD"))
                self.assertTrue(approval_required_for_action(mode, "RATE_COMMITMENT"))
                self.assertTrue(approval_required_for_action(mode, "SEND_FACTORING_PACKET"))
                self.assertFalse(is_autonomous_action_allowed(mode, "BOOK_LOAD"))
                self.assertFalse(is_autonomous_action_allowed(mode, "RATE_COMMITMENT"))
                self.assertFalse(is_autonomous_action_allowed(mode, "LEGAL_COMMITMENT"))

    def test_safe_informational_action_can_be_allowed(self):
        for mode in [MODE_COPILOT, MODE_SUPERVISED, MODE_AUTOPILOT]:
            with self.subTest(mode=mode):
                self.assertFalse(approval_required_for_action(mode, "SHOW_RECOMMENDATION"))
                self.assertFalse(approval_required_for_action(mode, "DRY_RUN_REPORT"))
                self.assertTrue(is_autonomous_action_allowed(mode, "SHOW_RECOMMENDATION"))
                self.assertTrue(is_autonomous_action_allowed(mode, "FORMAT_PREVIEW"))

    def test_unknown_noninformational_action_requires_approval(self):
        self.assertTrue(approval_required_for_action(MODE_AUTOPILOT, "CALL_BROKER"))
        self.assertFalse(is_autonomous_action_allowed(MODE_AUTOPILOT, "CALL_BROKER"))

    def test_no_forbidden_imports(self):
        source = inspect.getsource(approval_modes).lower()

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
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
