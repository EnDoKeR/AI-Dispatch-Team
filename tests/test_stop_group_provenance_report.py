import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.document_ai.stop_group_provenance_report import (
    DEFAULT_STOP_GROUP_PROVENANCE_JSON,
    DEFAULT_STOP_GROUP_PROVENANCE_MD,
    ROOT_CAUSE_NORMALIZER_PASSTHROUGH,
    ROOT_CAUSE_ONE_GROUP_PER_CELL,
    ROOT_CAUSE_TABLE_ROW_NOT_MERGED,
    build_stop_group_provenance_markdown,
    build_stop_group_provenance_report_payload,
    build_stop_group_provenance_report_rows,
    write_stop_group_provenance_report,
)


class StopGroupProvenanceReportTests(unittest.TestCase):
    def _rows(self):
        return [
            {
                "document_alias": "RATECON_001",
                "normalized_stop_count": 3,
                "stop_duplicate_removed_count": 0,
                "stop_noise_removed_count": 0,
                "date_candidate_generated_count": 2,
                "unresolved_due_to_missing_date": 1,
                "warning_codes": [],
                "stop_group_provenance_summary": {
                    "document_alias": "RATECON_001",
                    "raw_group_count": 3,
                    "groups_by_source_type": {"table_cell": 3},
                    "groups_by_page": {"1": 3},
                    "groups_by_table": {"T1": 3},
                    "groups_by_row_key": {"1|T1|1": 3},
                    "groups_by_section_role": {"STOP_TABLE": 3},
                    "groups_by_trigger_label": {"pickup": 1, "date": 1, "time": 1},
                    "one_group_per_cell_suspected_count": 3,
                    "one_group_per_line_suspected_count": 0,
                    "table_row_merge_candidate_count": 2,
                    "section_cluster_merge_candidate_count": 0,
                    "duplicate_candidate_count": 2,
                    "noise_candidate_count": 0,
                    "warning_codes": ["row_merge_candidate"],
                    "raw_text_included": False,
                    "private_values_redacted": True,
                },
            }
        ]

    def test_report_rows_include_safe_root_causes(self):
        rows = build_stop_group_provenance_report_rows(self._rows())

        self.assertEqual(rows[0]["alias"], "RATECON_001")
        self.assertIn(ROOT_CAUSE_NORMALIZER_PASSTHROUGH, rows[0]["suspected_root_causes"])
        self.assertIn(ROOT_CAUSE_ONE_GROUP_PER_CELL, rows[0]["suspected_root_causes"])
        self.assertIn(ROOT_CAUSE_TABLE_ROW_NOT_MERGED, rows[0]["suspected_root_causes"])
        self.assertFalse(rows[0]["raw_text_included"])
        self.assertTrue(rows[0]["private_values_redacted"])

    def test_payload_serializes_without_values(self):
        payload = build_stop_group_provenance_report_payload(self._rows())
        text = json.dumps(payload, sort_keys=True)

        self.assertIn("RATECON_001", text)
        self.assertIn("table_cell", text)
        self.assertNotIn("FAKE_SECRET_VALUE", text)
        self.assertNotIn("raw_text\":", text)

    def test_markdown_is_aliases_and_counts_only(self):
        text = build_stop_group_provenance_markdown(self._rows())

        self.assertIn("Stop Group Provenance Report", text)
        self.assertIn("RATECON_001", text)
        self.assertIn("ONE_GROUP_PER_CELL", text)
        self.assertNotIn("FAKE BROKER LLC", text)
        self.assertNotIn("MC 123456", text)

    def test_report_writer_uses_safe_local_only_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = write_stop_group_provenance_report(
                self._rows(),
                output_dir=temp_dir,
                allow_custom_output_dir=True,
            )
            json_text = Path(result["json"]).read_text(encoding="utf-8")
            md_text = Path(result["md"]).read_text(encoding="utf-8")

        self.assertEqual(result["row_count"], 1)
        self.assertTrue(result["local_only"])
        self.assertIn("private_values_redacted", json_text)
        self.assertIn("No raw text", md_text)

    def test_default_paths_are_gitignored(self):
        for path in [DEFAULT_STOP_GROUP_PROVENANCE_JSON, DEFAULT_STOP_GROUP_PROVENANCE_MD]:
            with self.subTest(path=path):
                result = subprocess.run(
                    ["git", "check-ignore", str(path)],
                    cwd=Path(__file__).resolve().parents[1],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

                self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
