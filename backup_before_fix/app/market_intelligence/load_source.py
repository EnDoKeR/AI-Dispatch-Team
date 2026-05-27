import json
from pathlib import Path

from app.market_intelligence.market_models import MarketLoad


LOADS_FILE = Path("data/current_loads.json")


def load_market_loads(file_path=LOADS_FILE):
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"Loads file not found: {file_path}")
        return []

    with open(file_path, "r", encoding="utf-8") as file:
        raw_loads = json.load(file)

    loads = []

    for item in raw_loads:
        if not isinstance(item, dict):
            continue

        load = MarketLoad(
            origin=item.get("origin", ""),
            destination=item.get("destination", ""),

            rate=item.get("rate", 0),
            loaded_miles=item.get("loaded_miles", item.get("trip", 0)),
            empty_miles=item.get("empty_miles", 0),
            total_miles=item.get("total_miles", 0),

            pickup_date=item.get("pickup_date", ""),
            delivery_date=item.get("delivery_date", ""),
            pickup=item.get("pickup", ""),
            delivery=item.get("delivery", ""),
            pickup_time=item.get("pickup_time", ""),
            delivery_time=item.get("delivery_time", ""),

            weight=item.get("weight", 0),
            posted_trailer_type=item.get(
                "posted_trailer_type",
                item.get("equipment", item.get("truck", "")),
            ),
            equipment=item.get("equipment", item.get("posted_trailer_type", "")),
            commodity=item.get("commodity", ""),

            notes=item.get("notes", ""),
            parsed_notes=item.get("parsed_notes", {}),

            broker_name=item.get("broker_name", ""),
            broker_mc=item.get("broker_mc", ""),
            broker_contact=item.get("broker_contact", ""),
            broker_contact_raw=item.get("broker_contact_raw", ""),
            parsed_contact=item.get("parsed_contact", {}),

            credit_score=item.get("credit_score", ""),
            days_to_pay=item.get("days_to_pay", ""),
            reference_id=item.get("reference_id", ""),

            is_bookable=item.get("is_bookable", False),
            is_private=item.get("is_private", False),
            is_partial=item.get("is_partial", False),
            is_od=item.get("is_od", False),
            is_tracking_required=item.get("is_tracking_required", False),

            broker_status=item.get("broker_status", "UNKNOWN"),
            delivery_zone=item.get("delivery_zone", "UNKNOWN"),
        )

        loads.append(load)

    return loads