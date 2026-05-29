import io
import unittest
from contextlib import redirect_stdout

from app.market_intelligence.market_snapshot_console_report import print_driver_report


class FakeSearchRequest:
    driver_name = "Alex"
    current_location = "Dallas, TX"
    available_time = "10 AM"
    equipment = "Flatbed"
    max_weight = 48000
    max_empty_miles = 150
    target_direction = "Texas"


class FakeLoad:
    def __init__(self, pickup, delivery, rate, total_rpm, score, action, notes=""):
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate
        self.total_rpm = total_rpm
        self.driver_match_notes = notes
        self._score = score
        self._action = action

    def opportunity_score(self):
        return self._score

    def suggested_action(self):
        return self._action


class MarketSnapshotConsoleReportTest(unittest.TestCase):
    def test_print_driver_report_outputs_market_sections(self):
        stats = {}
        recommendation = {
            "market_activity": "MEDIUM",
            "driver_fit": "WORKABLE",
            "action_status": "SOME_MATCHES_AVAILABLE",
            "best_bucket": "700-1300",
            "total_good_loads": 3,
            "total_qualified_loads": 4,
            "total_clean_matches": 2,
            "total_review_once": 1,
            "total_blocked": 5,
        }
        top_opportunities = [
            FakeLoad(
                pickup="Dallas, TX",
                delivery="Houston, TX",
                rate=1200,
                total_rpm=4.8,
                score=90,
                action="SEND",
            )
        ]
        review_once_loads = [
            FakeLoad(
                pickup="Austin, TX",
                delivery="San Antonio, TX",
                rate=0,
                total_rpm=0,
                score=60,
                action="RATE CHECK",
                notes=["Rate missing"],
            )
        ]
        chain_candidates = [
            {
                "first_load": FakeLoad("Dallas, TX", "Houston, TX", 1200, 4.8, 90, "SEND"),
                "reload_load": FakeLoad("Houston, TX", "Dallas, TX", 1000, 4.0, 85, "SEND"),
                "chain_data": {
                    "total_gross": 2200,
                    "total_rpm": 4.4,
                    "chain_score": 88,
                },
            }
        ]

        output = io.StringIO()

        with redirect_stdout(output):
            print_driver_report(
                request_file="alex_active.json",
                stats=stats,
                recommendation=recommendation,
                top_opportunities=top_opportunities,
                review_once_loads=review_once_loads,
                search_request=FakeSearchRequest(),
                chain_candidates=chain_candidates,
            )

        text = output.getvalue()

        self.assertIn("Reload Chain Candidates", text)
        self.assertIn("ACTIVE SEARCH: alex_active.json", text)
        self.assertIn("Driver: Alex", text)
        self.assertIn("Market Activity: MEDIUM", text)
        self.assertIn("Top Match Opportunities", text)
        self.assertIn("Dallas, TX -> Houston, TX", text)
        self.assertIn("Review Once Opportunities", text)
        self.assertIn("Austin, TX -> San Antonio, TX", text)


if __name__ == "__main__":
    unittest.main()
