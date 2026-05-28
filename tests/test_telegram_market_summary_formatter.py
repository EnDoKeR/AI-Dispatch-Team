import unittest

from app.market_intelligence.telegram_market_summary_formatter import format_market_summary_message


class FakeSearchRequest:
    driver_name = "Alex"
    available_time = "10 AM"
    equipment = "Flatbed"
    target_direction = "TX"


class FakeLoad:
    pickup = "Dallas, TX"
    delivery = "Houston, TX"
    rate = 2200
    total_miles = 260
    total_rpm = 8.46
    pickup_time = "10 AM"
    delivery_time = "2 PM"

    def opportunity_score(self):
        return 91

    def suggested_action(self):
        return "SEND"


class TestTelegramMarketSummaryFormatter(unittest.TestCase):
    def build_stats(self):
        return {
            "700-1300": {
                "total_loads": 10,
                "qualified_loads": 6,
                "good_loads": 4,
                "clean_match_loads": 2,
                "review_once_loads": 1,
                "avg_total_rpm": 2.35,
                "avg_good_score": 84,
            }
        }

    def build_recommendation(self, driver_fit="WORKABLE", market_activity="MEDIUM"):
        return {
            "market_activity": market_activity,
            "market_status": market_activity,
            "driver_fit": driver_fit,
            "action_status": "SOME_MATCHES_AVAILABLE",
            "best_bucket": "700-1300",
            "total_good_loads": 4,
            "total_qualified_loads": 6,
            "total_clean_matches": 2,
            "total_review_once": 1,
            "total_blocked": 3,
        }

    def test_format_market_summary_message_includes_market_and_best_load_details(self):
        message = format_market_summary_message(
            stats=self.build_stats(),
            recommendation=self.build_recommendation(),
            top_opportunities=[FakeLoad()],
            search_request=FakeSearchRequest(),
            search_location="Dallas, TX",
        )

        self.assertIn("MARKET SNAPSHOT", message)
        self.assertIn("Alex", message)
        self.assertIn("Search Area: Dallas, TX", message)
        self.assertIn("Available: 10 AM", message)
        self.assertIn("Equipment: Flatbed", message)
        self.assertIn("Target: TX", message)

        self.assertIn("Market Activity: MEDIUM", message)
        self.assertIn("Driver Fit: WORKABLE", message)
        self.assertIn("Action Status: SOME_MATCHES_AVAILABLE", message)
        self.assertIn("Best Bucket: 700-1300", message)
        self.assertIn("Good Loads: 4", message)
        self.assertIn("Qualified Loads: 6", message)
        self.assertIn("Clean Matches: 2", message)
        self.assertIn("Review Once: 1", message)
        self.assertIn("Blocked: 3", message)

        self.assertIn("Best Bucket Details:", message)
        self.assertIn("- Total loads: 10", message)
        self.assertIn("- Qualified: 6", message)
        self.assertIn("- Good: 4", message)
        self.assertIn("- Clean matches: 2", message)
        self.assertIn("- Review once: 1", message)
        self.assertIn("- Avg total RPM: $2.35", message)
        self.assertIn("- Avg good score: 84", message)

        self.assertIn("Best Clean Match:", message)
        self.assertIn("Dallas, TX", message)
        self.assertIn("Houston, TX", message)
        self.assertIn("Rate: $2200", message)
        self.assertIn("Total miles: 260", message)
        self.assertIn("Total RPM: $8.46", message)
        self.assertIn("Pickup: 10 AM", message)
        self.assertIn("Delivery: 2 PM", message)
        self.assertIn("Delivery Zone: GOOD / STRONG RELOAD AREA", message)
        self.assertIn("Score: 91", message)
        self.assertIn("Action: SEND", message)

        self.assertIn(
            "Some clean matches available. Focus on the strongest options first.",
            message,
        )

    def test_format_market_summary_message_handles_no_best_load(self):
        message = format_market_summary_message(
            stats=self.build_stats(),
            recommendation=self.build_recommendation(driver_fit="NO_MATCH"),
            top_opportunities=[],
            search_request=FakeSearchRequest(),
            search_location="Dallas, TX",
        )

        self.assertIn("Best Clean Match:", message)
        self.assertIn("No clean match under current driver settings.", message)
        self.assertIn("No clean matches found. Keep monitoring or adjust search settings.", message)

    def test_format_market_summary_message_uses_market_status_fallback(self):
        recommendation = self.build_recommendation()
        recommendation.pop("market_activity")

        message = format_market_summary_message(
            stats=self.build_stats(),
            recommendation=recommendation,
            top_opportunities=[],
            search_request=FakeSearchRequest(),
            search_location="Dallas, TX",
        )

        self.assertIn("Market Activity: MEDIUM", message)


if __name__ == "__main__":
    unittest.main()
