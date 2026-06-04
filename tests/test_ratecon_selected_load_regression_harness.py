import json
import unittest

from tests.helpers.ratecon_selected_load_regression import (
    FIXTURE_PATH,
    load_selected_load_cases,
    run_selected_load_case,
    run_selected_load_cases,
)


class RateconSelectedLoadRegressionHarnessTests(unittest.TestCase):
    def test_every_fixture_pins_current_selected_load_behavior(self):
        cases = load_selected_load_cases()
        self.assertEqual(12, len(cases))

        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                result = run_selected_load_case(case)
                expected = case["expected"]
                for key in (
                    "selected_value",
                    "selected_source",
                    "selected_confidence",
                    "selected_label",
                    "status",
                    "missing",
                    "needs_check",
                    "conflict",
                ):
                    self.assertEqual(expected[key], result[key])
                self.assertEqual(case["known_debt"], result["known_debt"])
                self.assertFalse(result["pdf_processing_attempted"])
                self.assertFalse(result["ocr_attempted"])
                self.assertFalse(result["google_called"])
                self.assertFalse(result["model_or_cloud_called"])

    def test_known_debt_cases_are_explicitly_marked(self):
        results = run_selected_load_cases()
        known_debt = [result for result in results if result["known_debt"]]

        self.assertEqual(
            [
                "pro_number_current_behavior_resolves",
                "table_neighbor_wrong_cell_known_debt",
                "nearby_row_wrong_pair_known_debt",
            ],
            [result["case_id"] for result in known_debt],
        )
        self.assertTrue(all(result["debt_note"] for result in known_debt))

    def test_fixture_contains_only_sanitized_values(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        text = json.dumps(payload).lower()
        forbidden = (
            "data/private_ratecons",
            ".gold.json",
            "api_key",
            "secret",
            "service account",
            "google token",
            "raw extracted",
            "private pdf",
        )

        self.assertEqual([marker for marker in forbidden if marker in text], [])
        self.assertIn("fake-load", text)


if __name__ == "__main__":
    unittest.main()
