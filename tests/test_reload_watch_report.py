import copy
import inspect
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence.reload_watch_record import normalize_record
from app.market_intelligence.reload_watch_repository import save_reload_watch_records
from app.market_intelligence.reload_watch_report import (
    build_reload_watch_report,
    format_reload_watch_report,
)


def temp_file(directory):
    return Path(directory) / "reload_watch_records.json"


def record(watch_id, status="WATCH_ACTIVE", **overrides):
    data = {
        "watch_id": watch_id,
        "watch_status": status,
        "driver_name": "Alex",
        "parent_reference_id": f"REF-{watch_id}",
        "delivery_city": "Denver",
        "delivery_state": "CO",
        "last_event_type": "RELOAD_WATCH_STARTED",
        "clean_exit_count": 1,
        "review_exit_count": 2,
        "rate_check_exit_count": 3,
        "best_exit_reference_id": f"EXIT-{watch_id}",
        "best_exit_pickup": "Denver, CO",
        "best_exit_delivery": "Houston, TX",
        "best_exit_rate": 2600,
        "chain_status": "STRONG_CHAIN",
        "combined_rpm": 3.25,
        "updated_at_utc": "2026-05-29T10:00:00Z",
    }
    data.update(overrides)

    return normalize_record(data)


class TestReloadWatchReport(unittest.TestCase):
    def test_missing_file_returns_empty_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = build_reload_watch_report(temp_file(temp_dir))

            self.assertEqual(report["total_watches"], 0)
            self.assertEqual(report["active_watches"], [])
            self.assertEqual(report["inactive_watches"], [])
            self.assertIn("No reload watches found.", format_reload_watch_report(report))

    def test_status_counts_are_correct(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_reload_watch_records(
                [
                    record("A1", "WATCH_ACTIVE"),
                    record("A2", "WATCH_ACTIVE"),
                    record("M1", "WATCH_MUTED"),
                    record("S1", "WATCH_STOPPED"),
                    record("D1", "DRIVER_LOADED"),
                    record("R1", "PARENT_LOAD_REMOVED"),
                ],
                file_path,
            )

            report = build_reload_watch_report(file_path)

            self.assertEqual(report["total_watches"], 6)
            self.assertEqual(report["status_counts"]["WATCH_ACTIVE"], 2)
            self.assertEqual(report["status_counts"]["WATCH_MUTED"], 1)
            self.assertEqual(report["status_counts"]["WATCH_STOPPED"], 1)
            self.assertEqual(report["status_counts"]["DRIVER_LOADED"], 1)
            self.assertEqual(report["status_counts"]["PARENT_LOAD_REMOVED"], 1)

    def test_active_and_muted_watches_appear_in_active_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_reload_watch_records(
                [
                    record("A1", "WATCH_ACTIVE"),
                    record("M1", "WATCH_MUTED"),
                    record("S1", "WATCH_STOPPED"),
                ],
                file_path,
            )

            report = build_reload_watch_report(file_path)

            self.assertEqual(
                [item["watch_id"] for item in report["active_watches"]],
                ["A1", "M1"],
            )

    def test_stopped_loaded_removed_watches_appear_in_inactive_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_reload_watch_records(
                [
                    record("S1", "WATCH_STOPPED"),
                    record("D1", "DRIVER_LOADED"),
                    record("R1", "PARENT_LOAD_REMOVED"),
                    record("A1", "WATCH_ACTIVE"),
                ],
                file_path,
            )

            report = build_reload_watch_report(file_path)

            self.assertEqual(
                [item["watch_id"] for item in report["inactive_watches"]],
                ["S1", "D1", "R1"],
            )

    def test_formatted_report_includes_core_watch_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            save_reload_watch_records([record("WATCH-1", "WATCH_ACTIVE")], file_path)

            text = format_reload_watch_report(build_reload_watch_report(file_path))

            self.assertIn("RELOAD WATCH DRY-RUN REPORT", text)
            self.assertIn("WATCH-1", text)
            self.assertIn("Driver: Alex", text)
            self.assertIn("Delivery: Denver, CO", text)
            self.assertIn("Clean exits: 1", text)
            self.assertIn("Review exits: 2", text)
            self.assertIn("Rate-check exits: 3", text)
            self.assertIn("Best exit: Denver, CO -> Houston, TX | $2600 | REF: EXIT-WATCH-1", text)
            self.assertIn("Chain: STRONG_CHAIN | RPM: $3.25", text)

    def test_formatted_report_handles_missing_watch_fields_safely(self):
        report = {
            "total_watches": 1,
            "status_counts": {"WATCH_ACTIVE": 1},
            "active_watches": [
                {
                    "watch_id": "WATCH-MISSING",
                    "watch_status": "WATCH_ACTIVE",
                }
            ],
            "inactive_watches": [],
        }

        text = format_reload_watch_report(report)

        self.assertIn("WATCH-MISSING", text)
        self.assertIn("Driver: NEEDS CHECK", text)
        self.assertIn("Delivery: NEEDS CHECK", text)
        self.assertNotIn("Driver: 0", text)

    def test_helper_does_not_mutate_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            records = [record("WATCH-1", "WATCH_ACTIVE")]
            before = copy.deepcopy(records)
            save_reload_watch_records(records, file_path)

            build_reload_watch_report(file_path)

            self.assertEqual(records, before)

    def test_report_does_not_import_messaging_or_case_layers(self):
        import app.market_intelligence.reload_watch_report as report_module

        source = inspect.getsource(report_module)

        self.assertNotIn("telegram_sender", source)
        self.assertNotIn("telegram_notifier", source)
        self.assertNotIn("telegram_watch_formatter", source)
        self.assertNotIn("event_logger", source)
        self.assertNotIn("dispatch_case", source)

    def test_script_exists_and_imports_report_helper_only(self):
        script_path = Path("scripts/report_reload_watch.py")
        self.assertTrue(script_path.exists())

        source = script_path.read_text(encoding="utf-8")

        self.assertIn("build_reload_watch_report", source)
        self.assertIn("format_reload_watch_report", source)
        self.assertNotIn("telegram_sender", source)
        self.assertNotIn("telegram_notifier", source)
        self.assertNotIn("event_logger", source)


if __name__ == "__main__":
    unittest.main()
