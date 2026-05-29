import copy
import inspect
import json
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence import intake_record_repository
from app.market_intelligence.intake_record_repository import (
    get_intake_record_by_id,
    get_intake_records_by_status,
    load_intake_records,
    save_intake_records,
    upsert_intake_record,
)


def temp_file(directory, name="intake_records.json"):
    return Path(directory) / "nested" / name


def record(intake_id, status="READY_FOR_REVIEW", rate=3200):
    return {
        "intake_id": intake_id,
        "status": status,
        "source_type": "synthetic_repository_test",
        "source_file_name": f"{intake_id or 'missing'}_synthetic.json",
        "broker_name": "Synthetic Repo Broker",
        "broker_mc": "SYNTH-MC-3001",
        "rate": rate,
        "pickup_location": "Dallas, TX",
        "pickup_date": "2026-05-30",
        "delivery_location": "Denver, CO",
        "delivery_date": "2026-05-31",
        "commodity": "Steel coils",
        "weight": 42000,
        "reference_id": f"SYNTH-REPO-{intake_id or 'NO-ID'}",
        "equipment": "Conestoga",
    }


class TestIntakeRecordRepository(unittest.TestCase):
    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            self.assertEqual(load_intake_records(file_path), [])

    def test_save_then_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            records = [
                record("INTAKE-1"),
                record("INTAKE-2", "MISSING_FIELDS", 0),
            ]

            saved_records = save_intake_records(records, file_path)

            self.assertEqual(load_intake_records(file_path), saved_records)
            self.assertEqual(saved_records[0]["intake_id"], "INTAKE-1")
            self.assertEqual(saved_records[1]["status"], "MISSING_FIELDS")

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            save_intake_records([record("INTAKE-1")], file_path)

            self.assertTrue(file_path.exists())
            self.assertTrue(file_path.parent.exists())

    def test_invalid_json_or_non_list_json_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = temp_file(temp_dir, "invalid.json")
            invalid_path.parent.mkdir(parents=True, exist_ok=True)
            invalid_path.write_text("{bad json", encoding="utf-8")

            non_list_path = temp_file(temp_dir, "non_list.json")
            non_list_path.parent.mkdir(parents=True, exist_ok=True)
            non_list_path.write_text('{"intake_id": "INTAKE-1"}', encoding="utf-8")

            self.assertEqual(load_intake_records(invalid_path), [])
            self.assertEqual(load_intake_records(non_list_path), [])

    def test_upsert_appends_new_intake_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            upsert_intake_record(record("INTAKE-1"), file_path)

            records = load_intake_records(file_path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["intake_id"], "INTAKE-1")

    def test_upsert_replaces_existing_intake_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_intake_records([record("INTAKE-1", rate=3200)], file_path)

            upsert_intake_record(record("INTAKE-1", rate=3600), file_path)

            records = load_intake_records(file_path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["rate"], 3600)

    def test_upsert_without_intake_id_appends(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            upsert_intake_record(record("", rate=3100), file_path)
            upsert_intake_record(record("", rate=3200), file_path)

            records = load_intake_records(file_path)
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["intake_id"], "")
            self.assertEqual(records[1]["intake_id"], "")

    def test_get_by_intake_id_returns_expected_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            saved_records = save_intake_records(
                [record("INTAKE-1"), record("INTAKE-2")],
                file_path,
            )

            self.assertEqual(
                get_intake_record_by_id("INTAKE-2", file_path),
                saved_records[1],
            )
            self.assertIsNone(get_intake_record_by_id("MISSING", file_path))

    def test_get_records_by_status_filters_existing_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            saved_records = save_intake_records(
                [
                    record("READY", "READY_FOR_REVIEW"),
                    record("MISSING", "MISSING_FIELDS"),
                    record("CHECK", "NEEDS_CHECK"),
                ],
                file_path,
            )

            self.assertEqual(
                get_intake_records_by_status("missing_fields", file_path),
                [saved_records[1]],
            )

    def test_repository_does_not_mutate_input_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            records = [record("INTAKE-1")]
            new_record = record("INTAKE-2")
            before_records = copy.deepcopy(records)
            before_new_record = copy.deepcopy(new_record)

            save_intake_records(records, file_path)
            upsert_intake_record(new_record, file_path)

            self.assertEqual(records, before_records)
            self.assertEqual(new_record, before_new_record)

    def test_tests_use_temp_file_not_default_runtime_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            save_intake_records([record("INTAKE-1")], file_path)

            self.assertIn(temp_dir, str(file_path))
            self.assertTrue(file_path.exists())

    def test_runtime_path_is_gitignored(self):
        gitignore_text = Path(".gitignore").read_text(encoding="utf-8")

        self.assertIn("data/intake_records.json", gitignore_text)

    def test_repository_does_not_import_forbidden_layers(self):
        source = inspect.getsource(intake_record_repository).lower()

        forbidden = [
            "pypdf",
            "pdfreader",
            "ocr",
            "gspread",
            "google.oauth",
            "gmail",
            "telegram_sender",
            "telegram_notifier",
            "dispatch_case",
            "event_logger",
            "scheduler",
            "threading",
            "googlemaps",
            "dat_api",
            "from app.load_intake",
            "import app.load_intake",
            "intake_parser_contract",
        ]

        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
