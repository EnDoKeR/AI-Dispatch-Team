import json
import unittest
from pathlib import Path

from app.document_ai.ratecon_local_provider_readiness import (
    default_readiness_template,
    validate_readiness_payload,
)
from app.document_ai.ratecon_model_provider_contract import default_provider_config
from app.document_ai.ratecon_model_provider_registry import evaluate_provider_readiness


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_readiness"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class RateConLocalProviderReadinessTests(unittest.TestCase):
    def test_valid_fixture_only_readiness_passes_as_fixture_only_plan(self):
        validation = validate_readiness_payload(_fixture("valid_fixture_only_readiness.json"))

        self.assertTrue(validation.valid)
        self.assertEqual(validation.status, "fixture_only_plan_valid")

    def test_private_local_execution_approval_fails_in_this_phase(self):
        validation = validate_readiness_payload(_fixture("invalid_private_execution_approved.json"))

        self.assertFalse(validation.valid)
        self.assertEqual(validation.status, "private_local_execution_not_approved")
        self.assertTrue(any("private_local_only" in error for error in validation.errors))

    def test_cloud_approval_fails(self):
        validation = validate_readiness_payload(_fixture("invalid_cloud_approved.json"))

        self.assertFalse(validation.valid)
        self.assertEqual(validation.status, "cloud_execution_forbidden")
        self.assertTrue(any("approved_for_cloud" in error for error in validation.errors))

    def test_external_calls_requested_fails(self):
        validation = validate_readiness_payload(_fixture("invalid_external_calls_requested.json"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("external_calls" in error for error in validation.errors))

    def test_auto_accept_disabled_false_fails(self):
        validation = validate_readiness_payload(_fixture("invalid_auto_accept_enabled.json"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("auto_accept_disabled" in error for error in validation.errors))

    def test_stops_review_required_false_fails(self):
        validation = validate_readiness_payload(_fixture("invalid_stops_not_review_required.json"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("stops_review_required" in error for error in validation.errors))

    def test_production_output_unchanged_false_fails(self):
        payload = _fixture("valid_fixture_only_readiness.json")
        payload["safety_review"]["production_output_unchanged"] = False
        validation = validate_readiness_payload(payload)

        self.assertFalse(validation.valid)
        self.assertTrue(any("production_output_unchanged" in error for error in validation.errors))

    def test_missing_manual_baseline_fails(self):
        validation = validate_readiness_payload(_fixture("invalid_missing_manual_baseline.json"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("manual_baseline_required" in error for error in validation.errors))

    def test_missing_fixture_smoke_test_fails(self):
        validation = validate_readiness_payload(_fixture("invalid_missing_fixture_smoke_test.json"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("fixture_smoke_test_required" in error for error in validation.errors))

    def test_readiness_cannot_unblock_local_model_placeholder(self):
        payload = default_readiness_template(provider_name="local_model_placeholder_v1", provider_type="local_model_placeholder")
        evaluation = evaluate_provider_readiness(
            "local_model_placeholder_v1",
            payload,
            default_provider_config("local_model_placeholder_v1"),
        )

        self.assertFalse(evaluation["provider_execution_allowed"])
        self.assertEqual(evaluation["provider_readiness_status"], "private_local_execution_not_approved")
        self.assertTrue(any("not executable" in reason for reason in evaluation["blocking_reasons"]))

    def test_readiness_cannot_unblock_cloud_model_placeholder(self):
        payload = default_readiness_template(provider_name="cloud_model_placeholder_v1", provider_type="cloud_model_placeholder")
        evaluation = evaluate_provider_readiness(
            "cloud_model_placeholder_v1",
            payload,
            default_provider_config("cloud_model_placeholder_v1"),
        )

        self.assertFalse(evaluation["provider_execution_allowed"])
        self.assertEqual(evaluation["provider_readiness_status"], "cloud_execution_forbidden")
        self.assertTrue(any("forbidden" in reason for reason in evaluation["blocking_reasons"]))


if __name__ == "__main__":
    unittest.main()
