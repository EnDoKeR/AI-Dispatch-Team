import unittest

from app.document_ai.layout_artifacts import (
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
)
from app.document_ai.stop_span_extractor import (
    build_layout_line_features,
    build_stop_spans_from_anchors,
    detect_stop_span_anchors,
    detect_stop_span_boundaries,
)


def _features(lines):
    artifact = build_layout_extraction_artifact(
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
    return build_layout_line_features(artifact, include_safe_text=True)


class StopSpanBoundaryTests(unittest.TestCase):
    def test_pickup_span_includes_lines_until_delivery_anchor(self):
        features = _features([
            ("Pickup", "PICKUP_SECTION"),
            ("Fake Pickup Facility", "PICKUP_SECTION"),
            ("Date 01/02/2099", "PICKUP_SECTION"),
            ("Delivery", "DELIVERY_SECTION"),
            ("Fake Delivery Facility", "DELIVERY_SECTION"),
        ])
        anchors = detect_stop_span_anchors(features)
        spans = build_stop_spans_from_anchors(features, anchors)

        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0]["line_ids"], ["l001", "l002", "l003"])
        self.assertEqual(spans[1]["line_ids"], ["l004", "l005"])

    def test_delivery_span_stops_before_payment_boundary(self):
        features = _features([
            ("Deliver To", "DELIVERY_SECTION"),
            ("Fake Delivery Facility", "DELIVERY_SECTION"),
            ("Delivery Date 01/03/2099", "DELIVERY_SECTION"),
            ("Carrier Freight Pay FAKE_AMOUNT", "RATE_SUMMARY"),
        ])
        spans = build_stop_spans_from_anchors(features, detect_stop_span_anchors(features))

        self.assertEqual(spans[0]["line_ids"], ["l001", "l002", "l003"])

    def test_signature_footer_excluded(self):
        features = _features([
            ("PU 1", "PICKUP_SECTION"),
            ("Fake Pickup Facility", "PICKUP_SECTION"),
            ("Signature", "SIGNATURE_BLOCK"),
            ("Please Sign and Return", "SIGNATURE_BLOCK"),
        ])
        spans = build_stop_spans_from_anchors(features, detect_stop_span_anchors(features))

        self.assertEqual(spans[0]["line_ids"], ["l001", "l002"])

    def test_terms_billing_excluded(self):
        features = _features([
            ("SO 2", "DELIVERY_SECTION"),
            ("Fake Delivery Facility", "DELIVERY_SECTION"),
            ("Billing Instructions", "BILLING_INSTRUCTIONS"),
            ("Terms due by 01/04/2099", "LEGAL_TERMS"),
        ])
        spans = build_stop_spans_from_anchors(features, detect_stop_span_anchors(features))

        self.assertEqual(spans[0]["line_ids"], ["l001", "l002"])

    def test_multi_stop_creates_multiple_spans(self):
        features = _features([
            ("PU 1 Fake Origin", "MULTI_STOP_SECTION"),
            ("Date 01/02/2099", "MULTI_STOP_SECTION"),
            ("SO 2 Fake First Destination", "MULTI_STOP_SECTION"),
            ("Date 01/03/2099", "MULTI_STOP_SECTION"),
            ("SO 3 Fake Second Destination", "MULTI_STOP_SECTION"),
            ("Date 01/04/2099", "MULTI_STOP_SECTION"),
        ])
        spans = build_stop_spans_from_anchors(features, detect_stop_span_anchors(features))

        self.assertEqual(len(spans), 3)
        self.assertEqual([span["sequence"] for span in spans], [1, 2, 3])

    def test_ambiguous_generic_stop_spans_low_confidence(self):
        features = _features([
            ("Stop 1", "MULTI_STOP_SECTION"),
            ("Fake Stop A", "MULTI_STOP_SECTION"),
            ("Stop 2", "MULTI_STOP_SECTION"),
            ("Fake Stop B", "MULTI_STOP_SECTION"),
        ])
        spans = build_stop_spans_from_anchors(features, detect_stop_span_anchors(features))

        self.assertEqual(len(spans), 2)
        self.assertIn("ambiguous_generic_stop_anchor", spans[0]["warning_codes"])

    def test_boundary_detector_marks_payment_and_signature(self):
        features = _features([
            ("Payment Summary", "RATE_SUMMARY"),
            ("Signature", "SIGNATURE_BLOCK"),
        ])

        self.assertEqual(len(detect_stop_span_boundaries(features)), 2)


if __name__ == "__main__":
    unittest.main()

