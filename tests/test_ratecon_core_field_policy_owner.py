import unittest

from app.document_ai import ratecon_core_field_policy as policy
from app.market_intelligence.intake import rate_confirmation_intake


EXPECTED_LEGACY_CRITICAL_FIELDS = (
    "document_id",
    "broker_name",
    "load_number",
    "rate",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "commodity",
    "weight",
)

EXPECTED_INTAKE_CORE_FIELDS = (
    "broker_name",
    "customer_name",
    "customer_or_broker",
    "load_number",
    "order_number",
    "pro_number",
    "tender_id",
    "tender_number",
    "shipment_number",
    "rate",
    "payment_amount",
    "total_carrier_pay",
    "agreed_amount",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
)

EXPECTED_DISPATCH_CRITICAL_FIELDS = (
    "broker_name",
    "broker_mc",
    "load_number",
    "rate",
    "pickup_location",
    "pickup_date",
    "pickup_time",
    "delivery_location",
    "delivery_date",
    "delivery_time",
    "equipment",
    "weight",
    "commodity",
    "special_requirement",
)

EXPECTED_EXTRACTION_REVIEW_FIELDS = (
    "broker_name",
    "customer_name",
    "customer_or_broker",
    "broker_mc",
    "load_number",
    "order_number",
    "pro_number",
    "tender_id",
    "tender_number",
    "shipment_number",
    "rate",
    "payment_amount",
    "total_carrier_pay",
    "agreed_amount",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "pickup_time",
    "delivery_time",
    "equipment",
    "weight",
    "commodity",
    "special_requirement",
    "reference",
    "customer_reference",
    "po_number",
    "bol_number",
)


class RateconCoreFieldPolicyOwnerTests(unittest.TestCase):
    def test_canonical_owner_exposes_legacy_critical_fields(self):
        self.assertEqual(
            policy.get_legacy_critical_fields(),
            EXPECTED_LEGACY_CRITICAL_FIELDS,
        )

    def test_legacy_critical_fields_surface_still_matches_prior_values(self):
        self.assertIsInstance(rate_confirmation_intake.CRITICAL_FIELDS, list)
        self.assertEqual(
            tuple(rate_confirmation_intake.CRITICAL_FIELDS),
            EXPECTED_LEGACY_CRITICAL_FIELDS,
        )
        self.assertEqual(
            rate_confirmation_intake.CRITICAL_FIELDS,
            list(policy.get_legacy_critical_fields()),
        )

    def test_readiness_required_fields_match_previous_intake_core_behavior(self):
        self.assertEqual(
            policy.get_readiness_required_fields(),
            EXPECTED_INTAKE_CORE_FIELDS,
        )
        self.assertEqual(
            policy.get_readiness_required_fields(),
            tuple(
                policy.get_required_fields_for_readiness(
                    policy.FIELD_POLICY_ROLE_INTAKE_CORE
                )
            ),
        )

    def test_intake_core_fields_match_previous_behavior(self):
        self.assertEqual(policy.get_intake_core_fields(), EXPECTED_INTAKE_CORE_FIELDS)

    def test_dispatch_critical_fields_match_previous_behavior(self):
        self.assertEqual(
            policy.get_dispatch_critical_fields(),
            EXPECTED_DISPATCH_CRITICAL_FIELDS,
        )

    def test_extraction_review_fields_match_previous_behavior(self):
        self.assertEqual(
            policy.get_extraction_review_fields(),
            EXPECTED_EXTRACTION_REVIEW_FIELDS,
        )

    def test_required_operational_fields_remain_present_where_applicable(self):
        self.assertIn("load_number", policy.get_intake_core_fields())
        self.assertIn("rate", policy.get_intake_core_fields())
        self.assertIn("pickup_location", policy.get_intake_core_fields())
        self.assertIn("pickup_date", policy.get_intake_core_fields())
        self.assertIn("delivery_location", policy.get_intake_core_fields())
        self.assertIn("delivery_date", policy.get_intake_core_fields())
        self.assertIn("broker_name", policy.get_dispatch_critical_fields())
        self.assertIn("broker_mc", policy.get_dispatch_critical_fields())
        self.assertIn("commodity", policy.get_dispatch_critical_fields())
        self.assertIn("weight", policy.get_dispatch_critical_fields())

    def test_legacy_imports_and_intake_behavior_still_work(self):
        source = {
            "document_id": "DOC-1",
            "broker_name": "Example Broker",
            "load_number": "LOAD-1",
            "rate": "1200",
            "pickup_location": "City A",
            "pickup_date": "2026-01-01",
            "delivery_location": "City B",
            "delivery_date": "2026-01-02",
            "commodity": "General",
            "weight": "1000",
        }
        intake = rate_confirmation_intake.build_rate_confirmation_intake(source)
        self.assertEqual(intake["missing_fields"], [])
        self.assertEqual(intake["status"], rate_confirmation_intake.STATUS_READY_FOR_REVIEW)

    def test_importing_policy_and_legacy_intake_does_not_create_circular_import(self):
        self.assertTrue(policy.POLICY_VERSION)
        self.assertTrue(rate_confirmation_intake.CRITICAL_FIELDS)


if __name__ == "__main__":
    unittest.main()
