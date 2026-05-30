import json
import unittest
from pathlib import Path

from app.document_ai.stop_normalization import (
    DEDUP_WARNING_DUPLICATE,
    NOISE_WARNING_SIGNATURE,
    NOISE_WARNING_TERMS,
    compute_stop_group_signature,
    dedupe_stop_groups,
    filter_stop_group_noise,
    is_likely_duplicate_stop_group,
    is_likely_stop_noise,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_normalization"
)
CALIBRATION_DIR = FIXTURE_DIR / "calibration_patterns"


def load_fixture(name):
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def load_calibration_fixture(name):
    return json.loads((CALIBRATION_DIR / f"{name}.json").read_text(encoding="utf-8"))


class StopGroupDedupeNoiseTests(unittest.TestCase):
    def test_duplicate_header_groups_collapse(self):
        fixture = load_fixture("fake_duplicate_header_stop_groups")
        result = dedupe_stop_groups(fixture["stop_groups"])

        self.assertEqual(result["removed_count"], 1)
        self.assertEqual(len(result["kept_groups"]), 2)
        self.assertIn(DEDUP_WARNING_DUPLICATE, result["warning_codes"])

    def test_signature_noise_removed(self):
        fixture = load_fixture("fake_signature_footer_noise_groups")
        result = filter_stop_group_noise(fixture["stop_groups"])

        self.assertEqual(result["removed_count"], 2)
        self.assertEqual(len(result["kept_groups"]), 1)
        self.assertIn(NOISE_WARNING_SIGNATURE, result["warning_codes"])

    def test_terms_payment_noise_not_used_as_core_stop(self):
        fixture = load_fixture("fake_terms_payment_noise_groups")
        result = filter_stop_group_noise(fixture["stop_groups"])

        self.assertEqual(result["removed_count"], 2)
        self.assertEqual(result["kept_groups"], [])
        self.assertIn(NOISE_WARNING_TERMS, result["warning_codes"])

    def test_strong_table_row_group_preserved(self):
        fixture = load_fixture("fake_table_pickup_delivery_groups")
        result = filter_stop_group_noise(fixture["stop_groups"])

        self.assertEqual(result["removed_count"], 0)
        self.assertEqual(len(result["kept_groups"]), 2)

    def test_ambiguous_only_group_preserved_for_review(self):
        fixture = load_fixture("fake_ambiguous_stop_type_groups")
        result = filter_stop_group_noise(fixture["stop_groups"])

        self.assertEqual(result["removed_count"], 0)
        self.assertEqual(len(result["kept_groups"]), 2)

    def test_duplicate_detection_uses_safe_signature_not_values(self):
        fixture = load_fixture("fake_duplicate_header_stop_groups")
        first, second = fixture["stop_groups"][0], fixture["stop_groups"][1]
        signature = compute_stop_group_signature(first)

        self.assertTrue(is_likely_duplicate_stop_group(first, second))
        self.assertNotIn("raw_value", signature)
        self.assertNotIn("normalized_value", signature)

    def test_noise_filter_is_conservative_for_location_without_date(self):
        fixture = load_fixture("fake_location_without_date")
        group = fixture["stop_groups"][0]

        self.assertFalse(is_likely_stop_noise(group))

    def test_repeated_header_location_only_noise_removed(self):
        fixture = load_calibration_fixture("fake_duplicate_stop_groups_repeated_header")
        result = filter_stop_group_noise(fixture["stop_groups"])

        self.assertEqual(result["removed_count"], 2)
        self.assertEqual(result["kept_groups"], [])

    def test_terms_billing_reference_only_noise_removed(self):
        fixture = load_calibration_fixture("fake_terms_billing_noise_stop_like")
        result = filter_stop_group_noise(fixture["stop_groups"])

        self.assertEqual(result["removed_count"], 2)
        self.assertEqual(result["kept_groups"], [])


if __name__ == "__main__":
    unittest.main()
