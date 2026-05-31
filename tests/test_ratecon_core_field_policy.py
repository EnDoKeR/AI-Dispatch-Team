import unittest

from app.document_ai.ratecon_core_field_policy import (
    FIELD_POLICY_ROLE_DISPATCH_DECISION,
    FIELD_POLICY_ROLE_INTAKE_CORE,
    FIELD_REQUIREMENT_NON_APPLICABLE,
    FIELD_REQUIREMENT_REQUIRED,
    FIELD_REQUIREMENT_REVIEW_REQUIRED,
    build_document_context,
    classify_field_policy_gap,
    get_field_requirement,
    get_required_fields_for_readiness,
    is_field_blocker_for_level,
)


class RateConCoreFieldPolicyTests(unittest.TestCase):
    def test_broker_mc_not_intake_blocker(self):
        context = build_document_context({"normal_load_movement": True})

        self.assertFalse(
            is_field_blocker_for_level(
                "broker_mc",
                "missing",
                FIELD_POLICY_ROLE_INTAKE_CORE,
                context,
            )
        )

    def test_equipment_weight_commodity_not_intake_blockers(self):
        context = build_document_context({"normal_load_movement": True})

        for field_name in ["equipment", "weight", "commodity"]:
            with self.subTest(field_name=field_name):
                self.assertFalse(
                    is_field_blocker_for_level(
                        field_name,
                        "missing",
                        FIELD_POLICY_ROLE_INTAKE_CORE,
                        context,
                    )
                )
                self.assertEqual(
                    get_field_requirement(
                        field_name,
                        FIELD_POLICY_ROLE_INTAKE_CORE,
                        context,
                    ),
                    FIELD_REQUIREMENT_REVIEW_REQUIRED,
                )

    def test_pickup_and_delivery_dates_are_intake_blockers_for_normal_load(self):
        context = build_document_context({"normal_load_movement": True})

        for field_name in ["pickup_date", "delivery_date"]:
            with self.subTest(field_name=field_name):
                self.assertEqual(
                    get_field_requirement(
                        field_name,
                        FIELD_POLICY_ROLE_INTAKE_CORE,
                        context,
                    ),
                    FIELD_REQUIREMENT_REQUIRED,
                )
                self.assertTrue(
                    is_field_blocker_for_level(
                        field_name,
                        "missing",
                        FIELD_POLICY_ROLE_INTAKE_CORE,
                        context,
                    )
                )

    def test_pickup_time_not_hard_intake_blocker(self):
        context = build_document_context({"normal_load_movement": True})

        self.assertEqual(
            get_field_requirement(
                "pickup_time",
                FIELD_POLICY_ROLE_INTAKE_CORE,
                context,
            ),
            FIELD_REQUIREMENT_REVIEW_REQUIRED,
        )
        self.assertFalse(
            is_field_blocker_for_level(
                "pickup_time",
                "missing",
                FIELD_POLICY_ROLE_INTAKE_CORE,
                context,
            )
        )

    def test_normal_stop_fields_non_applicable_for_tonu(self):
        context = build_document_context({"document_type": "TRUCK_ORDER_NOT_USED"})

        self.assertEqual(
            get_field_requirement(
                "pickup_date",
                FIELD_POLICY_ROLE_INTAKE_CORE,
                context,
            ),
            FIELD_REQUIREMENT_NON_APPLICABLE,
        )

    def test_ocr_docs_do_not_create_digital_missing_blockers(self):
        context = build_document_context({"extraction_status": "EMPTY_TEXT"})

        self.assertEqual(
            get_field_requirement("rate", FIELD_POLICY_ROLE_INTAKE_CORE, context),
            FIELD_REQUIREMENT_NON_APPLICABLE,
        )
        self.assertFalse(
            is_field_blocker_for_level(
                "rate",
                "missing",
                FIELD_POLICY_ROLE_INTAKE_CORE,
                context,
            )
        )

    def test_supplemental_docs_do_not_create_ratecon_blockers(self):
        context = build_document_context(
            {"classification_status": "supplemental_only", "extraction_relevant": False}
        )

        self.assertEqual(
            get_field_requirement("rate", FIELD_POLICY_ROLE_INTAKE_CORE, context),
            FIELD_REQUIREMENT_NON_APPLICABLE,
        )

    def test_dispatch_decision_is_stricter_for_operational_fields(self):
        context = build_document_context({"normal_load_movement": True})

        self.assertTrue(
            is_field_blocker_for_level(
                "weight",
                "missing",
                FIELD_POLICY_ROLE_DISPATCH_DECISION,
                context,
            )
        )

    def test_policy_gap_classifies_optional_missing_field(self):
        context = build_document_context({"normal_load_movement": True})

        self.assertEqual(
            classify_field_policy_gap(
                "reference",
                "missing",
                FIELD_POLICY_ROLE_INTAKE_CORE,
                context,
            ),
            "optional_missing_field",
        )

    def test_required_field_listing_uses_context(self):
        normal_context = build_document_context({"normal_load_movement": True})
        tonu_context = build_document_context({"document_type": "TRUCK_ORDER_NOT_USED"})

        self.assertIn(
            "pickup_date",
            get_required_fields_for_readiness(
                FIELD_POLICY_ROLE_INTAKE_CORE,
                normal_context,
            ),
        )
        self.assertNotIn(
            "pickup_date",
            get_required_fields_for_readiness(
                FIELD_POLICY_ROLE_INTAKE_CORE,
                tonu_context,
            ),
        )


if __name__ == "__main__":
    unittest.main()
