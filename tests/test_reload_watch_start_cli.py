import contextlib
import inspect
import io
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence.reload_watch_repository import (
    get_reload_watch_by_id,
    load_reload_watch_records,
)


def temp_file(directory):
    return Path(directory) / "reload_watch_records.json"


class TestReloadWatchStartCli(unittest.TestCase):
    def run_cli(self, args):
        from app.market_intelligence.reload_watch_start_cli import main

        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(args)

        return exit_code, output.getvalue()

    def required_args(self, file_path):
        return [
            "--file-path",
            str(file_path),
            "--watch-id",
            "WATCH-1",
            "--driver-name",
            "Alex",
            "--parent-load-id",
            "LOAD-1",
            "--parent-reference-id",
            "REF-1",
            "--pickup",
            "Dallas, TX",
            "--delivery",
            "Denver, CO",
            "--rate",
            "3200",
            "--timestamp",
            "2026-05-29T10:00:00Z",
        ]

    def test_cli_script_exists(self):
        script_path = Path("scripts/start_reload_watch.py")

        self.assertTrue(script_path.exists())

    def test_missing_watch_id_exits_safely(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--driver-name",
                    "Alex",
                    "--delivery",
                    "Denver, CO",
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("ERROR:", output)
            self.assertIn("watch_id", output)

    def test_start_cli_creates_watch_record_in_temp_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            exit_code, output = self.run_cli(self.required_args(file_path))
            records = load_reload_watch_records(file_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["watch_id"], "WATCH-1")
            self.assertEqual(records[0]["watch_status"], "WATCH_ACTIVE")
            self.assertIn("saved: True", output)

    def test_start_cli_stores_driver_load_reference_and_delivery_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            self.run_cli(self.required_args(file_path))
            record = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(record["driver_name"], "Alex")
            self.assertEqual(record["parent_load_id"], "LOAD-1")
            self.assertEqual(record["parent_reference_id"], "REF-1")
            self.assertEqual(record["delivery_city"], "Denver")
            self.assertEqual(record["delivery_state"], "CO")

    def test_start_cli_stores_exit_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            args = self.required_args(file_path) + [
                "--clean-exits",
                "2",
                "--review-exits",
                "1",
                "--rate-check-exits",
                "3",
            ]

            self.run_cli(args)
            record = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(record["clean_exit_count"], 2)
            self.assertEqual(record["review_exit_count"], 1)
            self.assertEqual(record["rate_check_exit_count"], 3)

    def test_start_cli_prints_human_readable_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            exit_code, output = self.run_cli(self.required_args(file_path))

            self.assertEqual(exit_code, 0)
            self.assertIn("RELOAD WATCH START DRY-RUN", output)
            self.assertIn("watch_id: WATCH-1", output)
            self.assertIn("watch_status: WATCH_ACTIVE", output)
            self.assertIn("driver_name: Alex", output)
            self.assertIn("parent_reference_id: REF-1", output)
            self.assertIn("delivery: Denver, CO", output)
            self.assertIn("clean_exit_count: 0", output)
            self.assertNotIn("clean_exit_count: 0.0", output)
            self.assertIn(f"file_path: {file_path}", output)

    def test_start_cli_uses_temp_file_in_tests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            self.run_cli(self.required_args(file_path))

            self.assertTrue(file_path.exists())
            self.assertIn(str(Path(temp_dir)), str(file_path))

    def test_starting_same_watch_id_again_replaces_existing_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            self.run_cli(self.required_args(file_path))
            self.run_cli(
                self.required_args(file_path)
                + [
                    "--driver-name",
                    "Sergey",
                    "--parent-reference-id",
                    "REF-UPDATED",
                    "--delivery",
                    "Houston, TX",
                ]
            )
            records = load_reload_watch_records(file_path)
            record = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(len(records), 1)
            self.assertEqual(record["driver_name"], "Sergey")
            self.assertEqual(record["parent_reference_id"], "REF-UPDATED")
            self.assertEqual(record["delivery_city"], "Houston")
            self.assertEqual(record["delivery_state"], "TX")

    def test_start_cli_does_not_import_sender_or_case_layers(self):
        import app.market_intelligence.reload_watch_start_cli as cli_module

        source = inspect.getsource(cli_module)
        script_source = Path("scripts/start_reload_watch.py").read_text(
            encoding="utf-8"
        )

        for text in [source, script_source]:
            self.assertNotIn("telegram_sender", text)
            self.assertNotIn("telegram_notifier", text)
            self.assertNotIn("dispatch_case", text)
            self.assertNotIn("event_logger", text)


if __name__ == "__main__":
    unittest.main()
