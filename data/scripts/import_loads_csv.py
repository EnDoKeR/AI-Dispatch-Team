import csv
import json
import re
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
        value = str(value or "").strip()

        if not value:
            return default

        value = value.replace("$", "")
        value = value.replace(",", "")
        value = value.replace("lbs", "")
        value = value.replace("lb", "")
        value = value.replace("mi", "")
        value = value.strip()

        return int(float(value))

    except Exception:
        return default


def to_bool(value):
    text = str(value or "").strip().lower()

    return text in ["true", "yes", "y", "1"]


def clean(value):
    return str(value or "").strip()


def first_value(row, keys, default=""):
    for key in keys:
        value = clean(row.get(key, ""))

        if value:
            return value

    return default


def notes_look_like_dat_broker_block(notes):
    notes_lower = clean(notes).lower()

    return (
        "mc#" in notes_lower
        or "mc #" in notes_lower
        or "contact:" in notes_lower
        or "reference id" in notes_lower
        or "factoring" in notes_lower
    )


def extract_broker_name_from_notes(notes):
    notes = clean(notes)

    if not notes:
        return ""

    if not notes_look_like_dat_broker_block(notes):
        return ""

    first_part = notes.split("|")[0].strip()

    bad_broker_phrases = [
        "tarp required",
        "no tarps",
        "od load",
        "flatbed posting",
        "test load",
        "overweight load",
        "tracking required",
    ]

    if not first_part:
        return ""

    if any(phrase in first_part.lower() for phrase in bad_broker_phrases):
        return ""

    return first_part


def extract_mc_from_notes(notes):
    match = re.search(
        r"\bMC\s*#?\s*(\d+)\b",
        clean(notes),
        re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return ""


def extract_reference_id_from_notes(notes):
    match = re.search(
        r"\bReference\s*ID\s*:\s*([A-Za-z0-9\-]+)",
        clean(notes),
        re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return ""


def extract_contact_text_from_notes(notes):
    match = re.search(
        r"\bContact\s*:\s*([^|]+)",
        clean(notes),
        re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return ""


def extract_credit_score_from_notes(notes):
    match = re.search(
        r"\bCredit\s*Score\s*:\s*(\d+)",
        clean(notes),
        re.IGNORECASE,
    )

    if match:
        return to_int(match.group(1))

    return 0


def extract_days_to_pay_from_notes(notes):
    match = re.search(
        r"\bDays\s*to\s*Pay\s*:\s*(\d+)",
        clean(notes),
        re.IGNORECASE,
    )

    if match:
        return to_int(match.group(1))

    return 0


def normalize_broker_status(row, notes):
    broker_status = first_value(
        row,
        ["broker_status", "brokerStatus", "broker_status_text", "factoring_status"],
        default="",
    )

    if broker_status and broker_status.upper() not in ["UNKNOWN", "N/A", "NA"]:
        return broker_status

    notes_lower = clean(notes).lower()

    if "no buy" in notes_lower or "no-buy" in notes_lower:
        return "NO_BUY"

    if "factoring status not clearly shown" in notes_lower:
        return "BUY_REVIEW"

    if "factoring eligible" in notes_lower:
        return "UNKNOWN"

    if broker_status:
        return broker_status

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
    notes = first_value(row, ["notes", "comments", "comment", "load_comments"])
    commodity = first_value(row, ["commodity", "commodity_name", "description"])
    posted_trailer_type = first_value(
        row,
        ["posted_trailer_type", "equipment", "truck", "truck_type", "trailer_type"],
        default="Conestoga",
    )

    broker_name = first_value(row, ["broker_name", "broker", "company", "company_name"])
    broker_mc = first_value(row, ["broker_mc", "mc", "mc_number", "broker_mc_number"])
    broker_contact_raw = first_value(row, ["broker_contact", "contact", "contact_info", "phone", "email"])
    reference_id = first_value(row, ["reference_id", "ref", "ref_id", "load_id", "reference"])

    notes_broker_name = extract_broker_name_from_notes(notes)
    notes_broker_mc = extract_mc_from_notes(notes)
    notes_contact = extract_contact_text_from_notes(notes)
    notes_reference_id = extract_reference_id_from_notes(notes)

    if not broker_name:
        broker_name = notes_broker_name

    if not broker_mc:
        broker_mc = notes_broker_mc

    if not broker_contact_raw:
        broker_contact_raw = notes_contact

    if not reference_id:
        reference_id = notes_reference_id

    contact_info = parse_contact_info(
        broker_contact_raw,
        notes,
        broker_name,
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

    original_pickup_time = first_value(row, ["pickup_time", "pickup_window", "pickup_appointment"])
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

    credit_score = to_int(row.get("credit_score", 0))
    days_to_pay = to_int(row.get("days_to_pay", 0))

    if not credit_score:
        credit_score = extract_credit_score_from_notes(notes)

    if not days_to_pay:
        days_to_pay = extract_days_to_pay_from_notes(notes)

    parsed_flags = {
        "no_conestoga": parsed_notes.get("no_conestoga", False),
        "flatbed_required": parsed_notes.get("flatbed_required", False),
        "forklift_required": parsed_notes.get("forklift_required", False),
        "tracking_required": parsed_notes.get("tracking_required", False),
        "appointment_required": parsed_notes.get("appointment_required", False),
        "straight_through": parsed_notes.get("straight_through", False),
    }

    has_email = to_bool(row.get("has_email", False)) or bool(contact_info.get("emails"))
    has_phone = to_bool(row.get("has_phone", False)) or bool(contact_info.get("phones"))

    return {
        "pickup": first_value(row, ["pickup", "origin", "pickup_city"]),
        "delivery": first_value(row, ["delivery", "destination", "delivery_city"]),
        "rate": to_int(first_value(row, ["rate", "posted_rate", "linehaul_rate"])),
        "loaded_miles": to_int(first_value(row, ["loaded_miles", "trip_miles", "miles", "loaded"])),
        "empty_miles": to_int(first_value(row, ["empty_miles", "deadhead", "dh_miles", "deadhead_miles"])),
        "stops": final_stops,
        "weight": final_weight,
        "posted_trailer_type": posted_trailer_type,
        "commodity": commodity,
        "pickup_time": final_pickup_time,
        "delivery_time": first_value(row, ["delivery_time", "delivery_window", "delivery_appointment"]),
        "notes": merge_notes_summary(notes, parsed_notes),
        "parsed_notes": parsed_notes,
        "has_email": has_email,
        "has_phone": has_phone,
        "requires_tarp": requires_tarp,
        "is_od": is_od,
        "is_overweight": is_overweight,
        "broker_status": normalize_broker_status(row, notes),
        "broker_name": broker_name,
        "broker_mc": broker_mc,
        "broker_contact": contact_info.get("normalized_contact") or broker_contact_raw,
        "broker_contact_raw": broker_contact_raw,
        "parsed_contact": contact_info,
        "credit_score": credit_score,
        "days_to_pay": days_to_pay,
        "reference_id": reference_id,
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
    broker_count = 0
    mc_count = 0
    contact_count = 0
    reference_count = 0

    for load in loads:
        if "Parsed notes:" in load.get("notes", ""):
            parsed_count += 1

        if load.get("broker_name"):
            broker_count += 1

        if load.get("broker_mc"):
            mc_count += 1

        if load.get("broker_contact"):
            contact_count += 1

        if load.get("reference_id"):
            reference_count += 1

    print(f"Loads with parsed notes: {parsed_count}")
    print(f"Loads with broker name: {broker_count}")
    print(f"Loads with broker MC: {mc_count}")
    print(f"Loads with broker contact: {contact_count}")
    print(f"Loads with reference ID: {reference_count}")


if __name__ == "__main__":
    import_csv_to_json()
