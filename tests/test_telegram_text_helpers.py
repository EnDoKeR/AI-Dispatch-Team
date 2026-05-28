import unittest

from app.market_intelligence.telegram_text_helpers import (
    delivery_zone_outlook,
    extract_state,
    safe_value,
)


class TestTelegramTextHelpers(unittest.TestCase):
    def test_safe_value_returns_fallback_for_none_or_empty(self):
        self.assertEqual(safe_value(None), "NEEDS CHECK")
        self.assertEqual(safe_value(""), "NEEDS CHECK")
        self.assertEqual(safe_value("   "), "NEEDS CHECK")
        self.assertEqual(safe_value(None, fallback="No notes posted"), "No notes posted")

    def test_safe_value_strips_and_returns_text(self):
        self.assertEqual(safe_value("  10 AM  "), "10 AM")
        self.assertEqual(safe_value(2200), "2200")

    def test_extract_state_from_city_state(self):
        self.assertEqual(extract_state("Dallas, TX"), "TX")
        self.assertEqual(extract_state("Chicago, IL 60601"), "IL")

    def test_extract_state_from_space_separated_location(self):
        self.assertEqual(extract_state("Dallas TX"), "TX")
        self.assertEqual(extract_state("Billings MT"), "MT")

    def test_extract_state_returns_empty_for_empty_location(self):
        self.assertEqual(extract_state(""), "")
        self.assertEqual(extract_state("   "), "")

    def test_delivery_zone_outlook_for_strong_states(self):
        self.assertEqual(delivery_zone_outlook("Dallas, TX"), "GOOD / STRONG RELOAD AREA")
        self.assertEqual(delivery_zone_outlook("Chicago, IL"), "GOOD / STRONG RELOAD AREA")

    def test_delivery_zone_outlook_for_workable_states(self):
        self.assertEqual(delivery_zone_outlook("Nashville, TN"), "WORKABLE / CHECK RELOADS")
        self.assertEqual(delivery_zone_outlook("Louisville, KY"), "WORKABLE / CHECK RELOADS")

    def test_delivery_zone_outlook_for_risky_states(self):
        self.assertEqual(delivery_zone_outlook("Billings, MT"), "RISKY / EXIT PLAN NEEDED")
        self.assertEqual(delivery_zone_outlook("Fargo, ND"), "RISKY / EXIT PLAN NEEDED")

    def test_delivery_zone_outlook_for_unknown_states(self):
        self.assertEqual(delivery_zone_outlook("Phoenix, AZ"), "UNKNOWN / NEEDS MARKET CHECK")
        self.assertEqual(delivery_zone_outlook(""), "UNKNOWN / NEEDS MARKET CHECK")


if __name__ == "__main__":
    unittest.main()
