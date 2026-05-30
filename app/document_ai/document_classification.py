"""Document, page, section, and extraction-scope classification contracts."""

import re

DOCUMENT_CLASSIFIER_VERSION = "document_classification_v1"

DOCUMENT_TYPE_RATE_CONFIRMATION = "RATE_CONFIRMATION"
DOCUMENT_TYPE_RATE_LOAD_CONFIRMATION = "RATE_LOAD_CONFIRMATION"
DOCUMENT_TYPE_LOAD_CONFIRMATION = "LOAD_CONFIRMATION"
DOCUMENT_TYPE_ORDER_CONFIRMATION = "ORDER_CONFIRMATION"
DOCUMENT_TYPE_CARRIER_LOAD_TENDER = "CARRIER_LOAD_TENDER"
DOCUMENT_TYPE_LOAD_TENDER = "LOAD_TENDER"
DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED = "TRUCK_ORDER_NOT_USED"
DOCUMENT_TYPE_RATE_CONFIRMATION_SUPPLEMENT = "RATE_CONFIRMATION_SUPPLEMENT"
DOCUMENT_TYPE_DRIVER_CARRIER_INFO_SHEET = "DRIVER_CARRIER_INFO_SHEET"
DOCUMENT_TYPE_BILL_OF_LADING = "BILL_OF_LADING"
DOCUMENT_TYPE_PROOF_OF_DELIVERY = "PROOF_OF_DELIVERY"
DOCUMENT_TYPE_CERTIFICATE_OF_INSURANCE = "CERTIFICATE_OF_INSURANCE"
DOCUMENT_TYPE_CERTIFICATE_OF_SIGNATURE = "CERTIFICATE_OF_SIGNATURE"
DOCUMENT_TYPE_BILLING_INSTRUCTIONS = "BILLING_INSTRUCTIONS"
DOCUMENT_TYPE_TERMS_AND_CONDITIONS = "TERMS_AND_CONDITIONS"
DOCUMENT_TYPE_CARRIER_RATE_AGREEMENT = "CARRIER_RATE_AGREEMENT"
DOCUMENT_TYPE_INVOICE = "INVOICE"
DOCUMENT_TYPE_LUMPER_RECEIPT = "LUMPER_RECEIPT"
DOCUMENT_TYPE_UNKNOWN = "UNKNOWN"

DOCUMENT_TYPES = {
    DOCUMENT_TYPE_RATE_CONFIRMATION,
    DOCUMENT_TYPE_RATE_LOAD_CONFIRMATION,
    DOCUMENT_TYPE_LOAD_CONFIRMATION,
    DOCUMENT_TYPE_ORDER_CONFIRMATION,
    DOCUMENT_TYPE_CARRIER_LOAD_TENDER,
    DOCUMENT_TYPE_LOAD_TENDER,
    DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED,
    DOCUMENT_TYPE_RATE_CONFIRMATION_SUPPLEMENT,
    DOCUMENT_TYPE_DRIVER_CARRIER_INFO_SHEET,
    DOCUMENT_TYPE_BILL_OF_LADING,
    DOCUMENT_TYPE_PROOF_OF_DELIVERY,
    DOCUMENT_TYPE_CERTIFICATE_OF_INSURANCE,
    DOCUMENT_TYPE_CERTIFICATE_OF_SIGNATURE,
    DOCUMENT_TYPE_BILLING_INSTRUCTIONS,
    DOCUMENT_TYPE_TERMS_AND_CONDITIONS,
    DOCUMENT_TYPE_CARRIER_RATE_AGREEMENT,
    DOCUMENT_TYPE_INVOICE,
    DOCUMENT_TYPE_LUMPER_RECEIPT,
    DOCUMENT_TYPE_UNKNOWN,
}

PAGE_ROLE_MAIN_RATECONF = "MAIN_RATECONF"
PAGE_ROLE_MAIN_LOAD_CONFIRMATION = "MAIN_LOAD_CONFIRMATION"
PAGE_ROLE_MAIN_TENDER = "MAIN_TENDER"
PAGE_ROLE_STOP_DETAILS = "STOP_DETAILS"
PAGE_ROLE_PAYMENT_SUMMARY = "PAYMENT_SUMMARY"
PAGE_ROLE_TERMS = "TERMS"
PAGE_ROLE_BILLING = "BILLING"
PAGE_ROLE_SIGNATURE = "SIGNATURE"
PAGE_ROLE_CERTIFICATE_SIGNATURE = "CERTIFICATE_SIGNATURE"
PAGE_ROLE_CARRIER_INFO = "CARRIER_INFO"
PAGE_ROLE_DRIVER_INFO = "DRIVER_INFO"
PAGE_ROLE_SUPPLEMENTAL_INSTRUCTIONS = "SUPPLEMENTAL_INSTRUCTIONS"
PAGE_ROLE_BOL = "BOL"
PAGE_ROLE_INSURANCE_CERTIFICATE = "INSURANCE_CERTIFICATE"
PAGE_ROLE_UNKNOWN = "UNKNOWN"

PAGE_ROLES = {
    PAGE_ROLE_MAIN_RATECONF,
    PAGE_ROLE_MAIN_LOAD_CONFIRMATION,
    PAGE_ROLE_MAIN_TENDER,
    PAGE_ROLE_STOP_DETAILS,
    PAGE_ROLE_PAYMENT_SUMMARY,
    PAGE_ROLE_TERMS,
    PAGE_ROLE_BILLING,
    PAGE_ROLE_SIGNATURE,
    PAGE_ROLE_CERTIFICATE_SIGNATURE,
    PAGE_ROLE_CARRIER_INFO,
    PAGE_ROLE_DRIVER_INFO,
    PAGE_ROLE_SUPPLEMENTAL_INSTRUCTIONS,
    PAGE_ROLE_BOL,
    PAGE_ROLE_INSURANCE_CERTIFICATE,
    PAGE_ROLE_UNKNOWN,
}

SECTION_ROLE_HEADER = "HEADER"
SECTION_ROLE_BROKER_CONTACT = "BROKER_CONTACT"
SECTION_ROLE_CARRIER_CONTACT = "CARRIER_CONTACT"
SECTION_ROLE_LOAD_IDENTITY = "LOAD_IDENTITY"
SECTION_ROLE_EQUIPMENT_SUMMARY = "EQUIPMENT_SUMMARY"
SECTION_ROLE_RATE_SUMMARY = "RATE_SUMMARY"
SECTION_ROLE_RATE_BREAKDOWN = "RATE_BREAKDOWN"
SECTION_ROLE_STOP_TABLE = "STOP_TABLE"
SECTION_ROLE_PICKUP_SECTION = "PICKUP_SECTION"
SECTION_ROLE_DELIVERY_SECTION = "DELIVERY_SECTION"
SECTION_ROLE_MULTI_STOP_SECTION = "MULTI_STOP_SECTION"
SECTION_ROLE_COMMODITY_WEIGHT = "COMMODITY_WEIGHT"
SECTION_ROLE_SPECIAL_INSTRUCTIONS = "SPECIAL_INSTRUCTIONS"
SECTION_ROLE_PAYMENT_TERMS = "PAYMENT_TERMS"
SECTION_ROLE_BILLING_INSTRUCTIONS = "BILLING_INSTRUCTIONS"
SECTION_ROLE_QUICK_PAY = "QUICK_PAY"
SECTION_ROLE_DEDUCTIONS_PENALTIES = "DEDUCTIONS_PENALTIES"
SECTION_ROLE_LEGAL_TERMS = "LEGAL_TERMS"
SECTION_ROLE_SIGNATURE_BLOCK = "SIGNATURE_BLOCK"
SECTION_ROLE_CERTIFICATE_SIGNATURE_BLOCK = "CERTIFICATE_SIGNATURE_BLOCK"
SECTION_ROLE_BOL_BODY = "BOL_BODY"
SECTION_ROLE_TONU_PAYMENT = "TONU_PAYMENT"
SECTION_ROLE_UNKNOWN = "UNKNOWN"

SECTION_ROLES = {
    SECTION_ROLE_HEADER,
    SECTION_ROLE_BROKER_CONTACT,
    SECTION_ROLE_CARRIER_CONTACT,
    SECTION_ROLE_LOAD_IDENTITY,
    SECTION_ROLE_EQUIPMENT_SUMMARY,
    SECTION_ROLE_RATE_SUMMARY,
    SECTION_ROLE_RATE_BREAKDOWN,
    SECTION_ROLE_STOP_TABLE,
    SECTION_ROLE_PICKUP_SECTION,
    SECTION_ROLE_DELIVERY_SECTION,
    SECTION_ROLE_MULTI_STOP_SECTION,
    SECTION_ROLE_COMMODITY_WEIGHT,
    SECTION_ROLE_SPECIAL_INSTRUCTIONS,
    SECTION_ROLE_PAYMENT_TERMS,
    SECTION_ROLE_BILLING_INSTRUCTIONS,
    SECTION_ROLE_QUICK_PAY,
    SECTION_ROLE_DEDUCTIONS_PENALTIES,
    SECTION_ROLE_LEGAL_TERMS,
    SECTION_ROLE_SIGNATURE_BLOCK,
    SECTION_ROLE_CERTIFICATE_SIGNATURE_BLOCK,
    SECTION_ROLE_BOL_BODY,
    SECTION_ROLE_TONU_PAYMENT,
    SECTION_ROLE_UNKNOWN,
}

EXTRACTION_SCOPE_RATECON_CORE_ALLOWED = "RATECON_CORE_ALLOWED"
EXTRACTION_SCOPE_RATE_ONLY_ALLOWED = "RATE_ONLY_ALLOWED"
EXTRACTION_SCOPE_STOP_EXTRACTION_ALLOWED = "STOP_EXTRACTION_ALLOWED"
EXTRACTION_SCOPE_REQUIREMENTS_ONLY_ALLOWED = "REQUIREMENTS_ONLY_ALLOWED"
EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED = "PAYMENT_TERMS_ONLY_ALLOWED"
EXTRACTION_SCOPE_BILLING_ONLY = "BILLING_ONLY"
EXTRACTION_SCOPE_SIGNATURE_ONLY = "SIGNATURE_ONLY"
EXTRACTION_SCOPE_SUPPLEMENTAL_ONLY = "SUPPLEMENTAL_ONLY"
EXTRACTION_SCOPE_NON_RATECON_SKIP = "NON_RATECON_SKIP"
EXTRACTION_SCOPE_OCR_REQUIRED = "OCR_REQUIRED"
EXTRACTION_SCOPE_REVIEW_REQUIRED = "REVIEW_REQUIRED"

EXTRACTION_SCOPES = {
    EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
    EXTRACTION_SCOPE_RATE_ONLY_ALLOWED,
    EXTRACTION_SCOPE_STOP_EXTRACTION_ALLOWED,
    EXTRACTION_SCOPE_REQUIREMENTS_ONLY_ALLOWED,
    EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED,
    EXTRACTION_SCOPE_BILLING_ONLY,
    EXTRACTION_SCOPE_SIGNATURE_ONLY,
    EXTRACTION_SCOPE_SUPPLEMENTAL_ONLY,
    EXTRACTION_SCOPE_NON_RATECON_SKIP,
    EXTRACTION_SCOPE_OCR_REQUIRED,
    EXTRACTION_SCOPE_REVIEW_REQUIRED,
}

CLASSIFICATION_STATUS_RATECON_ELIGIBLE = "ratecon_eligible"
CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY = "supplemental_only"
CLASSIFICATION_STATUS_NON_RATECON = "non_ratecon"
CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED = "unknown_review_required"

CLASSIFICATION_STATUSES = {
    CLASSIFICATION_STATUS_RATECON_ELIGIBLE,
    CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY,
    CLASSIFICATION_STATUS_NON_RATECON,
    CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
}

CONFIDENCE_BUCKET_LOW = "low"
CONFIDENCE_BUCKET_MEDIUM = "medium"
CONFIDENCE_BUCKET_HIGH = "high"
CONFIDENCE_BUCKET_UNKNOWN = "unknown"

CONFIDENCE_BUCKETS = {
    CONFIDENCE_BUCKET_LOW,
    CONFIDENCE_BUCKET_MEDIUM,
    CONFIDENCE_BUCKET_HIGH,
    CONFIDENCE_BUCKET_UNKNOWN,
}


def _text(value):
    return str(value or "").strip()


def _normalize_token(value, allowed_values, default_value):
    text = _text(value).upper().replace(" ", "_").replace("-", "_")
    if text in allowed_values:
        return text
    return default_value


def _normalize_status(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    if text in CLASSIFICATION_STATUSES:
        return text
    return CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED


def _normalize_confidence(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0

    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def confidence_bucket(confidence):
    value = _normalize_confidence(confidence)
    if value >= 0.75:
        return CONFIDENCE_BUCKET_HIGH
    if value >= 0.45:
        return CONFIDENCE_BUCKET_MEDIUM
    if value > 0:
        return CONFIDENCE_BUCKET_LOW
    return CONFIDENCE_BUCKET_UNKNOWN


def _normalize_list(value):
    if value is None:
        values = []
    elif isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    normalized = []
    for item in values:
        text = _text(item)
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _normalize_roles(values, allowed_values, unknown_value):
    roles = [
        _normalize_token(value, allowed_values, unknown_value)
        for value in _normalize_list(values)
    ]
    roles = [role for role in roles if role != unknown_value]
    return roles or [unknown_value]


def _normalize_scopes(values):
    scopes = [
        _normalize_token(value, EXTRACTION_SCOPES, EXTRACTION_SCOPE_REVIEW_REQUIRED)
        for value in _normalize_list(values)
    ]
    scopes = [scope for scope in scopes if scope]
    return scopes or [EXTRACTION_SCOPE_REVIEW_REQUIRED]


def build_section_classification_result(
    section_role=SECTION_ROLE_UNKNOWN,
    extraction_scopes=None,
    page_number=0,
    approximate_line_range=None,
    confidence=0.0,
    reasons=None,
    warning_codes=None,
):
    return {
        "section_role": _normalize_token(section_role, SECTION_ROLES, SECTION_ROLE_UNKNOWN),
        "extraction_scopes": _normalize_scopes(extraction_scopes),
        "page_number": int(page_number or 0),
        "approximate_line_range": (
            list(approximate_line_range)
            if isinstance(approximate_line_range, (list, tuple))
            else []
        ),
        "confidence": _normalize_confidence(confidence),
        "reasons": _normalize_list(reasons),
        "warning_codes": _normalize_list(warning_codes),
    }


def build_page_classification_result(
    page_number=0,
    page_roles=None,
    primary_page_role=PAGE_ROLE_UNKNOWN,
    confidence=0.0,
    reasons=None,
    warning_codes=None,
    section_summaries=None,
):
    roles = _normalize_roles(page_roles, PAGE_ROLES, PAGE_ROLE_UNKNOWN)
    primary = _normalize_token(primary_page_role, PAGE_ROLES, PAGE_ROLE_UNKNOWN)
    if primary == PAGE_ROLE_UNKNOWN and roles:
        primary = roles[0]

    return {
        "page_number": int(page_number or 0),
        "page_roles": roles,
        "primary_page_role": primary,
        "confidence": _normalize_confidence(confidence),
        "confidence_bucket": confidence_bucket(confidence),
        "reasons": _normalize_list(reasons),
        "warning_codes": _normalize_list(warning_codes),
        "section_summaries": [
            section
            for section in section_summaries or []
            if isinstance(section, dict)
        ],
    }


def build_document_classification_result(
    document_alias="",
    document_type=DOCUMENT_TYPE_UNKNOWN,
    ratecon_eligible=False,
    supplemental_only=False,
    confidence=0.0,
    reasons=None,
    warning_codes=None,
    page_roles=None,
    page_results=None,
    classification_status=None,
    classifier_version=DOCUMENT_CLASSIFIER_VERSION,
):
    normalized_type = _normalize_token(document_type, DOCUMENT_TYPES, DOCUMENT_TYPE_UNKNOWN)
    eligible = bool(ratecon_eligible)
    supplemental = bool(supplemental_only)
    status = classification_status

    if not status:
        if eligible:
            status = CLASSIFICATION_STATUS_RATECON_ELIGIBLE
        elif supplemental:
            status = CLASSIFICATION_STATUS_SUPPLEMENTAL_ONLY
        elif normalized_type == DOCUMENT_TYPE_UNKNOWN:
            status = CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED
        else:
            status = CLASSIFICATION_STATUS_NON_RATECON

    return {
        "document_alias": _text(document_alias),
        "document_type": normalized_type,
        "ratecon_eligible": eligible,
        "supplemental_only": supplemental,
        "confidence": _normalize_confidence(confidence),
        "confidence_bucket": confidence_bucket(confidence),
        "reasons": _normalize_list(reasons),
        "warning_codes": _normalize_list(warning_codes),
        "page_roles": _normalize_roles(page_roles, PAGE_ROLES, PAGE_ROLE_UNKNOWN),
        "page_results": [
            page
            for page in page_results or []
            if isinstance(page, dict)
        ],
        "classification_status": _normalize_status(status),
        "classifier_version": _text(classifier_version or DOCUMENT_CLASSIFIER_VERSION),
        "raw_text_included": False,
        "private_values_redacted": True,
    }


def _lower_text(value):
    return str(value or "").lower()


def _line_values(page_text):
    return [
        line.strip()
        for line in str(page_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if line.strip()
    ]


def _contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def _count_hits(text, phrases):
    return sum(1 for phrase in phrases if phrase in text)


def _role_score(text, phrases):
    hits = _count_hits(text, phrases)
    if hits >= 4:
        return 0.88
    if hits == 3:
        return 0.76
    if hits == 2:
        return 0.62
    if hits == 1:
        return 0.42
    return 0.0


def _stop_count(text):
    return len(re.findall(r"\bstop\s*\d+\b", text))


def _page_role_candidates(text):
    candidates = []

    role_signals = [
        (
            PAGE_ROLE_BOL,
            [
                "bill of lading",
                "bol no",
                "bol #",
                "received by",
                "shipper signature",
                "carrier signature",
                "description of articles",
            ],
            "bol-like labels detected",
        ),
        (
            PAGE_ROLE_CERTIFICATE_SIGNATURE,
            [
                "certificate of signature",
                "document completed by all parties",
                "signed with",
                "signer:",
                "timestamp:",
                "certificate id",
            ],
            "certificate signature labels detected",
        ),
        (
            PAGE_ROLE_INSURANCE_CERTIFICATE,
            [
                "certificate of liability insurance",
                "acord",
                "producer",
                "insured",
                "coverages",
                "certificate holder",
            ],
            "insurance certificate labels detected",
        ),
        (
            PAGE_ROLE_CARRIER_INFO,
            [
                "driver / carrier information sheet",
                "carrier information sheet",
                "carrier name:",
                "carrier mc:",
                "dispatcher name:",
                "truck number",
                "trailer number",
            ],
            "carrier information labels detected",
        ),
        (
            PAGE_ROLE_DRIVER_INFO,
            [
                "driver / carrier information sheet",
                "driver information sheet",
                "driver name:",
                "driver phone",
                "truck number",
                "trailer number",
            ],
            "driver information labels detected",
        ),
        (
            PAGE_ROLE_MAIN_RATECONF,
            [
                "rate confirmation",
                "rate & load confirmation",
                "dispatch confirmation",
                "carrier pay",
                "total carrier pay",
                "broker mc",
                "pickup date",
                "delivery date",
            ],
            "rate confirmation labels detected",
        ),
        (
            PAGE_ROLE_MAIN_TENDER,
            [
                "carrier load tender",
                "load tender",
                "route details",
                "origin:",
                "destination:",
                "shipment #",
                "docket mc",
            ],
            "carrier tender labels detected",
        ),
        (
            PAGE_ROLE_MAIN_LOAD_CONFIRMATION,
            [
                "load confirmation",
                "order confirmation",
                "load / order confirmation",
                "order number",
                "load number",
                "carrier freight pay",
            ],
            "load or order confirmation labels detected",
        ),
        (
            PAGE_ROLE_STOP_DETAILS,
            [
                "pickup",
                "delivery",
                "shipper",
                "consignee",
                "origin",
                "destination",
                "stop table",
                "stop 1",
                "stop 2",
            ],
            "stop detail labels detected",
        ),
        (
            PAGE_ROLE_PAYMENT_SUMMARY,
            [
                "payment summary",
                "rate table",
                "carrier pay",
                "agreed rate",
                "agreed amount",
                "linehaul",
                "carrier freight pay",
                "total charge",
                "truck ordered not used payment",
            ],
            "payment or rate summary labels detected",
        ),
        (
            PAGE_ROLE_TERMS,
            [
                "terms and conditions",
                "carrier rate agreement",
                "broker-carrier terms",
                "rate agreement addendum",
                "legal terms",
                "fraud",
                "detention policy",
                "tonu policy",
            ],
            "terms or legal labels detected",
        ),
        (
            PAGE_ROLE_BILLING,
            [
                "billing instructions",
                "remit to",
                "invoice to",
                "quick pay",
                "payment terms",
                "paperwork submission",
                "carrier invoice",
            ],
            "billing labels detected",
        ),
        (
            PAGE_ROLE_SIGNATURE,
            [
                "signature page",
                "carrier signature",
                "accepted by",
                "printed name",
                "please sign",
                "authorized carrier signature",
            ],
            "signature labels detected",
        ),
        (
            PAGE_ROLE_SUPPLEMENTAL_INSTRUCTIONS,
            [
                "supplemental instructions",
                "special instructions",
                "call before pickup",
                "appointment required",
                "seal required",
            ],
            "supplemental instruction labels detected",
        ),
    ]

    thresholds = {
        PAGE_ROLE_BOL: 0.62,
        PAGE_ROLE_MAIN_RATECONF: 0.62,
        PAGE_ROLE_MAIN_LOAD_CONFIRMATION: 0.62,
        PAGE_ROLE_MAIN_TENDER: 0.62,
        PAGE_ROLE_SIGNATURE: 0.62,
    }

    for role, phrases, reason in role_signals:
        score = _role_score(text, phrases)
        if score >= thresholds.get(role, 0.42):
            candidates.append((role, score, reason))

    if "truck order not used" in text or "tonu" in text or "order not used" in text:
        candidates.append((PAGE_ROLE_PAYMENT_SUMMARY, 0.76, "TONU payment labels detected"))
        candidates.append((PAGE_ROLE_SUPPLEMENTAL_INSTRUCTIONS, 0.55, "TONU status labels detected"))

    return candidates


def _primary_page_role(role_scores):
    priority = [
        PAGE_ROLE_BOL,
        PAGE_ROLE_CERTIFICATE_SIGNATURE,
        PAGE_ROLE_INSURANCE_CERTIFICATE,
        PAGE_ROLE_TERMS,
        PAGE_ROLE_BILLING,
        PAGE_ROLE_SIGNATURE,
        PAGE_ROLE_CARRIER_INFO,
        PAGE_ROLE_DRIVER_INFO,
        PAGE_ROLE_MAIN_RATECONF,
        PAGE_ROLE_MAIN_TENDER,
        PAGE_ROLE_MAIN_LOAD_CONFIRMATION,
        PAGE_ROLE_STOP_DETAILS,
        PAGE_ROLE_PAYMENT_SUMMARY,
        PAGE_ROLE_SUPPLEMENTAL_INSTRUCTIONS,
        PAGE_ROLE_UNKNOWN,
    ]
    scores = dict(role_scores)

    for role in priority:
        if scores.get(role, 0.0) >= 0.42:
            return role
    return PAGE_ROLE_UNKNOWN


def _section_scope(section_role):
    mapping = {
        SECTION_ROLE_HEADER: [EXTRACTION_SCOPE_RATECON_CORE_ALLOWED],
        SECTION_ROLE_BROKER_CONTACT: [EXTRACTION_SCOPE_RATECON_CORE_ALLOWED],
        SECTION_ROLE_CARRIER_CONTACT: [EXTRACTION_SCOPE_RATECON_CORE_ALLOWED],
        SECTION_ROLE_LOAD_IDENTITY: [EXTRACTION_SCOPE_RATECON_CORE_ALLOWED],
        SECTION_ROLE_EQUIPMENT_SUMMARY: [EXTRACTION_SCOPE_RATECON_CORE_ALLOWED],
        SECTION_ROLE_RATE_SUMMARY: [
            EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
            EXTRACTION_SCOPE_RATE_ONLY_ALLOWED,
        ],
        SECTION_ROLE_RATE_BREAKDOWN: [
            EXTRACTION_SCOPE_RATE_ONLY_ALLOWED,
            EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED,
        ],
        SECTION_ROLE_STOP_TABLE: [
            EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
            EXTRACTION_SCOPE_STOP_EXTRACTION_ALLOWED,
        ],
        SECTION_ROLE_PICKUP_SECTION: [
            EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
            EXTRACTION_SCOPE_STOP_EXTRACTION_ALLOWED,
        ],
        SECTION_ROLE_DELIVERY_SECTION: [
            EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
            EXTRACTION_SCOPE_STOP_EXTRACTION_ALLOWED,
        ],
        SECTION_ROLE_MULTI_STOP_SECTION: [
            EXTRACTION_SCOPE_RATECON_CORE_ALLOWED,
            EXTRACTION_SCOPE_STOP_EXTRACTION_ALLOWED,
        ],
        SECTION_ROLE_COMMODITY_WEIGHT: [EXTRACTION_SCOPE_RATECON_CORE_ALLOWED],
        SECTION_ROLE_SPECIAL_INSTRUCTIONS: [EXTRACTION_SCOPE_REQUIREMENTS_ONLY_ALLOWED],
        SECTION_ROLE_PAYMENT_TERMS: [EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED],
        SECTION_ROLE_BILLING_INSTRUCTIONS: [EXTRACTION_SCOPE_BILLING_ONLY],
        SECTION_ROLE_QUICK_PAY: [EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED],
        SECTION_ROLE_DEDUCTIONS_PENALTIES: [EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED],
        SECTION_ROLE_LEGAL_TERMS: [EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED],
        SECTION_ROLE_SIGNATURE_BLOCK: [EXTRACTION_SCOPE_SIGNATURE_ONLY],
        SECTION_ROLE_CERTIFICATE_SIGNATURE_BLOCK: [EXTRACTION_SCOPE_SIGNATURE_ONLY],
        SECTION_ROLE_BOL_BODY: [EXTRACTION_SCOPE_NON_RATECON_SKIP],
        SECTION_ROLE_TONU_PAYMENT: [
            EXTRACTION_SCOPE_RATE_ONLY_ALLOWED,
            EXTRACTION_SCOPE_PAYMENT_TERMS_ONLY_ALLOWED,
        ],
        SECTION_ROLE_UNKNOWN: [EXTRACTION_SCOPE_REVIEW_REQUIRED],
    }
    return mapping.get(section_role, [EXTRACTION_SCOPE_REVIEW_REQUIRED])


def _section_candidates(text):
    stop_matches = _stop_count(text)
    candidates = []

    section_signals = [
        (
            SECTION_ROLE_HEADER,
            ["rate confirmation", "load confirmation", "order confirmation", "carrier load tender"],
            "header confirmation label detected",
        ),
        (
            SECTION_ROLE_BROKER_CONTACT,
            ["broker", "broker mc", "docket mc", "dispatch contact", "logistics"],
            "broker contact labels detected",
        ),
        (
            SECTION_ROLE_CARRIER_CONTACT,
            ["carrier:", "carrier name", "carrier contact", "driver name", "dispatcher name"],
            "carrier contact labels detected",
        ),
        (
            SECTION_ROLE_LOAD_IDENTITY,
            ["load number", "load id", "order number", "order #", "shipment #", "pro number"],
            "load identity labels detected",
        ),
        (
            SECTION_ROLE_EQUIPMENT_SUMMARY,
            ["equipment", "trailer type", "truck number", "trailer number"],
            "equipment labels detected",
        ),
        (
            SECTION_ROLE_RATE_SUMMARY,
            [
                "carrier pay",
                "total carrier pay",
                "agreed rate",
                "agreed amount",
                "linehaul",
                "rate table",
                "payment summary",
                "carrier freight pay",
                "truck ordered not used payment",
            ],
            "rate summary labels detected",
        ),
        (
            SECTION_ROLE_RATE_BREAKDOWN,
            ["accessorial", "fuel included", "detention", "layover", "lumper"],
            "rate breakdown labels detected",
        ),
        (
            SECTION_ROLE_STOP_TABLE,
            ["stop table", "stop |", "stop 1", "stop 2", "stop off"],
            "stop table labels detected",
        ),
        (
            SECTION_ROLE_PICKUP_SECTION,
            ["pickup", "shipper", "origin", "pu section"],
            "pickup labels detected",
        ),
        (
            SECTION_ROLE_DELIVERY_SECTION,
            ["delivery", "consignee", "destination", "so section"],
            "delivery labels detected",
        ),
        (
            SECTION_ROLE_COMMODITY_WEIGHT,
            ["commodity", "weight", "gross weight", "pieces"],
            "commodity or weight labels detected",
        ),
        (
            SECTION_ROLE_SPECIAL_INSTRUCTIONS,
            ["special instructions", "supplemental instructions", "call before pickup", "seal required"],
            "special instruction labels detected",
        ),
        (
            SECTION_ROLE_PAYMENT_TERMS,
            ["payment terms", "terms and conditions", "detention policy", "layover policy", "tonu policy"],
            "payment terms labels detected",
        ),
        (
            SECTION_ROLE_BILLING_INSTRUCTIONS,
            ["billing instructions", "invoice to", "remit to", "paperwork submission"],
            "billing instruction labels detected",
        ),
        (
            SECTION_ROLE_QUICK_PAY,
            ["quick pay", "quickpay"],
            "quick pay labels detected",
        ),
        (
            SECTION_ROLE_DEDUCTIONS_PENALTIES,
            ["deduction", "penalty", "late fee", "fee:"],
            "deduction or penalty labels detected",
        ),
        (
            SECTION_ROLE_LEGAL_TERMS,
            ["carrier rate agreement", "broker-carrier terms", "legal terms", "fraud", "agreement"],
            "legal terms labels detected",
        ),
        (
            SECTION_ROLE_SIGNATURE_BLOCK,
            ["signature", "accepted by", "printed name", "authorized carrier signature"],
            "signature block labels detected",
        ),
        (
            SECTION_ROLE_CERTIFICATE_SIGNATURE_BLOCK,
            ["certificate of signature", "document completed by all parties", "signed with", "signer:"],
            "certificate signature block labels detected",
        ),
        (
            SECTION_ROLE_BOL_BODY,
            ["bill of lading", "bol no", "description of articles", "received by"],
            "BOL body labels detected",
        ),
        (
            SECTION_ROLE_TONU_PAYMENT,
            ["truck order not used", "tonu", "order not used payment"],
            "TONU payment labels detected",
        ),
    ]

    for role, phrases, reason in section_signals:
        score = _role_score(text, phrases)
        if score:
            candidates.append((role, score, reason))

    if stop_matches >= 3:
        candidates.append(
            (
                SECTION_ROLE_MULTI_STOP_SECTION,
                0.82,
                "multiple stop labels detected",
            )
        )

    return candidates


def classify_sections_from_page_text(page_text, page_number=1):
    """Classify page sections from safe text without returning raw text."""
    text = _lower_text(page_text)
    candidates = _section_candidates(text)
    if not candidates:
        return [
            build_section_classification_result(
                section_role=SECTION_ROLE_UNKNOWN,
                extraction_scopes=[EXTRACTION_SCOPE_REVIEW_REQUIRED],
                page_number=page_number,
                confidence=0.0,
                reasons=["no section role signals detected"],
                warning_codes=["unknown_section_review_required"],
            )
        ]

    sections = []
    for role, score, reason in candidates:
        sections.append(
            build_section_classification_result(
                section_role=role,
                extraction_scopes=_section_scope(role),
                page_number=page_number,
                confidence=score,
                reasons=[reason],
            )
        )

    return sections


def classify_page_text(page_text, page_number=1):
    """Classify a page into page roles and safe section summaries."""
    text = _lower_text(page_text)
    candidates = _page_role_candidates(text)
    warnings = []

    if not candidates:
        return build_page_classification_result(
            page_number=page_number,
            page_roles=[PAGE_ROLE_UNKNOWN],
            primary_page_role=PAGE_ROLE_UNKNOWN,
            confidence=0.0,
            reasons=["no page role signals detected"],
            warning_codes=["unknown_page_review_required"],
            section_summaries=classify_sections_from_page_text(page_text, page_number),
        )

    role_scores = {}
    reasons = []
    for role, score, reason in candidates:
        role_scores[role] = max(role_scores.get(role, 0.0), score)
        if reason not in reasons:
            reasons.append(reason)

    roles = [
        role
        for role, score in sorted(role_scores.items(), key=lambda item: (-item[1], item[0]))
        if score >= 0.42
    ]
    primary = _primary_page_role(role_scores)
    confidence = max(role_scores.values()) if role_scores else 0.0

    if primary in {PAGE_ROLE_TERMS, PAGE_ROLE_BILLING, PAGE_ROLE_SIGNATURE} and any(
        role in roles
        for role in [
            PAGE_ROLE_PAYMENT_SUMMARY,
            PAGE_ROLE_STOP_DETAILS,
            PAGE_ROLE_MAIN_RATECONF,
            PAGE_ROLE_MAIN_LOAD_CONFIRMATION,
            PAGE_ROLE_MAIN_TENDER,
        ]
    ):
        warnings.append("mixed_page_roles_review_scope")

    if PAGE_ROLE_BOL in roles and PAGE_ROLE_PAYMENT_SUMMARY in roles:
        warnings.append("bol_like_page_overlaps_rate_labels")

    return build_page_classification_result(
        page_number=page_number,
        page_roles=roles,
        primary_page_role=primary,
        confidence=confidence,
        reasons=reasons,
        warning_codes=warnings,
        section_summaries=classify_sections_from_page_text(page_text, page_number),
    )
