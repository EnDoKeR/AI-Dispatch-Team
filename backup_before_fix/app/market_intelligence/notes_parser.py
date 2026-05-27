import re


def normalize_text(value):
    return str(value or "").strip()


def lower_text(value):
    return normalize_text(value).lower()


def detect_tarp_required(text):
    text = lower_text(text)

    tarp_keywords = [
        "tarp",
        "tarps",
        "tarps required",
        "tarp required",
        "6ft tarp",
        "6 ft tarp",
        "8ft tarp",
        "8 ft tarp",
    ]

    no_tarp_keywords = [
        "no tarp",
        "no tarps",
        "no tarping",
        "not tarp",
    ]

    for keyword in no_tarp_keywords:
        if keyword in text:
            return False

    for keyword in tarp_keywords:
        if keyword in text:
            return True

    return False


def detect_od(text):
    text = lower_text(text)

    od_keywords = [
        "od",
        "over dimension",
        "over-dimensional",
        "oversize",
        "over size",
        "wide load",
        "permit load",
        "permits required",
        "permit required",
    ]

    for keyword in od_keywords:
        if keyword in text:
            return True

    # Examples: 111W, 126 wide, 10' wide
    if re.search(r"\b\d{3}\s*w\b", text):
        return True

    if re.search(r"\b\d+\s*wide\b", text):
        return True

    return False


def detect_overweight(text):
    text = lower_text(text)

    overweight_keywords = [
        "overweight",
        "over weight",
        "heavy haul",
    ]

    for keyword in overweight_keywords:
        if keyword in text:
            return True

    return False


def detect_no_conestoga(text):
    text = lower_text(text)

    keywords = [
        "no conestoga",
        "no conestogas",
        "flatbed only",
        "must be flatbed",
        "flat only",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_flatbed_required(text):
    text = lower_text(text)

    keywords = [
        "flatbed only",
        "must be flatbed",
        "flat only",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_forklift_required(text):
    text = lower_text(text)

    keywords = [
        "forklift",
        "moffett",
        "moffet",
        "piggyback",
        "loader required",
        "unload equipment",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_tracking_required(text):
    text = lower_text(text)

    keywords = [
        "tracking required",
        "tracking req",
        "macropoint",
        "trucker tools",
        "tracking must",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_appointment_required(text):
    text = lower_text(text)

    keywords = [
        "appt",
        "appointment",
        "appointment required",
        "by appointment",
        "appt only",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_straight_through(text):
    text = lower_text(text)

    keywords = [
        "straight through",
        "deliver straight through",
        "must deliver straight",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_weight_from_text(text):
    text = lower_text(text)

    patterns = [
        r"(\d{2,3})\s*k\s*lbs",
        r"(\d{2,3})\s*k\b",
        r"(\d{2,3},?\d{3})\s*lbs",
        r"(\d{2,3},?\d{3})\s*lb",
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

        except:
            pass

    return 0


def detect_stops_from_text(text):
    text = lower_text(text)

    pickup_count = None
    delivery_count = None

    pickup_patterns = [
        r"(\d+)\s*p/u",
        r"(\d+)\s*pu",
        r"(\d+)\s*pick",
        r"(\d+)\s*pickup",
        r"(\d+)\s*pickups",
    ]

    delivery_patterns = [
        r"(\d+)\s*d/o",
        r"(\d+)\s*del",
        r"(\d+)\s*drop",
        r"(\d+)\s*delivery",
        r"(\d+)\s*deliveries",
    ]

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

    # Common DAT style: 1P/1D, 2P/1D
    match = re.search(r"(\d+)\s*p\s*/\s*(\d+)\s*d", text)

    if match:
        return int(match.group(1)) + int(match.group(2))

    return 0


def detect_pickup_time_from_text(text):
    original = normalize_text(text)
    text_lower = lower_text(text)

    if "fcfs" in text_lower:
        match = re.search(
            r"(fcfs\s*\d{1,2}\s*(?:am|pm)?\s*[-to]+\s*\d{1,2}\s*(?:am|pm)?)",
            text_lower,
        )

        if match:
            return match.group(1).upper()

        return "FCFS - NEEDS HOURS CHECK"

    time_window = re.search(
        r"(\d{1,2}\s*(?:am|pm)\s*[-to]+\s*\d{1,2}\s*(?:am|pm))",
        text_lower,
    )

    if time_window:
        return time_window.group(1).upper()

    military_window = re.search(
        r"(\d{3,4}\s*[-to]+\s*\d{3,4})",
        text_lower,
    )

    if military_window:
        return military_window.group(1).upper()

    if detect_appointment_required(original):
        return "Appointment required"

    return ""


def parse_notes(notes="", commodity="", posted_trailer_type=""):
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

    flags = {
        "requires_tarp": detect_tarp_required(combined_text),
        "is_od": detect_od(combined_text),
        "is_overweight": detect_overweight(combined_text),
        "no_conestoga": detect_no_conestoga(combined_text),
        "flatbed_required": detect_flatbed_required(combined_text),
        "forklift_required": detect_forklift_required(combined_text),
        "tracking_required": detect_tracking_required(combined_text),
        "appointment_required": detect_appointment_required(combined_text),
        "straight_through": detect_straight_through(combined_text),
        "detected_weight": detected_weight,
        "detected_stops": detected_stops,
        "detected_pickup_time": detected_pickup_time,
    }

    notes_summary = []

    if flags["requires_tarp"]:
        notes_summary.append("tarps detected")

    if flags["is_od"]:
        notes_summary.append("OD / permit / wide load detected")

    if flags["is_overweight"]:
        notes_summary.append("overweight detected")

    if flags["no_conestoga"]:
        notes_summary.append("Conestoga may not be accepted")

    if flags["forklift_required"]:
        notes_summary.append("forklift / moffett / unloading equipment detected")

    if flags["tracking_required"]:
        notes_summary.append("tracking required")

    if flags["appointment_required"]:
        notes_summary.append("appointment required")

    if flags["straight_through"]:
        notes_summary.append("straight-through delivery detected")

    if detected_weight:
        notes_summary.append(f"weight detected from notes: {detected_weight}")

    if detected_stops:
        notes_summary.append(f"stops detected from notes: {detected_stops}")

    if detected_pickup_time:
        notes_summary.append(f"pickup time detected from notes: {detected_pickup_time}")

    flags["notes_summary"] = notes_summary

    return flags