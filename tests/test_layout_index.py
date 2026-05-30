import json
import unittest
from pathlib import Path

from app.document_ai.layout_artifacts import (
    build_bounding_box,
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
    build_layout_word,
)
from app.document_ai.layout_index import (
    build_layout_index,
    find_lines_near_bbox,
    find_words_in_bbox,
    get_below_label_candidates,
    get_blocks_by_section_role,
    get_lines_by_page,
    get_right_of_label_candidates,
    get_same_row_candidates,
    get_tables_by_page,
    group_lines_by_vertical_gap,
    sort_lines_reading_order,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_artifacts")


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class LayoutIndexTests(unittest.TestCase):
    def test_reading_order_sorting(self):
        lines = [
            build_layout_line("L3", bbox=build_bounding_box(10, 50, 100, 60, page_number=1), page_number=1, reading_order_index=3),
            build_layout_line("L1", bbox=build_bounding_box(10, 10, 100, 20, page_number=1), page_number=1, reading_order_index=1),
            build_layout_line("L2", bbox=build_bounding_box(10, 30, 100, 40, page_number=1), page_number=1, reading_order_index=2),
        ]

        self.assertEqual([line["line_id"] for line in sort_lines_reading_order(lines)], ["L1", "L2", "L3"])

    def test_same_row_and_right_of_label_candidates(self):
        label = build_layout_line(
            "L_LABEL",
            text_redacted="Rate:",
            bbox=build_bounding_box(40, 40, 100, 58, page_number=1),
            page_number=1,
            reading_order_index=1,
        )
        value = build_layout_line(
            "L_VALUE",
            text_redacted="$2800.00",
            bbox=build_bounding_box(120, 40, 220, 58, page_number=1),
            page_number=1,
            reading_order_index=2,
        )
        other = build_layout_line(
            "L_OTHER",
            text_redacted="Other",
            bbox=build_bounding_box(40, 90, 100, 108, page_number=1),
            page_number=1,
            reading_order_index=3,
        )
        artifact = build_layout_extraction_artifact(
            pages=[build_layout_page_artifact(page_number=1, lines=[label, value, other])]
        )
        index = build_layout_index(artifact)

        self.assertEqual([line["line_id"] for line in get_same_row_candidates(index, label)], ["L_VALUE"])
        self.assertEqual([line["line_id"] for line in get_right_of_label_candidates(index, label)], ["L_VALUE"])

    def test_below_label_candidates(self):
        label = build_layout_line(
            "L_LABEL",
            text_redacted="Pickup:",
            bbox=build_bounding_box(40, 40, 160, 58, page_number=1),
            page_number=1,
            reading_order_index=1,
        )
        value = build_layout_line(
            "L_VALUE",
            text_redacted="FAKE ORIGIN ST",
            bbox=build_bounding_box(50, 66, 260, 84, page_number=1),
            page_number=1,
            reading_order_index=2,
        )
        artifact = build_layout_extraction_artifact(
            pages=[build_layout_page_artifact(page_number=1, lines=[label, value])]
        )
        index = build_layout_index(artifact)

        self.assertEqual([line["line_id"] for line in get_below_label_candidates(index, label)], ["L_VALUE"])

    def test_words_in_bbox(self):
        word_inside = build_layout_word(
            text="Rate",
            bbox=build_bounding_box(50, 50, 80, 60, page_number=1),
        )
        word_outside = build_layout_word(
            text="Outside",
            bbox=build_bounding_box(300, 300, 360, 320, page_number=1),
        )
        artifact = build_layout_extraction_artifact(
            pages=[build_layout_page_artifact(page_number=1, words=[word_inside, word_outside])]
        )
        index = build_layout_index(artifact)

        matches = find_words_in_bbox(index, build_bounding_box(40, 40, 120, 80, page_number=1))

        self.assertEqual([word["text"] for word in matches], ["Rate"])

    def test_table_and_section_lookup_from_synthetic_fixture(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")
        index = build_layout_index(artifact)

        self.assertEqual(len(get_tables_by_page(index, 1)), 2)
        self.assertEqual(len(get_blocks_by_section_role(index, "STOP_TABLE")), 1)
        self.assertGreaterEqual(len(get_lines_by_page(index, 1)), 1)

    def test_lines_near_bbox_and_vertical_groups(self):
        artifact = _load_fixture("fake_mcleod_pu_so_layout.json")
        index = build_layout_index(artifact)
        target = build_bounding_box(40, 130, 90, 148, page_number=1)

        nearby = find_lines_near_bbox(index, target, max_distance=35)
        groups = group_lines_by_vertical_gap(get_lines_by_page(index, 1), gap_threshold=40)

        self.assertTrue(any(line["line_id"] == "P1_L3" for line in nearby))
        self.assertGreaterEqual(len(groups), 2)


if __name__ == "__main__":
    unittest.main()
