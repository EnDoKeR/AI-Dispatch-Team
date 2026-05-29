import json
import tempfile
import unittest
from pathlib import Path

from app.market_intelligence.sqlite_memory_io import (
    json_text,
    load_jsonl,
)


class SQLiteMemoryIOTest(unittest.TestCase):
    def test_json_text_preserves_unicode(self):
        result = json_text({"city": "Chișinău", "emoji": "✅"})

        self.assertIn("Chișinău", result)
        self.assertIn("✅", result)

        parsed = json.loads(result)
        self.assertEqual(parsed["city"], "Chișinău")
        self.assertEqual(parsed["emoji"], "✅")

    def test_load_jsonl_returns_empty_list_for_missing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "missing.jsonl"

            self.assertEqual(load_jsonl(file_path), [])

    def test_load_jsonl_reads_valid_records_and_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "records.jsonl"
            file_path.write_text(
                '{"case_id": "CASE-1"}\n\n{"case_id": "CASE-2"}\n',
                encoding="utf-8",
            )

            result = load_jsonl(file_path)

            self.assertEqual(
                result,
                [
                    {"case_id": "CASE-1"},
                    {"case_id": "CASE-2"},
                ],
            )

    def test_load_jsonl_skips_invalid_json_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "records.jsonl"
            file_path.write_text(
                '{"case_id": "CASE-1"}\n'
                'not valid json\n'
                '{"case_id": "CASE-2"}\n',
                encoding="utf-8",
            )

            result = load_jsonl(file_path)

            self.assertEqual(
                result,
                [
                    {"case_id": "CASE-1"},
                    {"case_id": "CASE-2"},
                ],
            )


if __name__ == "__main__":
    unittest.main()
