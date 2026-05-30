import unittest

from app.document_ai.broker_template_candidate_extraction import (
    TRUSTED_TEMPLATE_SCORING_CONFIDENCE,
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.broker_templates import build_broker_template
from app.document_ai.broker_template_registry import BrokerTemplateRegistry
from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_candidates import (
    FIELD_PICKUP_LOCATION,
    FIELD_RATE,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_RESOLVED,
    resolve_ratecon_fields_with_template_context,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from tests.fixtures.document_ai.broker_templates.fixture_loader import FIXTURE_DIR
from tests.fixtures.document_ai.ratecon_text.fixture_loader import build_fixture_text_artifact


class BrokerTemplateResolverContextTests(unittest.TestCase):
    def setUp(self):
        self.registry = BrokerTemplateRegistry.from_directory(FIXTURE_DIR)

    def _template_aware(self, fixture_name, registry=None):
        artifact = build_fixture_text_artifact(fixture_name)
        return extract_ratecon_candidates_with_template_context(
            artifact,
            registry or self.registry,
        )

    def test_alpha_clean_fixture_resolves_with_template_context(self):
        template_result = self._template_aware("alpha_freight_mock_ratecon.txt")

        resolution = resolve_ratecon_fields_with_template_context(template_result)
        rate_resolution = [
            item for item in resolution["resolutions"] if item["field_name"] == FIELD_RATE
        ][0]

        self.assertTrue(resolution["template_context_used"])
        self.assertEqual(resolution["selected_template_id"], "alpha_freight_mock_v1")
        self.assertEqual(rate_resolution["status"], FIELD_RESOLUTION_STATUS_RESOLVED)

    def test_northstar_vocabulary_resolves_with_template_context(self):
        template_result = self._template_aware("northstar_logistics_mock_ratecon.txt")

        resolution = resolve_ratecon_fields_with_template_context(template_result)

        self.assertTrue(resolution["template_context_used"])
        self.assertEqual(resolution["selected_template_id"], "northstar_logistics_mock_v1")
        self.assertNotIn(FIELD_RATE, resolution["missing_fields"])

    def test_tablelane_stop_labels_boost_stop_candidates(self):
        template_result = self._template_aware("tablelane_transport_mock_ratecon.txt")
        adjustment_fields = {
            adjustment["field_name"]
            for adjustment in template_result["scoring_adjustments"]
        }

        resolution = resolve_ratecon_fields_with_template_context(template_result)

        self.assertIn(FIELD_PICKUP_LOCATION, adjustment_fields)
        self.assertTrue(resolution["template_context_used"])

    def test_conflict_rate_fixture_still_marks_rate_conflict(self):
        template_result = self._template_aware("conflict_rate_ratecon.txt")

        resolution = resolve_ratecon_fields_with_template_context(
            template_result,
            field_names=[FIELD_RATE],
        )

        self.assertEqual(
            resolution["resolutions"][0]["status"],
            FIELD_RESOLUTION_STATUS_CONFLICT,
        )
        self.assertIn(FIELD_RATE, resolution["conflict_fields"])

    def test_unknown_broker_fallback_does_not_use_template_context(self):
        template_result = self._template_aware("unknown_broker_ratecon.txt")

        resolution = resolve_ratecon_fields_with_template_context(template_result)

        self.assertFalse(resolution["template_context_used"])
        self.assertEqual(resolution["selected_template_id"], "")
        self.assertIn("generic_resolution_without_template", resolution["warnings"])

    def test_low_confidence_template_selection_adds_review_marker(self):
        weak_template = build_broker_template(
            {
                "template_id": "weak_mock_v1",
                "broker_key": "weak_mock",
                "display_name": "Weak Mock",
                "version": "1",
                "created_for_testing": True,
                "match_rules": [
                    {
                        "keywords": ["Weak Mock"],
                        "confidence_boost": 0.05,
                    }
                ],
                "field_label_rules": [
                    {
                        "field_name": "rate",
                        "labels": ["Carrier Pay"],
                        "confidence_boost": 0.2,
                    }
                ],
            }
        )
        registry = BrokerTemplateRegistry([weak_template])
        artifact = build_text_extraction_artifact_for_candidates(
            full_text="Weak Mock\nCarrier Pay: $2,850.00\n",
            source_name="weak_mock_fake.txt",
        )
        template_result = extract_ratecon_candidates_with_template_context(
            artifact,
            registry,
        )

        resolution = resolve_ratecon_fields_with_template_context(
            template_result,
            field_names=[FIELD_RATE],
        )

        self.assertIn("template_match", resolution["needs_check_fields"])
        self.assertFalse(resolution["template_context_used"])
        self.assertIn("template_match_low_confidence", resolution["warnings"])

    def test_matched_below_trusted_threshold_adds_review_marker(self):
        weak_matched_template = build_broker_template(
            {
                "template_id": "weak_matched_mock_v1",
                "broker_key": "weak_matched_mock",
                "display_name": "Weak Matched Mock",
                "version": "1",
                "created_for_testing": True,
                "match_rules": [
                    {
                        "keywords": ["Weak Matched Mock"],
                        "confidence_boost": 0.26,
                    }
                ],
                "field_label_rules": [
                    {
                        "field_name": "rate",
                        "labels": ["Carrier Pay"],
                        "confidence_boost": 0.2,
                    }
                ],
            }
        )
        registry = BrokerTemplateRegistry([weak_matched_template])
        artifact = build_text_extraction_artifact_for_candidates(
            full_text="Weak Matched Mock\nCarrier Pay: $2,850.00\n",
            source_name="weak_matched_mock_fake.txt",
        )
        template_result = extract_ratecon_candidates_with_template_context(
            artifact,
            registry,
        )

        resolution = resolve_ratecon_fields_with_template_context(
            template_result,
            field_names=[FIELD_RATE],
        )

        self.assertLess(
            template_result["template_selection_result"]["selected_confidence"],
            TRUSTED_TEMPLATE_SCORING_CONFIDENCE,
        )
        self.assertFalse(template_result["template_scoring_applied"])
        self.assertFalse(resolution["template_context_used"])
        self.assertEqual(resolution["selected_template_id"], "")
        self.assertIn("template_match", resolution["needs_check_fields"])
        self.assertIn("template_match_untrusted_for_resolution", resolution["warnings"])

    def test_conflict_template_context_is_not_used_for_resolution(self):
        template_result = self._template_aware("template_conflict_ratecon.txt")

        resolution = resolve_ratecon_fields_with_template_context(
            template_result,
            field_names=[FIELD_RATE],
        )

        self.assertFalse(template_result["template_scoring_applied"])
        self.assertFalse(resolution["template_context_used"])
        self.assertIn("template_match", resolution["needs_check_fields"])
        self.assertIn("template_match_conflict", resolution["warnings"])

    def test_accessorial_amounts_are_not_selected_as_main_rate(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")
        base_result = extract_ratecon_candidates(artifact)
        template_result = {
            "base_candidate_result": base_result,
            "adjusted_candidate_result": base_result,
            "template_selection_result": {"status": "unknown", "selected_confidence": 0.0},
        }

        resolution = resolve_ratecon_fields_with_template_context(
            template_result,
            field_names=[FIELD_RATE],
        )

        self.assertEqual(
            resolution["resolutions"][0]["selected_candidate"]["normalized_value"],
            "3100.00",
        )


if __name__ == "__main__":
    unittest.main()
