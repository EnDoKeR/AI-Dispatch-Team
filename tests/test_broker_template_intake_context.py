import unittest

from app.document_ai.broker_template_candidate_extraction import (
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.ratecon_field_resolution import resolve_ratecon_fields_with_template_context
from app.document_ai.ratecon_intake_draft import build_ratecon_intake_from_resolution
from app.market_intelligence.intake.rate_confirmation_intake import STATUS_MISSING_FIELDS
from app.market_intelligence.intake.rate_confirmation_validation import (
    validate_rate_confirmation_intake,
)
from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from tests.fixtures.document_ai.broker_templates.fixture_loader import FIXTURE_DIR
from tests.fixtures.document_ai.ratecon_text.fixture_loader import build_fixture_text_artifact


class BrokerTemplateIntakeContextTests(unittest.TestCase):
    def setUp(self):
        self.registry = BrokerTemplateRegistry.from_directory(FIXTURE_DIR)

    def _intake_from_fixture(self, fixture_name):
        artifact = build_fixture_text_artifact(fixture_name)
        template_result = extract_ratecon_candidates_with_template_context(
            artifact,
            self.registry,
        )
        resolution = resolve_ratecon_fields_with_template_context(template_result)
        return build_ratecon_intake_from_resolution(resolution)

    def test_template_metadata_is_preserved_when_supported(self):
        intake = self._intake_from_fixture("alpha_freight_mock_ratecon.txt")
        context = intake["extraction_context"]

        self.assertEqual(context["extraction_template_id"], "alpha_freight_mock_v1")
        self.assertEqual(context["template_match_status"], "matched")
        self.assertTrue(context["template_context_used"])

    def test_missing_critical_fields_still_gate_validation(self):
        intake = self._intake_from_fixture("missing_core_fields_ratecon.txt")
        validation = validate_rate_confirmation_intake(intake)

        self.assertEqual(validation["status"], STATUS_MISSING_FIELDS)
        self.assertTrue(validation["missing_fields"])

    def test_conflict_fields_remain_visible(self):
        intake = self._intake_from_fixture("conflict_rate_ratecon.txt")

        self.assertIn("rate", intake["needs_check_fields"])

    def test_unknown_template_does_not_fake_template_metadata(self):
        intake = self._intake_from_fixture("unknown_broker_ratecon.txt")
        context = intake["extraction_context"]

        self.assertEqual(context["extraction_template_id"], "")
        self.assertEqual(context["template_match_status"], "unknown")
        self.assertFalse(context["template_context_used"])


if __name__ == "__main__":
    unittest.main()
