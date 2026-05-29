import copy
import json
import unittest

from app.market_intelligence.reload_watch_record import (
    build_reload_watch_record,
    update_reload_watch_record,
)


class FakeLoad:
    def __init__(
        self,
        load_id="LOAD-1",
        reference_id="REF-1",
        driver_name="Alex",
        delivery="Denver, CO",
    ):
        self.load_id = load_id
        self.reference_id = reference_id
        self.driver_name = driver_name
        self.delivery = delivery


class TestReloadWatchRecord(unittest.TestCase):
    def test_builds_active_watch_record_from_parent_load_and_payload(self):
        record = build_reload_watch_record(
            watch_id="WATCH-1",
            parent_load=FakeLoad(),
            payload={
                "clean_exit_count": 1,
                "review_exit_count": 2,
                "rate_check_exit_count": 3,
            },
            timestamp_utc="2026-05-29T10:00:00Z",
        )

        self.assertEqual(record["watch_id"], "WATCH-1")
        self.assertEqual(record["watch_status"], "WATCH_ACTIVE")
        self.assertEqual(record["parent_load_id"], "LOAD-1")
        self.assertEqual(record["parent_reference_id"], "REF-1")
        self.assertEqual(record["driver_name"], "Alex")
        self.assertEqual(record["delivery_city"], "Denver")
        self.assertEqual(record["delivery_state"], "CO")
        self.assertFalse(record["mute_normal_updates"])
        self.assertEqual(record["started_at_utc"], "2026-05-29T10:00:00Z")
        self.assertEqual(record["updated_at_utc"], "2026-05-29T10:00:00Z")
        self.assertEqual(record["clean_exit_count"], 1)
        self.assertEqual(record["review_exit_count"], 2)
        self.assertEqual(record["rate_check_exit_count"], 3)

    def test_missing_fields_are_safe_defaults(self):
        record = build_reload_watch_record(
            watch_id="WATCH-1",
            timestamp_utc="2026-05-29T10:00:00Z",
        )

        self.assertEqual(record["parent_load_id"], "")
        self.assertEqual(record["parent_reference_id"], "")
        self.assertEqual(record["driver_name"], "")
        self.assertEqual(record["delivery_city"], "")
        self.assertEqual(record["delivery_state"], "")
        self.assertEqual(record["last_event_payload"], {})
        self.assertEqual(record["clean_exit_count"], 0)
        self.assertEqual(record["best_exit_rate"], 0)
        self.assertEqual(record["combined_rpm"], 0)

    def test_mute_update_sets_status_and_mute_flag(self):
        record = build_reload_watch_record(watch_id="WATCH-1")

        updated = update_reload_watch_record(
            record,
            action_plan={
                "event_type": "MUTE_WATCH_UPDATES",
                "event_payload": {"event_type": "MUTE_WATCH_UPDATES"},
            },
            timestamp_utc="2026-05-29T10:05:00Z",
        )

        self.assertEqual(updated["watch_status"], "WATCH_MUTED")
        self.assertTrue(updated["mute_normal_updates"])
        self.assertEqual(updated["last_event_type"], "MUTE_WATCH_UPDATES")
        self.assertEqual(updated["updated_at_utc"], "2026-05-29T10:05:00Z")

    def test_driver_loaded_update_closes_watch(self):
        record = build_reload_watch_record(watch_id="WATCH-1")

        updated = update_reload_watch_record(
            record,
            action_plan={
                "event_type": "DRIVER_LOADED",
                "event_payload": {"event_type": "DRIVER_LOADED"},
            },
        )

        self.assertEqual(updated["watch_status"], "DRIVER_LOADED")

    def test_stop_search_update_closes_watch(self):
        record = build_reload_watch_record(watch_id="WATCH-1")

        updated = update_reload_watch_record(
            record,
            action_plan={
                "event_type": "STOP_SEARCH",
                "event_payload": {"event_type": "STOP_SEARCH"},
            },
        )

        self.assertEqual(updated["watch_status"], "WATCH_STOPPED")

    def test_parent_removed_update_closes_watch(self):
        record = build_reload_watch_record(watch_id="WATCH-1")

        updated = update_reload_watch_record(
            record,
            action_plan={
                "event_type": "PARENT_LOAD_REMOVED",
                "event_payload": {"event_type": "PARENT_LOAD_REMOVED"},
            },
        )

        self.assertEqual(updated["watch_status"], "PARENT_LOAD_REMOVED")

    def test_parent_updated_records_payload_but_keeps_active_or_muted_state(self):
        active_record = build_reload_watch_record(watch_id="WATCH-1")
        muted_record = {
            **active_record,
            "watch_status": "WATCH_MUTED",
            "mute_normal_updates": True,
        }
        action_plan = {
            "event_type": "PARENT_LOAD_UPDATED",
            "event_payload": {
                "event_type": "PARENT_LOAD_UPDATED",
                "old_rate": 3000,
                "new_rate": 3300,
            },
        }

        active_updated = update_reload_watch_record(active_record, action_plan)
        muted_updated = update_reload_watch_record(muted_record, action_plan)

        self.assertEqual(active_updated["watch_status"], "WATCH_ACTIVE")
        self.assertEqual(muted_updated["watch_status"], "WATCH_MUTED")
        self.assertEqual(active_updated["last_event_payload"]["old_rate"], 3000)
        self.assertEqual(active_updated["last_event_payload"]["new_rate"], 3300)

    def test_clean_exit_found_updates_exit_summary_and_keeps_state(self):
        record = build_reload_watch_record(watch_id="WATCH-1")

        updated = update_reload_watch_record(
            record,
            action_plan={
                "event_type": "CLEAN_EXIT_FOUND",
                "event_payload": {
                    "event_type": "CLEAN_EXIT_FOUND",
                    "clean_exit_count": 2,
                    "review_exit_count": 1,
                    "rate_check_exit_count": 0,
                    "best_exit_reference_id": "EXIT-1",
                    "best_exit_pickup": "Denver, CO",
                    "best_exit_delivery": "Houston, TX",
                    "best_exit_rate": 2600,
                },
            },
        )

        self.assertEqual(updated["watch_status"], "WATCH_ACTIVE")
        self.assertEqual(updated["clean_exit_count"], 2)
        self.assertEqual(updated["review_exit_count"], 1)
        self.assertEqual(updated["best_exit_reference_id"], "EXIT-1")
        self.assertEqual(updated["best_exit_rate"], 2600)

    def test_strong_chain_found_updates_chain_summary(self):
        record = build_reload_watch_record(watch_id="WATCH-1")

        updated = update_reload_watch_record(
            record,
            action_plan={
                "event_type": "STRONG_CHAIN_FOUND",
                "event_payload": {
                    "event_type": "STRONG_CHAIN_FOUND",
                    "chain_status": "STRONG_CHAIN",
                    "combined_rpm": 3.25,
                    "market_median_rpm": 2.5,
                },
            },
        )

        self.assertEqual(updated["chain_status"], "STRONG_CHAIN")
        self.assertEqual(updated["combined_rpm"], 3.25)
        self.assertEqual(updated["market_median_rpm"], 2.5)

    def test_update_returns_new_record_and_does_not_mutate_inputs(self):
        record = build_reload_watch_record(watch_id="WATCH-1")
        action_plan = {
            "event_type": "CLEAN_EXIT_FOUND",
            "event_payload": {
                "event_type": "CLEAN_EXIT_FOUND",
                "clean_exit_count": 1,
            },
        }
        before_record = copy.deepcopy(record)
        before_plan = copy.deepcopy(action_plan)

        updated = update_reload_watch_record(record, action_plan)

        self.assertIsNot(updated, record)
        self.assertEqual(record, before_record)
        self.assertEqual(action_plan, before_plan)

    def test_update_without_timestamp_preserves_existing_timestamps(self):
        record = build_reload_watch_record(
            watch_id="WATCH-1",
            timestamp_utc="2026-05-29T10:00:00Z",
        )

        updated = update_reload_watch_record(
            record,
            action_plan={
                "event_type": "CLEAN_EXIT_FOUND",
                "event_payload": {"event_type": "CLEAN_EXIT_FOUND"},
            },
        )

        self.assertEqual(updated["updated_at_utc"], "2026-05-29T10:00:00Z")
        self.assertEqual(updated["last_checked_at_utc"], "2026-05-29T10:00:00Z")

    def test_records_are_json_serializable(self):
        record = build_reload_watch_record(
            watch_id="WATCH-1",
            parent_load=FakeLoad(),
            timestamp_utc="2026-05-29T10:00:00Z",
        )
        updated = update_reload_watch_record(
            record,
            action_plan={
                "event_type": "STRONG_CHAIN_FOUND",
                "event_payload": {
                    "event_type": "STRONG_CHAIN_FOUND",
                    "chain_status": "STRONG_CHAIN",
                    "combined_rpm": 3.25,
                },
            },
        )

        json.dumps(updated, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
