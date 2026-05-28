import unittest

from app.market_intelligence.notes_parser_pickup import (
    detect_actual_pickup_city,
    detect_extra_pickup,
    detect_multiple_loads_available,
    detect_pickup_time_from_text,
)


class TestNotesParserPickup(unittest.TestCase):
    def test_detect_pickup_time_from_text_detects_fcfs_and_time_windows(self):
        self.assertEqual(
            detect_pickup_time_from_text("FCFS 8am-2pm"),
            "FCFS 8AM-2PM",
        )
        self.assertEqual(
            detect_pickup_time_from_text("pickup 8am-2pm"),
            "8AM-2PM",
        )
        self.assertEqual(
            detect_pickup_time_from_text("pickup 0800-1400"),
            "0800-1400",
        )

    def test_detect_pickup_time_from_text_detects_ready_now_and_appointment(self):
        self.assertEqual(detect_pickup_time_from_text("ready now"), "Ready now")
        self.assertEqual(
            detect_pickup_time_from_text("appointment required"),
            "Appointment required",
        )

    def test_detect_pickup_time_from_text_does_not_parse_phone_as_time(self):
        self.assertEqual(detect_pickup_time_from_text("call 443-2707"), "")

    def test_detect_actual_pickup_city_detects_explicit_actual_city_state(self):
        cases = [
            ("actual pickup in Dallas, TX", "Dallas, TX"),
            ("load actually in Chicago, IL", "Chicago, IL"),
            ("actual pickup city Dallas TX", "Dallas, TX"),
            ("actual pick up -- Dallas (TX)", "Dallas, TX"),
            ("actual PU: Atlanta (GA)", "Atlanta, GA"),
            ("pickup is actually in Phoenix, AZ", "Phoenix, AZ"),
        ]

        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(detect_actual_pickup_city(text), expected)

    def test_detect_actual_pickup_city_ignores_normal_pickup_city_without_actual_signal(self):
        self.assertEqual(detect_actual_pickup_city("pickup in Dallas, TX"), "")
        self.assertEqual(detect_actual_pickup_city("load in Dallas, TX"), "")
        self.assertEqual(detect_actual_pickup_city("pu in Dallas, TX"), "")
        self.assertEqual(detect_actual_pickup_city("load in Dallas"), "")

    def test_detect_extra_pickup(self):
        self.assertTrue(detect_extra_pickup("extra pickup"))
        self.assertTrue(detect_extra_pickup("extra pick up"))
        self.assertTrue(detect_extra_pickup("additional pu"))
        self.assertFalse(detect_extra_pickup("single pickup"))

    def test_detect_multiple_loads_available(self):
        self.assertTrue(detect_multiple_loads_available("multiple loads available"))
        self.assertTrue(detect_multiple_loads_available("more loads available"))
        self.assertTrue(detect_multiple_loads_available("several loads"))
        self.assertFalse(detect_multiple_loads_available("single load"))


if __name__ == "__main__":
    unittest.main()
