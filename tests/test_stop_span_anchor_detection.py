import unittest

from app.document_ai.layout_artifacts import (
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
)
from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_TYPE_DELIVERY,
    NORMALIZED_STOP_TYPE_PICKUP,
    NORMALIZED_STOP_TYPE_STOP,
)
from app.document_ai.ratecon_candidates import CANDIDATE_CONFIDENCE_MEDIUM
from app.document_ai.stop_span_extractor import (
    STOP_SPAN_ANCHOR_TYPE_DELIVER_TO,
    STOP_SPAN_ANCHOR_TYPE_PU,
    STOP_SPAN_ANCHOR_TYPE_STOP,
    build_layout_line_features,
    classify_anchor_type,
    detect_stop_span_anchors,
    score_stop_anchor,
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


class StopSpanAnchorDetectionTests(unittest.TestCase):
    def test_tql_pickup_delivery_anchors(self):
        features = build_layout_line_features(
            _artifact([
                ("Pick-up Location", "STOP_TABLE"),
                ("Delivery Location", "STOP_TABLE"),
            ]),
            include_safe_text=True,
        )
        anchors = detect_stop_span_anchors(features)

        self.assertEqual(len(anchors), 2)
        self.assertEqual(anchors[0]["stop_type"], NORMALIZED_STOP_TYPE_PICKUP)
        self.assertEqual(anchors[1]["stop_type"], NORMALIZED_STOP_TYPE_DELIVERY)

    def test_jay_load_at_deliver_to_anchors(self):
        features = build_layout_line_features(
            _artifact([
                ("Load At", "PICKUP_SECTION"),
                ("Deliver To", "DELIVERY_SECTION"),
            ]),
            include_safe_text=True,
        )

        self.assertEqual(classify_anchor_type(features[1]), STOP_SPAN_ANCHOR_TYPE_DELIVER_TO)
        self.assertEqual(len(detect_stop_span_anchors(features)), 2)

    def test_pu_so_anchors(self):
        features = build_layout_line_features(
            _artifact([
                ("PU 1", "PICKUP_SECTION"),
                ("SO 2", "DELIVERY_SECTION"),
            ]),
            include_safe_text=True,
        )

        self.assertEqual(classify_anchor_type(features[0]), STOP_SPAN_ANCHOR_TYPE_PU)
        self.assertEqual(len(detect_stop_span_anchors(features)), 2)

    def test_generic_stop_anchor_is_not_overclassified(self):
        features = build_layout_line_features(
            _artifact([("Stop #1", "MULTI_STOP_SECTION")]),
            include_safe_text=True,
        )
        anchors = detect_stop_span_anchors(features)

        self.assertEqual(anchors[0]["anchor_type"], STOP_SPAN_ANCHOR_TYPE_STOP)
        self.assertEqual(anchors[0]["stop_type"], NORMALIZED_STOP_TYPE_STOP)
        self.assertIn("ambiguous_generic_stop_anchor", anchors[0]["warning_codes"])

    def test_signature_terms_ignored(self):
        features = build_layout_line_features(
            _artifact([
                ("Signature", "SIGNATURE_BLOCK"),
                ("Billing Instructions", "BILLING_INSTRUCTIONS"),
            ]),
            include_safe_text=True,
        )

        self.assertEqual(detect_stop_span_anchors(features), [])

    def test_ambiguous_anchor_low_confidence(self):
        features = build_layout_line_features(
            _artifact([("Stop 1", "MULTI_STOP_SECTION")]),
            include_safe_text=True,
        )

        self.assertEqual(score_stop_anchor(features[0]), CANDIDATE_CONFIDENCE_MEDIUM)


if __name__ == "__main__":
    unittest.main()
