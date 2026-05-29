import unittest

from app.market_intelligence.reload_watch_state import (
    evaluate_reload_watch_state,
)


class TestReloadWatchState(unittest.TestCase):
    def test_active_watch_continues_when_parent_load_active(self):
        result = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="PARENT_LOAD_ACTIVE",
        )

        self.assertEqual(result["watch_status"], "WATCH_ACTIVE")
        self.assertTrue(result["continue_watch"])
        self.assertFalse(result["stop_watch"])
        self.assertFalse(result["send_critical_alert"])

    def test_driver_loaded_stops_watch(self):
        result = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="DRIVER_LOADED",
        )

        self.assertEqual(result["watch_status"], "DRIVER_LOADED")
        self.assertFalse(result["continue_watch"])
        self.assertTrue(result["stop_watch"])

    def test_stop_search_stops_watch(self):
        result = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="STOP_SEARCH",
        )

        self.assertEqual(result["watch_status"], "WATCH_STOPPED")
        self.assertFalse(result["continue_watch"])
        self.assertTrue(result["stop_watch"])

    def test_mute_suppresses_normal_status(self):
        muted = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="MUTE_WATCH_UPDATES",
        )
        status_due = evaluate_reload_watch_state(
            muted,
            event_type="NORMAL_STATUS_DUE",
        )

        self.assertEqual(muted["watch_status"], "WATCH_MUTED")
        self.assertTrue(muted["mute_normal_updates"])
        self.assertFalse(status_due["send_normal_status"])
        self.assertTrue(status_due["continue_watch"])

    def test_active_watch_sends_normal_status_when_due(self):
        result = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="NORMAL_STATUS_DUE",
        )

        self.assertTrue(result["send_normal_status"])
        self.assertFalse(result["send_critical_alert"])

    def test_muted_watch_still_allows_clean_exit_critical_alert(self):
        result = evaluate_reload_watch_state(
            {
                "watch_status": "WATCH_MUTED",
                "mute_normal_updates": True,
            },
            event_type="CLEAN_EXIT_FOUND",
        )

        self.assertEqual(result["watch_status"], "CLEAN_EXIT_FOUND")
        self.assertTrue(result["continue_watch"])
        self.assertTrue(result["send_critical_alert"])
        self.assertTrue(result["mute_normal_updates"])

    def test_parent_load_removed_triggers_critical_alert_and_stops(self):
        result = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="PARENT_LOAD_REMOVED",
        )

        self.assertEqual(result["watch_status"], "PARENT_LOAD_REMOVED")
        self.assertFalse(result["continue_watch"])
        self.assertTrue(result["stop_watch"])
        self.assertTrue(result["send_critical_alert"])

    def test_parent_load_updated_triggers_critical_alert_and_continues(self):
        result = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="PARENT_LOAD_UPDATED",
        )

        self.assertEqual(result["watch_status"], "PARENT_LOAD_UPDATED")
        self.assertTrue(result["continue_watch"])
        self.assertFalse(result["stop_watch"])
        self.assertTrue(result["send_critical_alert"])

    def test_clean_exit_found_triggers_critical_alert(self):
        result = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="CLEAN_EXIT_FOUND",
        )

        self.assertEqual(result["watch_status"], "CLEAN_EXIT_FOUND")
        self.assertTrue(result["send_critical_alert"])
        self.assertTrue(result["continue_watch"])

    def test_strong_chain_found_triggers_critical_alert(self):
        result = evaluate_reload_watch_state(
            {"watch_status": "WATCH_ACTIVE"},
            event_type="STRONG_CHAIN_FOUND",
        )

        self.assertEqual(result["watch_status"], "STRONG_CHAIN_FOUND")
        self.assertTrue(result["send_critical_alert"])
        self.assertTrue(result["continue_watch"])

    def test_helper_does_not_mutate_input_state_or_call_external_callbacks(self):
        def fail_if_called():
            raise AssertionError("external callback should not be called")

        watch_state = {
            "watch_status": "WATCH_MUTED",
            "mute_normal_updates": True,
            "send_telegram": fail_if_called,
        }
        before = dict(watch_state)

        result = evaluate_reload_watch_state(
            watch_state,
            event_type="STRONG_CHAIN_FOUND",
        )

        self.assertEqual(watch_state, before)
        self.assertTrue(result["send_critical_alert"])


if __name__ == "__main__":
    unittest.main()
