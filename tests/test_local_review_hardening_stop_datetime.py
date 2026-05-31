import json
import unittest
from pathlib import Path

from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_APPOINTMENT_WINDOW,
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_TIME,
)
from app.document_ai.stop_span_extractor import (
    build_layout_line_features,
    build_normalized_stop_set_from_spans,
    build_stop_span_extraction_result,
    build_stop_spans_from_anchors,
    detect_stop_span_anchors,
    extract_stop_span_field_candidates,
)


FIXTURE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "document_ai"
    / "local_review_hardening"
    / "stop_datetime"
)


def _load_fixture(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _run_fixture(path):
    payload = _load_fixture(path)
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


def _resolved_field_count(stop_set, field_name):
    return sum(
        1
        for stop in stop_set["stops"]
        for field in stop["fields"]
        if field["field_name"] == field_name
        and field["status"] == NORMALIZED_STOP_FIELD_STATUS_RESOLVED
    )


class LocalReviewHardeningStopDatetimeTests(unittest.TestCase):
    def test_selected_datetime_patterns_resolve_expected_date_and_time_counts(self):
        for path in FIXTURE_DIR.glob("*.json"):
            payload, result, stop_set = _run_fixture(path)
            with self.subTest(path=path.name):
                self.assertEqual(result["span_count"], payload["expected_span_count"])
                self.assertEqual(len(stop_set["stops"]), payload["expected_span_count"])
                self.assertEqual(
                    _resolved_field_count(stop_set, NORMALIZED_STOP_FIELD_DATE),
                    payload["expected_date_resolved"],
                )
                self.assertEqual(
                    _resolved_field_count(stop_set, NORMALIZED_STOP_FIELD_TIME),
                    payload["expected_time_resolved"],
                )

    def test_labeled_time_windows_create_appointment_window_candidates(self):
        window_fixture_names = {
            "fake_tql_datetime_columns.json",
            "fake_jay_earliest_latest_datetime.json",
            "fake_landstar_target_window_datetime.json",
            "fake_spi_expected_date_hours.json",
        }

        for name in window_fixture_names:
            _, _, stop_set = _run_fixture(FIXTURE_DIR / name)
            with self.subTest(path=name):
                self.assertGreaterEqual(
                    _resolved_field_count(
                        stop_set,
                        NORMALIZED_STOP_FIELD_APPOINTMENT_WINDOW,
                    ),
                    1,
                )

    def test_header_and_terms_datetime_noise_does_not_attach_to_stop(self):
        _, _, stop_set = _run_fixture(FIXTURE_DIR / "fake_header_terms_datetime_noise.json")

        self.assertEqual(_resolved_field_count(stop_set, NORMALIZED_STOP_FIELD_DATE), 0)
        self.assertEqual(_resolved_field_count(stop_set, NORMALIZED_STOP_FIELD_TIME), 0)


if __name__ == "__main__":
    unittest.main()
