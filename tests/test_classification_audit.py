import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.document_ai.classification_audit import (
    DEFAULT_CLASSIFICATION_AUDIT_REPORT,
    build_classification_audit_report,
    write_classification_audit_report,
)


class ClassificationAuditTests(unittest.TestCase):
    def _rows(self):
        return [
            {
                "document_alias": "RATECON_001",
                "document_type": "RATE_CONFIRMATION",
                "ratecon_eligible": True,
                "supplemental_only": False,
                "classification_status": "ratecon_eligible",
                "page_role_counts": {"MAIN_RATECONF": 1},
                "section_role_counts": {"RATE_SUMMARY": 1, "STOP_TABLE": 1},
                "extraction_scope_counts": {"RATECON_CORE_ALLOWED": 1},
                "classification_warning_codes": ["scope_limited"],
                "classification_reason_codes": ["main_confirmation_signals"],
                "candidate_counts_by_field": {"rate": 1},
                "blocker_categories": ["TEMPLATE_GAP"],
            },
            {
                "document_alias": "RATECON_002",
                "document_type": "BILL_OF_LADING",
                "ratecon_eligible": False,
                "supplemental_only": True,
                "classification_status": "supplemental_only",
                "page_role_counts": {"BOL": 1},
                "section_role_counts": {"BOL_BODY": 1},
                "blocker_categories": ["SUPPLEMENTAL_DOCUMENT_ONLY"],
            },
        ]

    def test_audit_report_uses_aliases_and_safe_classification_fields(self):
        text = build_classification_audit_report(self._rows())

        self.assertIn("RATECON_001", text)
        self.assertIn("RATE_CONFIRMATION", text)
        self.assertIn("BILL_OF_LADING", text)
        self.assertIn("ratecon_eligible: 1", text)
        self.assertNotIn("FAKE BROKER LLC", text)
        self.assertNotIn("raw_text", text)

    def test_audit_report_writer_uses_ignored_default_path(self):
        self.assertEqual(
            DEFAULT_CLASSIFICATION_AUDIT_REPORT.as_posix(),
            ".local_outputs/private_ratecon_measurement/classification_audit_report.md",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "classification_audit_report.md"
            written = write_classification_audit_report(self._rows(), output_path=path)
            text = written.read_text(encoding="utf-8")

        self.assertIn("Safe Classification Audit Report", text)
        self.assertNotIn("raw_text", text)

    def test_default_audit_output_path_is_gitignored(self):
        result = subprocess.run(
            ["git", "check-ignore", str(DEFAULT_CLASSIFICATION_AUDIT_REPORT)],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0)

    def test_report_payload_serializes_without_private_values(self):
        text = build_classification_audit_report(self._rows())
        payload = json.dumps({"report": text})

        self.assertNotIn("3200.00", payload)
        self.assertNotIn("MC 123456", payload)


if __name__ == "__main__":
    unittest.main()
