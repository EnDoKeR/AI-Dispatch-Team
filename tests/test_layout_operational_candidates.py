import json
import unittest
from pathlib import Path

from app.document_ai.layout_artifacts import (
    build_bounding_box,
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
    build_layout_table,
    build_layout_table_cell,
)
from app.document_ai.layout_operational_candidates import generate_layout_operational_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_COMMODITY,
    FIELD_EQUIPMENT,
    FIELD_SPECIAL_REQUIREMENT,
    FIELD_WEIGHT,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_artifacts")


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class LayoutOperationalCandidateTests(unittest.TestCase):
    def test_equipment_summary_candidates(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")

        candidates = generate_layout_operational_candidates(artifact)

        self.assertTrue(any(candidate["field_name"] == FIELD_EQUIPMENT for candidate in candidates))
        self.assertTrue(any(candidate["field_name"] == FIELD_WEIGHT for candidate in candidates))
        self.assertTrue(any(candidate["normalized_value"] == "40000" for candidate in candidates))

    def test_commodity_weight_table_candidates(self):
        bbox = build_bounding_box(40, 100, 420, 160, page_number=1)
        table = build_layout_table(
            table_id="T_COMMODITY",
            page_number=1,
            bbox=bbox,
            header_rows=[0],
            cells=[
                build_layout_table_cell(0, 0, "Equipment", bbox),
                build_layout_table_cell(0, 1, "Commodity", bbox),
                build_layout_table_cell(0, 2, "Weight", bbox),
                build_layout_table_cell(1, 0, "Flatbed", bbox),
                build_layout_table_cell(1, 1, "FAKE STEEL", bbox),
                build_layout_table_cell(1, 2, "44000", bbox),
            ],
        )
        artifact = build_layout_extraction_artifact(
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    tables=[table],
                    page_roles=["MAIN_RATECONF"],
                    section_roles=["COMMODITY_WEIGHT"],
                )
            ]
        )

        candidates = generate_layout_operational_candidates(artifact)
        fields = {candidate["field_name"] for candidate in candidates}

        self.assertIn(FIELD_EQUIPMENT, fields)
        self.assertIn(FIELD_COMMODITY, fields)
        self.assertIn(FIELD_WEIGHT, fields)

    def test_special_instructions_candidates(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")

        candidates = generate_layout_operational_candidates(artifact)
        requirement_types = {
            candidate["value_type"]
            for candidate in candidates
            if candidate["field_name"] == FIELD_SPECIAL_REQUIREMENT
        }

        self.assertIn("tracking_required", requirement_types)
        self.assertIn("no_touch", requirement_types)

    def test_tracking_tarp_and_straps_requirements(self):
        line = build_layout_line(
            "L_REQ",
            text_redacted="Special Instructions: tarp required; straps required; tracking required",
            bbox=build_bounding_box(40, 60, 520, 78, page_number=1),
            page_number=1,
            reading_order_index=1,
            section_role="SPECIAL_INSTRUCTIONS",
        )
        artifact = build_layout_extraction_artifact(
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    lines=[line],
                    page_roles=["MAIN_RATECONF"],
                    section_roles=["SPECIAL_INSTRUCTIONS"],
                )
            ]
        )

        candidates = generate_layout_operational_candidates(artifact)
        requirement_types = {candidate["value_type"] for candidate in candidates}

        self.assertIn("tarp_required", requirement_types)
        self.assertIn("straps_required", requirement_types)
        self.assertIn("tracking_required", requirement_types)

    def test_terms_only_requirement_lower_confidence(self):
        line = build_layout_line(
            "L_TERMS",
            text_redacted="Legal Terms: tracking required if broker requests status updates",
            bbox=build_bounding_box(40, 60, 520, 78, page_number=1),
            page_number=1,
            reading_order_index=1,
            section_role="LEGAL_TERMS",
        )
        artifact = build_layout_extraction_artifact(
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    lines=[line],
                    page_roles=["TERMS"],
                    section_roles=["LEGAL_TERMS"],
                )
            ]
        )

        candidates = generate_layout_operational_candidates(artifact)

        self.assertEqual(candidates[0]["confidence"], CANDIDATE_CONFIDENCE_LOW)
        self.assertIn("requirement_from_supplemental_terms", candidates[0]["warnings"])

    def test_no_driver_compatibility_decision_emitted(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")

        text = str(generate_layout_operational_candidates(artifact))

        self.assertNotIn("ACCEPT", text)
        self.assertNotIn("REJECT", text)
        self.assertNotIn("driver_compatible", text)


if __name__ == "__main__":
    unittest.main()
