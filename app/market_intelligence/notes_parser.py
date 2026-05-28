import re


from app.market_intelligence.notes_parser_text_helpers import (
    clean_text,
    lower_text,
    normalize_email,
    normalize_phone,
    normalize_text,
)


from app.market_intelligence.notes_parser_securement import (
    detect_number_of_straps,
    detect_straps_required,
    detect_tarp_required,
    detect_tarp_size,
)


from app.market_intelligence.notes_parser_dimensions import (
    detect_dimensions,
    detect_od,
    detect_overweight,
)


from app.market_intelligence.notes_parser_equipment import (
    detect_conestoga_ok,
    detect_flatbed_preferred,
    detect_flatbed_required,
    detect_no_box_truck,
    detect_no_conestoga,
    detect_stepdeck_allowed,
)


from app.market_intelligence.notes_parser_load_requirements import (
    detect_appointment_required,
    detect_forklift_required,
    detect_ramps_required,
    detect_straight_through,
    detect_tracking_required,
)


from app.market_intelligence.notes_parser_payment import (
    detect_cash_or_zelle,
    detect_quickpay_review,
)


def detect_hazmat_required(text):
    text = clean_text(text)

    patterns = [
        r"\bhazmat\b",
        r"\bhaz\s*mat\b",
        r"\bhazmat\s*required\b",
        r"\bhazmat\s*with\s*tarps\b",
        r"\bhazmat\s*load\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_tanker_required(text):
    text = clean_text(text)

    patterns = [
        r"\btanker\b",
        r"\btanker\s*endorsement\b",
        r"\btanker\s*endorsment\b",
        r"\btanker\s*required\b",
        r"\btanker\s*endorsement\s*required\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_twic_required(text):
    text = clean_text(text)

    patterns = [
        r"\btwic\b",
        r"\btwic\s*card\b",
        r"\btwic\s*required\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_document_required(text):
    text = clean_text(text)

    patterns = [
        r"\bus\s*citizen\b",
        r"\bu\.s\.\s*citizen\b",
        r"\bgreen\s*card\b",
        r"\bwork\s*permit\b",
        r"\bpassport\b",
        r"\bdriver\s*license\b",
        r"\bdl\s*required\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_iso_tank_required(text):
    text = clean_text(text)

    patterns = [
        r"\biso\s*tank\b",
        r"\biso\s*tanks\b",
        r"\bisotank\b",
        r"\bisotanks\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_weight_unknown(text, posted_weight=0):
    text = clean_text(text)

    try:
        if int(float(posted_weight or 0)) == 1:
            return True
    except Exception:
        pass

    patterns = [
        r"\bweight\s*needs\s*check\b",
        r"\bconfirm\s*weight\b",
        r"\bverify\s*weight\b",
        r"\bweight\s*tbd\b",
        r"\bweight\s*unknown\b",
        r"\bcall\s*for\s*weight\b",
        r"\bweight\s*1\s*lb\b",
        r"\bweight\s*1\s*lbs\b",
        r"\bposted\s*weight\s*1\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_weight_from_text(text):
    text = clean_text(text)

    patterns = [
        r"\b(\d{2,3})\s*k\s*lbs\b",
        r"\b(\d{2,3})\s*k\s*lb\b",
        r"\b(\d{2,3})\s*k\b",
        r"\b(\d{2,3},?\d{3})\s*lbs\b",
        r"\b(\d{2,3},?\d{3})\s*lb\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if not match:
            continue

        raw = match.group(1).replace(",", "")

        try:
            number = int(raw)

            if number < 1000:
                number = number * 1000

            if 1000 <= number <= 100000:
                return number

        except Exception:
            pass

    return 0


def detect_stops_from_text(text):
    text = clean_text(text)

    pickup_count = None
    delivery_count = None

    pickup_patterns = [
        r"\b(\d+)\s*p/u\b",
        r"\b(\d+)\s*pu\b",
        r"\b(\d+)\s*pick\b",
        r"\b(\d+)\s*pickup\b",
        r"\b(\d+)\s*pickups\b",
        r"\b(\d+)\s*p\b",
    ]

    delivery_patterns = [
        r"\b(\d+)\s*d/o\b",
        r"\b(\d+)\s*del\b",
        r"\b(\d+)\s*drop\b",
        r"\b(\d+)\s*drops\b",
        r"\b(\d+)\s*delivery\b",
        r"\b(\d+)\s*deliveries\b",
        r"\b(\d+)\s*d\b",
    ]

    # Common DAT style: 1P/1D, 2P/1D
    match = re.search(r"\b(\d+)\s*p\s*/\s*(\d+)\s*d\b", text)
    if match:
        return int(match.group(1)) + int(match.group(2))

    for pattern in pickup_patterns:
        match = re.search(pattern, text)
        if match:
            pickup_count = int(match.group(1))
            break

    for pattern in delivery_patterns:
        match = re.search(pattern, text)
        if match:
            delivery_count = int(match.group(1))
            break

    if pickup_count is not None or delivery_count is not None:
        if pickup_count is None:
            pickup_count = 1

        if delivery_count is None:
            delivery_count = 1

        return pickup_count + delivery_count

    # Examples:
    # "1 drop in hayward, 1 drop in tacoma"
    drop_matches = re.findall(r"\b\d+\s*drop\b", text)
    if drop_matches:
        return len(drop_matches) + 1

    multistop_patterns = [
        r"\bmultistop\b",
        r"\bmulti\s*stop\b",
        r"\bmulti\s*stops\b",
        r"\bmultiple\s*stops\b",
        r"\bmultiple\s*drops\b",
        r"\bmultiple\s*pickups\b",
    ]

    for pattern in multistop_patterns:
        if re.search(pattern, text):
            return 2

    # "multiple loads available" is NOT stops.
    return 0


def detect_pickup_time_from_text(text):
    original = normalize_text(text)
    text_lower = clean_text(text)

    if "fcfs" in text_lower:
        match = re.search(
            r"\bfcfs\s*\d{1,2}\s*(?:am|pm)?\s*(?:-|to)\s*\d{1,2}\s*(?:am|pm)?\b",
            text_lower,
        )

        if match:
            return match.group(0).upper()

        return "FCFS - NEEDS HOURS CHECK"

    time_window = re.search(
        r"\b\d{1,2}\s*(?:am|pm)\s*(?:-|to)\s*\d{1,2}\s*(?:am|pm)\b",
        text_lower,
    )

    if time_window:
        return time_window.group(0).upper()

    # Important: require 4 digits on both sides, so phone numbers like 443-2707 are NOT detected as time.
    military_window = re.search(
        r"\b([01]\d{3}|2[0-3]\d{2})\s*(?:-|to)\s*([01]\d{3}|2[0-3]\d{2})\b",
        text_lower,
    )

    if military_window:
        return military_window.group(0).upper()

    if re.search(r"\bready\s*now\b", text_lower):
        return "Ready now"

    if detect_appointment_required(original):
        return "Appointment required"

    return ""


def detect_contact_override(text):
    original = normalize_text(text)

    result = {
        "phone": "",
        "extension": "",
        "email": "",
    }

    phone_match = re.search(
        r"(\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})(?:\s*(?:x|ext|extension|ex)\s*\.?\s*(\d+))?",
        original,
        re.IGNORECASE,
    )

    if phone_match:
        result["phone"] = normalize_phone(phone_match.group(1))
        if phone_match.group(2):
            result["extension"] = phone_match.group(2).strip()

    # Direct or broken email:
    # name@domain.com
    # name@domain`com
    # name at domain dot com
    # name@domain com
    email_patterns = [
        r"(?<![A-Za-z0-9])(?:[A-Za-z0-9]\s+){2,}[A-Za-z0-9]\s+at\s+[A-Za-z0-9.\-]+\s+dot\s+[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s*@\s*[A-Za-z0-9.\-]+\s*(?:\.|`|,|\s+dot\s+|\s+)\s*[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s+at\s+[A-Za-z0-9.\-]+\s*(?:\.|\s+dot\s+|\s+)\s*[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s*\(\s*at\s*\)\s*[A-Za-z0-9.\-]+\s*\(\s*dot\s*\)\s*[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s*\[\s*at\s*\]\s*[A-Za-z0-9.\-]+\s*\[\s*dot\s*\]\s*[A-Za-z]{2,}",
    ]

    for pattern in email_patterns:
        email_match = re.search(pattern, original, re.IGNORECASE)
        if email_match:
            email = normalize_email(email_match.group(0))
            if email:
                result["email"] = email
                break

    return result


def detect_actual_pickup_city(text):
    original = normalize_text(text)

    city_state_patterns = [
        r"actual\s*pickup\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actual\s*pick\s*up\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actual\s*pu\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actual\s*pickup\s*city\s+([a-zA-Z\s.]+),?\s+([A-Z]{2})",
        r"actual\s*pick\s*up\s*[-:]+\s*([a-zA-Z\s.]+)\s*\(\s*([A-Z]{2})\s*\)",
        r"actual\s*pickup\s*[-:]+\s*([a-zA-Z\s.]+)\s*\(\s*([A-Z]{2})\s*\)",
        r"actual\s*pu\s*[-:]+\s*([a-zA-Z\s.]+)\s*\(\s*([A-Z]{2})\s*\)",
        r"load\s*actually\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actually\s*load\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"actually\s*loads\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"real\s*pickup\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"correct\s*pickup\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
        r"pickup\s*is\s*actually\s*in\s+([a-zA-Z\s.]+),\s*([A-Z]{2})",
    ]

    for pattern in city_state_patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            city = match.group(1).strip(" .,-:")
            state = match.group(2).strip().upper()
            return f"{city}, {state}"

    return ""


def detect_extra_pickup(text):
    text = clean_text(text)

    patterns = [
        r"\bextra\s*pick\s*up\b",
        r"\bextra\s*pickup\b",
        r"\bextra\s*pu\b",
        r"\badditional\s*pickup\b",
        r"\badditional\s*pu\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_multiple_loads_available(text):
    text = clean_text(text)

    patterns = [
        r"\bmultiple\s*loads\s*available\b",
        r"\bmore\s*loads\s*available\b",
        r"\bseveral\s*loads\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_dedicated_lane(text):
    text = clean_text(text)

    patterns = [
        r"\bdedicated\s*lane\b",
        r"\bneed\s*solid\s*drivers\b",
        r"\bneed\s*solid\s*driver\b",
        r"\bconsistent\s*lane\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_double_brokering_language(text):
    text = clean_text(text)

    patterns = [
        r"\bno\s*double\s*brokering\b",
        r"\bno\s*double\s*broker\b",
        r"\bdouble\s*brokering\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_mc_must_match(text):
    text = clean_text(text)

    patterns = [
        r"\bmc\s*must\s*match\b",
        r"\bname\s*must\s*match\b",
        r"\bcarrier\s*name\s*must\s*match\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def parse_notes(notes="", commodity="", posted_trailer_type="", posted_weight=0):
    combined_text = " ".join(
        [
            normalize_text(notes),
            normalize_text(commodity),
            normalize_text(posted_trailer_type),
        ]
    )

    detected_weight = detect_weight_from_text(combined_text)
    detected_stops = detect_stops_from_text(combined_text)
    detected_pickup_time = detect_pickup_time_from_text(combined_text)
    detected_contact = detect_contact_override(combined_text)
    detected_actual_pickup_city = detect_actual_pickup_city(combined_text)
    detected_dimensions = detect_dimensions(combined_text)
    tarp_size = detect_tarp_size(combined_text)
    strap_count = detect_number_of_straps(combined_text)

    flags = {
        "requires_tarp": detect_tarp_required(combined_text),
        "tarp_size": tarp_size,

        "requires_straps": detect_straps_required(combined_text),
        "strap_count": strap_count,

        "is_od": detect_od(combined_text),
        "dimensions": detected_dimensions,

        "is_overweight": detect_overweight(combined_text),
        "no_conestoga": detect_no_conestoga(combined_text),
        "conestoga_ok": detect_conestoga_ok(combined_text),
        "flatbed_required": detect_flatbed_required(combined_text),
        "flatbed_preferred": detect_flatbed_preferred(combined_text),
        "stepdeck_allowed": detect_stepdeck_allowed(combined_text),
        "no_box_truck": detect_no_box_truck(combined_text),

        "forklift_required": detect_forklift_required(combined_text),
        "ramps_required": detect_ramps_required(combined_text),
        "tracking_required": detect_tracking_required(combined_text),
        "appointment_required": detect_appointment_required(combined_text),
        "straight_through": detect_straight_through(combined_text),

        "cash_or_zelle": detect_cash_or_zelle(combined_text),
        "quickpay_review": detect_quickpay_review(combined_text),

        "hazmat_required": detect_hazmat_required(combined_text),
        "tanker_required": detect_tanker_required(combined_text),
        "twic_required": detect_twic_required(combined_text),
        "document_required": detect_document_required(combined_text),
        "iso_tank_required": detect_iso_tank_required(combined_text),

        "weight_unknown": detect_weight_unknown(combined_text, posted_weight),
        "detected_weight": detected_weight,
        "detected_stops": detected_stops,
        "detected_pickup_time": detected_pickup_time,
        "detected_contact": detected_contact,
        "actual_pickup_city": detected_actual_pickup_city,

        "extra_pickup": detect_extra_pickup(combined_text),
        "multiple_loads_available": detect_multiple_loads_available(combined_text),
        "dedicated_lane": detect_dedicated_lane(combined_text),
        "double_brokering_language": detect_double_brokering_language(combined_text),
        "mc_must_match": detect_mc_must_match(combined_text),
    }

    notes_summary = []

    if flags["requires_tarp"]:
        if tarp_size:
            notes_summary.append(f"{tarp_size} tarps detected")
        else:
            notes_summary.append("tarps detected")

    if flags["requires_straps"]:
        if strap_count:
            notes_summary.append(f"{strap_count} straps required")
        else:
            notes_summary.append("straps required")

    if flags["is_od"]:
        notes_summary.append("OD / permit / wide load detected")

    if detected_dimensions["raw"]:
        notes_summary.append(f"dimensions detected: {detected_dimensions['raw']}")

    if flags["is_overweight"]:
        notes_summary.append("overweight detected")

    if flags["no_conestoga"]:
        notes_summary.append("Conestoga may not be accepted")

    if flags["conestoga_ok"]:
        notes_summary.append("Conestoga appears acceptable")

    if flags["flatbed_required"]:
        notes_summary.append("flatbed required")

    if flags["flatbed_preferred"]:
        notes_summary.append("flatbed preferred; verify Conestoga acceptance")

    if flags["stepdeck_allowed"]:
        notes_summary.append("flatbed or step deck allowed")

    if flags["no_box_truck"]:
        notes_summary.append("no box truck")

    if flags["forklift_required"]:
        notes_summary.append("forklift / moffett / unloading equipment detected")

    if flags["ramps_required"]:
        notes_summary.append("ramps required")

    if flags["tracking_required"]:
        notes_summary.append("tracking required")

    if flags["appointment_required"]:
        notes_summary.append("appointment required")

    if flags["straight_through"]:
        notes_summary.append("straight-through delivery detected")

    if flags["cash_or_zelle"]:
        notes_summary.append("cash/Zelle payment language detected")

    if flags["quickpay_review"]:
        notes_summary.append("QuickPay language detected; check broker MC")

    if flags["hazmat_required"]:
        notes_summary.append("hazmat required")

    if flags["tanker_required"]:
        notes_summary.append("tanker endorsement required")

    if flags["twic_required"]:
        notes_summary.append("TWIC required")

    if flags["document_required"]:
        notes_summary.append("driver document requirement detected")

    if flags["iso_tank_required"]:
        notes_summary.append("ISO tank document/review warning detected")

    if flags["weight_unknown"]:
        notes_summary.append("posted weight may be incorrect / must verify real weight")

    if detected_weight:
        notes_summary.append(f"weight detected from notes: {detected_weight}")

    if detected_stops:
        notes_summary.append(f"stops detected from notes: {detected_stops}")

    if detected_pickup_time:
        notes_summary.append(f"pickup time detected from notes: {detected_pickup_time}")

    if detected_contact["phone"] or detected_contact["email"]:
        contact_parts = []

        if detected_contact["phone"]:
            phone_text = detected_contact["phone"]
            if detected_contact["extension"]:
                phone_text += f" x{detected_contact['extension']}"
            contact_parts.append(phone_text)

        if detected_contact["email"]:
            contact_parts.append(detected_contact["email"])

        notes_summary.append("contact override detected: " + " / ".join(contact_parts))

    if detected_actual_pickup_city:
        notes_summary.append(f"actual pickup city detected from notes: {detected_actual_pickup_city}")

    if flags["extra_pickup"]:
        notes_summary.append("extra pickup detected")

    if flags["multiple_loads_available"]:
        notes_summary.append("multiple loads available")

    if flags["dedicated_lane"]:
        notes_summary.append("dedicated lane / solid driver language detected")

    if flags["double_brokering_language"]:
        notes_summary.append("double brokering language detected")

    if flags["mc_must_match"]:
        notes_summary.append("MC / carrier name must match")

    flags["notes_summary"] = notes_summary

    return flags
