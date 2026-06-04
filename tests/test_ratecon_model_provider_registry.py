import unittest

from app.document_ai.ratecon_model_provider_contract import default_provider_config
from app.document_ai.ratecon_model_provider_registry import (
    dry_run_provider_plan,
    get_provider_descriptor,
    list_available_providers,
    provider_blocking_reasons,
    validate_provider_selection,
)


class RateConModelProviderRegistryTests(unittest.TestCase):
    def test_registry_lists_required_providers(self):
        names = {provider["provider_name"] for provider in list_available_providers()}

        self.assertIn("stub_empty_v1", names)
        self.assertIn("manual_baseline_reference_v1", names)
        self.assertIn("local_model_placeholder_v1", names)
        self.assertIn("cloud_model_placeholder_v1", names)

    def test_stub_provider_is_runnable_only_in_safe_config(self):
        descriptor = get_provider_descriptor("stub_empty_v1")
        validation = validate_provider_selection(default_provider_config("stub_empty_v1"))

        self.assertTrue(descriptor.can_execute)
        self.assertEqual(descriptor.status, "ready_stub_only")
        self.assertTrue(validation.valid)

    def test_local_model_placeholder_is_blocked(self):
        descriptor = get_provider_descriptor("local_model_placeholder_v1")
        validation = validate_provider_selection(default_provider_config("local_model_placeholder_v1"))

        self.assertFalse(descriptor.can_execute)
        self.assertFalse(validation.valid)
        self.assertIn("blocked_real_model_execution_not_implemented", provider_blocking_reasons("local_model_placeholder_v1"))

    def test_cloud_model_placeholder_is_blocked(self):
        descriptor = get_provider_descriptor("cloud_model_placeholder_v1")
        validation = validate_provider_selection(default_provider_config("cloud_model_placeholder_v1"))

        self.assertFalse(descriptor.can_execute)
        self.assertFalse(validation.valid)
        self.assertTrue(any("network" in reason.lower() for reason in provider_blocking_reasons("cloud_model_placeholder_v1")))

    def test_manual_baseline_reference_is_not_executable(self):
        validation = validate_provider_selection(default_provider_config("manual_baseline_reference_v1"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("manual_baseline" in error for error in validation.errors))

    def test_dry_run_provider_plan_has_no_execution(self):
        plan = dry_run_provider_plan(default_provider_config("stub_empty_v1"), template_count=3)

        self.assertTrue(plan["config_valid"])
        self.assertFalse(plan["execution_planned"])
        self.assertFalse(plan["external_api_calls_attempted"])
        self.assertFalse(plan["pdf_processing_attempted"])
        self.assertFalse(plan["ocr_attempted"])
        self.assertFalse(plan["ai_model_invocation_attempted"])
        self.assertEqual(plan["template_count"], 3)


if __name__ == "__main__":
    unittest.main()
