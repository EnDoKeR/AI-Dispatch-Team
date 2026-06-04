import json
import unittest

from app.document_ai.ratecon_model_provider_contract import (
    default_provider_config,
    validate_provider_config,
)
from app.document_ai.ratecon_model_provider_registry import get_provider_descriptor


class RateConModelProviderContractTests(unittest.TestCase):
    def test_valid_stub_config_passes(self):
        validation = validate_provider_config(
            default_provider_config("stub_empty_v1"),
            get_provider_descriptor("stub_empty_v1"),
        )

        self.assertTrue(validation.valid)
        self.assertTrue(any(gate["gate"] == "external_calls_disabled" for gate in validation.safety_gates))

    def test_external_calls_true_fails(self):
        config = default_provider_config("stub_empty_v1")
        config["allow_external_calls"] = True

        validation = validate_provider_config(config, get_provider_descriptor("stub_empty_v1"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("allow_external_calls" in error for error in validation.errors))

    def test_pdf_processing_true_fails(self):
        config = default_provider_config("stub_empty_v1")
        config["allow_pdf_processing"] = True

        validation = validate_provider_config(config, get_provider_descriptor("stub_empty_v1"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("allow_pdf_processing" in error for error in validation.errors))

    def test_ocr_processing_true_fails(self):
        config = default_provider_config("stub_empty_v1")
        config["allow_ocr_processing"] = True

        validation = validate_provider_config(config, get_provider_descriptor("stub_empty_v1"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("allow_ocr_processing" in error for error in validation.errors))

    def test_secret_like_keys_fail(self):
        config = default_provider_config("stub_empty_v1")
        config["nested"] = {"token": "redacted-placeholder"}

        validation = validate_provider_config(config, get_provider_descriptor("stub_empty_v1"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("secret-like" in error for error in validation.errors))

    def test_output_redaction_default_false_fails(self):
        config = default_provider_config("stub_empty_v1")
        config["output_redaction_default"] = False

        validation = validate_provider_config(config, get_provider_descriptor("stub_empty_v1"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("output_redaction_default" in error for error in validation.errors))

    def test_cloud_placeholder_is_blocked(self):
        config = default_provider_config("cloud_model_placeholder_v1")

        validation = validate_provider_config(config, get_provider_descriptor("cloud_model_placeholder_v1"))

        self.assertFalse(validation.valid)
        self.assertTrue(any("cloud_model_placeholder" in error for error in validation.errors))

    def test_config_is_json_safe(self):
        config = default_provider_config("stub_empty_v1")

        self.assertEqual(json.loads(json.dumps(config)), config)


if __name__ == "__main__":
    unittest.main()
