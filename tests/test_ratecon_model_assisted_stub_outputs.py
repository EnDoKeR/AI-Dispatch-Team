import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.create_ratecon_model_assisted_stub_outputs import (
    ModelAssistedStubOutputError,
    create_model_assisted_stub_outputs,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_assisted"
OUTPUT_ROOT = REPO_ROOT / ".local_outputs" / "test_ratecon_model_assisted_stub_outputs"


class RateConModelAssistedStubOutputsTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)

    def test_stub_generator_refuses_without_confirm_flag(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main(["--templates-dir", str(FIXTURE_ROOT), "--output-dir", str(OUTPUT_ROOT / "out"), "--fixture-mode"])
        self.assertNotEqual(context.exception.code, 0)

    def test_stub_generator_refuses_output_outside_local_outputs(self):
        with self.assertRaises(ModelAssistedStubOutputError):
            create_model_assisted_stub_outputs(
                templates_dir=FIXTURE_ROOT,
                output_dir=REPO_ROOT / "model_assisted_stub_out",
                fixture_mode=True,
            )

    def test_stub_generator_writes_valid_local_outputs(self):
        summary = create_model_assisted_stub_outputs(
            templates_dir=FIXTURE_ROOT,
            output_dir=OUTPUT_ROOT / "stub",
            fixture_mode=False,
            copy_manual_template_shape=True,
            max_docs=1,
        )

        self.assertEqual(summary["submission_count"], 1)
        self.assertEqual(summary["valid_submission_count"], 1)
        self.assertFalse(summary["external_api_calls_attempted"])
        self.assertFalse(summary["pdf_processing_attempted"])
        self.assertFalse(summary["ocr_attempted"])
        self.assertFalse(summary["ai_model_invocation_attempted"])
        files = list((OUTPUT_ROOT / "stub").glob("*.model_assisted_submission.json"))
        self.assertEqual(len(files), 1)
        payload = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["provider"]["provider_type"], "stub")
        self.assertFalse(payload["provider"]["external_call_made"])
        for field_name in ("pickup_stops", "delivery_stops"):
            for stop in payload["result"]["fields"][field_name]:
                self.assertTrue(stop["requires_human_review"])
                self.assertFalse(stop["auto_accept"])

    def test_stub_generator_does_not_copy_private_values_by_default(self):
        private_dir = OUTPUT_ROOT / "templates"
        private_dir.mkdir(parents=True)
        template = json.loads((FIXTURE_ROOT / "fake_hybrid_template.hybrid_result.json").read_text(encoding="utf-8"))
        template["file_name"] = "SECRET_PRIVATE_FILE.pdf"
        (private_dir / "private.hybrid_result.json").write_text(json.dumps(template), encoding="utf-8")

        create_model_assisted_stub_outputs(
            templates_dir=private_dir,
            output_dir=OUTPUT_ROOT / "stub",
            copy_manual_template_shape=True,
        )

        output_text = "\n".join(path.read_text(encoding="utf-8") for path in (OUTPUT_ROOT / "stub").glob("*") if path.is_file())
        self.assertNotIn("SECRET_PRIVATE_FILE", output_text)


if __name__ == "__main__":
    unittest.main()
