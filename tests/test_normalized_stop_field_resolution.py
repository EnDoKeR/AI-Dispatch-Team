import unittest

from app.document_ai.layout_artifacts import (
    build_bounding_box,
    build_layout_extraction_artifact,
    build_layout_page_artifact,
    build_layout_table,
    build_layout_table_cell,
)
from app.document_ai.private_measurement_pipeline import _layout_fusion_fields
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_TIME,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_TIME,
    SOURCE_SYNTHETIC_FIXTURE,
    build_field_candidate,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_MISSING,
    build_field_resolution,
    build_ratecon_field_resolution_result,
)


def _candidate(field_name, value):
    return build_field_candidate(
        field_name=field_name,
        raw_value=value,
        normalized_value=value,
        confidence=CANDIDATE_CONFIDENCE_HIGH,
        source=SOURCE_SYNTHETIC_FIXTURE,
        candidate_id=f"{field_name}_layout_candidate",
    )


def _stop_table_artifact():
    bbox = build_bounding_box(10, 10, 300, 140, page_number=1)
    cells = [
        build_layout_table_cell(0, 0, "Type", bbox=bbox),
        build_layout_table_cell(0, 1, "Location", bbox=bbox),
        build_layout_table_cell(0, 2, "Date", bbox=bbox),
        build_layout_table_cell(0, 3, "Time", bbox=bbox),
        build_layout_table_cell(1, 0, "Pickup", bbox=bbox),
        build_layout_table_cell(1, 1, "FAKE_PICKUP_CITY_ST", bbox=bbox),
        build_layout_table_cell(1, 2, "2026-01-01", bbox=bbox),
        build_layout_table_cell(1, 3, "08:00", bbox=bbox),
        build_layout_table_cell(2, 0, "Delivery", bbox=bbox),
        build_layout_table_cell(2, 1, "FAKE_DELIVERY_CITY_ST", bbox=bbox),
        build_layout_table_cell(2, 2, "2026-01-02", bbox=bbox),
        build_layout_table_cell(2, 3, "09:00", bbox=bbox),
    ]
    table = build_layout_table(
        table_id="T_STOP_RESOLUTION",
        page_number=1,
        bbox=bbox,
        cells=cells,
        header_rows=[0],
    )
    page = build_layout_page_artifact(
        page_number=1,
        tables=[table],
        page_roles=["MAIN_RATECONF"],
        section_roles=["STOP_TABLE"],
    )
    return build_layout_extraction_artifact(pages=[page])


class NormalizedStopFieldResolutionTests(unittest.TestCase):
    def test_normalized_pickup_delivery_fields_allow_layout_candidates_into_resolution(self):
        layout_candidates = [
            _candidate(FIELD_PICKUP_LOCATION, "FAKE_PICKUP_CITY_ST"),
            _candidate(FIELD_PICKUP_DATE, "2026-01-01"),
            _candidate(FIELD_PICKUP_TIME, "08:00"),
            _candidate(FIELD_DELIVERY_LOCATION, "FAKE_DELIVERY_CITY_ST"),
            _candidate(FIELD_DELIVERY_DATE, "2026-01-02"),
            _candidate(FIELD_DELIVERY_TIME, "09:00"),
        ]
        baseline = build_ratecon_field_resolution_result(
            resolutions=[
                build_field_resolution(field, FIELD_RESOLUTION_STATUS_MISSING)
                for field in [
                    FIELD_PICKUP_LOCATION,
                    FIELD_PICKUP_DATE,
                    FIELD_PICKUP_TIME,
                    FIELD_DELIVERY_LOCATION,
                    FIELD_DELIVERY_DATE,
                    FIELD_DELIVERY_TIME,
                ]
            ]
        )

        fusion = _layout_fusion_fields(
            text_candidate_result={"candidates": []},
            layout_fields={
                "layout_provider_status": "success",
                "layout_candidate_result": {"candidates": layout_candidates},
                "layout_artifact": _stop_table_artifact(),
            },
            baseline_resolution_result=baseline,
            document_type="RATE_CONFIRMATION",
            classification_result={
                "document_type": "RATE_CONFIRMATION",
                "normal_load_movement": True,
            },
            enable_layout_fusion=True,
        )

        fused_fields = {
            candidate["field_name"]
            for candidate in fusion["fused_candidate_result"]["candidates"]
        }
        self.assertIn(FIELD_PICKUP_LOCATION, fusion["fusion_improved_fields"])
        self.assertIn(FIELD_DELIVERY_DATE, fusion["fusion_improved_fields"])
        self.assertIn(FIELD_PICKUP_LOCATION, fused_fields)
        self.assertIn(FIELD_DELIVERY_DATE, fused_fields)
        self.assertEqual(fusion["normalized_stop_set"]["pickup_count"], 1)
        self.assertEqual(fusion["normalized_stop_set"]["delivery_count"], 1)

    def test_multi_stop_extra_stops_preserved_in_stop_set_metadata(self):
        fusion = _layout_fusion_fields(
            text_candidate_result={"candidates": []},
            layout_fields={
                "layout_provider_status": "success",
                "layout_candidate_result": {"candidates": []},
                "layout_artifact": _stop_table_artifact(),
            },
            baseline_resolution_result=build_ratecon_field_resolution_result(),
            document_type="RATE_CONFIRMATION",
            classification_result={
                "document_type": "RATE_CONFIRMATION",
                "normal_load_movement": True,
            },
            enable_layout_fusion=True,
        )

        self.assertEqual(fusion["normalized_stop_flat_fields"]["extra_stop_count"], 0)
        self.assertEqual(fusion["normalized_stop_set"]["review_required_stop_count"], 0)


if __name__ == "__main__":
    unittest.main()
