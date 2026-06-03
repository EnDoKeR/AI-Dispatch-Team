import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.run_ratecon_hybrid_eval_stub import (
    HybridEvalStubError,
    build_hybrid_result_template,
    build_stop_template,
    main,
    validate_hybrid_result_contract,
    validate_stop_contract,
    write_stub_outputs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class RateConHybridEvalStubTests(unittest.TestCase):
    def test_contract_schema_validates_minimal_hybrid_result(self):
        result = build_hybrid_result_template()

        validate_hybrid_result_contract(result)

        self.assertEqual(
            result["schema_version"],
            "ratecon_hybrid_extraction_result_v1",
        )
        self.assertEqual(result["model_provider"], "local_stub")
        self.assertTrue(result["requires_human_review"])

    def test_stop_schema_requires_role_and_review_required(self):
        stop = build_stop_template("pickup", 1)
        validate_stop_contract(stop)

        missing_review = dict(stop)
        missing_review["requires_human_review"] = False
        with self.assertRaises(HybridEvalStubError):
            validate_stop_contract(missing_review)

        bad_role = dict(stop)
        bad_role["role"] = "unknown"
        with self.assertRaises(HybridEvalStubError):
            validate_stop_contract(bad_role)

    def test_stub_refuses_without_confirm_private_local_run(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main([])

        self.assertNotEqual(context.exception.code, 0)

    def test_stub_writes_local_only_output(self):
        output_dir = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_eval_stub"
        shutil.rmtree(output_dir, ignore_errors=True)
        try:
            result = write_stub_outputs(output_dir=output_dir)

            self.assertFalse(result["external_api_calls_attempted"])
            self.assertTrue((output_dir / "hybrid_eval_plan_summary.json").exists())
            self.assertTrue((output_dir / "hybrid_result_template.json").exists())
            self.assertTrue((output_dir / "hybrid_eval_readme.md").exists())
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_stub_refuses_non_local_output_path(self):
        with self.assertRaises(HybridEvalStubError):
            write_stub_outputs(output_dir=REPO_ROOT / "tmp_hybrid_eval_stub")

    def test_no_external_api_call_path_exists_in_summary(self):
        output_dir = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_eval_stub_api"
        shutil.rmtree(output_dir, ignore_errors=True)
        try:
            write_stub_outputs(output_dir=output_dir)
            summary = json.loads(
                (output_dir / "hybrid_eval_plan_summary.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertFalse(summary["external_api_calls_attempted"])
            self.assertFalse(summary["pdf_processing_attempted"])
            self.assertFalse(summary["ai_model_invocation_attempted"])
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    def test_no_private_values_in_default_output(self):
        output_dir = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_eval_stub_redaction"
        eval_dir = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_eval_stub_eval"
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(eval_dir, ignore_errors=True)
        try:
            eval_dir.mkdir(parents=True)
            (eval_dir / "ratecon_gold_evaluation_summary.json").write_text(
                json.dumps(
                    {
                        "stop_metrics_consistent_summary": {
                            "private_like_value": "SECRET_STOP_VALUE"
                        },
                        "unsafe_private_key": "SECRET_SHOULD_NOT_APPEAR",
                    }
                ),
                encoding="utf-8",
            )

            write_stub_outputs(output_dir=output_dir, eval_dir=eval_dir)

            summary_text = (output_dir / "hybrid_eval_plan_summary.json").read_text(
                encoding="utf-8"
            )
            template_text = (output_dir / "hybrid_result_template.json").read_text(
                encoding="utf-8"
            )

            self.assertNotIn("SECRET_STOP_VALUE", summary_text)
            self.assertNotIn("SECRET_SHOULD_NOT_APPEAR", summary_text)
            self.assertNotIn("SECRET_STOP_VALUE", template_text)
            self.assertNotIn("SECRET_SHOULD_NOT_APPEAR", template_text)
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)
            shutil.rmtree(eval_dir, ignore_errors=True)

    def test_private_output_paths_are_ignored(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".local_outputs/", gitignore)
        self.assertIn(".local_outputs/**", gitignore)


if __name__ == "__main__":
    unittest.main()
