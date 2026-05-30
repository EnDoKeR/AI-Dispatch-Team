import json
import unittest

from app.document_ai.broker_templates import (
    BROKER_TEMPLATE_CONTRACT_VERSION,
    build_broker_template,
    build_broker_template_match_rule,
    build_field_label_rule,
    build_reference_type_rule,
    build_stop_section_rule,
    build_template_match_result,
)


class BrokerTemplateContractTests(unittest.TestCase):
    def test_create_fake_broker_template(self):
        template = build_broker_template(
            {
                "template_id": "alpha_freight_mock_v1",
                "broker_key": "alpha_freight_mock",
                "display_name": "Alpha Freight Mock",
                "version": "1",
                "created_for_testing": True,
                "match_rules": [
                    {
                        "keywords": ["Alpha Freight Mock"],
                        "aliases": ["Alpha Mock"],
                        "mc_numbers": ["MC111111"],
                        "confidence_boost": 0.3,
                    }
                ],
            }
        )

        self.assertEqual(template["template_id"], "alpha_freight_mock_v1")
        self.assertTrue(template["active"])
        self.assertTrue(template["created_for_testing"])
        self.assertEqual(template["contract_version"], BROKER_TEMPLATE_CONTRACT_VERSION)

    def test_template_serializes_and_round_trips(self):
        template = build_broker_template(
            {
                "template_id": "fake_template",
                "broker_key": "fake_broker",
                "display_name": "Fake Broker",
                "version": "1",
                "created_for_testing": True,
            }
        )

        payload = json.loads(json.dumps(template))

        self.assertEqual(payload["template_id"], "fake_template")

    def test_match_rules_support_aliases_excludes_and_fake_mc(self):
        rule = build_broker_template_match_rule(
            {
                "keywords": ["Alpha Freight Mock"],
                "aliases": ["Alpha Mock"],
                "exclude_keywords": ["Northstar Mock"],
                "mc_numbers": ["MC111111"],
                "email_domains": ["example.invalid"],
                "min_keyword_hits": 2,
                "confidence_boost": 0.25,
                "confidence_penalty": 0.4,
            }
        )

        self.assertIn("Alpha Mock", rule["aliases"])
        self.assertIn("Northstar Mock", rule["exclude_keywords"])
        self.assertIn("MC111111", rule["mc_numbers"])
        self.assertEqual(rule["min_keyword_hits"], 2)

    def test_field_labels_support_boosts_and_penalties(self):
        rule = build_field_label_rule(
            {
                "field_name": "rate",
                "labels": ["Carrier Pay"],
                "negative_labels": ["Detention"],
                "section_labels": ["Charges"],
                "regex_patterns": ["fake-pattern"],
                "confidence_boost": 0.2,
                "confidence_penalty": 0.3,
            }
        )

        self.assertEqual(rule["field_name"], "rate")
        self.assertIn("Carrier Pay", rule["labels"])
        self.assertIn("Detention", rule["negative_labels"])
        self.assertEqual(rule["confidence_boost"], 0.2)

    def test_stop_and_reference_rules_are_json_ready(self):
        stop_rule = build_stop_section_rule(
            {
                "pickup_labels": ["Pickup"],
                "delivery_labels": ["Delivery"],
                "generic_stop_labels": ["Stop"],
                "appointment_labels": ["Appt"],
            }
        )
        reference_rule = build_reference_type_rule(
            {
                "reference_type": "po_number",
                "labels": ["PO Number"],
                "negative_labels": ["Reference Terms"],
                "confidence_boost": 0.2,
            }
        )

        json.dumps({"stop_rule": stop_rule, "reference_rule": reference_rule})
        self.assertIn("Pickup", stop_rule["pickup_labels"])
        self.assertEqual(reference_rule["reference_type"], "po_number")

    def test_template_match_result_shape(self):
        result = build_template_match_result(
            template_id="alpha_freight_mock_v1",
            broker_key="alpha_freight_mock",
            confidence=0.85,
            matched_keywords=["Alpha Freight Mock"],
            excluded_keywords=[],
            reasons=["keyword_hit"],
        )

        self.assertEqual(result["confidence"], 0.85)
        self.assertIn("keyword_hit", result["reasons"])

    def test_template_does_not_include_broker_memory_or_business_risk_fields(self):
        template = build_broker_template(
            {
                "template_id": "alpha_freight_mock_v1",
                "broker_key": "alpha_freight_mock",
                "display_name": "Alpha Freight Mock",
                "version": "1",
                "created_for_testing": True,
            }
        )
        forbidden = {
            "credit_score",
            "days_to_pay",
            "factoring_status",
            "broker_risk",
            "payment_history",
            "dispatcher_experience",
        }

        self.assertFalse(forbidden.intersection(template.keys()))


if __name__ == "__main__":
    unittest.main()
