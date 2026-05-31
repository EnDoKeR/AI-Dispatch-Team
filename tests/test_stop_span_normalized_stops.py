import json
import unittest
from pathlib import Path

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_TYPE_DELIVERY,
    NORMALIZED_STOP_TYPE_PICKUP,
    NORMALIZED_STOP_TYPE_STOP,
)
from app.document_ai.stop_span_extractor import (
    build_layout_line_features,
    build_normalized_stop_set_from_spans,
    build_stop_span_extraction_result,
    build_stop_spans_from_anchors,
    detect_stop_span_anchors,
    extract_stop_span_field_candidates,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "document_ai" / "stop_spans"


def _run_fixture(name):
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    artifact = payload["layout_artifact"]
    features = build_layout_line_features(artifact, include_safe_text=True)
    anchors = detect_stop_span_anchors(features)
    spans = build_stop_spans_from_anchors(features, anchors)
    candidates = []
    for span in spans:
        candidates.extend(extract_stop_span_field_candidates(span, features, artifact))
    result = build_stop_span_extraction_result(
        document_alias="RATECON_FAKE",
        anchors=anchors,
        spans=spans,
        field_candidates=candidates,
        raw_line_count=len(features),
    )
    return payload, result, build_normalized_stop_set_from_spans(result)


class StopSpanNormalizedStopTests(unittest.TestCase):
    def test_tql_fixture_builds_two_normalized_stops(self):
        payload, result, stop_set = _run_fixture("fake_tql_blue_table_lines.json")

        self.assertEqual(result["span_count"], payload["expected_span_count"])
        self.assertEqual(len(stop_set["stops"]), 2)
        self.assertEqual(stop_set["pickup_count"], 1)
        self.assertEqual(stop_set["delivery_count"], 1)

    def test_jay_fixture_builds_two_normalized_stops(self):
        _, _, stop_set = _run_fixture("fake_jay_load_at_deliver_to_lines.json")

        self.assertEqual(len(stop_set["stops"]), 2)

    def test_beemac_fixture_builds_three_normalized_stops(self):
        _, _, stop_set = _run_fixture("fake_beemac_multi_stop_lines.json")

        self.assertEqual(len(stop_set["stops"]), 3)
        self.assertEqual(stop_set["delivery_count"], 2)

    def test_signature_fixture_builds_zero_stops(self):
        _, result, stop_set = _run_fixture("fake_signature_footer_lines.json")

        self.assertEqual(result["span_count"], 0)
        self.assertEqual(stop_set["stops"], [])

    def test_terms_fixture_builds_zero_stops(self):
        _, result, stop_set = _run_fixture("fake_terms_billing_lines.json")

        self.assertEqual(result["anchor_count"], 0)
        self.assertEqual(stop_set["stops"], [])

    def test_ambiguous_fixture_review_required(self):
        _, _, stop_set = _run_fixture("fake_ambiguous_stop_lines.json")

        self.assertEqual(len(stop_set["stops"]), 2)
        self.assertTrue(all(stop["review_required"] for stop in stop_set["stops"]))
        self.assertEqual(
            {stop["stop_type"] for stop in stop_set["stops"]},
            {NORMALIZED_STOP_TYPE_STOP},
        )

    def test_date_fields_resolved_where_present(self):
        _, _, stop_set = _run_fixture("fake_mcleod_pu_so_lines.json")
        date_fields = [
            field
            for stop in stop_set["stops"]
            for field in stop["fields"]
            if field["field_name"] == NORMALIZED_STOP_FIELD_DATE
        ]

        self.assertEqual(
            [field["status"] for field in date_fields],
            [NORMALIZED_STOP_FIELD_STATUS_RESOLVED, NORMALIZED_STOP_FIELD_STATUS_RESOLVED],
        )

    def test_landstar_stop_types_are_pickup_and_delivery(self):
        _, _, stop_set = _run_fixture("fake_landstar_route_details_lines.json")

        self.assertEqual(
            [stop["stop_type"] for stop in stop_set["stops"]],
            [NORMALIZED_STOP_TYPE_PICKUP, NORMALIZED_STOP_TYPE_DELIVERY],
        )

    def test_generic_stop_type_constant_imported_for_coverage(self):
        self.assertEqual(NORMALIZED_STOP_TYPE_STOP, "stop")


if __name__ == "__main__":
    unittest.main()

