import json
import unittest
from collections import Counter

from app.document_ai.broker_template_candidate_extraction import (
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.broker_template_matcher import (
    TEMPLATE_SELECTION_STATUS_MATCHED,
    TEMPLATE_SELECTION_STATUS_UNKNOWN,
)
from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from app.document_ai.ratecon_candidates import (
    FIELD_BROKER_NAME,
    FIELD_DELIVERY_TIME,
    FIELD_PICKUP_TIME,
    FIELD_RATE,
    FIELD_REFERENCE,
    FIELD_SPECIAL_REQUIREMENT,
)
from app.document_ai.ratecon_field_resolution import (
    resolve_ratecon_fields_with_template_context,
)
from app.document_ai.ratecon_intake_draft import build_ratecon_intake_from_resolution
from tests.fixtures.document_ai.broker_templates.fixture_loader import (
    FIXTURE_DIR as TEMPLATE_FIXTURE_DIR,
)
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


MATRIX = [
    {
        "fixture": "repeated_headers_terms_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "alpha_freight_mock_v1",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": [],
        "needs": [],
        "conflicts": [],
    },
    {
        "fixture": "multi_page_rate_terms_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "northstar_logistics_mock_v1",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": [],
        "needs": [],
        "conflicts": [],
    },
    {
        "fixture": "table_like_stops_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "tablelane_transport_mock_v1",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": ["equipment"],
        "needs": [],
        "conflicts": [],
    },
    {
        "fixture": "missing_broker_mc_header_only_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "alpha_freight_mock_v1",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": ["broker_name", "broker_mc"],
        "needs": [],
        "conflicts": [],
        "forbidden_resolved": ["broker_mc"],
    },
    {
        "fixture": "carrier_vs_broker_confusion_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "northstar_logistics_mock_v1",
        "resolved": ["broker_name", "rate", "pickup_location", "delivery_location"],
        "missing": [],
        "needs": [],
        "conflicts": [],
    },
    {
        "fixture": "references_near_wrong_stop_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "tablelane_transport_mock_v1",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": ["equipment"],
        "needs": [],
        "conflicts": [],
    },
    {
        "fixture": "conflicting_appointment_times_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "tablelane_transport_mock_v1",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": ["equipment"],
        "needs": [],
        "conflicts": [],
    },
    {
        "fixture": "buried_special_requirements_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "alpha_freight_mock_v1",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": [],
        "needs": [],
        "conflicts": [],
    },
    {
        "fixture": "revised_rate_conflict_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "northstar_logistics_mock_v1",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": [],
        "needs": [],
        "conflicts": [],
    },
    {
        "fixture": "unknown_hard_layout_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_UNKNOWN,
        "template_id": "",
        "resolved": ["pickup_location", "delivery_location"],
        "missing": ["broker_name", "broker_mc", "load_number"],
        "needs": ["rate"],
        "conflicts": [],
        "forbidden_resolved": ["rate"],
    },
]


class RateConHardLayoutRegressionMatrixTests(unittest.TestCase):
    def setUp(self):
        self.registry = BrokerTemplateRegistry.from_directory(TEMPLATE_FIXTURE_DIR)

    def _run_case(self, fixture_name):
        artifact = build_fixture_text_artifact(fixture_name)
        extraction = extract_ratecon_candidates_with_template_context(
            artifact,
            self.registry,
        )
        resolution = resolve_ratecon_fields_with_template_context(extraction)
        intake = build_ratecon_intake_from_resolution(resolution)
        return extraction, resolution, intake

    def _resolved_fields(self, resolution):
        return {
            item["field_name"]
            for item in resolution["resolutions"]
            if item["status"] == "resolved"
        }

    def _candidate_counts(self, extraction):
        return Counter(
            candidate["field_name"]
            for candidate in extraction["adjusted_candidate_result"]["candidates"]
        )

    def test_hard_layout_regression_matrix_baseline(self):
        for case in MATRIX:
            with self.subTest(fixture=case["fixture"]):
                extraction, resolution, intake = self._run_case(case["fixture"])
                selection = extraction["template_selection_result"]
                resolved_fields = self._resolved_fields(resolution)

                self.assertEqual(selection["status"], case["status"])
                self.assertEqual(selection["selected_template_id"], case["template_id"])

                for field_name in case["resolved"]:
                    self.assertIn(field_name, resolved_fields)
                for field_name in case["missing"]:
                    self.assertIn(field_name, resolution["missing_fields"])
                for field_name in case["needs"]:
                    self.assertIn(field_name, resolution["needs_check_fields"])
                for field_name in case["conflicts"]:
                    self.assertIn(field_name, resolution["conflict_fields"])
                for field_name in case.get("forbidden_resolved", []):
                    self.assertNotIn(field_name, resolved_fields)

                self.assertFalse(intake["cases_created"])
                self.assertFalse(intake["cases_linked"])

    def test_accessorial_amounts_do_not_become_main_rate(self):
        cases = {
            "repeated_headers_terms_ratecon.txt": {"2900.00"},
            "multi_page_rate_terms_ratecon.txt": {"3150.00"},
        }

        for fixture_name, allowed_values in cases.items():
            with self.subTest(fixture=fixture_name):
                _, resolution, _ = self._run_case(fixture_name)
                rate_resolution = [
                    item
                    for item in resolution["resolutions"]
                    if item["field_name"] == FIELD_RATE
                ][0]

                self.assertEqual(rate_resolution["status"], "resolved")
                self.assertIn(
                    rate_resolution["selected_candidate"]["normalized_value"],
                    allowed_values,
                )
                self.assertNotIn(
                    "accessorial_label_not_main_rate",
                    rate_resolution["selected_candidate"].get("warnings", []),
                )

    def test_carrier_name_is_not_selected_as_broker_name(self):
        _, resolution, _ = self._run_case("carrier_vs_broker_confusion_ratecon.txt")
        broker_resolution = [
            item
            for item in resolution["resolutions"]
            if item["field_name"] == FIELD_BROKER_NAME
        ][0]

        self.assertEqual(broker_resolution["status"], "resolved")
        self.assertNotEqual(
            broker_resolution["selected_candidate"]["normalized_value"],
            "Fake Carrier Placeholder LLC",
        )

    def test_reference_candidates_remain_typed_when_labels_are_clear(self):
        extraction, _, _ = self._run_case("references_near_wrong_stop_ratecon.txt")
        reference_types = {
            candidate["value_type"]
            for candidate in extraction["adjusted_candidate_result"]["candidates"]
            if candidate["field_name"] == FIELD_REFERENCE
        }

        self.assertIn("po_number", reference_types)
        self.assertIn("bol_number", reference_types)
        self.assertIn("customer_reference", reference_types)

    def test_revised_current_rate_is_selected_when_evidence_is_strong(self):
        _, resolution, _ = self._run_case("revised_rate_conflict_ratecon.txt")
        rate_resolution = [
            item
            for item in resolution["resolutions"]
            if item["field_name"] == FIELD_RATE
        ][0]

        self.assertEqual(rate_resolution["status"], "resolved")
        self.assertEqual(rate_resolution["selected_candidate_value"], "3050.00")
        self.assertIn(
            "selected_revised_current_rate_candidate",
            rate_resolution["reasons"],
        )

    def test_conflicting_appointment_candidates_are_visible(self):
        extraction, _, _ = self._run_case("conflicting_appointment_times_ratecon.txt")
        counts = self._candidate_counts(extraction)
        time_resolution = resolve_ratecon_fields_with_template_context(
            extraction,
            field_names=[FIELD_PICKUP_TIME, FIELD_DELIVERY_TIME],
        )

        self.assertGreaterEqual(counts[FIELD_PICKUP_TIME], 2)
        self.assertIn(FIELD_PICKUP_TIME, time_resolution["conflict_fields"])

    def test_buried_special_requirements_are_detected(self):
        extraction, _, _ = self._run_case("buried_special_requirements_ratecon.txt")
        counts = self._candidate_counts(extraction)

        self.assertGreaterEqual(counts[FIELD_SPECIAL_REQUIREMENT], 4)

    def test_no_dispatch_recommendation_or_case_output(self):
        for case in MATRIX:
            with self.subTest(fixture=case["fixture"]):
                extraction, resolution, intake = self._run_case(case["fixture"])
                payload = json.dumps(
                    {
                        "extraction": extraction,
                        "resolution": resolution,
                        "intake": intake,
                    }
                )

                for literal in ["ACCEPT", "REJECT", "DispatchCase"]:
                    self.assertNotIn(literal, payload)


if __name__ == "__main__":
    unittest.main()
