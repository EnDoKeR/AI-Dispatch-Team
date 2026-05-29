import unittest

from app.market_intelligence.reload_watch_action_planner import (
    plan_reload_watch_action,
)


class FakeLoad:
    def __init__(
        self,
        load_id="LOAD-1",
        reference_id="REF-1",
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


class TestReloadWatchActionPlanner(unittest.TestCase):
    def test_normal_active_watch_status_due_returns_normal_status(self):
        plan = plan_reload_watch_action(
            watch_state={"watch_id": "WATCH-1", "watch_status": "WATCH_ACTIVE"},
            event_type="NORMAL_STATUS_DUE",
            parent_load=FakeLoad(),
        )

        self.assertEqual(plan["action_type"], "NORMAL_STATUS")
        self.assertTrue(plan["send_normal_status"])
        self.assertFalse(plan["send_critical_alert"])
        self.assertEqual(plan["event_type"], "NORMAL_STATUS_DUE")

    def test_muted_watch_status_due_returns_muted_no_action(self):
        plan = plan_reload_watch_action(
            watch_state={
                "watch_id": "WATCH-1",
                "watch_status": "WATCH_MUTED",
                "mute_normal_updates": True,
            },
            event_type="NORMAL_STATUS_DUE",
            parent_load=FakeLoad(),
        )

        self.assertEqual(plan["action_type"], "MUTED_NO_ACTION")
        self.assertFalse(plan["send_normal_status"])
        self.assertFalse(plan["send_critical_alert"])
        self.assertTrue(plan["continue_watch"])

    def test_clean_exit_found_returns_critical_alert_with_payload(self):
        plan = plan_reload_watch_action(
            watch_state={"watch_id": "WATCH-1"},
            event_type="CLEAN_EXIT_FOUND",
            parent_load=FakeLoad(),
            best_exit_load=FakeLoad(
                load_id="EXIT-1",
                reference_id="EXIT-REF",
                pickup="Denver, CO",
                delivery="Houston, TX",
                rate=2600,
            ),
            exit_context={"clean_exit_count": 2},
        )

        self.assertEqual(plan["action_type"], "CRITICAL_ALERT")
        self.assertEqual(plan["event_type"], "CLEAN_EXIT_FOUND")
        self.assertEqual(plan["event_payload"]["best_exit_reference_id"], "EXIT-REF")
        self.assertEqual(plan["event_payload"]["clean_exit_count"], 2)

    def test_parent_load_updated_returns_critical_alert_and_continues(self):
        plan = plan_reload_watch_action(
            watch_state={"watch_id": "WATCH-1"},
            event_type="PARENT_LOAD_UPDATED",
            parent_load=FakeLoad(rate=3300),
            rate_update={"old_rate": 3000, "new_rate": 3300},
        )

        self.assertEqual(plan["action_type"], "CRITICAL_ALERT")
        self.assertTrue(plan["continue_watch"])
        self.assertFalse(plan["stop_watch"])
        self.assertEqual(plan["event_payload"]["old_rate"], 3000)
        self.assertEqual(plan["event_payload"]["new_rate"], 3300)

    def test_parent_load_removed_returns_critical_alert_and_stop_watch(self):
        plan = plan_reload_watch_action(
            watch_state={"watch_id": "WATCH-1"},
            event_type="PARENT_LOAD_REMOVED",
            parent_load=FakeLoad(),
        )

        self.assertEqual(plan["action_type"], "CRITICAL_ALERT")
        self.assertTrue(plan["send_critical_alert"])
        self.assertTrue(plan["stop_watch"])
        self.assertFalse(plan["continue_watch"])
        self.assertEqual(plan["event_payload"]["event_type"], "PARENT_LOAD_REMOVED")

    def test_driver_loaded_returns_stop_watch_without_critical_alert(self):
        plan = plan_reload_watch_action(
            watch_state={"watch_id": "WATCH-1"},
            event_type="DRIVER_LOADED",
            parent_load=FakeLoad(),
        )

        self.assertEqual(plan["action_type"], "STOP_WATCH")
        self.assertTrue(plan["stop_watch"])
        self.assertFalse(plan["send_critical_alert"])

    def test_no_meaningful_event_returns_no_action(self):
        plan = plan_reload_watch_action(
            watch_state={"watch_id": "WATCH-1", "watch_status": "WATCH_ACTIVE"},
            event_type="PARENT_LOAD_ACTIVE",
            parent_load=FakeLoad(),
        )

        self.assertEqual(plan["action_type"], "NO_ACTION")
        self.assertFalse(plan["send_normal_status"])
        self.assertFalse(plan["send_critical_alert"])
        self.assertTrue(plan["continue_watch"])

    def test_planner_does_not_mutate_input_records(self):
        watch_state = {"watch_id": "WATCH-1", "watch_status": "WATCH_MUTED"}
        parent_load = FakeLoad()
        exit_context = {"clean_exit_count": 1}
        rate_update = {"old_rate": 3000, "new_rate": 3300}
        before_watch = dict(watch_state)
        before_parent = dict(parent_load.__dict__)
        before_context = dict(exit_context)
        before_rate_update = dict(rate_update)

        plan_reload_watch_action(
            watch_state=watch_state,
            event_type="PARENT_LOAD_UPDATED",
            parent_load=parent_load,
            exit_context=exit_context,
            rate_update=rate_update,
        )

        self.assertEqual(watch_state, before_watch)
        self.assertEqual(parent_load.__dict__, before_parent)
        self.assertEqual(exit_context, before_context)
        self.assertEqual(rate_update, before_rate_update)

    def test_plan_includes_structured_payload_without_telegram_text(self):
        plan = plan_reload_watch_action(
            watch_state={"watch_id": "WATCH-1"},
            event_type="STRONG_CHAIN_FOUND",
            parent_load=FakeLoad(),
            chain_result={"chain_status": "STRONG_CHAIN", "combined_rpm": 3.2},
        )

        self.assertIn("event_payload", plan)
        self.assertEqual(plan["event_payload"]["chain_status"], "STRONG_CHAIN")
        self.assertNotIn("telegram_text", plan)
        self.assertNotIn("message_text", plan["event_payload"])


if __name__ == "__main__":
    unittest.main()
