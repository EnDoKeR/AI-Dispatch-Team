import contextlib
import inspect
import io
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence.reload_watch_repository import (
    get_reload_watch_by_id,
)
from app.market_intelligence.reload_watch_service import start_reload_watch


def temp_file(directory):
    return Path(directory) / "reload_watch_records.json"


class FakeLoad:
    load_id = "PARENT-1"
    reference_id = "PARENT-1"
    driver_name = "Alex"
    pickup = "Dallas, TX"
    delivery = "Denver, CO"
    rate = 3200


class TestReloadWatchManualCli(unittest.TestCase):
    def run_cli(self, args):
        from app.market_intelligence.reload_watch_manual_cli import main

        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(args)

        return exit_code, output.getvalue()

    def start_watch(self, file_path):
        start_reload_watch(
            watch_id="WATCH-1",
            parent_load=FakeLoad(),
            timestamp_utc="2026-05-29T10:00:00Z",
            file_path=file_path,
        )

    def test_cli_script_exists(self):
        script_path = Path("scripts/run_reload_watch_event.py")

        self.assertTrue(script_path.exists())

    def test_normal_status_due_prints_action_plan_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            self.start_watch(file_path)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--watch-id",
                    "WATCH-1",
                    "--event",
                    "NORMAL_STATUS_DUE",
                    "--timestamp",
                    "2026-05-29T10:30:00Z",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("watch_id: WATCH-1", output)
            self.assertIn("event_type: NORMAL_STATUS_DUE", output)
            self.assertIn("action_type: NORMAL_STATUS", output)
            self.assertIn("send_normal_status: True", output)

    def test_mute_watch_updates_record_and_prints_muted_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            self.start_watch(file_path)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--watch-id",
                    "WATCH-1",
                    "--event",
                    "MUTE_WATCH_UPDATES",
                ]
            )

            saved = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(saved["watch_status"], "WATCH_MUTED")
            self.assertIn("watch_status: WATCH_MUTED", output)

    def test_parent_load_updated_accepts_rate_update_and_prints_critical_alert(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            self.start_watch(file_path)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--watch-id",
                    "WATCH-1",
                    "--event",
                    "PARENT_LOAD_UPDATED",
                    "--old-rate",
                    "3000",
                    "--new-rate",
                    "3300",
                ]
            )

            saved = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("action_type: CRITICAL_ALERT", output)
            self.assertEqual(saved["last_event_payload"]["old_rate"], 3000)
            self.assertEqual(saved["last_event_payload"]["new_rate"], 3300)

    def test_clean_exit_found_accepts_best_exit_fields_and_updates_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            self.start_watch(file_path)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--watch-id",
                    "WATCH-1",
                    "--event",
                    "CLEAN_EXIT_FOUND",
                    "--clean-exits",
                    "2",
                    "--review-exits",
                    "1",
                    "--rate-check-exits",
                    "3",
                    "--best-exit-reference-id",
                    "EXIT-1",
                    "--best-exit-pickup",
                    "Denver, CO",
                    "--best-exit-delivery",
                    "Houston, TX",
                    "--best-exit-rate",
                    "2600",
                ]
            )

            saved = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("action_type: CRITICAL_ALERT", output)
            self.assertEqual(saved["clean_exit_count"], 2)
            self.assertEqual(saved["best_exit_reference_id"], "EXIT-1")
            self.assertEqual(saved["best_exit_rate"], 2600)

    def test_strong_chain_found_accepts_chain_fields_and_updates_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            self.start_watch(file_path)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--watch-id",
                    "WATCH-1",
                    "--event",
                    "STRONG_CHAIN_FOUND",
                    "--chain-status",
                    "STRONG_CHAIN",
                    "--combined-rpm",
                    "3.25",
                    "--market-median-rpm",
                    "2.55",
                ]
            )

            saved = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(exit_code, 0)
            self.assertIn("action_type: CRITICAL_ALERT", output)
            self.assertEqual(saved["chain_status"], "STRONG_CHAIN")
            self.assertEqual(saved["combined_rpm"], 3.25)

    def test_driver_loaded_stops_watch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            self.start_watch(file_path)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--watch-id",
                    "WATCH-1",
                    "--event",
                    "DRIVER_LOADED",
                ]
            )

            saved = get_reload_watch_by_id("WATCH-1", file_path)

            self.assertEqual(exit_code, 0)
            self.assertEqual(saved["watch_status"], "DRIVER_LOADED")
            self.assertIn("stop_watch: True", output)

    def test_missing_watch_id_exits_safely(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--event",
                    "NORMAL_STATUS_DUE",
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("ERROR:", output)
            self.assertIn("watch_id", output)

    def test_not_found_watch_id_exits_safely(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--watch-id",
                    "MISSING",
                    "--event",
                    "NORMAL_STATUS_DUE",
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("ERROR: Reload watch was not found.", output)

    def test_preview_message_prints_preview_and_no_send_notice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            self.start_watch(file_path)

            exit_code, output = self.run_cli(
                [
                    "--file-path",
                    str(file_path),
                    "--watch-id",
                    "WATCH-1",
                    "--event",
                    "CLEAN_EXIT_FOUND",
                    "--clean-exits",
                    "1",
                    "--best-exit-reference-id",
                    "EXIT-1",
                    "--best-exit-pickup",
                    "Denver, CO",
                    "--best-exit-delivery",
                    "Houston, TX",
                    "--best-exit-rate",
                    "2600",
                    "--preview-message",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("TELEGRAM PREVIEW ONLY - no message sent", output)
            self.assertIn("CLEAN EXIT FOUND", output)

    def test_cli_does_not_import_sender_or_case_layers(self):
        import app.market_intelligence.reload_watch_manual_cli as cli_module

        source = inspect.getsource(cli_module)
        script_source = Path("scripts/run_reload_watch_event.py").read_text(
            encoding="utf-8"
        )

        for text in [source, script_source]:
            self.assertNotIn("telegram_sender", text)
            self.assertNotIn("telegram_notifier", text)
            self.assertNotIn("dispatch_case", text)
            self.assertNotIn("event_logger", text)


if __name__ == "__main__":
    unittest.main()
