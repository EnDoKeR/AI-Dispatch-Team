import json
from pathlib import Path


LOADS_FILE = Path("data/current_loads.json")


TEST_LOAD = {
    "origin": "Lakeland, FL",
    "destination": "Houston, TX",

    "pickup": "Lakeland, FL",
    "delivery": "Houston, TX",

    "rate": 4100,
    "loaded_miles": 950,
    "empty_miles": 45,
    "total_miles": 995,

    "pickup_date": "May 26",
    "delivery_date": "May 27",
    "pickup_time": "FCFS 8 AM - 5 PM",
    "delivery_time": "Next day",

    "weight": 43000,
    "posted_trailer_type": "Flatbed",
    "equipment": "Flatbed",
    "commodity": "Machinery",

    "notes": (
        "TEST LOAD. Tanker endorsement required. "
        "Flatbed posting. Good test for driver document logic."
    ),
    "parsed_notes": {},

    "broker_name": "Test Broker For Documents",
    "broker_mc": "TEST123",
    "broker_contact": "test@example.com",
    "broker_contact_raw": "test@example.com",
    "parsed_contact": {},

    "credit_score": "99",
    "days_to_pay": "15",
    "reference_id": "TEST-TANKER-001",

    "is_bookable": False,
    "is_private": False,
    "is_partial": False,
    "is_od": False,
    "is_tracking_required": False,

    "broker_status": "TEST",
    "delivery_zone": "GOOD / STRONG RELOAD AREA",
}


def load_current_loads():
    if not LOADS_FILE.exists():
        return []

    with open(LOADS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_current_loads(loads):
    with open(LOADS_FILE, "w", encoding="utf-8") as file:
        json.dump(loads, file, indent=2)


def already_exists(loads):
    for load in loads:
        if load.get("reference_id") == TEST_LOAD["reference_id"]:
            return True

    return False


def main():
    loads = load_current_loads()

    if already_exists(loads):
        print("Test document load already exists in current_loads.json.")
        return

    loads.append(TEST_LOAD)
    save_current_loads(loads)

    print("Test document load added to current_loads.json.")
    print(f"Total loads now: {len(loads)}")


if __name__ == "__main__":
    main()