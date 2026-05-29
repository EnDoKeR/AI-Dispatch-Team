import unittest

from app.market_intelligence.market_driver_profile_model import DriverProfile
from app.market_intelligence.market_models import DriverProfile as MarketModelsDriverProfile


class TestMarketDriverProfileModel(unittest.TestCase):
    def test_driver_profile_initializes_core_search_fields(self):
        profile = DriverProfile(
            name="Alex",
            current_location="Dallas, TX",
            available_time="10 AM",
            equipment="Conestoga",
            max_weight="45,000",
            max_empty_miles="175",
            target_direction="TX",
            target_city="Houston",
            target_radius_miles="250",
            min_total_rpm="2.75",
            hazmat=True,
            tanker_endorsement=False,
            twic=True,
            us_citizen=True,
            green_card_holder=False,
            work_permit=True,
            ramps=False,
            dunnage=True,
            tracking_ok=False,
            custom_field="kept",
        )

        self.assertEqual(profile.name, "Alex")
        self.assertEqual(profile.current_location, "Dallas, TX")
        self.assertEqual(profile.available_time, "10 AM")
        self.assertEqual(profile.equipment, "Conestoga")
        self.assertEqual(profile.max_weight, 45000)
        self.assertEqual(profile.max_empty_miles, 175)
        self.assertEqual(profile.target_direction, "TX")
        self.assertEqual(profile.target_city, "Houston")
        self.assertEqual(profile.target_radius_miles, 250)
        self.assertEqual(profile.min_total_rpm, 2.75)
        self.assertTrue(profile.hazmat)
        self.assertFalse(profile.tanker_endorsement)
        self.assertTrue(profile.twic)
        self.assertTrue(profile.us_citizen)
        self.assertFalse(profile.green_card_holder)
        self.assertTrue(profile.work_permit)
        self.assertFalse(profile.ramps)
        self.assertTrue(profile.dunnage)
        self.assertFalse(profile.tracking_ok)
        self.assertEqual(profile.extra, {"custom_field": "kept"})

    def test_driver_profile_number_conversion_falls_back_to_zero(self):
        profile = DriverProfile(
            max_weight="bad",
            max_empty_miles=None,
            target_radius_miles="",
            min_total_rpm=None,
        )

        self.assertEqual(profile.max_weight, 0)
        self.assertEqual(profile.max_empty_miles, 0)
        self.assertEqual(profile.target_radius_miles, 0)
        self.assertEqual(profile.min_total_rpm, 0.0)

    def test_market_models_reexports_driver_profile_for_compatibility(self):
        self.assertIs(MarketModelsDriverProfile, DriverProfile)


if __name__ == "__main__":
    unittest.main()
