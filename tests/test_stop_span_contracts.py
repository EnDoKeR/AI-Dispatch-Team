import json
import unittest

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_TYPE_DELIVERY,
    NORMALIZED_STOP_TYPE_PICKUP,
)
from app.document_ai.ratecon_candidates import CANDIDATE_CONFIDENCE_HIGH
from app.document_ai.stop_span_extractor import (
    STOP_SPAN_EXTRACTOR_VERSION,
    STOP_SPAN_FIELD_DATE,
    STOP_SPAN_FIELD_LOCATION,
    STOP_SPAN_SOURCE_LAYOUT_LINE,
    STOP_SPAN_ANCHOR_TYPE_PICKUP,
    build_stop_span,
    build_stop_span_anchor,
    build_stop_span_extraction_result,
    build_stop_span_field_candidate,
)


class StopSpanContractTests(unittest.TestCase):
    def test_create_anchor(self):
        anchor = build_stop_span_anchor(
            anchor_id="anchor_001",
            anchor_type=STOP_SPAN_ANCHOR_TYPE_PICKUP,
            page_number=1,
            line_id="line_001",
            label_category="pickup",
            confidence=CANDIDATE_CONFIDENCE_HIGH,
        )

        self.assertEqual(anchor["anchor_type"], STOP_SPAN_ANCHOR_TYPE_PICKUP)
        self.assertEqual(anchor["page_number"], 1)
        self.assertEqual(anchor["line_id"], "line_001")

    def test_create_span(self):
        anchor = build_stop_span_anchor(
            anchor_id="anchor_002",
            anchor_type="delivery",
            page_number=2,
        )
        span = build_stop_span(
            span_id="span_002",
            anchor=anchor,
            page_number=2,
            line_ids=["line_010", "line_011"],
            stop_type=NORMALIZED_STOP_TYPE_DELIVERY,
            sequence=2,
        )

        self.assertEqual(span["stop_type"], NORMALIZED_STOP_TYPE_DELIVERY)
        self.assertEqual(span["sequence"], 2)
        self.assertEqual(span["line_ids"], ["line_010", "line_011"])

    def test_create_field_candidate(self):
        candidate = build_stop_span_field_candidate(
            span_id="span_001",
            field_name=STOP_SPAN_FIELD_DATE,
            candidate_id="span_001_date",
            evidence_ref={"line_id": "line_003", "evidence_type": "layout_line"},
            source=STOP_SPAN_SOURCE_LAYOUT_LINE,
        )

        self.assertEqual(candidate["field_name"], STOP_SPAN_FIELD_DATE)
        self.assertEqual(candidate["source"], STOP_SPAN_SOURCE_LAYOUT_LINE)
        self.assertNotIn("raw_value", candidate)

    def test_serialize_result(self):
        anchor = build_stop_span_anchor("anchor_001", "pickup", page_number=1)
        span = build_stop_span(
            "span_001",
            anchor=anchor,
            stop_type=NORMALIZED_STOP_TYPE_PICKUP,
            line_ids=["line_001", "line_002"],
        )
        candidate = build_stop_span_field_candidate(
            "span_001",
            STOP_SPAN_FIELD_LOCATION,
            "span_001_location",
        )
        result = build_stop_span_extraction_result(
            document_alias="RATECON_001",
            anchors=[anchor],
            spans=[span],
            field_candidates=[candidate],
            raw_line_count=8,
        )
        payload = json.loads(json.dumps(result, sort_keys=True))

        self.assertEqual(payload["extractor_version"], STOP_SPAN_EXTRACTOR_VERSION)
        self.assertEqual(payload["anchor_count"], 1)
        self.assertEqual(payload["span_count"], 1)
        self.assertFalse(payload["passthrough_detected"])

    def test_result_requires_no_private_text(self):
        result = build_stop_span_extraction_result(raw_line_count=0)

        self.assertFalse(result["raw_text_included"])
        self.assertTrue(result["private_values_redacted"])
        self.assertNotIn("raw_text", result)
        self.assertNotIn("filename", result)


if __name__ == "__main__":
    unittest.main()

