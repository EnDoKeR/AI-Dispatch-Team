import json
from pathlib import Path

from app.market_intelligence.driver_profile import load_driver_profile


SEARCH_REQUESTS_FOLDER = "data/search_requests"


class SearchRequest:
    def __init__(
        self,
        driver_name="",
        current_location="",
        available_time="",
        pickup_date="today",
        search_radius=200,
        target_direction="",
        target_direction_mode="SOFT",
        target_city="",
        target_radius_miles=200,
        min_total_rpm=2.5,
        notes="",
    ):
        self.driver_name = driver_name
        self.current_location = current_location
        self.available_time = available_time
        self.pickup_date = pickup_date
        self.search_radius = search_radius

        self.target_direction = target_direction
        self.target_direction_mode = target_direction_mode
        self.target_city = target_city
        self.target_radius_miles = target_radius_miles

        self.min_total_rpm = min_total_rpm
        self.notes = notes

        self.driver_profile = load_driver_profile(driver_name)

        self.equipment = self.driver_profile.equipment
        self.max_weight = self.driver_profile.max_weight
        self.max_empty_miles = search_radius

        self.route_fallback_active = False

    def parse_available_hour(self):
        text = str(self.available_time).upper().strip()

        if not text:
            return 8

        numbers = ""

        for char in text:
            if char.isdigit():
                numbers += char

        if not numbers:
            return 8

        hour = int(numbers)

        if "PM" in text and hour != 12:
            hour += 12

        if "AM" in text and hour == 12:
            hour = 0

        return hour

    def estimated_arrival_hour(self, empty_miles):
        available_hour = self.parse_available_hour()
        driving_hours = empty_miles / 50
        safety_buffer = 1

        return available_hour + driving_hours + safety_buffer


def load_search_request(file_name):
    path = Path(SEARCH_REQUESTS_FOLDER) / file_name

    if not path.exists():
        raise FileNotFoundError(f"Search request not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return SearchRequest(
        driver_name=data.get("driver_name", ""),
        current_location=data.get("current_location", ""),
        available_time=data.get("available_time", ""),
        pickup_date=data.get("pickup_date", "today"),
        search_radius=data.get("search_radius", 200),
        target_direction=data.get("target_direction", ""),
        target_direction_mode=data.get("target_direction_mode", "SOFT"),
        target_city=data.get("target_city", ""),
        target_radius_miles=data.get("target_radius_miles", 200),
        min_total_rpm=data.get("min_total_rpm", 2.5),
        notes=data.get("notes", ""),
    )
