from app.market_intelligence.decision_engine.result import (
    DECISION_BLOCK,
    DECISION_MATCH,
    DECISION_NO_ACTION,
    DECISION_REVIEW_ONCE,
    build_decision_result,
)


KNOWN_DECISIONS = {
    DECISION_MATCH,
    DECISION_REVIEW_ONCE,
    DECISION_BLOCK,
}


def value_from(source, key, default=""):
    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def normalize_status(value):
    status = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")

    if status in KNOWN_DECISIONS:
        return status

    return DECISION_NO_ACTION


def safe_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        items = value
    elif isinstance(value, (tuple, set)):
        items = list(value)
    else:
        items = [value]

    cleaned = []

    for item in items:
        text = str(item or "").strip()

        if text:
            cleaned.append(text)

    return cleaned


def dedupe_text(items):
    deduped = []
    seen = set()

    for item in safe_list(items):
        key = item.lower()

        if key in seen:
            continue

        seen.add(key)
        deduped.append(item)

    return deduped


def call_text(method, default=""):
    if not callable(method):
        return default

    try:
        value = method()
    except TypeError:
        return default

    return str(value or "").strip()


def category_from_load(load, decision):
    explicit_category = str(value_from(load, "category", "") or "").strip()

    if decision == DECISION_MATCH:
        return explicit_category or "LOAD OPPORTUNITY"

    if decision == DECISION_BLOCK:
        return explicit_category or "BLOCK"

    if decision == DECISION_REVIEW_ONCE:
        review_category = call_text(value_from(load, "review_category", None))

        return explicit_category or review_category or "GENERAL REVIEW"

    return explicit_category


def reason_fields(load):
    driver_notes = safe_list(value_from(load, "driver_match_notes", []))
    match_reasons = safe_list(value_from(load, "match_reasons", []))
    review_reasons = safe_list(value_from(load, "review_reasons", []))
    block_reasons = safe_list(value_from(load, "block_reasons", []))

    return driver_notes, match_reasons, review_reasons, block_reasons


def result_reasons(load, decision):
    driver_notes, match_reasons, review_reasons, block_reasons = reason_fields(load)

    if decision == DECISION_MATCH:
        return {
            "positive_signals": dedupe_text(driver_notes + match_reasons),
            "review_reasons": [],
            "block_reasons": [],
        }

    if decision == DECISION_REVIEW_ONCE:
        return {
            "positive_signals": dedupe_text(match_reasons),
            "review_reasons": dedupe_text(driver_notes + review_reasons),
            "block_reasons": [],
        }

    if decision == DECISION_BLOCK:
        return {
            "positive_signals": dedupe_text(match_reasons),
            "review_reasons": dedupe_text(review_reasons),
            "block_reasons": dedupe_text(driver_notes + block_reasons),
        }

    return {
        "positive_signals": dedupe_text(match_reasons),
        "review_reasons": dedupe_text(review_reasons),
        "block_reasons": dedupe_text(block_reasons),
    }


def truthy(value):
    if isinstance(value, bool):
        return value

    text = str(value or "").strip().lower()

    return text in ["1", "true", "yes", "y"]


def missing_number(value):
    if value in [None, ""]:
        return True

    try:
        return float(value) == 0
    except (TypeError, ValueError):
        return False


def reason_text(load):
    parts = []

    for values in reason_fields(load):
        parts.extend(values)

    return " ".join(parts).lower()


def add_flag(flags, flag_name):
    if flag_name not in flags:
        flags.append(flag_name)


def risk_flags_from_load(load):
    flags = []
    text = reason_text(load)

    if truthy(value_from(load, "is_low_rpm", False)) or "below preferred minimum" in text:
        add_flag(flags, "LOW_RPM")

    if truthy(value_from(load, "is_overweight", False)) or "weight" in text and "above" in text:
        add_flag(flags, "OVERWEIGHT")

    if truthy(value_from(load, "is_too_far_empty", False)) or "empty miles" in text and "above" in text:
        add_flag(flags, "PICKUP_TOO_FAR")

    if truthy(value_from(load, "is_local_load", False)) or "same pickup and delivery" in text or "local load" in text:
        add_flag(flags, "LOCAL_LOAD")

    if truthy(value_from(load, "is_od", False)) or any(
        term in text
        for term in [
            "od / permit",
            "permit load",
            "wide load",
            "oversize",
            "os/ow",
        ]
    ):
        add_flag(flags, "OD_PERMIT_LOAD")

    if any(
        term in text
        for term in [
            "rate is missing",
            "posted as $0",
            "rate check",
            "check rate with broker",
        ]
    ):
        add_flag(flags, "RATE_MISSING")
        add_flag(flags, "RATE_CHECK_REQUIRED")

    if "conestoga is not accepted" in text:
        add_flag(flags, "NO_CONESTOGA")

    if "conestoga must be verified" in text or "posted as flatbed" in text or "posted as flatbed/step deck" in text:
        add_flag(flags, "CONESTOGA_VERIFY")

    if "tracking required" in text:
        add_flag(flags, "TRACKING_REQUIRED")

    if "hazmat" in text:
        add_flag(flags, "HAZMAT_REQUIRED")

    if "twic" in text:
        add_flag(flags, "TWIC_REQUIRED")

    if "tanker" in text:
        add_flag(flags, "TANKER_REQUIRED")

    if "ramps" in text:
        add_flag(flags, "RAMPS_REQUIRED")

    if "dunnage" in text or "blocking" in text or "bracing" in text:
        add_flag(flags, "DUNNAGE_REQUIRED")

    if "legal status" in text or "us citizen" in text or "green card" in text or "work permit" in text:
        add_flag(flags, "LEGAL_STATUS_REQUIRED")

    if "broker memory watchlist" in text:
        add_flag(flags, "BROKER_WATCHLIST")

    if "rate negotiation risk" in text:
        add_flag(flags, "BROKER_RATE_NEGOTIATION_RISK")

    if "broker memory requires review" in text:
        add_flag(flags, "BROKER_RISK")

    if "cash/zelle" in text or "no-buy" in text or "risky broker payment" in text or "quickpay" in text:
        add_flag(flags, "PAYMENT_RISK")

    if "broker mc" in text and not str(value_from(load, "broker_mc", "") or "").strip():
        add_flag(flags, "BROKER_MC_MISSING")

    if "off-target" in text:
        add_flag(flags, "TARGET_DIRECTION_MISMATCH")

    if "actual pickup" in text:
        add_flag(flags, "ACTUAL_PICKUP_CHANGED")

    if "multiple stops" in text or "multi-stop" in text or "multistop" in text:
        add_flag(flags, "MULTISTOP_REVIEW")

    pickup_time = str(value_from(load, "pickup_time", "") or "").strip().upper()
    delivery_time = str(value_from(load, "delivery_time", "") or "").strip().upper()

    if pickup_time == "NEEDS CHECK":
        add_flag(flags, "PICKUP_TIME_NEEDS_CHECK")

    if delivery_time == "NEEDS CHECK":
        add_flag(flags, "DELIVERY_TIME_NEEDS_CHECK")

    return flags


def missing_fields_from_load(load):
    missing_fields = []
    text = reason_text(load)

    if missing_number(value_from(load, "rate", "")) and any(
        term in text
        for term in [
            "rate is missing",
            "posted as $0",
            "rate check",
            "check rate with broker",
        ]
    ):
        missing_fields.append("rate")

    if "weight is missing" in text:
        missing_fields.append("weight")

    if "broker mc" in text and not str(value_from(load, "broker_mc", "") or "").strip():
        missing_fields.append("broker_mc")

    return dedupe_text(missing_fields)


def needs_check_fields_from_load(load):
    needs_check_fields = []

    if str(value_from(load, "pickup_time", "") or "").strip().upper() == "NEEDS CHECK":
        needs_check_fields.append("pickup_time")

    if str(value_from(load, "delivery_time", "") or "").strip().upper() == "NEEDS CHECK":
        needs_check_fields.append("delivery_time")

    return needs_check_fields


def source_signals_from_load(load):
    return {
        "market_load": {
            "driver_match_status": value_from(load, "driver_match_status", ""),
            "driver_fit_status": value_from(load, "driver_fit_status", ""),
            "is_blocked": bool(value_from(load, "is_blocked", False)),
            "is_review_once": bool(value_from(load, "is_review_once", False)),
            "is_clean_match": bool(value_from(load, "is_clean_match", False)),
        }
    }


def decision_result_from_market_load(load):
    decision = normalize_status(value_from(load, "driver_match_status", ""))
    reasons = result_reasons(load, decision)
    category = category_from_load(load, decision)

    return build_decision_result(
        decision=decision,
        category=category,
        risk_flags=risk_flags_from_load(load),
        missing_fields=missing_fields_from_load(load),
        needs_check_fields=needs_check_fields_from_load(load),
        review_reasons=reasons["review_reasons"],
        block_reasons=reasons["block_reasons"],
        positive_signals=reasons["positive_signals"],
        confidence="HIGH" if decision in KNOWN_DECISIONS else "UNKNOWN",
        source_signals=source_signals_from_load(load),
        linked_load_id=value_from(load, "load_id", "") or value_from(load, "id", ""),
        reference_id=value_from(load, "reference_id", ""),
    )
