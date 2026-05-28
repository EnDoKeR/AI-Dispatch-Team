import hashlib


def stable_hash(text):
    text = str(text or "").strip().lower()

    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def normalize_text(value):
    return str(value or "").strip().lower()


def normalize_raw_text(value):
    return str(value or "").strip()


def build_case_id(driver_name, load_id, reference_id="", broker_mc=""):
    reference_id = str(reference_id or "").strip()
    load_id = str(load_id or "").strip()
    driver_name = str(driver_name or "").strip()
    broker_mc = str(broker_mc or "").strip()

    if reference_id and reference_id.upper() != "NO ID":
        base = f"{driver_name}|REF:{reference_id}|MC:{broker_mc}"

    elif load_id:
        base = f"{driver_name}|LOAD:{load_id}|MC:{broker_mc}"

    else:
        base = f"{driver_name}|MC:{broker_mc}"

    return f"CASE-{stable_hash(base)}"


def has_valid_reference_id(reference_id):
    reference_id = str(reference_id or "").strip()

    if not reference_id:
        return False

    invalid_values = {
        "NO ID",
        "NO_ID",
        "NEEDS CHECK",
        "NEEDS_CHECK",
        "UNKNOWN",
        "NONE",
        "N/A",
        "NA",
    }

    return reference_id.upper() not in invalid_values


def same_reference_id(left_reference_id, right_reference_id):
    if not has_valid_reference_id(left_reference_id):
        return False

    if not has_valid_reference_id(right_reference_id):
        return False

    return normalize_text(left_reference_id) == normalize_text(right_reference_id)


def same_driver_name(left_driver_name, right_driver_name):
    return normalize_text(left_driver_name) == normalize_text(right_driver_name)


def same_load_id(left_load_id, right_load_id):
    left_load_id = normalize_text(left_load_id)
    right_load_id = normalize_text(right_load_id)

    if not left_load_id or not right_load_id:
        return False

    return left_load_id == right_load_id


def same_lane(left_pickup, left_delivery, right_pickup, right_delivery):
    return (
        normalize_text(left_pickup) == normalize_text(right_pickup)
        and normalize_text(left_delivery) == normalize_text(right_delivery)
    )