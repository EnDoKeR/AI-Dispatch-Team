import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from app.market_intelligence.market_snapshot_telegram_dispatcher import (
    send_market_snapshot_to_telegram,
)


class FakeSearchRequest:
    def __init__(self):
        self.driver_name = "Alex"


class MarketSnapshotTelegramDispatcherTest(unittest.TestCase):
    def test_send_market_snapshot_to_telegram_calls_all_telegram_senders(self):
        stats = {"700-1300": {"total_loads": 2}}
        recommendation = {"market_activity": "MEDIUM"}
        top_opportunities = ["top-load"]
        review_once_loads = ["review-load"]
        search_request = FakeSearchRequest()
        loads = ["top-load", "review-load"]

        output = io.StringIO()

        with (
            patch(
                "app.market_intelligence.market_snapshot_telegram_dispatcher.send_market_summary_to_telegram"
            ) as send_summary,
            patch(
                "app.market_intelligence.market_snapshot_telegram_dispatcher.send_top_opportunities_to_telegram"
            ) as send_top,
            patch(
                "app.market_intelligence.market_snapshot_telegram_dispatcher.send_review_once_to_telegram"
            ) as send_review,
            patch(
                "app.market_intelligence.market_snapshot_telegram_dispatcher.send_search_health_check_to_telegram"
            ) as send_health,
            redirect_stdout(output),
        ):
            send_market_snapshot_to_telegram(
                stats=stats,
                recommendation=recommendation,
                top_opportunities=top_opportunities,
                review_once_loads=review_once_loads,
                search_request=search_request,
                loads=loads,
                search_location="Dallas, TX",
            )

        send_summary.assert_called_once_with(
            stats,
            recommendation,
            top_opportunities,
            search_request,
            search_location="Dallas, TX",
        )
        send_top.assert_called_once_with(
            top_opportunities,
            search_request,
            limit=3,
        )
        send_review.assert_called_once_with(
            review_once_loads,
            search_request,
            limit=3,
        )
        send_health.assert_called_once_with(
            search_request,
            loads,
            top_opportunities,
            review_once_loads,
            monitored_minutes=30,
        )

        text = output.getvalue()

        self.assertIn("TELEGRAM SUMMARY SEND - Alex", text)
        self.assertIn("TELEGRAM MATCH LOADS SEND - Alex", text)
        self.assertIn("TELEGRAM REVIEW ONCE SEND - Alex", text)
        self.assertIn("TELEGRAM SEARCH HEALTH CHECK - Alex", text)


if __name__ == "__main__":
    unittest.main()
