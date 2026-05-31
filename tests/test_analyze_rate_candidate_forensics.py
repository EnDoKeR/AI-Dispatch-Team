import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from app.document_ai.rate_candidate_forensics import (
    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
    RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
    RATE_FORENSICS_JSON,
    RATE_FORENSICS_MD,
    RATE_FORENSICS_RAW_JSON,
)
from scripts import analyze_rate_candidate_forensics as cli


def _write_safe_summary(root, rows):
    (root / "safe_summary.json").write_text(
        json.dumps({"rows": rows}),
        encoding="utf-8",
    )


class AnalyzeRateCandidateForensicsCliTests(unittest.TestCase):
    def test_cli_writes_reports_and_console_is_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_safe_summary(
                root,
                [
                    {
                        "document_alias": "RATECON_001",
                        "rate_forensics_records": [
                            {
                                "measurement_alias": "RATECON_001",
                                "rate_candidate_count": 2,
                                "main_rate_candidate_count": 2,
                                "conflict_present": True,
                                "conflict_reason": RATE_CONFLICT_MULTIPLE_STRONG_TOTALS,
                                "category_counts": {
                                    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY: 2
                                },
                            }
                        ],
                    }
                ],
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(
                    ["--input-dir", str(root), "--write-md", "--write-json"]
                )

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            self.assertIn("documents_analyzed: 1", output)
            self.assertIn("conflict_count: 1", output)
            self.assertIn(RATE_CONFLICT_MULTIPLE_STRONG_TOTALS, output)
            self.assertIn("money_values_printed: False", output)
            self.assertNotIn("$", output)
            self.assertNotIn("FAKE_RATE", output)
            self.assertTrue((root / RATE_FORENSICS_MD).exists())
            self.assertTrue((root / RATE_FORENSICS_JSON).exists())

    def test_cli_prefers_raw_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / RATE_FORENSICS_RAW_JSON).write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "measurement_alias": "RATECON_001",
                                "rate_candidate_count": 1,
                                "main_rate_candidate_count": 1,
                                "category_counts": {
                                    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY: 1
                                },
                            }
                        ],
                        "aggregate": {"document_count": 1},
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", str(root)])

            self.assertEqual(result, 0)
            self.assertIn("rate_candidate_count: 1", stdout.getvalue())

    def test_cli_missing_data_returns_friendly_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(["--input-dir", tmp])

        self.assertEqual(result, 2)
        self.assertIn("rate_candidate_forensics_error", stdout.getvalue())

    def test_cli_can_omit_alias_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_safe_summary(root, [{"document_alias": "RATECON_001"}])

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = cli.main(
                    ["--input-dir", str(root), "--no-console-alias-details"]
                )

        self.assertEqual(result, 0)
        self.assertNotIn("aliases_for_", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
