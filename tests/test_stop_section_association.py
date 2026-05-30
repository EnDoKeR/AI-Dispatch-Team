import json
import unittest
from pathlib import Path

from app.document_ai.stop_association import (
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_FIELD_TIME,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    STOP_TYPE_STOP,
    associate_nearby_date_time_to_stop,
    build_stop_groups_from_layout_sections,
    classify_stop_section,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_association")


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class StopSectionAssociationTests(unittest.TestCase):
    def test_mcleod_pu_so_sections_are_grouped_across_pages(self):
        artifact = _load_fixture("fake_layout_mcleod_pu_so_continuation.json")

        result = build_stop_groups_from_layout_sections(artifact)

        self.assertEqual(len(result["stop_groups"]), 2)
        self.assertEqual(result["stop_groups"][0]["stop_type"], STOP_TYPE_PICKUP)
        self.assertEqual(result["stop_groups"][1]["stop_type"], STOP_TYPE_DELIVERY)
        field_sets = [
            {candidate["field_name"] for candidate in group["field_candidates"]}
            for group in result["stop_groups"]
        ]
        self.assertIn(STOP_FIELD_DATE, field_sets[0])
        self.assertIn(STOP_FIELD_TIME, field_sets[1])

    def test_pickup_section_date_time_association(self):
        nearby = associate_nearby_date_time_to_stop("Pickup FAKE ORIGIN 2099-02-01 07:30")

        self.assertTrue(nearby["has_date"])
        self.assertTrue(nearby["has_time"])

    def test_header_date_is_not_used_as_stop_date(self):
        artifact = {
            "pages": [
                {
                    "page_number": 1,
                    "lines": [
                        {
                            "line_id": "header_date",
                            "text_redacted": "Tender Date 2099-01-01",
                            "section_role": "HEADER",
                        },
                        {
                            "line_id": "pickup_without_date",
                            "text_redacted": "Pickup FAKE ORIGIN ONLY",
                            "section_role": "PICKUP_SECTION",
                        },
                    ],
                    "blocks": [
                        {
                            "block_id": "pickup_block",
                            "block_type": "text",
                            "section_role": "PICKUP_SECTION",
                            "line_ids": ["pickup_without_date"],
                        }
                    ],
                }
            ]
        }

        result = build_stop_groups_from_layout_sections(artifact)

        fields = {
            candidate["field_name"]
            for group in result["stop_groups"]
            for candidate in group["field_candidates"]
        }
        self.assertIn(STOP_FIELD_LOCATION, fields)
        self.assertNotIn(STOP_FIELD_DATE, fields)

    def test_terms_and_signature_sections_are_ignored(self):
        artifact = _load_fixture("fake_layout_terms_money_noise.json")

        result = build_stop_groups_from_layout_sections(artifact)

        self.assertEqual(result["stop_groups"], [])

    def test_ambiguous_multi_stop_section_routes_review(self):
        classification = classify_stop_section(
            {
                "section_role": "MULTI_STOP_SECTION",
                "text_redacted": "Stop details appear in columns",
            }
        )

        self.assertEqual(classification["stop_type"], STOP_TYPE_STOP)
        self.assertIn("ambiguous_stop_type", classification["warning_codes"])

    def test_provider_style_lines_produce_stop_groups(self):
        artifact = {
            "pages": [
                {
                    "page_number": 1,
                    "lines": [
                        {
                            "line_id": "line_1",
                            "text_redacted": "PU FAKE ORIGIN <DATE> <TIME>",
                            "page_number": 1,
                        },
                        {
                            "line_id": "line_2",
                            "text_redacted": "SO FAKE DEST <DATE> <TIME>",
                            "page_number": 1,
                        },
                    ],
                    "blocks": [],
                }
            ]
        }

        result = build_stop_groups_from_layout_sections(artifact)

        self.assertEqual(len(result["stop_groups"]), 2)
        self.assertEqual(result["stop_groups"][0]["stop_type"], STOP_TYPE_PICKUP)
        self.assertEqual(result["stop_groups"][1]["stop_type"], STOP_TYPE_DELIVERY)
        field_sets = [
            {candidate["field_name"] for candidate in group["field_candidates"]}
            for group in result["stop_groups"]
        ]
        self.assertIn(STOP_FIELD_DATE, field_sets[0])
        self.assertIn(STOP_FIELD_TIME, field_sets[1])


if __name__ == "__main__":
    unittest.main()
