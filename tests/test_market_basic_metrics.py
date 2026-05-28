import unittest

from app.market_intelligence.market_basic_metrics import (
    broker_key,
    calculate_bucket,
    lane_key,
    loaded_rpm,
    rpm,
    to_bool,
    to_number,
)


class FakeLoad:
    def __init__(
        self,
        rate=0,
        loaded_miles=0,
        total_miles=0,
        origin="",
        destination="",
        broker_name="",
        broker_mc="",
    ):
        self.rate = rate
        self.loaded_miles = loaded_miles
        self.total_miles = total_miles
        self.origin = origin
        self.destination = destination
        self.broker_name = broker_name
        self.broker_mc = broker_mc


class TestMarketBasicMetrics(unittest.TestCase):
    def test_to_number_handles_none_empty_and_bad_values(self):
        self.assertEqual(to_number(None), 0)
        self.assertEqual(to_number(""), 0)
        self.assertEqual(to_number("bad"), 0)

    def test_to_number_handles_money_commas_weight_miles_and_float(self):
        self.assertEqual(to_number("$2,500"), 2500)
        self.assertEqual(to_number("45,000 lbs"), 45000)
        self.assertEqual(to_number("250 mi"), 250)
        self.assertEqual(to_number("2.75"), 2.75)

    def test_to_bool_handles_truthy_and_falsey_values(self):
        for value in [True, "true", "1", "yes", "y", "book", "bookable"]:
            self.assertTrue(to_bool(value))

        for value in [False, None, "", "no", "0", "false"]:
            self.assertFalse(to_bool(value))

    def test_rpm_returns_zero_when_total_miles_missing(self):
        self.assertEqual(rpm(FakeLoad(rate=2200, total_miles=0)), 0)

    def test_rpm_calculates_total_rpm(self):
        self.assertEqual(rpm(FakeLoad(rate=2200, total_miles=260)), 8.46)

    def test_loaded_rpm_returns_zero_when_loaded_miles_missing(self):
        self.assertEqual(loaded_rpm(FakeLoad(rate=2200, loaded_miles=0)), 0)

    def test_loaded_rpm_calculates_loaded_rpm(self):
        self.assertEqual(loaded_rpm(FakeLoad(rate=1200, loaded_miles=300)), 4.0)

    def test_calculate_bucket_uses_loaded_or_total_miles(self):
        self.assertEqual(calculate_bucket(FakeLoad(loaded_miles=100)), "0-450")
        self.assertEqual(calculate_bucket(FakeLoad(loaded_miles=500)), "450-700")
        self.assertEqual(calculate_bucket(FakeLoad(loaded_miles=900)), "700-1300")
        self.assertEqual(calculate_bucket(FakeLoad(loaded_miles=1400)), "1300+")
        self.assertEqual(calculate_bucket(FakeLoad(loaded_miles=0, total_miles=500)), "450-700")

    def test_lane_and_broker_keys(self):
        load = FakeLoad(
            origin="Dallas, TX",
            destination="Houston, TX",
            broker_name="Test Broker",
            broker_mc="123456",
        )

        self.assertEqual(lane_key(load), "Dallas, TX -> Houston, TX")
        self.assertEqual(broker_key(load), "Test Broker|123456")


if __name__ == "__main__":
    unittest.main()
