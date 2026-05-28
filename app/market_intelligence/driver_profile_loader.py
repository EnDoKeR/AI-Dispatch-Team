import json
from pathlib import Path


DRIVER_PROFILES_FILE = Path("data/driver_profiles.json")


def load_driver_profiles():
    """
    Loads all driver profiles from data/driver_profiles.json.
    """

    if not DRIVER_PROFILES_FILE.exists():
        print(f"Driver profiles file not found: {DRIVER_PROFILES_FILE}")
        return {}

    with open(DRIVER_PROFILES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_driver_profile(driver_name):
    """
    Returns one driver profile by driver name.
    If profile does not exist, returns empty dict.
    """

    profiles = load_driver_profiles()

    if not driver_name:
        return {}

    return profiles.get(driver_name, {})


def profile_value(profile, key, default=None):
    """
    Safe helper for reading driver profile values.
    """

    if not profile:
        return default

    return profile.get(key, default)


def driver_has_document(profile, document_key):
    """
    Returns:
    - True if driver has document
    - False if driver does not have document
    - None if unknown and should be asked once
    """

    return profile_value(profile, document_key, None)


def driver_can_take_od(profile):
    return bool(profile_value(profile, "can_take_od", False))


def driver_can_take_permit_loads(profile):
    return bool(profile_value(profile, "can_take_permit_loads", False))


def driver_can_take_tarps(profile):
    """
    Returns:
    - True if driver can take tarps
    - False if driver cannot take tarps
    - None if unknown and should be asked once
    """

    return profile_value(profile, "can_take_tarps", None)


def driver_max_tarp_size(profile):
    return profile_value(profile, "max_tarp_size", "")


def driver_tracking_ok(profile):
    return bool(profile_value(profile, "tracking_ok", True))


def apply_driver_profile_to_search_request(search_request):
    """
    Adds driver profile data to search_request object.

    This lets the load matching logic use:
    search_request.driver_profile
    search_request.driver_can_take_od
    search_request.driver_can_take_permit_loads
    search_request.driver_can_take_tarps
    search_request.driver_max_tarp_size
    search_request.driver_hazmat
    search_request.driver_twic
    etc.
    """

    driver_name = getattr(search_request, "driver_name", "")
    profile = get_driver_profile(driver_name)

    search_request.driver_profile = profile

    search_request.driver_can_take_od = driver_can_take_od(profile)
    search_request.driver_can_take_permit_loads = driver_can_take_permit_loads(profile)
    search_request.driver_can_take_tarps = driver_can_take_tarps(profile)
    search_request.driver_max_tarp_size = driver_max_tarp_size(profile)
    search_request.driver_tracking_ok = driver_tracking_ok(profile)

    search_request.driver_hazmat = driver_has_document(profile, "hazmat")
    search_request.driver_tanker_endorsement = driver_has_document(profile, "tanker_endorsement")
    search_request.driver_twic = driver_has_document(profile, "twic")

    search_request.driver_us_citizen = driver_has_document(profile, "us_citizen")
    search_request.driver_green_card_holder = driver_has_document(profile, "green_card_holder")
    search_request.driver_work_permit = driver_has_document(profile, "work_permit")

    search_request.driver_ramps = driver_has_document(profile, "ramps")
    search_request.driver_dunnage = driver_has_document(profile, "dunnage")

    if profile:
        print(f"Driver profile loaded: {driver_name}")
    else:
        print(f"No driver profile found for: {driver_name}")

    return search_request
