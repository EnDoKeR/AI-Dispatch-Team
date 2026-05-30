import json
import unittest
from pathlib import Path

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_TYPE_DELIVERY,
    NORMALIZED_STOP_TYPE_PICKUP,
    NORMALIZED_STOP_TYPE_UNKNOWN,
)
from app.document_ai.stop_association import build_stop_association_result
from app.document_ai.stop_normalization import (
    DEDUP_WARNING_DUPLICATE,
    WARNING_NORMALIZED_STOP_REVIEW_REQUIRED,
    WARNING_TONU_STOPS_NOT_APPLICABLE,
    build_normalized_stop_set,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_normalization"
)


def load_fixture(name):
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def build_set(name, classification_result=None):
    fixture = load_fixture(name)
    return build_normalized_stop_set(
        build_stop_association_result(stop_groups=fixture["stop_groups"]),
        classification_result=classification_result,
    )


class NormalizedStopSetBuilderTests(unittest.TestCase):
    def test_clean_pickup_delivery(self):
        stop_set = build_set("fake_table_pickup_delivery_groups")

        self.assertEqual(len(stop_set["stops"]), 2)
        self.assertEqual(stop_set["pickup_count"], 1)
        self.assertEqual(stop_set["delivery_count"], 1)

    def test_multi_stop_preserved(self):
        stop_set = build_set("fake_multi_stop_three_rows")

        self.assertEqual(len(stop_set["stops"]), 3)
        self.assertEqual(stop_set["delivery_count"], 2)
        self.assertEqual([stop["sequence"] for stop in stop_set["stops"]], [1, 2, 3])

    def test_duplicate_groups_removed(self):
        stop_set = build_set("fake_duplicate_header_stop_groups")

        self.assertEqual(len(stop_set["stops"]), 2)
        self.assertEqual(stop_set["stop_duplicate_removed_count"], 1)
        self.assertIn(DEDUP_WARNING_DUPLICATE, stop_set["warning_codes"])

    def test_ambiguous_groups_review_required(self):
        stop_set = build_set("fake_ambiguous_stop_type_groups")

        self.assertEqual(stop_set["unknown_count"], 2)
        self.assertEqual(stop_set["review_required_stop_count"], 2)
        self.assertIn(WARNING_NORMALIZED_STOP_REVIEW_REQUIRED, stop_set["warning_codes"])
        self.assertTrue(
            all(stop["stop_type"] == NORMALIZED_STOP_TYPE_UNKNOWN for stop in stop_set["stops"])
        )

    def test_terms_and_signature_noise_removed(self):
        signature_set = build_set("fake_signature_footer_noise_groups")
        terms_set = build_set("fake_terms_payment_noise_groups")

        self.assertEqual(signature_set["stop_noise_removed_count"], 2)
        self.assertEqual(len(signature_set["stops"]), 1)
        self.assertEqual(terms_set["stop_noise_removed_count"], 2)
        self.assertEqual(len(terms_set["stops"]), 0)

    def test_tonu_not_applicable(self):
        fixture = load_fixture("fake_table_pickup_delivery_groups")
        stop_set = build_normalized_stop_set(
            build_stop_association_result(stop_groups=fixture["stop_groups"]),
            classification_result={
                "document_alias": "RATECON_FAKE_TONU",
                "document_type": "TRUCK_ORDER_NOT_USED",
                "normal_load_movement": False,
            },
        )

        self.assertEqual(stop_set["stops"], [])
        self.assertEqual(stop_set["pickup_count"], 0)
        self.assertIn(WARNING_TONU_STOPS_NOT_APPLICABLE, stop_set["warning_codes"])

    def test_serialization_safe(self):
        stop_set = build_set("fake_pu_so_continuation_groups")
        payload = json.loads(json.dumps(stop_set, sort_keys=True))

        self.assertEqual(
            [stop["stop_type"] for stop in payload["stops"]],
            [NORMALIZED_STOP_TYPE_PICKUP, NORMALIZED_STOP_TYPE_DELIVERY],
        )
        self.assertNotIn("raw_text", payload)


if __name__ == "__main__":
    unittest.main()
