import copy
import unittest

from app.document_ai.ratecon_hybrid_contract import build_hybrid_result_template
from app.document_ai.ratecon_model_assisted_contract import (
    build_model_assisted_submission,
    validate_model_assisted_submission,
)


class RateConModelAssistedContractTests(unittest.TestCase):
    def test_valid_stub_submission_passes_contract_validation(self):
        submission = build_model_assisted_submission(build_hybrid_result_template("DOC-1"))

        validation = validate_model_assisted_submission(submission)

        self.assertTrue(validation.valid)

    def test_external_call_made_true_fails(self):
        submission = build_model_assisted_submission(build_hybrid_result_template("DOC-1"))
        submission["provider"]["external_call_made"] = True

        validation = validate_model_assisted_submission(submission)

        self.assertFalse(validation.valid)
        self.assertTrue(any("external_call_made" in error for error in validation.errors))

    def test_offline_only_false_fails(self):
        submission = build_model_assisted_submission(build_hybrid_result_template("DOC-1"))
        submission["provider"]["offline_only"] = False

        validation = validate_model_assisted_submission(submission)

        self.assertFalse(validation.valid)
        self.assertTrue(any("offline_only" in error for error in validation.errors))

    def test_cloud_model_provider_fails_in_this_phase(self):
        submission = build_model_assisted_submission(
            build_hybrid_result_template("DOC-1"),
            provider_type="cloud_model",
            provider_name="future_cloud_provider",
        )

        validation = validate_model_assisted_submission(submission)

        self.assertFalse(validation.valid)
        self.assertTrue(any("cloud_model" in error for error in validation.errors))

    def test_stop_auto_accept_true_fails(self):
        submission = build_model_assisted_submission(build_hybrid_result_template("DOC-1"))
        submission["result"]["fields"]["pickup_stops"][0]["auto_accept"] = True

        validation = validate_model_assisted_submission(submission)

        self.assertFalse(validation.valid)
        self.assertTrue(any("auto_accept" in error for error in validation.errors))

    def test_stop_requires_human_review_false_fails(self):
        submission = build_model_assisted_submission(build_hybrid_result_template("DOC-1"))
        submission["result"]["fields"]["pickup_stops"][0]["requires_human_review"] = False

        validation = validate_model_assisted_submission(submission)

        self.assertFalse(validation.valid)
        self.assertTrue(any("requires_human_review" in error for error in validation.errors))

    def test_missing_evidence_for_filled_value_fails(self):
        submission = build_model_assisted_submission(build_hybrid_result_template("DOC-1"))
        submission["result"]["fields"]["load_number"]["value"] = "LOAD-123"

        validation = validate_model_assisted_submission(submission)

        self.assertFalse(validation.valid)
        self.assertTrue(any("no evidence" in error for error in validation.errors))

    def test_private_local_only_false_fails(self):
        submission = build_model_assisted_submission(build_hybrid_result_template("DOC-1"))
        submission["input_policy"]["private_local_only"] = False

        validation = validate_model_assisted_submission(submission)

        self.assertFalse(validation.valid)
        self.assertTrue(any("private_local_only" in error for error in validation.errors))

    def test_validation_does_not_mutate_submission(self):
        submission = build_model_assisted_submission(build_hybrid_result_template("DOC-1"))
        original = copy.deepcopy(submission)

        validate_model_assisted_submission(submission)

        self.assertEqual(submission, original)


if __name__ == "__main__":
    unittest.main()
