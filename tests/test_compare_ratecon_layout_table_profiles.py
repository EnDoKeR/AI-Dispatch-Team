import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.compare_ratecon_layout_table_profiles import main


def fake_record(profile="default", load_present=1, table_cell_pairings=1):
    return {
        "document_id": f"RATECON_{profile}",
        "shadow": {"success": True, "needs_review": True, "review_reasons": []},
        "triage": {"pdf_type": "born_digital", "quality_flags": []},
        "artifact_summary": {
            "layout_provider_summary": {
                "provider_requested": "pdfplumber",
                "provider_used": "pdfplumber",
                "available": True,
                "status": "success",
                "pages_with_words": 1,
                "pages_with_lines": 1,
                "pages_with_tables": 1,
                "word_count": 10,
                "line_count": 3,
                "table_count": 1,
                "table_cell_count": 4,
                "warnings": [],
                "errors": [],
            }
        },
        "candidate_summary": {
            "candidates_by_field": {"load_number": load_present} if load_present else {},
            "table_extraction_summary": {
                "tables_detected": 1,
                "recognized_stop_tables": 1,
                "recognized_load_tables": load_present,
                "recognized_rate_tables": 0,
                "table_header_role_counts": {"load_identity": load_present},
                "table_row_role_counts": {"stop_role": 1},
            },
            "layout_load_pairing_summary": {
                "layout_candidates_emitted": load_present,
                "table_cell_pairings": table_cell_pairings,
            },
            "layout_stop_pairing_summary": {
                "layout_structured_stop_candidates": 1,
            },
        },
        "legacy_shadow_comparison": {},
        "failure_attribution": {"primary_suspected_layer": "candidate_generation", "codes": []},
    }


class CompareRateConLayoutTableProfilesTests(unittest.TestCase):
    def test_cli_compares_profile_outputs_safely(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = []
            for profile, load_present in [("default", 0), ("lines", 1)]:
                summary_path = root / f"{profile}_summary.json"
                audit_path = root / f"{profile}_audit.jsonl"
                summary_path.write_text('{"documents_processed": 1}', encoding="utf-8")
                audit_path.write_text(
                    json.dumps(fake_record(profile=profile, load_present=load_present)) + "\n",
                    encoding="utf-8",
                )
                paths.append(f"{profile}|{summary_path}|{audit_path}")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "--profile-result",
                        paths[0],
                        "--profile-result",
                        paths[1],
                        "--output-dir",
                        str(root),
                    ]
                )
            console = buffer.getvalue()
            summary = json.loads(
                (root / "ratecon_layout_table_profile_comparison.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("ratecon_layout_table_profile_comparison_written", console)
        self.assertEqual(summary["best_profile"], "lines")
        self.assertFalse(summary["private_values_printed"])
        self.assertNotIn("FAKE_PRIVATE_VALUE", console)


if __name__ == "__main__":
    unittest.main()
