import json
import unittest
from pathlib import Path

from app.document_ai.stop_span_extractor import (
    STOP_SPAN_FIELD_DATE,
    build_layout_line_features,
    build_stop_spans_from_anchors,
    detect_stop_span_anchors,
    extract_stop_span_field_candidates,
)


FIXTURE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "document_ai"
    / "candidate_coverage"
    / "stop_span_date"
)


def _run_fixture(name):
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    artifact = payload["layout_artifact"]
    features = build_layout_line_features(artifact, include_safe_text=True)
    anchors = detect_stop_span_anchors(features)
    spans = build_stop_spans_from_anchors(features, anchors)
    candidates = []
    for span in spans:
        candidates.extend(extract_stop_span_field_candidates(span, features, artifact))
    return payload, spans, candidates


class CandidateCoverageStopSpanDateGenerationTests(unittest.TestCase):
    def test_table_row_stop_dates_generate_date_candidates(self):
        fixture_names = [
            "fake_tql_date_columns_inside_stop_span.json",
            "fake_mcleod_pu_so_right_side_dates.json",
            "fake_landstar_target_window_lines.json",
            "fake_integrity_shipping_receiving_hours.json",
        ]

        for name in fixture_names:
            payload, spans, candidates = _run_fixture(name)
            date_candidates = [
                candidate
                for candidate in candidates
                if candidate["field_name"] == STOP_SPAN_FIELD_DATE
            ]
            with self.subTest(name=name):
                self.assertEqual(len(spans), payload["expected_span_count"])
                self.assertEqual(
                    len(date_candidates),
                    payload["expected_date_candidates"],
                )
                self.assertTrue(
                    all(
                        candidate["source"] == "layout_table_row"
                        for candidate in date_candidates
                    )
                )
                self.assertNotIn("raw_value", json.dumps(date_candidates))

    def test_header_and_terms_table_dates_are_ignored(self):
        fixture_names = [
            "fake_header_date_outside_span_ignored.json",
            "fake_terms_date_inside_billing_ignored.json",
        ]

        for name in fixture_names:
            payload, _, candidates = _run_fixture(name)
            date_candidates = [
                candidate
                for candidate in candidates
                if candidate["field_name"] == STOP_SPAN_FIELD_DATE
            ]
            with self.subTest(name=name):
                self.assertEqual(
                    len(date_candidates),
                    payload["expected_date_candidates"],
                )


if __name__ == "__main__":
    unittest.main()
