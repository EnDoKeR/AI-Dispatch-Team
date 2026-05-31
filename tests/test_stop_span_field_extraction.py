import unittest

from app.document_ai.layout_artifacts import (
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
)
from app.document_ai.stop_span_extractor import (
    STOP_SPAN_FIELD_APPOINTMENT_WINDOW,
    STOP_SPAN_FIELD_DATE,
    STOP_SPAN_FIELD_LOCATION,
    STOP_SPAN_FIELD_NOTES,
    STOP_SPAN_FIELD_REFERENCE,
    STOP_SPAN_FIELD_TIME,
    build_layout_line_features,
    build_stop_spans_from_anchors,
    detect_stop_span_anchors,
    extract_stop_span_field_candidates,
)


def _artifact(lines):
    return build_layout_extraction_artifact(
        pages=[
            build_layout_page_artifact(
                page_number=1,
                lines=[
                    build_layout_line(
                        f"l{index:03d}",
                        text_redacted=text,
                        page_number=1,
                        reading_order_index=index,
                        section_role=section_role,
                    )
                    for index, (text, section_role) in enumerate(lines, start=1)
                ],
            )
        ]
    )


def _span_and_features(lines):
    artifact = _artifact(lines)
    features = build_layout_line_features(artifact, include_safe_text=True)
    spans = build_stop_spans_from_anchors(features, detect_stop_span_anchors(features))
    return artifact, features, spans[0]


class StopSpanFieldExtractionTests(unittest.TestCase):
    def test_tql_pickup_date_time(self):
        artifact, features, span = _span_and_features([
            ("Pick-up Location", "PICKUP_SECTION"),
            ("Fake Pickup Facility", "PICKUP_SECTION"),
            ("PU Date 01/02/2099", "PICKUP_SECTION"),
            ("PU Time 08:00", "PICKUP_SECTION"),
        ])
        candidates = extract_stop_span_field_candidates(span, features, artifact)
        fields = {candidate["field_name"] for candidate in candidates}

        self.assertIn(STOP_SPAN_FIELD_LOCATION, fields)
        self.assertIn(STOP_SPAN_FIELD_DATE, fields)
        self.assertIn(STOP_SPAN_FIELD_TIME, fields)

    def test_tql_delivery_date_time(self):
        artifact, features, span = _span_and_features([
            ("Delivery Location", "DELIVERY_SECTION"),
            ("Fake Delivery Facility", "DELIVERY_SECTION"),
            ("Delivery Date 01/03/2099", "DELIVERY_SECTION"),
            ("Delivery Time 13:00", "DELIVERY_SECTION"),
        ])
        candidates = extract_stop_span_field_candidates(span, features, artifact)
        fields = [candidate["field_name"] for candidate in candidates]

        self.assertIn(STOP_SPAN_FIELD_DATE, fields)
        self.assertIn(STOP_SPAN_FIELD_TIME, fields)

    def test_jay_earliest_latest_dates(self):
        artifact, features, span = _span_and_features([
            ("Load At", "PICKUP_SECTION"),
            ("Fake Origin Warehouse", "PICKUP_SECTION"),
            ("Earliest Date 02/04/2099", "PICKUP_SECTION"),
            ("Latest Date 02/04/2099", "PICKUP_SECTION"),
        ])
        candidates = extract_stop_span_field_candidates(span, features, artifact)
        date_candidates = [
            candidate
            for candidate in candidates
            if candidate["field_name"] == STOP_SPAN_FIELD_DATE
        ]

        self.assertEqual(len(date_candidates), 2)

    def test_pu_so_date_lines(self):
        artifact, features, span = _span_and_features([
            ("PU 1", "PICKUP_SECTION"),
            ("Fake Pickup Site", "PICKUP_SECTION"),
            ("Appt 03/06/2099 07:30", "PICKUP_SECTION"),
        ])
        fields = {
            candidate["field_name"]
            for candidate in extract_stop_span_field_candidates(span, features, artifact)
        }

        self.assertIn(STOP_SPAN_FIELD_DATE, fields)
        self.assertIn(STOP_SPAN_FIELD_TIME, fields)

    def test_landstar_target_window(self):
        artifact, features, span = _span_and_features([
            ("Stop #1 Pickup Fake Origin", "MULTI_STOP_SECTION"),
            ("Target Window 05/11/2099 08:00-11:00", "MULTI_STOP_SECTION"),
        ])
        fields = {
            candidate["field_name"]
            for candidate in extract_stop_span_field_candidates(span, features, artifact)
        }

        self.assertIn(STOP_SPAN_FIELD_APPOINTMENT_WINDOW, fields)

    def test_spi_shipping_receiving_hours_notes(self):
        artifact, features, span = _span_and_features([
            ("Shipper Pickup Stop 1", "PICKUP_SECTION"),
            ("Fake Boxed Shipper", "PICKUP_SECTION"),
            ("Shipping 06/13/2099 07:00-09:00", "PICKUP_SECTION"),
        ])
        fields = {
            candidate["field_name"]
            for candidate in extract_stop_span_field_candidates(span, features, artifact)
        }

        self.assertIn(STOP_SPAN_FIELD_NOTES, fields)

    def test_reference_candidate(self):
        artifact, features, span = _span_and_features([
            ("Pickup", "PICKUP_SECTION"),
            ("Fake Pickup Facility", "PICKUP_SECTION"),
            ("Appointment Ref FAKE123", "PICKUP_SECTION"),
        ])
        fields = {
            candidate["field_name"]
            for candidate in extract_stop_span_field_candidates(span, features, artifact)
        }

        self.assertIn(STOP_SPAN_FIELD_REFERENCE, fields)

    def test_terms_date_ignored(self):
        artifact, features, span = _span_and_features([
            ("Delivery", "DELIVERY_SECTION"),
            ("Fake Delivery Facility", "DELIVERY_SECTION"),
            ("Terms due by 08/20/2099", "LEGAL_TERMS"),
        ])
        candidates = extract_stop_span_field_candidates(span, features, artifact)

        self.assertEqual(
            [
                candidate
                for candidate in candidates
                if candidate["field_name"] == STOP_SPAN_FIELD_DATE
            ],
            [],
        )

    def test_missing_date_stays_missing_at_candidate_stage(self):
        artifact, features, span = _span_and_features([
            ("Pickup", "PICKUP_SECTION"),
            ("Fake Pickup Facility", "PICKUP_SECTION"),
        ])
        fields = {
            candidate["field_name"]
            for candidate in extract_stop_span_field_candidates(span, features, artifact)
        }

        self.assertNotIn(STOP_SPAN_FIELD_DATE, fields)


if __name__ == "__main__":
    unittest.main()

