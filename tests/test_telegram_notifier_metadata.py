import unittest
from unittest.mock import patch

from app.market_intelligence.telegram_notifier import (
    send_chain_candidates_to_telegram,
    send_market_summary_to_telegram,
    send_review_once_to_telegram,
    send_search_health_check_to_telegram,
    send_top_opportunities_to_telegram,
)


class FakeLoad:
    pickup = "Dallas, TX"
    delivery = "Houston, TX"
    rate = 2200
    broker_name = "Primary Broker"
    broker = "Fallback Broker"
    broker_mc = "123456"
    reference_id = "REF-123"


class FakeSearchRequest:
    driver_name = "Alex"
    current_location = "Dallas, TX"
    available_time = "Now"
    equipment = "Flatbed"
    target_direction = "TX"
    max_weight = 48000
    max_empty_miles = 150
    min_total_rpm = 2.5


class TestTelegramNotifierMetadata(unittest.TestCase):
    def test_top_opportunity_sender_passes_load_metadata(self):
        load = FakeLoad()
        search_request = FakeSearchRequest()

        with patch(
            "app.market_intelligence.telegram_notifier.get_sent_loads",
            return_value=set(),
        ):
            with patch(
                "app.market_intelligence.telegram_notifier.select_new_loads",
                return_value={
                    "loads_to_send": [load],
                    "already_sent_loads": [],
                },
            ):
                with patch(
                    "app.market_intelligence.telegram_notifier.format_opportunity_message",
                    return_value="FORMATTED LOAD MESSAGE",
                ) as format_message:
                    with patch(
                        "app.market_intelligence.telegram_notifier.build_feedback_buttons",
                        return_value={"inline_keyboard": []},
                    ):
                        with patch(
                            "app.market_intelligence.telegram_notifier.send_telegram_message",
                            return_value=True,
                        ) as send_message:
                            with patch(
                                "app.market_intelligence.telegram_notifier.save_sent_load"
                            ):
                                with patch("builtins.print"):
                                    send_top_opportunities_to_telegram(
                                        [load],
                                        search_request,
                                        limit=1,
                                    )

        format_message.assert_called_once_with(load, 1, search_request)
        send_message.assert_called_once_with(
            "FORMATTED LOAD MESSAGE",
            reply_markup={"inline_keyboard": []},
            metadata={
                "message_type": "LOAD_OPPORTUNITY",
                "category": "LOAD OPPORTUNITY",
                "driver_name": "Alex",
                "pickup": "Dallas, TX",
                "delivery": "Houston, TX",
                "rate": 2200,
                "broker": "Primary Broker",
                "broker_mc": "123456",
                "reference_id": "REF-123",
            },
        )

    def test_top_opportunity_sender_uses_per_load_metadata(self):
        first_load = FakeLoad()
        second_load = FakeLoad()
        second_load.pickup = "Austin, TX"
        second_load.delivery = "Phoenix, AZ"
        second_load.rate = 2600
        second_load.broker_name = "Second Broker"
        second_load.broker_mc = "654321"
        second_load.reference_id = "REF-456"
        search_request = FakeSearchRequest()

        with patch(
            "app.market_intelligence.telegram_notifier.get_sent_loads",
            return_value=set(),
        ):
            with patch(
                "app.market_intelligence.telegram_notifier.select_new_loads",
                return_value={
                    "loads_to_send": [first_load, second_load],
                    "already_sent_loads": [],
                },
            ):
                with patch(
                    "app.market_intelligence.telegram_notifier.format_opportunity_message",
                    side_effect=["FIRST MESSAGE", "SECOND MESSAGE"],
                ):
                    with patch(
                        "app.market_intelligence.telegram_notifier.build_feedback_buttons",
                        return_value={"inline_keyboard": []},
                    ):
                        with patch(
                            "app.market_intelligence.telegram_notifier.send_telegram_message",
                            return_value=True,
                        ) as send_message:
                            with patch(
                                "app.market_intelligence.telegram_notifier.save_sent_load"
                            ):
                                with patch("builtins.print"):
                                    send_top_opportunities_to_telegram(
                                        [first_load, second_load],
                                        search_request,
                                        limit=2,
                                    )

        first_metadata = send_message.call_args_list[0].kwargs["metadata"]
        second_metadata = send_message.call_args_list[1].kwargs["metadata"]

        self.assertEqual(first_metadata["reference_id"], "REF-123")
        self.assertEqual(second_metadata["pickup"], "Austin, TX")
        self.assertEqual(second_metadata["delivery"], "Phoenix, AZ")
        self.assertEqual(second_metadata["rate"], 2600)
        self.assertEqual(second_metadata["broker"], "Second Broker")
        self.assertEqual(second_metadata["broker_mc"], "654321")
        self.assertEqual(second_metadata["reference_id"], "REF-456")

    def test_review_once_sender_passes_review_once_metadata(self):
        load = FakeLoad()
        search_request = FakeSearchRequest()

        with patch(
            "app.market_intelligence.telegram_notifier.get_sent_review_once_loads",
            return_value=set(),
        ):
            with patch(
                "app.market_intelligence.telegram_notifier.select_new_loads",
                return_value={
                    "loads_to_send": [load],
                    "already_sent_loads": [],
                },
            ):
                with patch(
                    "app.market_intelligence.telegram_notifier.format_review_once_message",
                    return_value="REVIEW MESSAGE",
                ):
                    with patch(
                        "app.market_intelligence.telegram_notifier.build_feedback_buttons",
                        return_value={"inline_keyboard": []},
                    ):
                        with patch(
                            "app.market_intelligence.telegram_notifier.send_telegram_message",
                            return_value=True,
                        ) as send_message:
                            with patch(
                                "app.market_intelligence.telegram_notifier.save_sent_review_once_load"
                            ):
                                with patch("builtins.print"):
                                    send_review_once_to_telegram(
                                        [load],
                                        search_request,
                                        limit=1,
                                    )

        send_message.assert_called_once_with(
            "REVIEW MESSAGE",
            reply_markup={"inline_keyboard": []},
            metadata={
                "message_type": "REVIEW_ONCE",
                "category": "REVIEW ONCE",
                "driver_name": "Alex",
                "pickup": "Dallas, TX",
                "delivery": "Houston, TX",
                "rate": 2200,
                "broker": "Primary Broker",
                "broker_mc": "123456",
                "reference_id": "REF-123",
            },
        )

    def test_review_once_sender_uses_per_load_metadata(self):
        first_load = FakeLoad()
        second_load = FakeLoad()
        second_load.pickup = "Laredo, TX"
        second_load.delivery = "Atlanta, GA"
        second_load.rate = 3100
        second_load.broker_name = "Review Broker"
        second_load.broker_mc = "777888"
        second_load.reference_id = "REV-456"
        search_request = FakeSearchRequest()

        with patch(
            "app.market_intelligence.telegram_notifier.get_sent_review_once_loads",
            return_value=set(),
        ):
            with patch(
                "app.market_intelligence.telegram_notifier.select_new_loads",
                return_value={
                    "loads_to_send": [first_load, second_load],
                    "already_sent_loads": [],
                },
            ):
                with patch(
                    "app.market_intelligence.telegram_notifier.format_review_once_message",
                    side_effect=["FIRST REVIEW", "SECOND REVIEW"],
                ):
                    with patch(
                        "app.market_intelligence.telegram_notifier.build_feedback_buttons",
                        return_value={"inline_keyboard": []},
                    ):
                        with patch(
                            "app.market_intelligence.telegram_notifier.send_telegram_message",
                            return_value=True,
                        ) as send_message:
                            with patch(
                                "app.market_intelligence.telegram_notifier.save_sent_review_once_load"
                            ):
                                with patch("builtins.print"):
                                    send_review_once_to_telegram(
                                        [first_load, second_load],
                                        search_request,
                                        limit=2,
                                    )

        first_metadata = send_message.call_args_list[0].kwargs["metadata"]
        second_metadata = send_message.call_args_list[1].kwargs["metadata"]

        self.assertEqual(first_metadata["message_type"], "REVIEW_ONCE")
        self.assertEqual(first_metadata["reference_id"], "REF-123")
        self.assertEqual(second_metadata["message_type"], "REVIEW_ONCE")
        self.assertEqual(second_metadata["pickup"], "Laredo, TX")
        self.assertEqual(second_metadata["delivery"], "Atlanta, GA")
        self.assertEqual(second_metadata["rate"], 3100)
        self.assertEqual(second_metadata["broker"], "Review Broker")
        self.assertEqual(second_metadata["broker_mc"], "777888")
        self.assertEqual(second_metadata["reference_id"], "REV-456")

    def test_market_summary_sender_passes_market_snapshot_metadata(self):
        search_request = FakeSearchRequest()
        stats = {"market_activity": "LOW"}
        recommendation = {
            "best_bucket": "400-700",
            "market_activity": "MEDIUM",
            "driver_fit": "GOOD",
            "action_status": "MONITOR",
            "total_good_loads": 4,
            "total_qualified_loads": 7,
            "total_clean_matches": 3,
            "total_review_once": 2,
            "total_blocked": 5,
        }
        top_opportunities = [FakeLoad()]

        with patch(
            "app.market_intelligence.telegram_notifier.get_sent_summaries",
            return_value=set(),
        ):
            with patch(
                "app.market_intelligence.telegram_notifier.market_summary_key",
                return_value="summary-key",
            ):
                with patch(
                    "app.market_intelligence.telegram_notifier.format_market_summary_message",
                    return_value="SUMMARY MESSAGE",
                ) as format_message:
                    with patch(
                        "app.market_intelligence.telegram_notifier.send_telegram_message",
                        return_value=True,
                    ) as send_message:
                        with patch(
                            "app.market_intelligence.telegram_notifier.save_sent_summary"
                        ):
                            with patch("builtins.print"):
                                send_market_summary_to_telegram(
                                    stats=stats,
                                    recommendation=recommendation,
                                    top_opportunities=top_opportunities,
                                    search_request=search_request,
                                    search_location="Dallas Market",
                                )

        format_message.assert_called_once_with(
            stats,
            recommendation,
            top_opportunities,
            search_request,
            "Dallas Market",
        )
        send_message.assert_called_once_with(
            "SUMMARY MESSAGE",
            metadata={
                "message_type": "MARKET_SNAPSHOT",
                "category": "MARKET SNAPSHOT",
                "driver_name": "Alex",
                "pickup": "",
                "delivery": "",
                "rate": "",
                "broker": "",
                "broker_mc": "",
                "reference_id": "",
                "search_area": "Dallas, TX",
                "current_location": "Dallas, TX",
                "available_time": "Now",
                "equipment": "Flatbed",
                "target_direction": "TX",
                "market_activity": "MEDIUM",
                "driver_fit": "GOOD",
                "action_status": "MONITOR",
                "best_bucket": "400-700",
                "good_loads": 4,
                "qualified_loads": 7,
                "clean_match_count": 3,
                "review_once_count": 2,
                "blocked_count": 5,
            },
        )

    def test_search_health_sender_passes_search_health_metadata(self):
        search_request = FakeSearchRequest()
        loads = [FakeLoad(), FakeLoad()]
        review_once_loads = [FakeLoad()]

        with patch(
            "app.market_intelligence.telegram_notifier.get_sent_health_alerts",
            return_value=set(),
        ):
            with patch(
                "app.market_intelligence.telegram_notifier.search_health_key",
                return_value="health-key",
            ):
                with patch(
                    "app.market_intelligence.telegram_notifier.format_search_health_message",
                    return_value="HEALTH MESSAGE",
                ) as format_message:
                    with patch(
                        "app.market_intelligence.telegram_notifier.send_telegram_message",
                        return_value=True,
                    ) as send_message:
                        with patch(
                            "app.market_intelligence.telegram_notifier.save_sent_health_alert"
                        ):
                            with patch("builtins.print"):
                                send_search_health_check_to_telegram(
                                    search_request,
                                    loads=loads,
                                    top_opportunities=[],
                                    review_once_loads=review_once_loads,
                                    monitored_minutes=45,
                                )

        format_message.assert_called_once_with(
            search_request,
            loads,
            [],
            review_once_loads,
            monitored_minutes=45,
        )
        send_message.assert_called_once_with(
            "HEALTH MESSAGE",
            metadata={
                "message_type": "SEARCH_HEALTH_CHECK",
                "category": "SEARCH HEALTH CHECK",
                "driver_name": "Alex",
                "pickup": "",
                "delivery": "",
                "rate": "",
                "broker": "",
                "broker_mc": "",
                "reference_id": "",
                "search_area": "Dallas, TX",
                "current_location": "Dallas, TX",
                "available_time": "Now",
                "equipment": "Flatbed",
                "target_direction": "TX",
                "monitored_minutes": 45,
                "total_loads": 2,
                "qualified_loads": 0,
                "clean_matches": 0,
                "top_opportunities": 0,
                "review_once_count": 1,
                "blocked_count": 0,
                "health_status": "",
                "action_status": "",
                "reason": "",
            },
        )

    def test_reload_chain_path_does_not_pass_metadata_yet(self):
        search_request = FakeSearchRequest()

        candidate = {
            "first_load": FakeLoad(),
            "reload_load": FakeLoad(),
            "chain_data": {},
        }

        with patch(
            "app.market_intelligence.telegram_notifier.get_sent_chain_alerts",
            return_value=set(),
        ):
            with patch(
                "app.market_intelligence.telegram_notifier.select_new_chain_candidates",
                return_value={
                    "candidates_to_send": [candidate],
                    "duplicate_candidates": [],
                    "already_sent_candidates": [],
                },
            ):
                with patch(
                    "app.market_intelligence.telegram_notifier.format_chain_candidate_message",
                    return_value="CHAIN MESSAGE",
                ):
                    with patch(
                        "app.market_intelligence.telegram_notifier.send_telegram_message",
                        return_value=True,
                    ) as send_message:
                        with patch(
                            "app.market_intelligence.telegram_notifier.save_sent_chain_alert"
                        ):
                            with patch("builtins.print"):
                                send_chain_candidates_to_telegram(
                                    [candidate],
                                    search_request,
                                    limit=1,
                                )

        self.assertNotIn("metadata", send_message.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
