import unittest

from app.market_intelligence.telegram_search_health_formatter import format_search_health_message


class FakeSearchRequest:
    driver_name = "Alex"
    current_location = "Dallas, TX"
    max_weight = 48000
    max_empty_miles = 150
    min_total_rpm = 2.0
    target_direction = "TX"
    equipment = "Flatbed"


class FakeLoad:
    def __init__(self, reasons):
        self._reasons = reasons

    def reject_reasons(self):
        return self._reasons


class TestTelegramSearchHealthFormatter(unittest.TestCase):
    def test_format_search_health_message_includes_current_filters_and_counts(self):
        loads = [
            FakeLoad(["Pickup appears too far from driver", "OK"]),
            FakeLoad(["Does not match target direction"]),
        ]

        message = format_search_health_message(
            search_request=FakeSearchRequest(),
            loads=loads,
            top_opportunities=[],
            review_once_loads=[object(), object()],
            monitored_minutes=45,
        )

        self.assertIn("SEARCH HEALTH CHECK", message)
        self.assertIn("Alex", message)
        self.assertIn("Location: Dallas, TX", message)
        self.assertIn("Monitored: ~45 min", message)

        self.assertIn("Current filters:", message)
        self.assertIn("- Max weight: 48000", message)
        self.assertIn("- Max empty: 150 mi", message)
        self.assertIn("- Preferred RPM: 2.0", message)
        self.assertIn("- Direction: TX", message)
        self.assertIn("- Equipment: Flatbed", message)

        self.assertIn("Near-miss / review options:", message)
        self.assertIn("- Review once loads: 2", message)
        self.assertIn("- Top matches: 0", message)

    def test_format_search_health_message_includes_common_blockers(self):
        loads = [
            FakeLoad(["Pickup appears too far from driver"]),
            FakeLoad(["Pickup appears too far from driver"]),
            FakeLoad(["Does not match target direction"]),
        ]

        message = format_search_health_message(
            search_request=FakeSearchRequest(),
            loads=loads,
            top_opportunities=[],
            review_once_loads=[],
        )

        self.assertIn("Most common blockers:", message)
        self.assertIn("- Pickup appears too far from driver: 2", message)
        self.assertIn("- Does not match target direction: 1", message)

    def test_format_search_health_message_suggests_target_and_pickup_adjustments(self):
        loads = [
            FakeLoad(["Pickup appears too far from driver"]),
            FakeLoad(["Does not match target direction"]),
        ]

        message = format_search_health_message(
            search_request=FakeSearchRequest(),
            loads=loads,
            top_opportunities=[],
            review_once_loads=[],
        )

        self.assertIn(
            "Most blocked loads are outside target direction.",
            message,
        )
        self.assertIn(
            "Many loads are too far from driver location.",
            message,
        )
        self.assertIn(
            "Current test load set does not fit this driver location/direction.",
            message,
        )

    def test_format_search_health_message_suggests_review_once_when_available(self):
        loads = [
            FakeLoad(["OK"]),
        ]

        message = format_search_health_message(
            search_request=FakeSearchRequest(),
            loads=loads,
            top_opportunities=[],
            review_once_loads=[object()],
        )

        self.assertIn(
            "There are review-once options available.",
            message,
        )
        self.assertIn(
            "No clean matches, but review-once options exist.",
            message,
        )

    def test_format_search_health_message_prioritizes_clean_opportunities(self):
        loads = [
            FakeLoad(["OK"]),
        ]

        message = format_search_health_message(
            search_request=FakeSearchRequest(),
            loads=loads,
            top_opportunities=[object()],
            review_once_loads=[],
        )

        self.assertIn(
            "Clean opportunities exist. Focus on top matches first.",
            message,
        )

    def test_format_search_health_message_handles_conestoga_tarp_guidance(self):
        search_request = FakeSearchRequest()
        search_request.equipment = "Conestoga"

        loads = [
            FakeLoad(["Tarps required"]),
        ]

        message = format_search_health_message(
            search_request=search_request,
            loads=loads,
            top_opportunities=[],
            review_once_loads=[],
        )

        self.assertIn(
            "Tarp-required loads should not block Conestoga",
            message,
        )


if __name__ == "__main__":
    unittest.main()
