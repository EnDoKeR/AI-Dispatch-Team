import io
import json
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts.create_ratecon_local_provider_design_review import (
    RateConLocalProviderDesignReviewError,
    create_design_review_outputs,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_design_review"
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_local_provider_design_review_cli"


class RateConLocalProviderDesignReviewCliTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def test_cli_refuses_without_confirm_flag(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(
                    [
                        "--evidence-pack-summary",
                        str(FIXTURES / "valid_evidence_pack_summary.json"),
                        "--output-dir",
                        str(OUTPUT_ROOT / "review"),
                    ]
                )
        self.assertNotEqual(context.exception.code, 0)

    def test_cli_refuses_output_outside_local_outputs(self):
        with self.assertRaises(RateConLocalProviderDesignReviewError):
            create_design_review_outputs(
                evidence_pack_summary=FIXTURES / "valid_evidence_pack_summary.json",
                output_dir=REPO_ROOT / "ratecon_design_review",
            )

    def test_cli_writes_summary_report_csv_and_checklist(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "--evidence-pack-summary",
                    str(FIXTURES / "valid_evidence_pack_summary.json"),
                    "--output-dir",
                    str(OUTPUT_ROOT / "review"),
                    "--confirm-private-local-run",
                    "--provider-name",
                    "local_model_placeholder_v1",
                    "--design-id",
                    "local_provider_design_v1",
                    "--fixture-only",
                ]
            )

        self.assertEqual(code, 0)
        self.assertTrue((OUTPUT_ROOT / "review" / "local_provider_design_review_summary.json").exists())
        self.assertTrue((OUTPUT_ROOT / "review" / "local_provider_design_review_report.md").exists())
        self.assertTrue((OUTPUT_ROOT / "review" / "local_provider_design_acceptance_criteria.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "review" / "local_provider_design_blockers.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "review" / "local_provider_design_next_actions.csv").exists())
        self.assertTrue((OUTPUT_ROOT / "review" / "local_provider_design_pr_checklist.md").exists())
        summary = json.loads((OUTPUT_ROOT / "review" / "local_provider_design_review_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["recommendation"], "design_pr_ready")
        self.assertFalse(summary["proposed_provider_scope"]["runtime_execution_allowed"])
        self.assertIn("provider_execution_allowed: False", stdout.getvalue())
        self.assertIn("pdf_processing_attempted: False", stdout.getvalue())
        self.assertIn("ocr_attempted: False", stdout.getvalue())
        self.assertIn("external_api_calls_attempted: False", stdout.getvalue())

    def test_missing_evidence_pack_file_writes_incomplete_review(self):
        review = create_design_review_outputs(
            evidence_pack_summary=OUTPUT_ROOT / "missing_summary.json",
            output_dir=OUTPUT_ROOT / "missing_review",
        )

        self.assertEqual(review["recommendation"], "design_review_incomplete")
        self.assertTrue((OUTPUT_ROOT / "missing_review" / "local_provider_design_review_summary.json").exists())

    def test_generated_pr_checklist_contains_no_private_values(self):
        create_design_review_outputs(
            evidence_pack_summary=FIXTURES / "valid_evidence_pack_summary.json",
            output_dir=OUTPUT_ROOT / "review",
        )
        checklist = (OUTPUT_ROOT / "review" / "local_provider_design_pr_checklist.md").read_text(encoding="utf-8")

        self.assertNotIn("SECRET_PRIVATE", checklist)
        self.assertNotIn("PRIVATE_VALUE", checklist)
        self.assertNotIn("data/private_ratecons", checklist)

    def test_generated_pr_checklist_states_design_is_not_implementation_approval(self):
        create_design_review_outputs(
            evidence_pack_summary=FIXTURES / "valid_evidence_pack_summary.json",
            output_dir=OUTPUT_ROOT / "review",
        )
        checklist = (OUTPUT_ROOT / "review" / "local_provider_design_pr_checklist.md").read_text(encoding="utf-8")

        self.assertIn("not implementation approval", checklist)
        self.assertIn("does not approve model execution", checklist)

    def test_no_private_values_in_fixtures_or_default_output(self):
        create_design_review_outputs(
            evidence_pack_summary=FIXTURES / "valid_evidence_pack_summary.json",
            output_dir=OUTPUT_ROOT / "review",
        )
        fixture_text = "\n".join(path.read_text(encoding="utf-8") for path in FIXTURES.glob("*.json"))
        output_text = "\n".join(path.read_text(encoding="utf-8") for path in (OUTPUT_ROOT / "review").glob("*") if path.is_file())

        for token in ("SECRET_PRIVATE", "PRIVATE_VALUE", "data/private_ratecons"):
            self.assertNotIn(token, fixture_text)
            self.assertNotIn(token, output_text)

    def test_cli_rejects_when_redaction_is_disabled(self):
        with self.assertRaises(RateConLocalProviderDesignReviewError):
            create_design_review_outputs(
                evidence_pack_summary=FIXTURES / "valid_evidence_pack_summary.json",
                output_dir=OUTPUT_ROOT / "review",
                redact_default=False,
            )


if __name__ == "__main__":
    unittest.main()
