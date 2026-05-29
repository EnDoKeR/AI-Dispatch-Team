import io
import unittest
from contextlib import redirect_stdout

from app.market_intelligence.driver_profile_loader import (
    apply_driver_profile_to_search_request,
    load_driver_profiles,
)
from app.market_intelligence.search_request import SearchRequest


DOCUMENT_FIELDS = [
    ("driver_hazmat", "hazmat"),
    ("driver_tanker_endorsement", "tanker_endorsement"),
    ("driver_twic", "twic"),
    ("driver_us_citizen", "us_citizen"),
    ("driver_green_card_holder", "green_card_holder"),
    ("driver_work_permit", "work_permit"),
    ("driver_ramps", "ramps"),
    ("driver_dunnage", "dunnage"),
]


def apply_profile_quietly(search_request):
    output = io.StringIO()

    with redirect_stdout(output):
        return apply_driver_profile_to_search_request(search_request)


class TestSearchRequestDriverProfileCompatibility(unittest.TestCase):
    def test_search_request_starts_with_legacy_core_fields_aligned_to_primary(self):
        primary_profiles = load_driver_profiles()

        for driver_name, primary_profile in primary_profiles.items():
            with self.subTest(driver=driver_name):
                search_request = SearchRequest(driver_name=driver_name)

                self.assertEqual(search_request.driver_name, driver_name)
                self.assertEqual(search_request.equipment, primary_profile["equipment"])
                self.assertEqual(search_request.max_weight, primary_profile["max_weight"])
                self.assertEqual(search_request.driver_profile.driver_name, driver_name)
                self.assertEqual(search_request.driver_profile.equipment, primary_profile["equipment"])
                self.assertEqual(search_request.driver_profile.max_weight, primary_profile["max_weight"])

    def test_apply_driver_profile_adds_primary_business_fields(self):
        primary_profiles = load_driver_profiles()

        for driver_name, primary_profile in primary_profiles.items():
            with self.subTest(driver=driver_name):
                search_request = SearchRequest(driver_name=driver_name)
                enriched_request = apply_profile_quietly(search_request)

                self.assertIs(enriched_request, search_request)
                self.assertEqual(search_request.driver_profile, primary_profile)
                self.assertEqual(search_request.equipment, primary_profile["equipment"])
                self.assertEqual(search_request.max_weight, primary_profile["max_weight"])
                self.assertEqual(
                    search_request.driver_can_take_tarps,
                    primary_profile["can_take_tarps"],
                )
                self.assertEqual(
                    search_request.driver_max_tarp_size,
                    primary_profile["max_tarp_size"],
                )
                self.assertEqual(
                    search_request.driver_can_take_od,
                    primary_profile["can_take_od"],
                )
                self.assertEqual(
                    search_request.driver_can_take_permit_loads,
                    primary_profile["can_take_permit_loads"],
                )
                self.assertEqual(
                    search_request.driver_tracking_ok,
                    primary_profile["tracking_ok"],
                )

                for request_field, profile_field in DOCUMENT_FIELDS:
                    self.assertEqual(
                        getattr(search_request, request_field),
                        primary_profile[profile_field],
                    )

    def test_apply_driver_profile_preserves_search_request_filters(self):
        search_request = SearchRequest(
            driver_name="Alex",
            current_location="Dallas, TX",
            available_time="9 AM",
            pickup_date="tomorrow",
            search_radius=175,
            target_direction="Southeast",
            target_direction_mode="STRICT",
            target_city="Atlanta, GA",
            target_radius_miles=125,
            min_total_rpm=3.1,
            notes="Keep filters stable.",
        )

        apply_profile_quietly(search_request)

        self.assertEqual(search_request.current_location, "Dallas, TX")
        self.assertEqual(search_request.available_time, "9 AM")
        self.assertEqual(search_request.pickup_date, "tomorrow")
        self.assertEqual(search_request.search_radius, 175)
        self.assertEqual(search_request.max_empty_miles, 175)
        self.assertEqual(search_request.target_direction, "Southeast")
        self.assertEqual(search_request.target_direction_mode, "STRICT")
        self.assertEqual(search_request.target_city, "Atlanta, GA")
        self.assertEqual(search_request.target_radius_miles, 125)
        self.assertEqual(search_request.min_total_rpm, 3.1)
        self.assertEqual(search_request.notes, "Keep filters stable.")


if __name__ == "__main__":
    unittest.main()
