import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.contact_parser import parse_contact_info
from app.market_intelligence.notes_parser import parse_notes


INPUT_FILE = "data/imported_loads.csv"
OUTPUT_FILE = "data/current_loads.json"


def to_int(value, default=0):
    try:
        value = str(value).strip()

        if not value:
            return default

        value = value.replace("$", "")
        value = value.replace(",", "")
        value = value.replace("lbs", "")
        value = value.replace("lb", "")
        value = value.replace("mi", "")

        return int(float(value))

    except:
        return default


def to_bool(value):
    text = str(value).strip().lower()

    return text in ["true", "yes", "y", "1"]


def clean(value):
    return str(value or "").strip()


def normalize_broker_status(row):
    broker_status = clean(row.get("broker_status", ""))

    if broker_status:
        return broker_status

    notes = clean(row.get("notes", ""))

    if "factoring eligible" in notes.lower():
        return "BUY_REVIEW"

    return "UNKNOWN"


def merge_notes_summary(notes, parsed_notes):
    notes = clean(notes)
    notes_summary = parsed_notes.get("notes_summary", [])

    if not notes_summary:
        return notes

    summary_text = " | Parsed notes: " + ", ".join(notes_summary)

    if notes:
        return notes + summary_text

    return summary_text.strip()


def normalize_row(row):
    notes = clean(row.get("notes", ""))
    commodity = clean(row.get("commodity", ""))
    posted_trailer_type = clean(row.get("posted_trailer_type", "Conestoga"))
    
    broker_contact_raw = clean(row.get("broker_contact", ""))

    contact_info = parse_contact_info(
    broker_contact_raw,
    notes,
    clean(row.get("broker_name", "")),
)

    parsed_notes = parse_notes(
        notes=notes,
        commodity=commodity,
        posted_trailer_type=posted_trailer_type,
    )

    original_weight = to_int(row.get("weight", 0))
    detected_weight = parsed_notes.get("detected_weight", 0)

    if original_weight:
        final_weight = original_weight
    else:
        final_weight = detected_weight

    original_stops = to_int(row.get("stops", 2), default=2)
    detected_stops = parsed_notes.get("detected_stops", 0)

    if detected_stops:
        final_stops = detected_stops
    else:
        final_stops = original_stops

    original_pickup_time = clean(row.get("pickup_time", ""))
    detected_pickup_time = parsed_notes.get("detected_pickup_time", "")

    if original_pickup_time:
        final_pickup_time = original_pickup_time
    else:
        final_pickup_time = detected_pickup_time

    requires_tarp = (
        to_bool(row.get("requires_tarp", False))
        or parsed_notes.get("requires_tarp", False)
    )

    is_od = (
        to_bool(row.get("is_od", False))
        or parsed_notes.get("is_od", False)
    )

    is_overweight = (
        to_bool(row.get("is_overweight", False))
        or parsed_notes.get("is_overweight", False)
    )

    parsed_flags = {
        "no_conestoga": parsed_notes.get("no_conestoga", False),
        "flatbed_required": parsed_notes.get("flatbed_required", False),
        "forklift_required": parsed_notes.get("forklift_required", False),
        "tracking_required": parsed_notes.get("tracking_required", False),
        "appointment_required": parsed_notes.get("appointment_required", False),
        "straight_through": parsed_notes.get("straight_through", False),
    }

    return {
        "pickup": clean(row.get("pickup", "")),
        "delivery": clean(row.get("delivery", "")),
        "rate": to_int(row.get("rate", 0)),
        "loaded_miles": to_int(row.get("loaded_miles", 0)),
        "empty_miles": to_int(row.get("empty_miles", 0)),
        "stops": final_stops,
        "weight": final_weight,
        "posted_trailer_type": posted_trailer_type,
        "commodity": commodity,
        "pickup_time": final_pickup_time,
        "delivery_time": clean(row.get("delivery_time", "")),
        "notes": merge_notes_summary(notes, parsed_notes),
        "has_email": to_bool(row.get("has_email", False)),
        "has_phone": to_bool(row.get("has_phone", False)),
        "requires_tarp": requires_tarp,
        "is_od": is_od,
        "is_overweight": is_overweight,
        "broker_status": normalize_broker_status(row),
        "broker_name": clean(row.get("broker_name", "")),
        "broker_mc": clean(row.get("broker_mc", "")),
        "broker_contact": contact_info.get("normalized_contact") or clean(row.get("broker_contact", "")),
        "broker_contact_raw": clean(row.get("broker_contact", "")),
        "parsed_contact": contact_info,
        "credit_score": to_int(row.get("credit_score", 0)),
        "days_to_pay": to_int(row.get("days_to_pay", 0)),
        "reference_id": clean(row.get("reference_id", "")),
        "parsed_flags": parsed_flags,
    }


def import_csv_to_json():
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():
        print(f"CSV file not found: {input_path}")
        return

    loads = []

    with open(input_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        for row in reader:
            load = normalize_row(row)
            loads.append(load)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(loads, file, indent=2, ensure_ascii=False)

    print(f"Imported loads: {len(loads)}")
    print(f"Saved to: {OUTPUT_FILE}")

    parsed_count = 0

    for load in loads:
        if "Parsed notes:" in load.get("notes", ""):
            parsed_count += 1

    print(f"Loads with parsed notes: {parsed_count}")


if __name__ == "__main__":
    import_csv_to_json()