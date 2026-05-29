import unittest

from app.market_intelligence.market_baseline import (
    build_market_baseline,
    mileage_bucket,
)


class FakeLoad:
    def __init__(
        self,
        pickup="Dallas, TX",
        delivery="Houston, TX",
        pickup_date="2026-05-28",
        reference_id="",
        broker_mc="123456",
        rate=2200,
        gross=None,
        loaded_miles=900,
        total_miles=900,
        total_rpm=2.44,
        driver_match_status="MATCH",
        qualified=True,
        review_category="",
        posted_trailer_type="Flatbed",
        equipment="Flatbed",
    ):
        self.pickup = pickup
        self.delivery = delivery
        self.pickup_date = pickup_date
        self.reference_id = reference_id
        self.broker_mc = broker_mc
        self.rate = rate
        self.gross = rate if gross is None else gross
        self.loaded_miles = loaded_miles
        self.total_miles = total_miles
        self.total_rpm = total_rpm
        self.driver_match_status = driver_match_status
        self._qualified = qualified
        self._review_category = review_category
        self.posted_trailer_type = posted_trailer_type
        self.equipment = equipment

    def is_qualified(self):
        return self._qualified

    def review_category(self):
        return self._review_category


class TestMarketBaseline(unittest.TestCase):
    def test_mileage_bucket_uses_required_ranges(self):
        self.assertEqual(mileage_bucket(FakeLoad(loaded_miles=100)), "0-400")
        self.assertEqual(mileage_bucket(FakeLoad(loaded_miles=400)), "0-400")
        self.assertEqual(mileage_bucket(FakeLoad(loaded_miles=401)), "400-700")
        self.assertEqual(mileage_bucket(FakeLoad(loaded_miles=700)), "400-700")
        self.assertEqual(mileage_bucket(FakeLoad(loaded_miles=701)), "700-1300")
        self.assertEqual(mileage_bucket(FakeLoad(loaded_miles=1300)), "700-1300")
        self.assertEqual(mileage_bucket(FakeLoad(loaded_miles=1301)), "1300+")

    def test_baseline_counts_loads_by_mileage_bucket(self):
        baseline = build_market_baseline(
            [
                FakeLoad(reference_id="SHORT", loaded_miles=100, total_rpm=9.0),
                FakeLoad(reference_id="MID", loaded_miles=500, total_rpm=2.4),
                FakeLoad(reference_id="LONG", loaded_miles=900, total_rpm=2.3),
                FakeLoad(reference_id="XLONG", loaded_miles=1400, total_rpm=2.2),
            ]
        )

        self.assertEqual(baseline["load_count"], 4)
        self.assertEqual(baseline["buckets"]["0-400"]["load_count"], 1)
        self.assertEqual(baseline["buckets"]["400-700"]["load_count"], 1)
        self.assertEqual(baseline["buckets"]["700-1300"]["load_count"], 1)
        self.assertEqual(baseline["buckets"]["1300+"]["load_count"], 1)

    def test_short_high_rpm_loads_do_not_distort_long_haul_bucket(self):
        baseline = build_market_baseline(
            [
                FakeLoad(reference_id="S1", loaded_miles=100, total_rpm=10.0, rate=1000),
                FakeLoad(reference_id="S2", loaded_miles=120, total_rpm=9.0, rate=1080),
                FakeLoad(reference_id="L1", loaded_miles=1400, total_rpm=2.0, rate=2800),
                FakeLoad(reference_id="L2", loaded_miles=1500, total_rpm=2.2, rate=3300),
                FakeLoad(reference_id="L3", loaded_miles=1600, total_rpm=2.4, rate=3840),
            ]
        )

        short_bucket = baseline["buckets"]["0-400"]
        long_bucket = baseline["buckets"]["1300+"]

        self.assertEqual(short_bucket["median_rpm"], 9.5)
        self.assertEqual(long_bucket["median_rpm"], 2.2)
        self.assertEqual(long_bucket["market_status"], "NORMAL_MARKET")
        self.assertNotEqual(long_bucket["market_status"], "STRONG_MARKET")

    def test_low_data_means_low_confidence_not_bad_market(self):
        baseline = build_market_baseline(
            [
                FakeLoad(reference_id="ONLY", loaded_miles=900, total_rpm=2.6),
            ]
        )

        self.assertEqual(baseline["market_status"], "LOW_DATA")
        self.assertEqual(baseline["buckets"]["700-1300"]["market_status"], "LOW_DATA")
        self.assertEqual(baseline["buckets"]["700-1300"]["load_count"], 1)

    def test_rate_zero_and_missing_rate_do_not_corrupt_rpm_or_rate_medians(self):
        baseline = build_market_baseline(
            [
                FakeLoad(
                    reference_id="RATEZERO",
                    rate=0,
                    gross=0,
                    total_rpm=0,
                    driver_match_status="REVIEW_ONCE",
                    review_category="RATE CHECK",
                ),
                FakeLoad(
                    reference_id="MISSING",
                    rate="",
                    gross="",
                    total_rpm=0,
                    driver_match_status="REVIEW_ONCE",
                    review_category="RATE CHECK",
                ),
                FakeLoad(reference_id="A", rate=2100, total_rpm=2.1),
                FakeLoad(reference_id="B", rate=2500, total_rpm=2.5),
                FakeLoad(reference_id="C", rate=2900, total_rpm=2.9),
            ]
        )

        self.assertEqual(baseline["load_count"], 5)
        self.assertEqual(baseline["rate_check_count"], 2)
        self.assertEqual(baseline["median_rpm"], 2.5)
        self.assertEqual(baseline["median_rate"], 2500)
        self.assertEqual(baseline["avg_rpm"], 2.5)

    def test_equipment_views_keep_flatbed_and_conestoga_separate(self):
        baseline = build_market_baseline(
            [
                FakeLoad(reference_id="F1", posted_trailer_type="Flatbed", equipment="Flatbed"),
                FakeLoad(reference_id="F2", posted_trailer_type="Flat", equipment="Flatbed"),
                FakeLoad(reference_id="C1", posted_trailer_type="Conestoga", equipment="Conestoga"),
                FakeLoad(reference_id="C2", posted_trailer_type="Stoga", equipment="Conestoga"),
            ]
        )

        self.assertEqual(baseline["equipment_views"]["flatbed"]["load_count"], 2)
        self.assertEqual(baseline["equipment_views"]["conestoga"]["load_count"], 2)

    def test_baseline_uses_repost_identity_to_dedupe_snapshot_loads(self):
        baseline = build_market_baseline(
            [
                FakeLoad(reference_id="", broker_mc="123456", rate=2200),
                FakeLoad(reference_id="", broker_mc="123456", rate=2600),
                FakeLoad(reference_id="", broker_mc="654321", rate=2400),
            ]
        )

        self.assertEqual(baseline["source_load_count"], 3)
        self.assertEqual(baseline["load_count"], 2)


if __name__ == "__main__":
    unittest.main()
