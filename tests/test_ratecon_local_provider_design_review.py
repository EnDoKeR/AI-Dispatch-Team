import copy
import json
import unittest
from pathlib import Path

from app.document_ai.ratecon_local_provider_design_review import (
    build_design_review,
    checklist_markdown,
    validate_design_review,
)
from app.document_ai.ratecon_model_provider_contract import default_provider_config
from app.document_ai.ratecon_model_provider_registry import evaluate_provider_readiness


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_design_review"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class RateConLocalProviderDesignReviewTests(unittest.TestCase):
    def _ready_review(self) -> dict:
        return build_design_review(
            evidence_pack_summary=_fixture("valid_evidence_pack_summary.json"),
            provider_name="local_model_placeholder_v1",
            design_review_id="local_provider_design_v1",
        )

    def test_valid_evidence_pack_summary_produces_design_pr_ready(self):
        review = self._ready_review()

        self.assertEqual(review["recommendation"], "design_pr_ready")
        self.assertTrue(review["evidence_pack_reference"]["validated"])
        self.assertGreater(len(review["acceptance_criteria"]), 0)
        self.assertFalse(review["proposed_provider_scope"]["runtime_execution_allowed"])
        self.assertFalse(review["proposed_provider_scope"]["pdf_processing_allowed"])
        self.assertFalse(review["proposed_provider_scope"]["ocr_allowed"])

    def test_missing_evidence_pack_produces_design_review_incomplete(self):
        review = build_design_review(
            evidence_pack_summary=_fixture("missing_evidence_pack_summary.json"),
            provider_name="local_model_placeholder_v1",
            design_review_id="local_provider_design_v1",
        )

        self.assertEqual(review["recommendation"], "design_review_incomplete")
        self.assertTrue(any("evidence pack reference" in blocker for blocker in review["blockers"]))

    def test_evidence_pack_recommendation_reject_blocks_design(self):
        review = build_design_review(
            evidence_pack_summary=_fixture("invalid_evidence_recommendation_reject.json"),
            provider_name="local_model_placeholder_v1",
            design_review_id="local_provider_design_v1",
        )

        self.assertEqual(review["recommendation"], "reject")
        self.assertTrue(any("recommendation" in blocker for blocker in review["blockers"]))

    def test_evidence_pack_recommendation_fixture_only_continue_blocks_design(self):
        review = build_design_review(
            evidence_pack_summary=_fixture("invalid_evidence_recommendation_fixture_only_continue.json"),
            provider_name="local_model_placeholder_v1",
            design_review_id="local_provider_design_v1",
        )

        self.assertEqual(review["recommendation"], "reject")
        self.assertTrue(any("recommendation" in blocker for blocker in review["blockers"]))

    def test_unsafe_fixture_designs_reject(self):
        cases = {
            "unsafe_design_runtime_execution_allowed.json": "runtime_execution_allowed",
            "unsafe_design_pdf_processing_allowed.json": "pdf_processing_allowed",
            "unsafe_design_external_calls_allowed.json": "external_calls_allowed",
            "unsafe_design_auto_accept_allowed.json": "auto_accept_forbidden",
        }
        for fixture_name, expected_blocker in cases.items():
            with self.subTest(fixture_name=fixture_name):
                validation = validate_design_review(_fixture(fixture_name))
                self.assertEqual(validation.recommendation, "reject")
                self.assertTrue(any(expected_blocker in blocker for blocker in validation.blockers))

    def test_ocr_allowed_true_rejects(self):
        review = self._ready_review()
        review["proposed_provider_scope"]["ocr_allowed"] = True
        validation = validate_design_review(review)

        self.assertEqual(validation.recommendation, "reject")
        self.assertTrue(any("ocr_allowed" in blocker for blocker in validation.blockers))

    def test_model_weight_download_allowed_true_rejects(self):
        review = self._ready_review()
        review["proposed_provider_scope"]["model_weight_download_allowed"] = True
        validation = validate_design_review(review)

        self.assertEqual(validation.recommendation, "reject")
        self.assertTrue(any("model_weight_download_allowed" in blocker for blocker in validation.blockers))

    def test_private_pdf_input_true_rejects(self):
        review = self._ready_review()
        review["input_policy"]["private_pdf_input"] = True
        validation = validate_design_review(review)

        self.assertEqual(validation.recommendation, "reject")
        self.assertTrue(any("private_pdf_input" in blocker for blocker in validation.blockers))

    def test_private_text_and_image_inputs_true_reject(self):
        for key in ("private_text_input", "private_image_input"):
            with self.subTest(key=key):
                review = self._ready_review()
                review["input_policy"][key] = True
                validation = validate_design_review(review)
                self.assertEqual(validation.recommendation, "reject")
                self.assertTrue(any(key in blocker for blocker in validation.blockers))

    def test_stops_review_required_false_rejects(self):
        review = self._ready_review()
        review["output_policy"]["stops_review_required"] = False
        validation = validate_design_review(review)

        self.assertEqual(validation.recommendation, "reject")
        self.assertTrue(any("stops_review_required" in blocker for blocker in validation.blockers))

    def test_auto_accept_forbidden_false_rejects(self):
        review = self._ready_review()
        review["output_policy"]["auto_accept_forbidden"] = False
        validation = validate_design_review(review)

        self.assertEqual(validation.recommendation, "reject")
        self.assertTrue(any("auto_accept_forbidden" in blocker for blocker in validation.blockers))

    def test_manual_baseline_required_false_rejects(self):
        review = self._ready_review()
        review["benchmark_policy"]["manual_baseline_required"] = False
        validation = validate_design_review(review)

        self.assertEqual(validation.recommendation, "reject")
        self.assertTrue(any("manual_baseline_required" in blocker for blocker in validation.blockers))

    def test_generated_pr_checklist_contains_no_private_values(self):
        checklist = checklist_markdown(self._ready_review())

        self.assertNotIn("SECRET_PRIVATE", checklist)
        self.assertNotIn("PRIVATE_VALUE", checklist)
        self.assertNotIn("data/private_ratecons", checklist)

    def test_generated_pr_checklist_states_design_is_not_implementation_approval(self):
        checklist = checklist_markdown(self._ready_review())

        self.assertIn("not implementation approval", checklist)
        self.assertIn("does not approve model execution", checklist)
        self.assertIn("Implementation requires a separate PR", checklist)

    def test_design_review_cannot_unblock_real_model_placeholders(self):
        review = self._ready_review()
        self.assertEqual(review["recommendation"], "design_pr_ready")
        for provider_name in ("local_model_placeholder_v1", "cloud_model_placeholder_v1"):
            with self.subTest(provider_name=provider_name):
                payload = copy.deepcopy(review)
                payload["provider_name"] = provider_name
                evaluation = evaluate_provider_readiness(
                    provider_name,
                    {"schema_version": "ratecon_local_provider_readiness_v1"},
                    default_provider_config(provider_name),
                )
                self.assertFalse(evaluation["provider_execution_allowed"])


if __name__ == "__main__":
    unittest.main()
