import json
import unittest
from pathlib import Path


PRIMARY_PROFILE_FILE = Path("data/driver_profiles.json")
LEGACY_PROFILE_DIR = Path("data/drivers")

REQUIRED_PRIMARY_FIELDS = [
    "driver_name",
    "equipment",
    "max_weight",
    "can_take_tarps",
    "max_tarp_size",
    "can_take_od",
    "can_take_permit_loads",
    "hazmat",
    "tanker_endorsement",
    "twic",
    "us_citizen",
    "green_card_holder",
    "work_permit",
    "ramps",
    "dunnage",
    "tracking_ok",
]

DOCUMENT_FIELDS = [
    "hazmat",
    "tanker_endorsement",
    "twic",
    "us_citizen",
    "green_card_holder",
    "work_permit",
    "ramps",
    "dunnage",
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def legacy_tarp_value(profile):
    if "can_take_tarps" in profile:
        return profile["can_take_tarps"]

    return profile.get("accept_tarps")


class TestDriverProfileSources(unittest.TestCase):
    def test_primary_driver_profiles_have_required_dispatch_fields(self):
        self.assertTrue(PRIMARY_PROFILE_FILE.exists())

        profiles = load_json(PRIMARY_PROFILE_FILE)

        self.assertIsInstance(profiles, dict)
        self.assertGreater(len(profiles), 0)

        for profile_key, profile in profiles.items():
            with self.subTest(driver=profile_key):
                for field in REQUIRED_PRIMARY_FIELDS:
                    self.assertIn(field, profile)

                self.assertEqual(profile["driver_name"], profile_key)
                self.assertTrue(profile["equipment"])
                self.assertIsInstance(profile["max_weight"], int)
                self.assertGreater(profile["max_weight"], 0)
                self.assertIsInstance(profile["can_take_tarps"], bool)
                self.assertIsInstance(profile["can_take_od"], bool)
                self.assertIsInstance(profile["can_take_permit_loads"], bool)
                self.assertIsInstance(profile["tracking_ok"], bool)

                for field in DOCUMENT_FIELDS:
                    self.assertIn(profile[field], [True, False, None])

    def test_legacy_driver_profiles_have_matching_primary_profiles(self):
        primary_profiles = load_json(PRIMARY_PROFILE_FILE)
        legacy_files = sorted(LEGACY_PROFILE_DIR.glob("*.json"))

        self.assertGreater(len(legacy_files), 0)

        for legacy_file in legacy_files:
            legacy_profile = load_json(legacy_file)
            driver_name = legacy_profile.get("driver_name", "")

            with self.subTest(driver=driver_name):
                self.assertTrue(driver_name)
                self.assertIn(driver_name, primary_profiles)

    def test_legacy_driver_profiles_do_not_conflict_on_core_fields(self):
        primary_profiles = load_json(PRIMARY_PROFILE_FILE)

        for legacy_file in sorted(LEGACY_PROFILE_DIR.glob("*.json")):
            legacy_profile = load_json(legacy_file)
            driver_name = legacy_profile.get("driver_name", "")
            primary_profile = primary_profiles[driver_name]

            with self.subTest(driver=driver_name):
                self.assertEqual(
                    legacy_profile.get("equipment"),
                    primary_profile.get("equipment"),
                )
                self.assertEqual(
                    legacy_profile.get("max_weight"),
                    primary_profile.get("max_weight"),
                )
                self.assertEqual(
                    legacy_tarp_value(legacy_profile),
                    primary_profile.get("can_take_tarps"),
                )


if __name__ == "__main__":
    unittest.main()
