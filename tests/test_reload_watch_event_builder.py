import unittest

from app.market_intelligence.reload_watch_event_builder import (
    build_reload_watch_event_payload,
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


class TestReloadWatchEventBuilder(unittest.TestCase):
    def test_builds_reload_watch_started_payload(self):
        payload = build_reload_watch_event_payload(
            event_type="RELOAD_WATCH_STARTED",
            watch_state={
                "watch_id": "WATCH-1",
                "watch_status": "WATCH_ACTIVE",
            },
            parent_load=FakeLoad(),
            exit_context={
                "clean_exit_count": 0,
                "review_exit_count": 1,
                "rate_check_exit_count": 2,
            },
            source="unit_test",
            reason="Strong pay into weak exit market.",
        )

        self.assertEqual(payload["event_type"], "RELOAD_WATCH_STARTED")
        self.assertEqual(payload["watch_id"], "WATCH-1")
        self.assertEqual(payload["watch_status"], "WATCH_ACTIVE")
        self.assertEqual(payload["parent_load_id"], "LOAD-1")
        self.assertEqual(payload["parent_reference_id"], "REF-1")
        self.assertEqual(payload["driver_name"], "Alex")
        self.assertEqual(payload["delivery_city"], "Denver")
        self.assertEqual(payload["delivery_state"], "CO")
        self.assertEqual(payload["clean_exit_count"], 0)
        self.assertEqual(payload["review_exit_count"], 1)
        self.assertEqual(payload["rate_check_exit_count"], 2)
        self.assertEqual(payload["source"], "unit_test")
        self.assertEqual(payload["reason"], "Strong pay into weak exit market.")

    def test_builds_parent_load_updated_payload_with_old_and_new_rate(self):
        payload = build_reload_watch_event_payload(
            event_type="PARENT_LOAD_UPDATED",
            watch_state={"watch_id": "WATCH-1"},
            parent_load=FakeLoad(rate=3300),
            rate_update={
                "old_rate": 3000,
                "new_rate": 3300,
            },
        )

        self.assertEqual(payload["event_type"], "PARENT_LOAD_UPDATED")
        self.assertEqual(payload["old_rate"], 3000)
        self.assertEqual(payload["new_rate"], 3300)
        self.assertEqual(payload["parent_reference_id"], "REF-1")

    def test_builds_clean_exit_found_payload_with_best_exit_summary(self):
        payload = build_reload_watch_event_payload(
            event_type="CLEAN_EXIT_FOUND",
            parent_load=FakeLoad(),
            best_exit_load=FakeLoad(
                load_id="EXIT-1",
                reference_id="EXIT-REF",
                pickup="Denver, CO",
                delivery="Houston, TX",
                rate=2600,
            ),
            exit_context={
                "clean_exit_count": 2,
                "review_exit_count": 0,
                "rate_check_exit_count": 1,
            },
        )

        self.assertEqual(payload["event_type"], "CLEAN_EXIT_FOUND")
        self.assertEqual(payload["clean_exit_count"], 2)
        self.assertEqual(payload["best_exit_reference_id"], "EXIT-REF")
        self.assertEqual(payload["best_exit_pickup"], "Denver, CO")
        self.assertEqual(payload["best_exit_delivery"], "Houston, TX")
        self.assertEqual(payload["best_exit_rate"], 2600)

    def test_builds_strong_chain_found_payload_with_chain_summary(self):
        payload = build_reload_watch_event_payload(
            event_type="STRONG_CHAIN_FOUND",
            parent_load=FakeLoad(),
            chain_result={
                "chain_status": "STRONG_CHAIN",
                "combined_rpm": 3.31,
                "market_median_rpm": 2.5,
            },
        )

        self.assertEqual(payload["event_type"], "STRONG_CHAIN_FOUND")
        self.assertEqual(payload["chain_status"], "STRONG_CHAIN")
        self.assertEqual(payload["combined_rpm"], 3.31)
        self.assertEqual(payload["market_median_rpm"], 2.5)

    def test_handles_missing_optional_fields_safely(self):
        payload = build_reload_watch_event_payload(
            event_type="RELOAD_WATCH_STATUS_DUE",
        )

        self.assertEqual(payload["event_type"], "RELOAD_WATCH_STATUS_DUE")
        self.assertEqual(payload["watch_id"], "")
        self.assertEqual(payload["parent_load_id"], "")
        self.assertEqual(payload["delivery_city"], "")
        self.assertEqual(payload["clean_exit_count"], 0)
        self.assertEqual(payload["best_exit_rate"], 0)
        self.assertEqual(payload["combined_rpm"], 0)

    def test_does_not_mutate_input_records(self):
        watch_state = {"watch_id": "WATCH-1", "watch_status": "WATCH_ACTIVE"}
        parent_load = FakeLoad()
        exit_context = {"clean_exit_count": 1}
        chain_result = {"chain_status": "STRONG_CHAIN", "combined_rpm": 3.0}
        before_watch = dict(watch_state)
        before_parent = dict(parent_load.__dict__)
        before_context = dict(exit_context)
        before_chain = dict(chain_result)

        build_reload_watch_event_payload(
            event_type="STRONG_CHAIN_FOUND",
            watch_state=watch_state,
            parent_load=parent_load,
            exit_context=exit_context,
            chain_result=chain_result,
        )

        self.assertEqual(watch_state, before_watch)
        self.assertEqual(parent_load.__dict__, before_parent)
        self.assertEqual(exit_context, before_context)
        self.assertEqual(chain_result, before_chain)

    def test_event_type_is_explicit_and_stable(self):
        payload = build_reload_watch_event_payload(
            event_type="clean_exit_found",
            parent_load=FakeLoad(),
        )

        self.assertEqual(payload["event_type"], "CLEAN_EXIT_FOUND")

    def test_payload_does_not_require_telegram_text_parsing(self):
        payload = build_reload_watch_event_payload(
            event_type="STRONG_CHAIN_FOUND",
            parent_load=FakeLoad(),
            best_exit_load=FakeLoad(reference_id="EXIT-REF"),
            chain_result={"chain_status": "STRONG_CHAIN"},
        )

        self.assertNotIn("telegram_text", payload)
        self.assertNotIn("message_text", payload)
        self.assertEqual(payload["best_exit_reference_id"], "EXIT-REF")
        self.assertEqual(payload["chain_status"], "STRONG_CHAIN")


if __name__ == "__main__":
    unittest.main()
