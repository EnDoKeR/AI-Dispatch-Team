import json
import unittest
from pathlib import Path

from app.document_ai.layout_artifacts import (
    build_bounding_box,
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
)
from app.document_ai.layout_proximity import (
    PROXIMITY_BELOW_LABEL,
    PROXIMITY_SAME_ROW_RIGHT,
    PROXIMITY_SECTION_FOLLOWING,
    PROXIMITY_TABLE_ROW,
    detect_label_columns_in_table,
    detect_value_cells_for_label,
    find_label_value_pairs,
    score_label_value_pair,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_artifacts")


class LayoutProximityTests(unittest.TestCase):
    def test_same_row_label_value(self):
        label = build_layout_line(
            "L_LABEL",
            text_redacted="Rate",
            bbox=build_bounding_box(40, 40, 90, 58, page_number=1),
            page_number=1,
            reading_order_index=1,
            section_role="RATE_SUMMARY",
        )
        value = build_layout_line(
            "L_VALUE",
            text_redacted="$2800.00",
            bbox=build_bounding_box(120, 40, 220, 58, page_number=1),
            page_number=1,
            reading_order_index=2,
            section_role="RATE_SUMMARY",
        )
        artifact = build_layout_extraction_artifact(
            pages=[build_layout_page_artifact(page_number=1, lines=[label, value])]
        )

        pairs = find_label_value_pairs(artifact, {"rate": ["Rate"]})

        self.assertEqual(pairs[0]["proximity_type"], PROXIMITY_SAME_ROW_RIGHT)
        self.assertEqual(pairs[0]["value_text_redacted"], "$2800.00")
        self.assertEqual(pairs[0]["source_field"], "rate")
        self.assertIn(pairs[0]["confidence"], {"HIGH", "MEDIUM"})

    def test_below_label_value(self):
        label = build_layout_line(
            "L_LABEL",
            text_redacted="Pickup Location",
            bbox=build_bounding_box(40, 40, 180, 58, page_number=1),
            page_number=1,
            reading_order_index=1,
            section_role="PICKUP_SECTION",
        )
        value = build_layout_line(
            "L_VALUE",
            text_redacted="FAKE ORIGIN ST",
            bbox=build_bounding_box(50, 70, 240, 88, page_number=1),
            page_number=1,
            reading_order_index=2,
            section_role="PICKUP_SECTION",
        )
        artifact = build_layout_extraction_artifact(
            pages=[build_layout_page_artifact(page_number=1, lines=[label, value])]
        )

        pairs = find_label_value_pairs(artifact, {"pickup_location": ["Pickup Location"]})

        self.assertEqual(pairs[0]["proximity_type"], PROXIMITY_BELOW_LABEL)
        self.assertEqual(pairs[0]["value_text_redacted"], "FAKE ORIGIN ST")

    def test_table_row_label_value(self):
        artifact = json.loads((FIXTURE_DIR / "fake_blue_table_ratecon_layout.json").read_text(encoding="utf-8"))

        pairs = find_label_value_pairs(artifact, {"rate": ["Total Carrier Pay"]})

        table_pairs = [pair for pair in pairs if pair["proximity_type"] == PROXIMITY_TABLE_ROW]
        self.assertEqual(table_pairs[0]["value_text_redacted"], "$2800.00")
        self.assertEqual(table_pairs[0]["evidence_ref"]["table_id"], "P1_T_RATE")

    def test_section_following_value(self):
        label = build_layout_line(
            "L_LABEL",
            text_redacted="Payment Notes",
            bbox=build_bounding_box(40, 40, 180, 58, page_number=1),
            page_number=1,
            reading_order_index=1,
            section_role="PAYMENT_TERMS",
        )
        value = build_layout_line(
            "L_VALUE",
            text_redacted="Quick pay available",
            bbox=build_bounding_box(50, 70, 260, 88, page_number=1),
            page_number=1,
            reading_order_index=2,
            section_role="QUICK_PAY",
        )
        artifact = build_layout_extraction_artifact(
            pages=[build_layout_page_artifact(page_number=1, lines=[label, value])]
        )

        pairs = find_label_value_pairs(artifact, {"payment_terms": ["Payment Notes"]})

        self.assertEqual(pairs[0]["proximity_type"], PROXIMITY_SECTION_FOLLOWING)

    def test_ambiguous_multiple_values_lower_confidence(self):
        label = build_layout_line(
            "L_LABEL",
            text_redacted="Rate",
            bbox=build_bounding_box(40, 40, 90, 58, page_number=1),
            page_number=1,
            reading_order_index=1,
            section_role="RATE_SUMMARY",
        )
        value_one = build_layout_line(
            "L_VALUE_1",
            text_redacted="$2800.00",
            bbox=build_bounding_box(120, 40, 220, 58, page_number=1),
            page_number=1,
            reading_order_index=2,
            section_role="RATE_SUMMARY",
        )
        value_two = build_layout_line(
            "L_VALUE_2",
            text_redacted="$3000.00",
            bbox=build_bounding_box(240, 40, 330, 58, page_number=1),
            page_number=1,
            reading_order_index=3,
            section_role="RATE_SUMMARY",
        )
        artifact = build_layout_extraction_artifact(
            pages=[build_layout_page_artifact(page_number=1, lines=[label, value_one, value_two])]
        )

        pairs = find_label_value_pairs(artifact, {"rate": ["Rate"]})

        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(pair["confidence"] in {"MEDIUM", "LOW"} for pair in pairs))

    def test_table_detection_helpers(self):
        artifact = json.loads((FIXTURE_DIR / "fake_blue_table_ratecon_layout.json").read_text(encoding="utf-8"))
        table = artifact["pages"][0]["tables"][0]

        labels = detect_label_columns_in_table(table, {"rate": ["Total Carrier Pay"]})
        values = detect_value_cells_for_label(table, labels[0]["cell"])

        self.assertEqual(labels[0]["source_field"], "rate")
        self.assertEqual(values[0]["text_redacted"], "$2800.00")

    def test_score_decreases_with_distance_and_ambiguity(self):
        near = score_label_value_pair(
            PROXIMITY_SAME_ROW_RIGHT,
            {"x0": 0, "y0": 0, "x1": 40, "y1": 20},
            {"x0": 45, "y0": 0, "x1": 100, "y1": 20},
        )
        far_ambiguous = score_label_value_pair(
            PROXIMITY_SAME_ROW_RIGHT,
            {"x0": 0, "y0": 0, "x1": 40, "y1": 20},
            {"x0": 400, "y0": 0, "x1": 500, "y1": 20},
            ambiguous=True,
        )

        self.assertGreater(near["distance_score"], far_ambiguous["distance_score"])


if __name__ == "__main__":
    unittest.main()
