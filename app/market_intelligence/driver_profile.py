import json
from pathlib import Path


DRIVERS_FOLDER = "data/drivers"


class DriverProfile:
    def __init__(
        self,
        driver_name="",
        equipment="Conestoga",
        max_weight=40000,
        accept_coils=True,
        accept_tarps=False,
        blocked_states=None,
        preferred_directions=None,
        avg_daily_miles=650,
        home_city="",
        home_state="",
        notes="",
    ):
        self.driver_name = driver_name
        self.equipment = equipment
        self.max_weight = max_weight
        self.accept_coils = accept_coils
        self.accept_tarps = accept_tarps
        self.blocked_states = blocked_states or []
        self.preferred_directions = preferred_directions or []
        self.avg_daily_miles = avg_daily_miles
        self.home_city = home_city
        self.home_state = home_state
        self.notes = notes


def load_driver_profile(driver_name):
    file_name = f"{str(driver_name).lower()}".replace(" ", "_") + ".json"
    path = Path(DRIVERS_FOLDER) / file_name

    if not path.exists():
        raise FileNotFoundError(f"Driver profile not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    return DriverProfile(
        driver_name=data.get("driver_name", driver_name),
        equipment=data.get("equipment", "Conestoga"),
        max_weight=data.get("max_weight", 40000),
        accept_coils=data.get("accept_coils", True),
        accept_tarps=data.get("accept_tarps", False),
        blocked_states=data.get("blocked_states", []),
        preferred_directions=data.get("preferred_directions", []),
        avg_daily_miles=data.get("avg_daily_miles", 650),
        home_city=data.get("home_city", ""),
        home_state=data.get("home_state", ""),
        notes=data.get("notes", ""),
    )
