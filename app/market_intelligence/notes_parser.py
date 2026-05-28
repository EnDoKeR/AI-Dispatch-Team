import re


def normalize_text(value):
    return str(value or "").strip()


def lower_text(value):
    return normalize_text(value).lower()


def clean_text(value):
    text = lower_text(value)

    replacements = {
        "`": ".",
        "вЂ™": "'",
        "вЂ": "'",
        "вЂњ": '"',
        "вЂќ": '"',
        "_": " ",
        ";": " ",
        "|": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_email(raw_email):
    if not raw_email:
        return ""

    email = str(raw_email).strip().lower()

    email = email.replace("`", ".")
    email = email.replace("'", "")

    email = re.sub(r"\s*\(\s*at\s*\)\s*", "@", email)
    email = re.sub(r"\s*\[\s*at\s*\]\s*", "@", email)
    email = re.sub(r"\s+at\s+", "@", email)
    email = re.sub(r"\bat\b", "@", email)

    email = re.sub(r"\s*\(\s*dot\s*\)\s*", ".", email)
    email = re.sub(r"\s*\[\s*dot\s*\]\s*", ".", email)
    email = re.sub(r"\s+dot\s+", ".", email)
    email = re.sub(r"\bdot\b", ".", email)

    email = email.replace(" ", "")

    # Common DAT/manual mistakes:
    # info@national-transportservices`com
    # info@national-transportservices com
    # info@national-transportservices,com
    email = email.replace(",", ".")
    email = email.replace(";", ".")

    # Fix duplicated dots
    email = re.sub(r"\.{2,}", ".", email)

    # Remove invalid trailing characters
    email = email.strip(".-_:,/")

    if "@" not in email:
        return ""

    if not re.search(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", email):
        return ""

    return email


def normalize_phone(raw_phone):
    if not raw_phone:
        return ""

    phone = str(raw_phone).strip()
    phone = re.sub(r"\s+", " ", phone)
    return phone


def detect_tarp_required(text):
    text = clean_text(text)

    no_tarp_patterns = [
        r"\bno\s*tarp\b",
        r"\bno\s*tarps\b",
        r"\bno\s*tarping\b",
        r"\bnot\s*tarp\b",
        r"\bnot\s*tarps\b",
        r"\btarp\s*not\s*required\b",
        r"\btarps\s*not\s*required\b",
        r"\btarp\s*not\s*needed\b",
        r"\btarps\s*not\s*needed\b",
        r"\bno\s*tarp\s*needed\b",
        r"\bno\s*tarps\s*needed\b",
    ]

    for pattern in no_tarp_patterns:
        if re.search(pattern, text):
            return False

    tarp_patterns = [
        r"\btarp\s*required\b",
        r"\btarps\s*required\b",
        r"\btarp\s*req\b",
        r"\btarps\s*req\b",
        r"\btarp\s*needed\b",
        r"\btarps\s*needed\b",
        r"\bneed\s*tarp\b",
        r"\bneed\s*tarps\b",
        r"\bneeds\s*tarp\b",
        r"\bneeds\s*tarps\b",
        r"\b\d+\s*ft\s*tarp\b",
        r"\b\d+\s*ft\s*tarps\b",
        r"\b\d+ft\s*tarp\b",
        r"\b\d+ft\s*tarps\b",
        r"\b\d+'\s*tarp\b",
        r"\b\d+'\s*tarps\b",
        r"\b\d+\s*foot\s*tarp\b",
        r"\b\d+\s*foot\s*tarps\b",
    ]

    for pattern in tarp_patterns:
        if re.search(pattern, text):
            return True

    # Example from screenshots: "6FT" alone means tarp requirement.
    if re.search(r"\b(4|6|8)\s*ft\b", text):
        return True

    return False


def detect_tarp_size(text):
    text = clean_text(text)

    patterns = [
        r"\b(4|6|8)\s*ft\s*tarps?\b",
        r"\b(4|6|8)ft\s*tarps?\b",
        r"\b(4|6|8)'\s*tarps?\b",
        r"\b(4|6|8)\s*foot\s*tarps?\b",
        r"\bneed\s*(4|6|8)\s*ft\b",
        r"\b(4|6|8)\s*ft\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return f"{match.group(1)} ft"

    return ""


def detect_straps_required(text):
    text = clean_text(text)

    patterns = [
        r"\bstrap\s*and\s*go\b",
        r"\bstraps?\s*required\b",
        r"\bstraps?\s*req\b",
        r"\bneed\s*straps?\b",
        r"\bneeds\s*straps?\b",
        r"\b\d+\s*straps?\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_number_of_straps(text):
    text = clean_text(text)

    match = re.search(r"\b(\d+)\s*straps?\b", text)
    if match:
        return int(match.group(1))

    return 0


def detect_od(text):
    text = clean_text(text)

    # Do NOT search simple "od" alone.
    od_patterns = [
        r"\bpermit\s*load\b",
        r"\bpermits\s*required\b",
        r"\bpermit\s*required\b",
        r"\bpermit\s*needed\b",
        r"\bneeds\s*permit\b",
        r"\bneed\s*permit\b",
        r"\bneed\s*permits\b",
        r"\brequires\s*permit\b",
        r"\bover\s*dimension\b",
        r"\bover\s*dimensional\b",
        r"\boverdimension\b",
        r"\boverdimensional\b",
        r"\bover\s*size\b",
        r"\boversize\b",
        r"\bwide\s*load\b",
        r"\bwide\b.*\bload\b",
        r"\bod\s*load\b",
        r"\bod\s*permit\b",
        r"\bod\s*required\b",
        r"\bod\s*req\b",
        r"\bod\s*/\s*permit\b",
        r"\bescort\s*required\b",
        r"\bpilot\s*car\b",
        r"\blegal\s*overdimension\b",
        r"\blegal\s*over\s*dimension\b",
    ]

    for pattern in od_patterns:
        if re.search(pattern, text):
            return True

    # Width over legal 102 inches.
    width_patterns = [
        r"\b(10[3-9]|1[1-9][0-9])\s*w\b",
        r"\b(10[3-9]|1[1-9][0-9])\s*wide\b",
        r"\b(10[3-9]|1[1-9][0-9])\s*inch\s*wide\b",
        r"\b(10[3-9]|1[1-9][0-9])\s*inches\s*wide\b",
    ]

    for pattern in width_patterns:
        if re.search(pattern, text):
            return True

    # Examples: 58L x 111W x 7H
    dimension_patterns = [
        r"\b\d+\s*l\s*x\s*(10[3-9]|1[1-9][0-9])\s*w\b",
        r"\b\d+\s*x\s*(10[3-9]|1[1-9][0-9])\s*x\s*\d+\b",
        r"\b\d+\s*long\s*x\s*(10[3-9]|1[1-9][0-9])\s*wide\b",
    ]

    for pattern in dimension_patterns:
        if re.search(pattern, text):
            return True

    # 9 ft+ width should be review/OD.
    feet_width_patterns = [
        r"\b(9|10|11|12|13|14|15|16)\s*ft\s*wide\b",
        r"\b(9|10|11|12|13|14|15|16)'\s*wide\b",
        r"\b(9|10|11|12|13|14|15|16)\s*feet\s*wide\b",
    ]

    for pattern in feet_width_patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_dimensions(text):
    text = clean_text(text)

    result = {
        "length": "",
        "width": "",
        "height": "",
        "raw": "",
    }

    patterns = [
        r"\b(\d+(?:\.\d+)?)\s*l\s*x\s*(\d+(?:\.\d+)?)\s*w\s*x\s*(\d+(?:\.\d+)?)\s*h\b",
        r"\b(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\b",
        r"\b(\d+(?:\.\d+)?)\s*long\s*x\s*(\d+(?:\.\d+)?)\s*wide\s*x\s*(\d+(?:\.\d+)?)\s*high\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            result["length"] = match.group(1)
            result["width"] = match.group(2)
            result["height"] = match.group(3)
            result["raw"] = match.group(0)
            return result

    return result


def detect_overweight(text):
    text = clean_text(text)

    keywords = [
        "overweight",
        "over weight",
        "heavy haul",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_no_conestoga(text):
    text = clean_text(text)

    keywords = [
        "no conestoga",
        "no conestogas",
        "no stoga",
        "no stogas",
        "conestoga no",
        "flatbed only",
        "flat only",
        "must be flatbed",
        "conestoga wouldn't work",
        "conestoga would not work",
        "conestoga wont work",
        "conestoga won't work",
        "no con",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_conestoga_ok(text):
    text = clean_text(text)

    patterns = [
        r"\bconestoga\s*ok\b",
        r"\bstoga\s*ok\b",
        r"\bconestoga\s*works\b",
        r"\bconestoga\s*accepted\b",
        r"\btarps?\s*/\s*conestoga\s*ok\b",
        r"\bconestoga\s*would\s*work\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_flatbed_required(text):
    text = clean_text(text)

    keywords = [
        "flatbed only",
        "must be flatbed",
        "flat only",
        "flatbed required",
        "flatbed needed",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_stepdeck_allowed(text):
    text = clean_text(text)

    patterns = [
        r"\bflatbed\s*or\s*step\s*deck\b",
        r"\bflatbed\s*/\s*step\s*deck\b",
        r"\bfd\s*or\s*sd\b",
        r"\bsd\s*or\s*fd\b",
        r"\bstepdeck\s*ok\b",
        r"\bstep\s*deck\s*ok\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_no_box_truck(text):
    text = clean_text(text)

    patterns = [
        r"\bno\s*box\s*truck\b",
        r"\bno\s*box\s*trucks\b",
        r"\bno\s*box\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_forklift_required(text):
    text = clean_text(text)

    keywords = [
        "forklift",
        "moffett",
        "moffet",
        "piggyback",
        "loader required",
        "unload equipment",
        "unloading equipment",
        "driver unload",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_ramps_required(text):
    text = clean_text(text)

    patterns = [
        r"\bneed\s*ramps\b",
        r"\bneeds\s*ramps\b",
        r"\bramps?\s*required\b",
        r"\bramps?\s*needed\b",
        r"\bramps?\s*req\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_tracking_required(text):
    text = clean_text(text)

    keywords = [
        "tracking required",
        "tracking req",
        "tracking must",
        "macropoint",
        "macro point",
        "trucker tools",
        "12 month active mc required",
        "12 months active mc required",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_appointment_required(text):
    text = clean_text(text)

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
    text = clean_text(text)

    keywords = [
        "straight through",
        "deliver straight through",
        "must deliver straight",
        "straight thru",
        "deliver straight thru",
        "straight thru delivery",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False


def detect_cash_or_zelle(text):
    text = clean_text(text)

    patterns = [
        r"\bcash\s*or\s*zelle\b",
        r"\bzelle\s*or\s*cash\b",
        r"\bcashapp\b",
        r"\bcash\s*app\b",
        r"\bzelle\b",
        r"\bcash\s*on\s*delivery\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_quickpay_review(text):
    text = clean_text(text)

    patterns = [
        r"\bquickpay\b",
        r"\bquick\s*pay\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


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
        r"[A-Za-z0-9._%+\-]+\s*@\s*[A-Za-z0-9.\-]+\s*(?:\.|`|,|\s+dot\s+|\s+)\s*[A-Za-z]{2,}",
        r"[A-Za-z0-9._%+\-]+\s+at\s+[A-Za-z0-9.\-]+\s+(?:dot\s+)?[A-Za-z]{2,}",
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

    patterns = [
        r"actually\s*load\s*in\s+([a-zA-Z\s.]+,\s*[A-Z]{2})",
        r"actual\s*pickup\s*in\s+([a-zA-Z\s.]+,\s*[A-Z]{2})",
        r"actual\s*pick\s*up\s*in\s+([a-zA-Z\s.]+,\s*[A-Z]{2})",
        r"actual\s*pu\s*in\s+([a-zA-Z\s.]+,\s*[A-Z]{2})",
        r"load\s*in\s+([a-zA-Z\s.]+,\s*[A-Z]{2})",
        r"pickup\s*in\s+([a-zA-Z\s.]+,\s*[A-Z]{2})",
        r"pu\s*in\s+([a-zA-Z\s.]+,\s*[A-Z]{2})",
        r"load\s*actually\s*in\s+([a-zA-Z\s.]+,\s*[A-Z]{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,-")

    soft_patterns = [
        r"actually\s*load\s*in\s+([a-zA-Z\s.]+)",
        r"actual\s*pickup\s*in\s+([a-zA-Z\s.]+)",
        r"actual\s*pick\s*up\s*in\s+([a-zA-Z\s.]+)",
        r"actual\s*pu\s*in\s+([a-zA-Z\s.]+)",
        r"load\s*actually\s*in\s+([a-zA-Z\s.]+)",
        r"load\s*in\s+([a-zA-Z\s.]+)",
    ]

    stop_words = [
        "today",
        "tomorrow",
        "with",
        "from",
        "at",
        "pickup",
        "delivery",
        "deliver",
        "need",
        "needs",
        "no",
        "yes",
        "load",
    ]

    for pattern in soft_patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            city = match.group(1).strip(" .,-")
            city_words = city.split()
            clean_words = []

            for word in city_words:
                if word.lower().strip(".,") in stop_words:
                    break
                clean_words.append(word)

            if clean_words:
                return " ".join(clean_words).strip(" .,-")

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
