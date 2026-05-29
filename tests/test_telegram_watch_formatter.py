import copy
import inspect
import unittest

from app.market_intelligence.telegram_watch_formatter import (
    format_reload_watch_message,
)


def build_plan(action_type, event_type, payload=None, reason=""):
    return {
        "action_type": action_type,
        "event_type": event_type,
        "reason": reason,
        "event_payload": payload or {},
    }


class TestTelegramWatchFormatter(unittest.TestCase):
    def test_formats_normal_status_message(self):
        message = format_reload_watch_message(
            build_plan(
                "NORMAL_STATUS",
                "NORMAL_STATUS_DUE",
                {
                    "parent_reference_id": "PARENT-1",
                    "delivery_city": "Denver",
                    "delivery_state": "CO",
                    "clean_exit_count": 2,
                    "review_exit_count": 1,
                    "rate_check_exit_count": 3,
                },
                reason="Normal reload-watch status is due.",
            )
        )

        self.assertIn("🔎 RELOAD WATCH STATUS", message)
        self.assertIn("Why shown:", message)
        self.assertIn("Normal reload-watch status is due.", message)
        self.assertIn("Reference ID: PARENT-1", message)
        self.assertIn("Delivery: Denver, CO", message)
        self.assertIn("Clean exits: 2", message)
        self.assertIn("Review exits: 1", message)
        self.assertIn("Rate-check exits: 3", message)

    def test_formats_clean_exit_critical_alert(self):
        message = format_reload_watch_message(
            build_plan(
                "CRITICAL_ALERT",
                "CLEAN_EXIT_FOUND",
                {
                    "parent_reference_id": "PARENT-1",
                    "delivery_city": "Denver",
                    "delivery_state": "CO",
                    "best_exit_reference_id": "EXIT-1",
                    "best_exit_pickup": "Denver, CO",
                    "best_exit_delivery": "Houston, TX",
                    "best_exit_rate": 2600,
                    "clean_exit_count": 1,
                },
                reason="Clean exit appeared; notify dispatcher and continue watching.",
            )
        )

        self.assertIn("✅ CLEAN EXIT FOUND", message)
        self.assertIn("Why shown:", message)
        self.assertIn("Clean exit appeared", message)
        self.assertIn("Best exit:", message)
        self.assertIn("Denver, CO -> Houston, TX", message)
        self.assertIn("Rate: $2600", message)
        self.assertIn("Reference ID: EXIT-1", message)

    def test_formats_strong_chain_critical_alert(self):
        message = format_reload_watch_message(
            build_plan(
                "CRITICAL_ALERT",
                "STRONG_CHAIN_FOUND",
                {
                    "parent_reference_id": "PARENT-1",
                    "delivery_city": "Denver",
                    "delivery_state": "CO",
                    "chain_status": "STRONG_CHAIN",
                    "combined_rpm": 3.2,
                    "market_median_rpm": 2.55,
                },
            )
        )

        self.assertIn("🔥 STRONG CHAIN FOUND", message)
        self.assertIn("Chain status: STRONG_CHAIN", message)
        self.assertIn("Combined RPM: $3.2", message)
        self.assertIn("Market median RPM: $2.55", message)

    def test_formats_parent_load_updated_with_old_and_new_rate(self):
        message = format_reload_watch_message(
            build_plan(
                "CRITICAL_ALERT",
                "PARENT_LOAD_UPDATED",
                {
                    "parent_reference_id": "PARENT-1",
                    "delivery_city": "Denver",
                    "delivery_state": "CO",
                    "old_rate": 3000,
                    "new_rate": 3300,
                },
            )
        )

        self.assertIn("📈 WATCHED LOAD UPDATED", message)
        self.assertIn("Rate changed: $3000 -> $3300", message)
        self.assertIn("Reload watch continues.", message)

    def test_formats_parent_load_removed(self):
        message = format_reload_watch_message(
            build_plan(
                "CRITICAL_ALERT",
                "PARENT_LOAD_REMOVED",
                {
                    "parent_reference_id": "PARENT-1",
                    "delivery_city": "Denver",
                    "delivery_state": "CO",
                },
            )
        )

        self.assertIn("⚠️ WATCHED LOAD REMOVED", message)
        self.assertIn("Reload watch should stop.", message)
        self.assertIn("Action:", message)

    def test_muted_no_action_returns_empty_message(self):
        message = format_reload_watch_message(
            build_plan("MUTED_NO_ACTION", "NORMAL_STATUS_DUE")
        )

        self.assertEqual(message, "")

    def test_handles_missing_fields_safely(self):
        message = format_reload_watch_message(
            build_plan("CRITICAL_ALERT", "CLEAN_EXIT_FOUND")
        )

        self.assertIn("NEEDS CHECK", message)
        self.assertIn("Clean exits: 0", message)

    def test_does_not_mutate_plan_or_payload(self):
        plan = build_plan(
            "CRITICAL_ALERT",
            "PARENT_LOAD_UPDATED",
            {
                "parent_reference_id": "PARENT-1",
                "old_rate": 3000,
                "new_rate": 3300,
            },
        )
        before = copy.deepcopy(plan)

        format_reload_watch_message(plan)

        self.assertEqual(plan, before)

    def test_does_not_import_telegram_sender_or_send(self):
        import app.market_intelligence.telegram_watch_formatter as formatter

        source = inspect.getsource(formatter)

        self.assertNotIn("telegram_sender", source)
        self.assertNotIn("telegram_notifier", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("send_telegram", source)

    def test_does_not_require_telegram_text_parsing(self):
        import app.market_intelligence.telegram_watch_formatter as formatter

        source = inspect.getsource(formatter)

        self.assertNotIn("telegram_outbox_logger", source)
        self.assertNotIn("Select-String", source)
        self.assertNotIn("regex", source.lower())


if __name__ == "__main__":
    unittest.main()
