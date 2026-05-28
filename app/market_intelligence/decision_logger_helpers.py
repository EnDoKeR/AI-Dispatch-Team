import hashlib


def safe_value(value, default=""):
    if value is None:
        return default

    return value


def safe_list(value):
    if isinstance(value, list):
        return value

    if value:
        return [str(value)]

    return []


def stable_text_hash(text):
    text = str(text or "").strip().lower()

    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def build_load_id(load):
    reference_id = str(getattr(load, "reference_id", "") or "").strip()
    broker_mc = str(getattr(load, "broker_mc", "") or "").strip()

    if reference_id and reference_id.upper() != "NO ID":
        if broker_mc:
            return f"MC{broker_mc}-REF{reference_id}"

        return f"REF{reference_id}"

    base = "|".join(
        [
            str(getattr(load, "pickup", "") or ""),
            str(getattr(load, "delivery", "") or ""),
            str(getattr(load, "rate", "") or ""),
            str(getattr(load, "loaded_miles", "") or ""),
            str(getattr(load, "weight", "") or ""),
            str(getattr(load, "broker_mc", "") or ""),
            str(getattr(load, "notes", "") or "")[:300],
        ]
    )

    return f"LOAD-{stable_text_hash(base)}"


def get_decision_category(load):
    status = str(getattr(load, "driver_match_status", "") or "").upper()

    if status == "MATCH":
        return "LOAD OPPORTUNITY"

    if status == "BLOCK":
        return "BLOCK"

    if status == "REVIEW_ONCE":
        if hasattr(load, "review_category") and callable(load.review_category):
            return load.review_category()

        return "GENERAL REVIEW"

    return status or "UNKNOWN"


def get_decision(load):
    status = str(getattr(load, "driver_match_status", "") or "").upper()

    if status in ["MATCH", "REVIEW_ONCE", "BLOCK"]:
        return status

    return status or "UNKNOWN"


def build_reason_list(load):
    reasons = []

    for attr_name in [
        "driver_match_notes",
        "match_reasons",
        "review_reasons",
        "block_reasons",
    ]:
        for reason in safe_list(getattr(load, attr_name, [])):
            reason_text = str(reason or "").strip()

            if reason_text and reason_text not in reasons:
                reasons.append(reason_text)

    return reasons
