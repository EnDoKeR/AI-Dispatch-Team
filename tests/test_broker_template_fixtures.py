import json
import unittest

from tests.fixtures.document_ai.broker_templates.fixture_loader import (
    TEMPLATE_FIXTURE_NAMES,
    load_all_template_fixtures,
    load_template_fixture,
    load_template_fixture_payload,
)


class BrokerTemplateFixturesTests(unittest.TestCase):
    def test_load_one_fake_template_fixture(self):
        template = load_template_fixture("alpha_freight_mock_v1.json")

        self.assertEqual(template["template_id"], "alpha_freight_mock_v1")
        self.assertTrue(template["created_for_testing"])
        self.assertTrue(template["match_rules"])

    def test_load_all_fake_templates(self):
        templates = load_all_template_fixtures()

        self.assertEqual(len(templates), len(TEMPLATE_FIXTURE_NAMES))
        self.assertTrue(all(template["created_for_testing"] for template in templates))

    def test_templates_are_json_serializable(self):
        for name in TEMPLATE_FIXTURE_NAMES:
            with self.subTest(name=name):
                json.dumps(load_template_fixture(name))

    def test_templates_do_not_contain_real_or_private_names(self):
        forbidden = [
            "TQL",
            "CH Robinson",
            "Landstar",
            "RXO",
            "Coyote",
        ]

        for name in TEMPLATE_FIXTURE_NAMES:
            payload_text = json.dumps(load_template_fixture_payload(name))
            for term in forbidden:
                with self.subTest(name=name, term=term):
                    self.assertNotIn(term, payload_text)

    def test_templates_have_extraction_rules(self):
        for template in load_all_template_fixtures():
            with self.subTest(template=template["template_id"]):
                self.assertTrue(template["match_rules"])
                self.assertTrue(template["field_label_rules"])
                self.assertTrue(template["stop_section_rules"])
                self.assertTrue(template["reference_type_rules"])

    def test_templates_do_not_include_broker_memory_fields(self):
        forbidden_keys = {
            "credit_score",
            "days_to_pay",
            "factoring_status",
            "payment_history",
            "broker_risk",
            "dispatcher_experience",
        }

        for template in load_all_template_fixtures():
            with self.subTest(template=template["template_id"]):
                self.assertFalse(forbidden_keys.intersection(template.keys()))


if __name__ == "__main__":
    unittest.main()
