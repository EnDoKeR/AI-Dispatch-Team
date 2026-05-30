import json
import unittest
from pathlib import Path

from app.document_ai.layout_artifacts import (
    build_bounding_box,
    build_layout_extraction_artifact,
    build_layout_page_artifact,
    build_layout_table,
    build_layout_table_cell,
)
from app.document_ai.layout_stop_candidates import generate_layout_stop_candidates
from app.document_ai.ratecon_candidates import (
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_REFERENCE,
    FIELD_UNKNOWN,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_artifacts")


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class LayoutStopCandidateTests(unittest.TestCase):
    def test_mcleod_pu_so_layout_produces_pickup_and_delivery_candidates(self):
        artifact = _load_fixture("fake_mcleod_pu_so_layout.json")

        candidates = generate_layout_stop_candidates(artifact)

        self.assertTrue(any(candidate["field_name"] == FIELD_PICKUP_LOCATION for candidate in candidates))
        self.assertTrue(any(candidate["field_name"] == FIELD_PICKUP_DATE for candidate in candidates))
        self.assertTrue(any(candidate["field_name"] == FIELD_DELIVERY_LOCATION for candidate in candidates))
        self.assertTrue(any(candidate["field_name"] == FIELD_DELIVERY_DATE for candidate in candidates))

    def test_blue_table_pickup_delivery_rows_preserve_table_association(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")

        candidates = generate_layout_stop_candidates(artifact)
        pickup = [candidate for candidate in candidates if candidate["field_name"] == FIELD_PICKUP_LOCATION]
        delivery = [candidate for candidate in candidates if candidate["field_name"] == FIELD_DELIVERY_LOCATION]

        self.assertEqual(pickup[0]["raw_value"], "FAKE ORIGIN ST")
        self.assertEqual(delivery[0]["raw_value"], "FAKE DESTINATION ST")
        self.assertEqual(pickup[0]["layout_table_id"], "P1_T_STOPS")
        self.assertEqual(delivery[0]["layout_table_id"], "P1_T_STOPS")

    def test_carrier_tender_route_details_extracts_dates_and_times(self):
        artifact = _load_fixture("fake_carrier_tender_route_details_layout.json")

        candidates = generate_layout_stop_candidates(artifact)
        values = {candidate["raw_value"] for candidate in candidates}

        self.assertIn("2099-03-03", values)
        self.assertIn("09:00", values)
        self.assertIn("2099-03-04", values)
        self.assertIn("16:00", values)

    def test_multi_stop_order_preserves_multiple_pickups(self):
        artifact = _load_fixture("fake_multi_stop_order_confirmation_layout.json")

        candidates = generate_layout_stop_candidates(artifact)
        pickup_locations = [
            candidate for candidate in candidates if candidate["field_name"] == FIELD_PICKUP_LOCATION
        ]
        stop_refs = [candidate for candidate in candidates if candidate["field_name"] == FIELD_REFERENCE]

        self.assertEqual(len(pickup_locations), 2)
        self.assertGreaterEqual(len(stop_refs), 3)

    def test_ambiguous_stop_type_is_low_confidence(self):
        bbox = build_bounding_box(40, 100, 360, 160, page_number=1)
        table = build_layout_table(
            table_id="T_AMBIG",
            page_number=1,
            bbox=bbox,
            header_rows=[0],
            cells=[
                build_layout_table_cell(0, 0, "Seq", bbox),
                build_layout_table_cell(0, 1, "Location", bbox),
                build_layout_table_cell(0, 2, "Date", bbox),
                build_layout_table_cell(1, 0, "1", bbox),
                build_layout_table_cell(1, 1, "FAKE UNKNOWN STOP ST", bbox),
                build_layout_table_cell(1, 2, "2099-05-01", bbox),
            ],
        )
        artifact = build_layout_extraction_artifact(
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    tables=[table],
                    page_roles=["STOP_DETAILS"],
                    section_roles=["STOP_TABLE"],
                )
            ]
        )

        candidates = generate_layout_stop_candidates(artifact)

        self.assertTrue(any(candidate["field_name"] == FIELD_UNKNOWN for candidate in candidates))
        self.assertTrue(any("stop_type_ambiguous" in candidate["warnings"] for candidate in candidates))
        self.assertFalse(any(candidate["field_name"] == FIELD_PICKUP_LOCATION for candidate in candidates))
        self.assertFalse(any(candidate["field_name"] == FIELD_DELIVERY_LOCATION for candidate in candidates))

    def test_missing_date_is_not_invented(self):
        artifact = _load_fixture("fake_blue_table_ratecon_layout.json")
        artifact["pages"][0]["tables"][1]["cells"] = [
            cell
            for cell in artifact["pages"][0]["tables"][1]["cells"]
            if cell["col_index"] != 3
        ]

        candidates = generate_layout_stop_candidates(artifact)

        self.assertFalse(any(candidate["field_name"] == FIELD_PICKUP_DATE for candidate in candidates))

    def test_continuation_page_delivery_preserved(self):
        artifact = _load_fixture("fake_mcleod_pu_so_layout.json")

        candidates = generate_layout_stop_candidates(artifact)
        delivery = [candidate for candidate in candidates if candidate["field_name"] == FIELD_DELIVERY_LOCATION]

        self.assertEqual(delivery[0]["page_number"], 2)
        self.assertEqual(delivery[0]["layout_section_role"], "DELIVERY_SECTION")


if __name__ == "__main__":
    unittest.main()
