import io
import json
import shutil
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts.create_ratecon_hybrid_result_templates import (
    HybridTemplateError,
    create_hybrid_result_templates,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class RateConHybridResultTemplateTests(unittest.TestCase):
    def setUp(self):
        self.root = REPO_ROOT / ".local_outputs" / "test_ratecon_hybrid_templates"
        shutil.rmtree(self.root, ignore_errors=True)
        self.output_dir = self.root / "templates"
        self.audit = self.root / "audit.jsonl"
        self.root.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_refuses_without_confirm_private_local_run(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                main([])

        self.assertNotEqual(context.exception.code, 0)

    def test_refuses_output_outside_local_outputs(self):
        with self.assertRaises(HybridTemplateError):
            create_hybrid_result_templates(
                audit=None,
                output_dir=REPO_ROOT / "tmp_hybrid_templates",
            )

    def test_creates_blank_templates_from_audit_aliases(self):
        self.audit.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "document_id": "RATECON_001",
                            "file_name": "FAKE_LOCAL_NAME.pdf",
                            "file_hash_prefix": "abc123",
                        }
                    ),
                    json.dumps({"document_id": "RATECON_002"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        summary = create_hybrid_result_templates(
            audit=self.audit,
            output_dir=self.output_dir,
        )

        self.assertEqual(summary["template_count"], 2)
        first = json.loads(
            (self.output_dir / "RATECON_001.hybrid_result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(first["fields"]["pickup_stops"][0]["requires_human_review"])
        self.assertFalse(first["fields"]["pickup_stops"][0]["auto_accept"])
        self.assertNotIn("FAKE_LOCAL_NAME", json.dumps(first))
        self.assertTrue((self.output_dir / "hybrid_template_index.csv").exists())
        self.assertTrue((self.output_dir / "hybrid_template_readme.md").exists())

    def test_private_values_only_with_explicit_flag(self):
        self.audit.write_text(
            json.dumps(
                {
                    "document_id": "RATECON_001",
                    "file_name": "FAKE_LOCAL_NAME.pdf",
                    "file_hash_prefix": "abc123",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        create_hybrid_result_templates(
            audit=self.audit,
            output_dir=self.output_dir,
            include_private_values_local_only=True,
        )
        payload = json.loads(
            (self.output_dir / "RATECON_001.hybrid_result.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(payload["file_name"], "FAKE_LOCAL_NAME.pdf")
        self.assertEqual(payload["file_hash_prefix"], "abc123")

    def test_creates_single_generic_template_without_audit(self):
        summary = create_hybrid_result_templates(audit=None, output_dir=self.output_dir)

        self.assertEqual(summary["template_count"], 1)
        self.assertTrue((self.output_dir / "RATECON_001.hybrid_result.json").exists())


if __name__ == "__main__":
    unittest.main()
