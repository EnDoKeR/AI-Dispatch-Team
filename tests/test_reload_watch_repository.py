import json
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence.reload_watch_repository import (
    get_active_reload_watches,
    get_reload_watch_by_id,
    load_reload_watch_records,
    save_reload_watch_records,
    upsert_reload_watch_record,
)
from app.market_intelligence.reload_watch_record import normalize_record


def temp_file(directory, name="reload_watch_records.json"):
    return Path(directory) / "nested" / name


def record(watch_id, status="WATCH_ACTIVE"):
    return normalize_record(
        {
            "watch_id": watch_id,
            "watch_status": status,
            "parent_reference_id": f"REF-{watch_id}",
        }
    )


class TestReloadWatchRepository(unittest.TestCase):
    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            self.assertEqual(load_reload_watch_records(file_path), [])

    def test_save_then_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            records = [record("WATCH-1"), record("WATCH-2", "WATCH_MUTED")]

            save_reload_watch_records(records, file_path)

            self.assertEqual(load_reload_watch_records(file_path), records)

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            save_reload_watch_records([record("WATCH-1")], file_path)

            self.assertTrue(file_path.exists())
            self.assertTrue(file_path.parent.exists())

    def test_invalid_json_or_non_list_json_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = temp_file(temp_dir, "invalid.json")
            invalid_path.parent.mkdir(parents=True, exist_ok=True)
            invalid_path.write_text("{bad json", encoding="utf-8")

            non_list_path = temp_file(temp_dir, "non_list.json")
            non_list_path.parent.mkdir(parents=True, exist_ok=True)
            non_list_path.write_text('{"watch_id": "WATCH-1"}', encoding="utf-8")

            self.assertEqual(load_reload_watch_records(invalid_path), [])
            self.assertEqual(load_reload_watch_records(non_list_path), [])

    def test_upsert_appends_new_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            upsert_reload_watch_record(record("WATCH-1"), file_path)

            self.assertEqual(load_reload_watch_records(file_path), [record("WATCH-1")])

    def test_upsert_replaces_existing_watch_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_reload_watch_records([record("WATCH-1")], file_path)

            upsert_reload_watch_record(
                record("WATCH-1", "WATCH_MUTED"),
                file_path,
            )

            self.assertEqual(
                load_reload_watch_records(file_path),
                [record("WATCH-1", "WATCH_MUTED")],
            )

    def test_get_by_watch_id_returns_expected_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_reload_watch_records([record("WATCH-1"), record("WATCH-2")], file_path)

            self.assertEqual(
                get_reload_watch_by_id("WATCH-2", file_path),
                record("WATCH-2"),
            )
            self.assertIsNone(get_reload_watch_by_id("MISSING", file_path))

    def test_active_watches_filters_active_and_muted_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_reload_watch_records(
                [
                    record("ACTIVE", "WATCH_ACTIVE"),
                    record("MUTED", "WATCH_MUTED"),
                    record("STOPPED", "WATCH_STOPPED"),
                    record("LOADED", "DRIVER_LOADED"),
                    record("REMOVED", "PARENT_LOAD_REMOVED"),
                ],
                file_path,
            )

            self.assertEqual(
                get_active_reload_watches(file_path),
                [
                    record("ACTIVE", "WATCH_ACTIVE"),
                    record("MUTED", "WATCH_MUTED"),
                ],
            )

    def test_repository_does_not_mutate_input_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            records = [record("WATCH-1")]
            new_record = record("WATCH-2")
            before_records = json.loads(json.dumps(records))
            before_new_record = dict(new_record)

            save_reload_watch_records(records, file_path)
            upsert_reload_watch_record(new_record, file_path)

            self.assertEqual(records, before_records)
            self.assertEqual(new_record, before_new_record)

    def test_tests_use_temp_file_not_default_runtime_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            save_reload_watch_records([record("WATCH-1")], file_path)

            self.assertIn(temp_dir, str(file_path))
            self.assertTrue(file_path.exists())


if __name__ == "__main__":
    unittest.main()
