ACTION_BLOCK = "BLOCK"
ACTION_REVIEW = "REVIEW"
ACTION_INFO = "INFO"

CATEGORY_MISSING_DATA = "missing_data"
CATEGORY_EQUIPMENT = "equipment_mismatch"
CATEGORY_CONESTOGA = "conestoga_compatibility"
CATEGORY_WEIGHT_DIMENSIONS = "weight_dimensions"
CATEGORY_TIMING = "appointment_timing"
CATEGORY_RATE_MARKET = "rate_market"
CATEGORY_EXIT_RISK = "reload_exit_risk"
CATEGORY_BROKER_PAYMENT = "broker_payment"
CATEGORY_DOCUMENTS = "document_requirements"
CATEGORY_TRACKING_DRIVER = "tracking_driver_requirements"
CATEGORY_NOTES_AMBIGUITY = "notes_ambiguity"
CATEGORY_PARSER_CONFIDENCE = "parser_confidence"
CATEGORY_ACCOUNTING_FUTURE = "accounting_future"


def flag(name, category, usual_action, meaning):
    return {
        "name": name,
        "category": category,
        "usual_action": usual_action,
        "meaning": meaning,
    }


RISK_FLAGS = {
    "MISSING_RATE": flag(
        "MISSING_RATE",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Rate is absent or posted as zero.",
    ),
    "MISSING_WEIGHT": flag(
        "MISSING_WEIGHT",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Weight is missing.",
    ),
    "MISSING_DIMENSIONS": flag(
        "MISSING_DIMENSIONS",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Dimensions are missing when they matter for compatibility.",
    ),
    "MISSING_COMMODITY": flag(
        "MISSING_COMMODITY",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Commodity is missing.",
    ),
    "MISSING_REFERENCE_ID": flag(
        "MISSING_REFERENCE_ID",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Broker/load/reference number is missing.",
    ),
    "MISSING_PICKUP_DATE": flag(
        "MISSING_PICKUP_DATE",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Pickup date is missing.",
    ),
    "MISSING_DELIVERY_DATE": flag(
        "MISSING_DELIVERY_DATE",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Delivery date is missing.",
    ),
    "BROKER_MC_MISSING": flag(
        "BROKER_MC_MISSING",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Broker MC is missing or invalid.",
    ),
    "BROKER_NAME_MISSING": flag(
        "BROKER_NAME_MISSING",
        CATEGORY_MISSING_DATA,
        ACTION_REVIEW,
        "Broker name is missing.",
    ),
    "UNCLEAR_EQUIPMENT": flag(
        "UNCLEAR_EQUIPMENT",
        CATEGORY_EQUIPMENT,
        ACTION_REVIEW,
        "Equipment type is missing or ambiguous.",
    ),
    "EQUIPMENT_MISMATCH": flag(
        "EQUIPMENT_MISMATCH",
        CATEGORY_EQUIPMENT,
        ACTION_REVIEW,
        "Posted equipment does not clearly match driver capability.",
    ),
    "FLATBED_VERIFY": flag(
        "FLATBED_VERIFY",
        CATEGORY_EQUIPMENT,
        ACTION_REVIEW,
        "Flatbed-style posting may need verification.",
    ),
    "STEPDECK_VERIFY": flag(
        "STEPDECK_VERIFY",
        CATEGORY_EQUIPMENT,
        ACTION_REVIEW,
        "Step Deck posting may need verification.",
    ),
    "NO_BOX_TRUCK": flag(
        "NO_BOX_TRUCK",
        CATEGORY_EQUIPMENT,
        ACTION_INFO,
        "Notes exclude box truck equipment.",
    ),
    "NO_CONESTOGA": flag(
        "NO_CONESTOGA",
        CATEGORY_CONESTOGA,
        ACTION_BLOCK,
        "Notes explicitly reject Conestoga/Stoga or require flatbed only.",
    ),
    "CONESTOGA_VERIFY": flag(
        "CONESTOGA_VERIFY",
        CATEGORY_CONESTOGA,
        ACTION_REVIEW,
        "Conestoga compatibility needs verification.",
    ),
    "CONESTOGA_COVERS_TARP": flag(
        "CONESTOGA_COVERS_TARP",
        CATEGORY_CONESTOGA,
        ACTION_INFO,
        "Tarp requirement is covered by Conestoga.",
    ),
    "CONESTOGA_OD_BLOCK": flag(
        "CONESTOGA_OD_BLOCK",
        CATEGORY_CONESTOGA,
        ACTION_BLOCK,
        "OD/permit/wide load is not acceptable for Conestoga.",
    ),
    "OVERWEIGHT": flag(
        "OVERWEIGHT",
        CATEGORY_WEIGHT_DIMENSIONS,
        ACTION_REVIEW,
        "Weight exceeds driver max weight.",
    ),
    "WEIGHT_REVIEW": flag(
        "WEIGHT_REVIEW",
        CATEGORY_WEIGHT_DIMENSIONS,
        ACTION_REVIEW,
        "Weight needs dispatcher verification.",
    ),
    "OD_PERMIT_LOAD": flag(
        "OD_PERMIT_LOAD",
        CATEGORY_WEIGHT_DIMENSIONS,
        ACTION_REVIEW,
        "OD/permit/wide load detected.",
    ),
    "DIMENSIONS_NEED_CHECK": flag(
        "DIMENSIONS_NEED_CHECK",
        CATEGORY_WEIGHT_DIMENSIONS,
        ACTION_REVIEW,
        "Dimensions are incomplete or suspicious.",
    ),
    "MULTISTOP_REVIEW": flag(
        "MULTISTOP_REVIEW",
        CATEGORY_WEIGHT_DIMENSIONS,
        ACTION_REVIEW,
        "Multiple stops or extra pickup/delivery clues require review.",
    ),
    "PICKUP_TIME_NEEDS_CHECK": flag(
        "PICKUP_TIME_NEEDS_CHECK",
        CATEGORY_TIMING,
        ACTION_REVIEW,
        "Pickup time is missing, unclear, or marked needs check.",
    ),
    "DELIVERY_TIME_NEEDS_CHECK": flag(
        "DELIVERY_TIME_NEEDS_CHECK",
        CATEGORY_TIMING,
        ACTION_REVIEW,
        "Delivery time is missing, unclear, or marked needs check.",
    ),
    "APPOINTMENT_REQUIRED": flag(
        "APPOINTMENT_REQUIRED",
        CATEGORY_TIMING,
        ACTION_REVIEW,
        "Appointment or delivery/pickup window is required.",
    ),
    "ACTUAL_PICKUP_CHANGED": flag(
        "ACTUAL_PICKUP_CHANGED",
        CATEGORY_TIMING,
        ACTION_REVIEW,
        "Notes indicate actual pickup differs from posted pickup.",
    ),
    "TIMING_RISK": flag(
        "TIMING_RISK",
        CATEGORY_TIMING,
        ACTION_REVIEW,
        "Timing may not support pickup/reload feasibility.",
    ),
    "RATE_MISSING": flag(
        "RATE_MISSING",
        CATEGORY_RATE_MARKET,
        ACTION_REVIEW,
        "Rate is missing or zero.",
    ),
    "RATE_CHECK_REQUIRED": flag(
        "RATE_CHECK_REQUIRED",
        CATEGORY_RATE_MARKET,
        ACTION_REVIEW,
        "Dispatcher should confirm rate with broker.",
    ),
    "RATE_BELOW_MARKET": flag(
        "RATE_BELOW_MARKET",
        CATEGORY_RATE_MARKET,
        ACTION_REVIEW,
        "Rate/RPM is below current market context.",
    ),
    "LOW_RPM": flag(
        "LOW_RPM",
        CATEGORY_RATE_MARKET,
        ACTION_INFO,
        "RPM is below preferred threshold.",
    ),
    "STRONG_GROSS": flag(
        "STRONG_GROSS",
        CATEGORY_RATE_MARKET,
        ACTION_INFO,
        "Gross pay is strong.",
    ),
    "STRONG_RPM": flag(
        "STRONG_RPM",
        CATEGORY_RATE_MARKET,
        ACTION_INFO,
        "RPM is strong for the relevant mileage bucket.",
    ),
    "LOW_DATA_MARKET": flag(
        "LOW_DATA_MARKET",
        CATEGORY_RATE_MARKET,
        ACTION_INFO,
        "Market data is too limited for confident classification.",
    ),
    "LOW_EXIT_CONFIDENCE": flag(
        "LOW_EXIT_CONFIDENCE",
        CATEGORY_EXIT_RISK,
        ACTION_REVIEW,
        "Delivery market has too little exit data.",
    ),
    "WEAK_EXIT_MARKET": flag(
        "WEAK_EXIT_MARKET",
        CATEGORY_EXIT_RISK,
        ACTION_REVIEW,
        "Delivery market has weak current exit context.",
    ),
    "RISKY_EXIT_MARKET": flag(
        "RISKY_EXIT_MARKET",
        CATEGORY_EXIT_RISK,
        ACTION_REVIEW,
        "Delivery market has few or no clean exits.",
    ),
    "CLEAN_EXIT_AVAILABLE": flag(
        "CLEAN_EXIT_AVAILABLE",
        CATEGORY_EXIT_RISK,
        ACTION_INFO,
        "Clean exit options are visible.",
    ),
    "RATE_CHECK_EXITS_AVAILABLE": flag(
        "RATE_CHECK_EXITS_AVAILABLE",
        CATEGORY_EXIT_RISK,
        ACTION_REVIEW,
        "Exit options exist but need rate check.",
    ),
    "RELOAD_WATCH_RECOMMENDED": flag(
        "RELOAD_WATCH_RECOMMENDED",
        CATEGORY_EXIT_RISK,
        ACTION_REVIEW,
        "Inbound load may be worth watching for reload options.",
    ),
    "SECONDARY_EXIT_RISK": flag(
        "SECONDARY_EXIT_RISK",
        CATEGORY_EXIT_RISK,
        ACTION_REVIEW,
        "Second leg delivers into weak or risky context.",
    ),
    "BROKER_RISK": flag(
        "BROKER_RISK",
        CATEGORY_BROKER_PAYMENT,
        ACTION_REVIEW,
        "Broker memory or notes indicate broker risk.",
    ),
    "BROKER_WATCHLIST": flag(
        "BROKER_WATCHLIST",
        CATEGORY_BROKER_PAYMENT,
        ACTION_REVIEW,
        "Broker has watchlist-type history.",
    ),
    "BROKER_RATE_NEGOTIATION_RISK": flag(
        "BROKER_RATE_NEGOTIATION_RISK",
        CATEGORY_BROKER_PAYMENT,
        ACTION_REVIEW,
        "Broker history suggests rate negotiation issues.",
    ),
    "BROKER_POSITIVE_MEMORY": flag(
        "BROKER_POSITIVE_MEMORY",
        CATEGORY_BROKER_PAYMENT,
        ACTION_INFO,
        "Broker history is positive.",
    ),
    "PAYMENT_RISK": flag(
        "PAYMENT_RISK",
        CATEGORY_BROKER_PAYMENT,
        ACTION_REVIEW,
        "Notes indicate payment, quickpay, factoring, or no-buy concerns.",
    ),
    "FACTORING_NEEDS_CHECK": flag(
        "FACTORING_NEEDS_CHECK",
        CATEGORY_BROKER_PAYMENT,
        ACTION_REVIEW,
        "Factoring status is unclear.",
    ),
    "HAZMAT_REQUIRED": flag(
        "HAZMAT_REQUIRED",
        CATEGORY_DOCUMENTS,
        ACTION_REVIEW,
        "Hazmat is required.",
    ),
    "TWIC_REQUIRED": flag(
        "TWIC_REQUIRED",
        CATEGORY_DOCUMENTS,
        ACTION_REVIEW,
        "TWIC is required.",
    ),
    "TANKER_REQUIRED": flag(
        "TANKER_REQUIRED",
        CATEGORY_DOCUMENTS,
        ACTION_REVIEW,
        "Tanker endorsement is required.",
    ),
    "RAMPS_REQUIRED": flag(
        "RAMPS_REQUIRED",
        CATEGORY_DOCUMENTS,
        ACTION_REVIEW,
        "Ramps are required.",
    ),
    "DUNNAGE_REQUIRED": flag(
        "DUNNAGE_REQUIRED",
        CATEGORY_DOCUMENTS,
        ACTION_REVIEW,
        "Dunnage/wood/blocking/bracing is required.",
    ),
    "LEGAL_STATUS_REQUIRED": flag(
        "LEGAL_STATUS_REQUIRED",
        CATEGORY_DOCUMENTS,
        ACTION_REVIEW,
        "US citizen/green card/work permit requirement exists.",
    ),
    "DOCUMENTS_NEED_CHECK": flag(
        "DOCUMENTS_NEED_CHECK",
        CATEGORY_DOCUMENTS,
        ACTION_REVIEW,
        "Required document status is unknown.",
    ),
    "TRACKING_REQUIRED": flag(
        "TRACKING_REQUIRED",
        CATEGORY_TRACKING_DRIVER,
        ACTION_REVIEW,
        "Tracking is required.",
    ),
    "DRIVER_PROFILE_UNKNOWN": flag(
        "DRIVER_PROFILE_UNKNOWN",
        CATEGORY_TRACKING_DRIVER,
        ACTION_REVIEW,
        "Driver profile lacks a needed capability answer.",
    ),
    "TARGET_DIRECTION_MISMATCH": flag(
        "TARGET_DIRECTION_MISMATCH",
        CATEGORY_TRACKING_DRIVER,
        ACTION_REVIEW,
        "Load does not fit target direction or city policy.",
    ),
    "PICKUP_TOO_FAR": flag(
        "PICKUP_TOO_FAR",
        CATEGORY_TRACKING_DRIVER,
        ACTION_REVIEW,
        "Pickup appears too far from driver location.",
    ),
    "LOCAL_LOAD": flag(
        "LOCAL_LOAD",
        CATEGORY_TRACKING_DRIVER,
        ACTION_REVIEW,
        "Local/same-city or too-short load context.",
    ),
    "NOTES_AMBIGUOUS": flag(
        "NOTES_AMBIGUOUS",
        CATEGORY_NOTES_AMBIGUITY,
        ACTION_REVIEW,
        "Notes contain unclear language affecting compatibility.",
    ),
    "LOW_CONFIDENCE_PARSER_FIELD": flag(
        "LOW_CONFIDENCE_PARSER_FIELD",
        CATEGORY_PARSER_CONFIDENCE,
        ACTION_REVIEW,
        "Parser extracted a field with low confidence.",
    ),
    "CONFLICTING_DOCUMENT_FIELDS": flag(
        "CONFLICTING_DOCUMENT_FIELDS",
        CATEGORY_PARSER_CONFIDENCE,
        ACTION_REVIEW,
        "Source document has conflicting values.",
    ),
    "CONTACT_NEEDS_CHECK": flag(
        "CONTACT_NEEDS_CHECK",
        CATEGORY_NOTES_AMBIGUITY,
        ACTION_REVIEW,
        "Broker/contact data is unclear or conflicting.",
    ),
    "FACTORING_PACKET_INCOMPLETE": flag(
        "FACTORING_PACKET_INCOMPLETE",
        CATEGORY_ACCOUNTING_FUTURE,
        ACTION_REVIEW,
        "Required future factoring packet fields/documents are missing.",
    ),
    "BROKER_FACTORING_NOT_APPROVED": flag(
        "BROKER_FACTORING_NOT_APPROVED",
        CATEGORY_ACCOUNTING_FUTURE,
        ACTION_REVIEW,
        "Future broker/factoring eligibility is not approved.",
    ),
    "POD_MISSING": flag(
        "POD_MISSING",
        CATEGORY_ACCOUNTING_FUTURE,
        ACTION_REVIEW,
        "Proof of delivery is missing.",
    ),
    "RATECON_MISSING": flag(
        "RATECON_MISSING",
        CATEGORY_ACCOUNTING_FUTURE,
        ACTION_REVIEW,
        "Rate confirmation is missing.",
    ),
    "INVOICE_DATA_MISSING": flag(
        "INVOICE_DATA_MISSING",
        CATEGORY_ACCOUNTING_FUTURE,
        ACTION_REVIEW,
        "Invoice fields are missing.",
    ),
}

FLAG_GROUPS = {}

for flag_name, metadata in RISK_FLAGS.items():
    FLAG_GROUPS.setdefault(metadata["category"], []).append(flag_name)

FLAG_GROUPS = {
    category: tuple(flag_names)
    for category, flag_names in sorted(FLAG_GROUPS.items())
}

ALL_RISK_FLAGS = tuple(RISK_FLAGS.keys())


def normalize_risk_flag(value):
    text = str(value or "").strip().upper()

    for old, new in [
        ("-", "_"),
        (" ", "_"),
        ("/", "_"),
    ]:
        text = text.replace(old, new)

    while "__" in text:
        text = text.replace("__", "_")

    return text.strip("_")


def is_known_risk_flag(value):
    return normalize_risk_flag(value) in RISK_FLAGS


def risk_flag_metadata(value):
    flag_name = normalize_risk_flag(value)
    metadata = RISK_FLAGS.get(flag_name)

    if metadata:
        return dict(metadata)

    return {
        "name": flag_name,
        "category": "unknown",
        "usual_action": ACTION_REVIEW,
        "meaning": "",
    }


def risk_flag_category(value):
    return risk_flag_metadata(value)["category"]


def risk_flag_action(value):
    return risk_flag_metadata(value)["usual_action"]


def dedupe_risk_flags(flags):
    deduped = []
    seen = set()

    for item in flags or []:
        flag_name = normalize_risk_flag(item)

        if not flag_name:
            continue

        if flag_name in seen:
            continue

        seen.add(flag_name)
        deduped.append(flag_name)

    return deduped
