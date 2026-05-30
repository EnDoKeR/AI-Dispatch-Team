import json
import unittest
from pathlib import Path

from app.document_ai.stop_association import (
    STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    STOP_TYPE_UNKNOWN,
    build_stop_group_candidate,
)
from app.document_ai.stop_normalization import (
    SEQUENCE_WARNING_INFERRED,
    TYPE_WARNING_AMBIGUOUS,
    TYPE_WARNING_OVERCLASSIFIED,
    assign_stop_sequence_order,
    infer_stop_sequence,
    resolve_stop_type,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "document_ai"
    / "stop_normalization"
)


def load_fixture(name):
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


class StopSequenceTypeResolutionTests(unittest.TestCase):
    def test_pu_so_mapping_from_section_roles(self):
        pickup = build_stop_group_candidate(
            "pu_group",
            stop_type=STOP_TYPE_UNKNOWN,
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="PICKUP_SECTION",
        )
        delivery = build_stop_group_candidate(
            "so_group",
            stop_type=STOP_TYPE_UNKNOWN,
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="DELIVERY_SECTION",
        )

        self.assertEqual(resolve_stop_type(pickup)["stop_type"], STOP_TYPE_PICKUP)
        self.assertEqual(resolve_stop_type(delivery)["stop_type"], STOP_TYPE_DELIVERY)

    def test_stop_one_stop_two_sequence_mapping(self):
        fixture = load_fixture("fake_table_pickup_delivery_groups")
        sequenced = assign_stop_sequence_order(fixture["stop_groups"])

        self.assertEqual([group["stop_sequence"] for group in sequenced], [1, 2])
        self.assertEqual(sequenced[0]["stop_type"], STOP_TYPE_PICKUP)
        self.assertEqual(sequenced[1]["stop_type"], STOP_TYPE_DELIVERY)

    def test_multi_stop_sequence_preserved(self):
        fixture = load_fixture("fake_multi_stop_three_rows")
        sequenced = assign_stop_sequence_order(fixture["stop_groups"])

        self.assertEqual([group["stop_sequence"] for group in sequenced], [1, 2, 3])
        self.assertEqual(
            [group["stop_type"] for group in sequenced],
            [STOP_TYPE_PICKUP, STOP_TYPE_DELIVERY, STOP_TYPE_DELIVERY],
        )

    def test_ambiguous_stays_unknown(self):
        fixture = load_fixture("fake_ambiguous_stop_type_groups")
        result = resolve_stop_type(fixture["stop_groups"][0])

        self.assertEqual(result["stop_type"], STOP_TYPE_UNKNOWN)
        self.assertIn(TYPE_WARNING_AMBIGUOUS, result["warning_codes"])

    def test_generic_stop_labels_are_not_overclassified_as_pickup_delivery(self):
        fixture = json.loads(
            (
                FIXTURE_DIR
                / "calibration_patterns"
                / "fake_pickup_delivery_overclassified.json"
            ).read_text(encoding="utf-8")
        )

        results = [resolve_stop_type(group) for group in fixture["stop_groups"]]

        self.assertEqual(
            [result["stop_type"] for result in results],
            [STOP_TYPE_UNKNOWN, STOP_TYPE_UNKNOWN],
        )
        self.assertTrue(
            all(TYPE_WARNING_OVERCLASSIFIED in result["warning_codes"] for result in results)
        )

    def test_generic_stop_type_with_ambiguous_warning_stays_unknown(self):
        group = build_stop_group_candidate(
            "generic_stop",
            stop_type="stop",
            source=STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
            section_role="MULTI_STOP_SECTION",
            warning_codes=["ambiguous_stop_type"],
        )

        result = resolve_stop_type(group)

        self.assertEqual(result["stop_type"], STOP_TYPE_UNKNOWN)
        self.assertIn(TYPE_WARNING_AMBIGUOUS, result["warning_codes"])

    def test_page_order_fallback_is_low_confidence(self):
        group = build_stop_group_candidate(
            "fallback_group",
            page_number=2,
            section_role="PICKUP_SECTION",
        )
        result = infer_stop_sequence(group, [group])

        self.assertEqual(result["sequence"], 1)
        self.assertEqual(result["confidence"], "LOW")
        self.assertIn(SEQUENCE_WARNING_INFERRED, result["warning_codes"])

    def test_delivery_only_not_forced_to_pickup(self):
        group = build_stop_group_candidate(
            "delivery_only",
            stop_type=STOP_TYPE_DELIVERY,
            page_number=1,
            section_role="DELIVERY_SECTION",
        )
        sequenced = assign_stop_sequence_order([group])

        self.assertEqual(sequenced[0]["stop_type"], STOP_TYPE_DELIVERY)
        self.assertEqual(sequenced[0]["stop_sequence"], 1)


if __name__ == "__main__":
    unittest.main()
