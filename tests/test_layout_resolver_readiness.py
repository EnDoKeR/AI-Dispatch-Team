import json
import unittest
from pathlib import Path

from app.document_ai.layout_artifacts import (
    build_bounding_box,
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
)
from app.document_ai.layout_candidate_extraction import extract_ratecon_layout_candidates
from app.document_ai.ratecon_candidates import (
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_RATE,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
    FIELD_RESOLUTION_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_RESOLVED,
    resolve_ratecon_fields,
)


FIXTURE_DIR = Path("tests/fixtures/document_ai/layout_artifacts")


def _load_fixture(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _resolution_for(result, field_name):
    for resolution in result["resolutions"]:
        if resolution["field_name"] == field_name:
            return resolution
    raise AssertionError(f"Missing resolution for {field_name}")


class LayoutResolverReadinessTests(unittest.TestCase):
    def test_rate_summary_beats_terms_accessorial_amounts_by_candidate_shape(self):
        blue = extract_ratecon_layout_candidates(_load_fixture("fake_blue_table_ratecon_layout.json"))
        terms = extract_ratecon_layout_candidates(_load_fixture("fake_terms_billing_signature_layout.json"))
        candidate_result = dict(blue)
        candidate_result["candidates"] = blue["candidates"] + terms["candidates"]

        resolved = resolve_ratecon_fields(candidate_result, field_names=[FIELD_RATE])
        rate = _resolution_for(resolved, FIELD_RATE)

        self.assertEqual(rate["status"], FIELD_RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(rate["selected_candidate"]["normalized_value"], "2800.00")
        self.assertNotEqual(rate["selected_candidate"]["normalized_value"], "75.00")

    def test_linehaul_and_total_rate_candidates_conflict_when_values_differ(self):
        linehaul = build_layout_line(
            "L_LINEHAUL",
            text_redacted="Linehaul: $3000.00",
            bbox=build_bounding_box(40, 40, 260, 58, page_number=1),
            page_number=1,
            reading_order_index=1,
            section_role="RATE_SUMMARY",
        )
        total = build_layout_line(
            "L_TOTAL",
            text_redacted="Total Carrier Pay: $3200.00",
            bbox=build_bounding_box(40, 70, 280, 88, page_number=1),
            page_number=1,
            reading_order_index=2,
            section_role="RATE_SUMMARY",
        )
        artifact = build_layout_extraction_artifact(
            pages=[
                build_layout_page_artifact(
                    page_number=1,
                    lines=[linehaul, total],
                    page_roles=["PAYMENT_SUMMARY"],
                    section_roles=["RATE_SUMMARY"],
                )
            ]
        )
        candidate_result = extract_ratecon_layout_candidates(artifact)

        resolved = resolve_ratecon_fields(candidate_result, field_names=[FIELD_RATE])

        self.assertEqual(_resolution_for(resolved, FIELD_RATE)["status"], FIELD_RESOLUTION_STATUS_CONFLICT)

    def test_pickup_date_from_table_row_resolves_for_simple_two_stop_layout(self):
        candidate_result = extract_ratecon_layout_candidates(_load_fixture("fake_blue_table_ratecon_layout.json"))

        resolved = resolve_ratecon_fields(candidate_result, field_names=[FIELD_PICKUP_DATE])
        pickup_date = _resolution_for(resolved, FIELD_PICKUP_DATE)

        self.assertEqual(pickup_date["status"], FIELD_RESOLUTION_STATUS_RESOLVED)
        self.assertEqual(pickup_date["selected_candidate"]["normalized_value"], "2099-01-10")
        self.assertEqual(pickup_date["selected_candidate"]["layout_table_id"], "P1_T_STOPS")

    def test_multi_stop_is_not_collapsed_into_one_pickup(self):
        candidate_result = extract_ratecon_layout_candidates(
            _load_fixture("fake_multi_stop_order_confirmation_layout.json")
        )

        resolved = resolve_ratecon_fields(candidate_result, field_names=[FIELD_PICKUP_LOCATION])

        self.assertEqual(_resolution_for(resolved, FIELD_PICKUP_LOCATION)["status"], FIELD_RESOLUTION_STATUS_CONFLICT)

    def test_tonu_payment_does_not_become_normal_rate(self):
        candidate_result = extract_ratecon_layout_candidates(_load_fixture("fake_tonu_payment_layout.json"))

        resolved = resolve_ratecon_fields(candidate_result, field_names=[FIELD_RATE])

        self.assertEqual(_resolution_for(resolved, FIELD_RATE)["status"], FIELD_RESOLUTION_STATUS_MISSING)
        self.assertTrue(any(candidate["value_type"] == "TONU_pay" for candidate in candidate_result["candidates"]))

    def test_low_confidence_layout_money_routes_review(self):
        line = build_layout_line(
            "L_UNKNOWN_MONEY",
            text_redacted="Misc amount $999.00",
            bbox=build_bounding_box(40, 40, 260, 58, page_number=1),
            page_number=1,
            reading_order_index=1,
            section_role="UNKNOWN",
        )
        artifact = build_layout_extraction_artifact(
            pages=[build_layout_page_artifact(page_number=1, lines=[line], page_roles=["UNKNOWN"])]
        )
        candidate_result = extract_ratecon_layout_candidates(artifact)

        resolved = resolve_ratecon_fields(candidate_result, field_names=[FIELD_RATE])

        self.assertEqual(_resolution_for(resolved, FIELD_RATE)["status"], FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE)


if __name__ == "__main__":
    unittest.main()
