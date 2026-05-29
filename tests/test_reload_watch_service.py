import copy
import tempfile
from pathlib import Path
import unittest

from app.market_intelligence.reload_watch_repository import (
    get_reload_watch_by_id,
    load_reload_watch_records,
)
from app.market_intelligence.reload_watch_service import (
    handle_reload_watch_event,
    start_reload_watch,
)


class FakeLoad:
    def __init__(
        self,
        load_id="LOAD-1",
        reference_id="PARENT-1",
        driver_name="Alex",
        pickup="Dallas, TX",
        delivery="Denver, CO",
        rate=3200,
    ):
        self.load_id = load_id
        self.reference_id = reference_id
        self.driver_name = driver_name
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate


def temp_file(directory):
    return Path(directory) / "reload_watch_records.json"


class TestReloadWatchService(unittest.TestCase):
    def test_start_reload_watch_creates_and_saves_active_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            result = start_reload_watch(
                watch_id="WATCH-1",
                parent_load=FakeLoad(),
                payload={"clean_exit_count": 1},
                timestamp_utc="2026-05-29T10:00:00Z",
                file_path=file_path,
            )

            self.assertTrue(result["saved"])
            self.assertEqual(result["watch_record"]["watch_status"], "WATCH_ACTIVE")
            self.assertEqual(result["watch_record"]["parent_reference_id"], "PARENT-1")
            self.assertEqual(
                load_reload_watch_records(file_path),
                [result["watch_record"]],
            )

    def test_handle_mute_event_updates_record_to_muted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            start_reload_watch("WATCH-1", FakeLoad(), file_path=file_path)

            result = handle_reload_watch_event(
                watch_id="WATCH-1",
                event_type="MUTE_WATCH_UPDATES",
                timestamp_utc="2026-05-29T10:05:00Z",
                file_path=file_path,
            )

            self.assertTrue(result["saved"])
            self.assertEqual(result["watch_record"]["watch_status"], "WATCH_MUTED")
            self.assertTrue(result["watch_record"]["mute_normal_updates"])

    def test_normal_status_due_returns_normal_status_and_saves_checked_timestamp(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            start_reload_watch("WATCH-1", FakeLoad(), file_path=file_path)

            result = handle_reload_watch_event(
                watch_id="WATCH-1",
                event_type="NORMAL_STATUS_DUE",
                timestamp_utc="2026-05-29T10:30:00Z",
                file_path=file_path,
            )

            self.assertEqual(result["action_plan"]["action_type"], "NORMAL_STATUS")
            self.assertEqual(
                result["watch_record"]["last_checked_at_utc"],
                "2026-05-29T10:30:00Z",
            )
            self.assertEqual(
                get_reload_watch_by_id("WATCH-1", file_path)["last_checked_at_utc"],
                "2026-05-29T10:30:00Z",
            )

    def test_clean_exit_found_updates_record_and_returns_critical_alert(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            start_reload_watch("WATCH-1", FakeLoad(), file_path=file_path)

            result = handle_reload_watch_event(
                watch_id="WATCH-1",
                event_type="CLEAN_EXIT_FOUND",
                parent_load=FakeLoad(),
                best_exit_load=FakeLoad(
                    load_id="EXIT-1",
                    reference_id="EXIT-1",
                    pickup="Denver, CO",
                    delivery="Houston, TX",
                    rate=2600,
                ),
                exit_context={"clean_exit_count": 2},
                file_path=file_path,
            )

            self.assertEqual(result["action_plan"]["action_type"], "CRITICAL_ALERT")
            self.assertEqual(result["watch_record"]["clean_exit_count"], 2)
            self.assertEqual(result["watch_record"]["best_exit_reference_id"], "EXIT-1")
            self.assertEqual(result["watch_record"]["best_exit_rate"], 2600)

    def test_strong_chain_found_updates_chain_summary_and_returns_critical_alert(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            start_reload_watch("WATCH-1", FakeLoad(), file_path=file_path)

            result = handle_reload_watch_event(
                watch_id="WATCH-1",
                event_type="STRONG_CHAIN_FOUND",
                parent_load=FakeLoad(),
                chain_result={
                    "chain_status": "STRONG_CHAIN",
                    "combined_rpm": 3.25,
                    "market_median_rpm": 2.5,
                },
                file_path=file_path,
            )

            self.assertEqual(result["action_plan"]["action_type"], "CRITICAL_ALERT")
            self.assertEqual(result["watch_record"]["chain_status"], "STRONG_CHAIN")
            self.assertEqual(result["watch_record"]["combined_rpm"], 3.25)

    def test_parent_load_updated_records_rate_update_and_continues(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            start_reload_watch("WATCH-1", FakeLoad(), file_path=file_path)

            result = handle_reload_watch_event(
                watch_id="WATCH-1",
                event_type="PARENT_LOAD_UPDATED",
                parent_load=FakeLoad(rate=3300),
                rate_update={"old_rate": 3000, "new_rate": 3300},
                file_path=file_path,
            )

            self.assertTrue(result["action_plan"]["continue_watch"])
            self.assertEqual(result["watch_record"]["watch_status"], "WATCH_ACTIVE")
            self.assertEqual(result["watch_record"]["last_event_payload"]["old_rate"], 3000)
            self.assertEqual(result["watch_record"]["last_event_payload"]["new_rate"], 3300)

    def test_parent_load_removed_stops_watch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            start_reload_watch("WATCH-1", FakeLoad(), file_path=file_path)

            result = handle_reload_watch_event(
                watch_id="WATCH-1",
                event_type="PARENT_LOAD_REMOVED",
                parent_load=FakeLoad(),
                file_path=file_path,
            )

            self.assertEqual(
                result["watch_record"]["watch_status"],
                "PARENT_LOAD_REMOVED",
            )
            self.assertTrue(result["action_plan"]["stop_watch"])

    def test_driver_loaded_stops_watch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            start_reload_watch("WATCH-1", FakeLoad(), file_path=file_path)

            result = handle_reload_watch_event(
                watch_id="WATCH-1",
                event_type="DRIVER_LOADED",
                file_path=file_path,
            )

            self.assertEqual(result["watch_record"]["watch_status"], "DRIVER_LOADED")
            self.assertTrue(result["action_plan"]["stop_watch"])

    def test_missing_watch_id_returns_safe_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)

            result = handle_reload_watch_event(
                watch_id="",
                event_type="NORMAL_STATUS_DUE",
                file_path=file_path,
            )

            self.assertFalse(result["saved"])
            self.assertIsNone(result["watch_record"])
            self.assertEqual(result["action_plan"], {})
            self.assertIn("watch_id", result["reason"])

    def test_service_does_not_mutate_input_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = temp_file(temp_dir)
            parent_load = FakeLoad()
            exit_context = {"clean_exit_count": 1}
            rate_update = {"old_rate": 3000, "new_rate": 3300}
            before_parent = dict(parent_load.__dict__)
            before_context = copy.deepcopy(exit_context)
            before_rate_update = copy.deepcopy(rate_update)
            start_reload_watch("WATCH-1", parent_load, file_path=file_path)

            handle_reload_watch_event(
                watch_id="WATCH-1",
                event_type="PARENT_LOAD_UPDATED",
                parent_load=parent_load,
                exit_context=exit_context,
                rate_update=rate_update,
                file_path=file_path,
            )

            self.assertEqual(parent_load.__dict__, before_parent)
            self.assertEqual(exit_context, before_context)
            self.assertEqual(rate_update, before_rate_update)


if __name__ == "__main__":
    unittest.main()
