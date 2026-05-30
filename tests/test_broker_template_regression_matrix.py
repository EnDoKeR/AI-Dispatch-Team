import json
import unittest

from app.document_ai.broker_template_candidate_extraction import (
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.broker_template_matcher import (
    TEMPLATE_SELECTION_STATUS_CONFLICT,
    TEMPLATE_SELECTION_STATUS_MATCHED,
    TEMPLATE_SELECTION_STATUS_UNKNOWN,
)
from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from app.document_ai.ratecon_candidates import FIELD_RATE, FIELD_REFERENCE
from app.document_ai.ratecon_field_resolution import resolve_ratecon_fields_with_template_context
from app.document_ai.ratecon_intake_draft import build_ratecon_intake_from_resolution
from tests.fixtures.document_ai.broker_templates.fixture_loader import FIXTURE_DIR
from tests.fixtures.document_ai.ratecon_text.fixture_loader import build_fixture_text_artifact


MATRIX = [
    {
        "fixture": "alpha_freight_mock_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "alpha_freight_mock_v1",
        "resolved": ["broker_name", "rate", "pickup_location", "delivery_location"],
        "missing": [],
        "conflicts": [],
    },
    {
        "fixture": "northstar_logistics_mock_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "northstar_logistics_mock_v1",
        "resolved": ["broker_name", "rate", "pickup_location", "delivery_location"],
        "missing": [],
        "conflicts": [],
    },
    {
        "fixture": "tablelane_transport_mock_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_MATCHED,
        "template_id": "tablelane_transport_mock_v1",
        "resolved": ["broker_name", "rate", "pickup_location", "delivery_location"],
        "missing": ["equipment"],
        "conflicts": [],
    },
    {
        "fixture": "unknown_broker_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_UNKNOWN,
        "template_id": "",
        "resolved": ["broker_name", "rate"],
        "missing": [],
        "conflicts": [],
    },
    {
        "fixture": "template_conflict_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_CONFLICT,
        "template_id": "",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": ["broker_name", "broker_mc"],
        "conflicts": [],
    },
    {
        "fixture": "multi_amount_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_UNKNOWN,
        "template_id": "",
        "resolved": ["rate"],
        "missing": [],
        "conflicts": [],
    },
    {
        "fixture": "ambiguous_references_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_UNKNOWN,
        "template_id": "",
        "resolved": ["rate", "pickup_location", "delivery_location"],
        "missing": [],
        "conflicts": ["load_number"],
    },
    {
        "fixture": "missing_core_fields_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_UNKNOWN,
        "template_id": "",
        "resolved": ["broker_name", "pickup_location", "delivery_location"],
        "missing": ["rate", "pickup_date", "weight", "commodity"],
        "conflicts": [],
    },
    {
        "fixture": "conflict_rate_ratecon.txt",
        "status": TEMPLATE_SELECTION_STATUS_UNKNOWN,
        "template_id": "",
        "resolved": ["broker_name", "pickup_location", "delivery_location"],
        "missing": [],
        "conflicts": ["rate"],
    },
]


class BrokerTemplateRegressionMatrixTests(unittest.TestCase):
    def setUp(self):
        self.registry = BrokerTemplateRegistry.from_directory(FIXTURE_DIR)

    def _run_case(self, fixture_name):
        artifact = build_fixture_text_artifact(fixture_name)
        extraction = extract_ratecon_candidates_with_template_context(artifact, self.registry)
        resolution = resolve_ratecon_fields_with_template_context(extraction)
        intake = build_ratecon_intake_from_resolution(resolution)
        return extraction, resolution, intake

    def test_template_regression_matrix(self):
        for case in MATRIX:
            with self.subTest(fixture=case["fixture"]):
                extraction, resolution, intake = self._run_case(case["fixture"])
                selection = extraction["template_selection_result"]
                resolved_fields = {
                    item["field_name"]
                    for item in resolution["resolutions"]
                    if item["status"] == "resolved"
                }

                self.assertEqual(selection["status"], case["status"])
                self.assertEqual(selection["selected_template_id"], case["template_id"])
                for field_name in case["resolved"]:
                    self.assertIn(field_name, resolved_fields)
                for field_name in case["missing"]:
                    self.assertIn(field_name, resolution["missing_fields"])
                for field_name in case["conflicts"]:
                    self.assertIn(field_name, resolution["conflict_fields"])
                self.assertFalse(intake["cases_created"])
                self.assertFalse(intake["cases_linked"])

    def test_multi_amount_rate_is_not_accessorial_amount(self):
        _, resolution, _ = self._run_case("multi_amount_ratecon.txt")
        rate_resolution = [
            item for item in resolution["resolutions"] if item["field_name"] == FIELD_RATE
        ][0]

        self.assertEqual(rate_resolution["selected_candidate"]["normalized_value"], "3100.00")

    def test_typed_reference_candidates_are_preserved_where_possible(self):
        extraction, _, _ = self._run_case("ambiguous_references_ratecon.txt")
        reference_types = {
            candidate["value_type"]
            for candidate in extraction["adjusted_candidate_result"]["candidates"]
            if candidate["field_name"] == FIELD_REFERENCE
        }

        self.assertIn("po_number", reference_types)
        self.assertIn("bol_number", reference_types)
        self.assertIn("pickup_number", reference_types)
        self.assertIn("delivery_number", reference_types)

    def test_no_dispatch_recommendation_or_case_output(self):
        extraction, resolution, intake = self._run_case("alpha_freight_mock_ratecon.txt")
        text = json.dumps(
            {
                "extraction": extraction,
                "resolution": resolution,
                "intake": intake,
            }
        )

        for literal in ["ACCEPT", "REJECT", "DispatchCase"]:
            with self.subTest(literal=literal):
                self.assertNotIn(literal, text)


if __name__ == "__main__":
    unittest.main()
