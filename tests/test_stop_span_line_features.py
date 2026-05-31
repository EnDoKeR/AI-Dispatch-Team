import unittest

from app.document_ai.layout_artifacts import (
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
)
from app.document_ai.stop_span_extractor import (
    LINE_LABEL_DELIVERY,
    LINE_LABEL_LOCATION,
    LINE_LABEL_NOISE,
    LINE_LABEL_PICKUP,
    LINE_LABEL_REFERENCE,
    LINE_LABEL_TIME,
    build_layout_line_features,
    classify_line_label_category,
    detect_line_has_date,
    detect_line_has_location_like,
    detect_line_has_reference_like,
    detect_line_has_time,
    detect_line_is_noise,
    normalize_line_text_for_features,
)


def _line(text, section_role=""):
    return build_layout_line(
        line_id="line_test",
        text_redacted=text,
        page_number=1,
        section_role=section_role,
    )


class StopSpanLineFeatureTests(unittest.TestCase):
    def test_normalize_line_text(self):
        self.assertEqual(
            normalize_line_text_for_features("  Pick   Up\nLocation  "),
            "Pick Up Location",
        )

    def test_pickup_label_line(self):
        categories = classify_line_label_category(_line("PU 1 Fake Origin"))

        self.assertIn(LINE_LABEL_PICKUP, categories)
        self.assertIn(LINE_LABEL_LOCATION, categories)

    def test_delivery_label_line(self):
        categories = classify_line_label_category(_line("Deliver To Fake Destination"))

        self.assertIn(LINE_LABEL_DELIVERY, categories)

    def test_date_time_line(self):
        line = _line("Date 01/02/2099 Time 08:00-10:00")

        self.assertTrue(detect_line_has_date(line))
        self.assertTrue(detect_line_has_time(line))
        self.assertIn(LINE_LABEL_TIME, classify_line_label_category(line))

    def test_location_like_line(self):
        self.assertTrue(detect_line_has_location_like(_line("Fake Shipper Facility")))

    def test_reference_like_line(self):
        self.assertTrue(detect_line_has_reference_like(_line("Appointment Ref FAKE123")))
        self.assertIn(LINE_LABEL_REFERENCE, classify_line_label_category(_line("PO FAKE123")))

    def test_terms_billing_noise_line(self):
        line = _line("Quick Pay terms fake amount", "QUICK_PAY")

        self.assertTrue(detect_line_is_noise(line))
        self.assertIn(LINE_LABEL_NOISE, classify_line_label_category(line))

    def test_signature_footer_noise_line(self):
        line = _line("Please Sign and Return", "SIGNATURE_BLOCK")

        self.assertTrue(detect_line_is_noise(line))

    def test_build_features_without_text_by_default(self):
        artifact = build_layout_extraction_artifact(
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    lines=[_line("Pick-up Location"), _line("Date 01/02/2099")],
                )
            ]
        )
        features = build_layout_line_features(artifact)

        self.assertEqual(len(features), 2)
        self.assertNotIn("safe_text_redacted", features[0])
        self.assertTrue(features[1]["has_date"])

    def test_build_features_can_include_fake_text_for_tests(self):
        artifact = build_layout_extraction_artifact(
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    lines=[_line("Pick-up Location")],
                )
            ]
        )
        features = build_layout_line_features(artifact, include_safe_text=True)

        self.assertEqual(features[0]["safe_text_redacted"], "Pick-up Location")


if __name__ == "__main__":
    unittest.main()

