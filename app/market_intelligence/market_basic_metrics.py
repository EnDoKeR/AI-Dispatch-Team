def to_number(value):
    if value is None:
        return 0

    if isinstance(value, (int, float)):
        return value

    text = str(value).strip()

    if not text:
        return 0

    text = text.replace("$", "")
    text = text.replace(",", "")
    text = text.replace("lbs", "")
    text = text.replace("lb", "")
    text = text.replace("mi", "")
    text = text.strip()

    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return 0


def to_bool(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    text = str(value).strip().lower()

    return text in ["true", "1", "yes", "y", "book", "bookable"]


def rpm(load):
    if not load.total_miles:
        return 0

    return round(load.rate / load.total_miles, 2)


def loaded_rpm(load):
    if not load.loaded_miles:
        return 0

    return round(load.rate / load.loaded_miles, 2)


def calculate_bucket(load):
    miles = load.loaded_miles or load.total_miles

    if miles < 450:
        return "0-450"

    if miles < 700:
        return "450-700"

    if miles < 1300:
        return "700-1300"

    return "1300+"


def lane_key(load):
    return f"{load.origin} -> {load.destination}"


def broker_key(load):
    return f"{load.broker_name}|{load.broker_mc}".strip("|")
