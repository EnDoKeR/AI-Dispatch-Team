"""Canonical RateCon readiness and critical-field policy owner.

This module is the single owner for RateCon readiness/critical-field policy:
extraction-review fields, intake-core fields, dispatch-critical fields, and the
legacy intake ``CRITICAL_FIELDS`` compatibility list.

The policy is count/status only. It does not expose private values, invoke any
business decision layer, process PDFs, call OCR, call models, or sync external
services.
"""


FIELD_POLICY_ROLE_EXTRACTION_REVIEW = "extraction_review"
FIELD_POLICY_ROLE_INTAKE_CORE = "intake_core"
FIELD_POLICY_ROLE_DISPATCH_DECISION = "dispatch_decision"

FIELD_POLICY_ROLES = {
    FIELD_POLICY_ROLE_EXTRACTION_REVIEW,
    FIELD_POLICY_ROLE_INTAKE_CORE,
    FIELD_POLICY_ROLE_DISPATCH_DECISION,
}

FIELD_REQUIREMENT_REQUIRED = "required"
FIELD_REQUIREMENT_REVIEW_REQUIRED = "review_required"
FIELD_REQUIREMENT_OPTIONAL = "optional"
FIELD_REQUIREMENT_NON_APPLICABLE = "non_applicable"
FIELD_REQUIREMENT_CONDITIONAL = "conditional"

FIELD_REQUIREMENT_LEVELS = {
    FIELD_REQUIREMENT_REQUIRED,
    FIELD_REQUIREMENT_REVIEW_REQUIRED,
    FIELD_REQUIREMENT_OPTIONAL,
    FIELD_REQUIREMENT_NON_APPLICABLE,
    FIELD_REQUIREMENT_CONDITIONAL,
}

FIELD_STATUS_RESOLVED = "resolved"
FIELD_STATUS_MISSING = "missing"
FIELD_STATUS_NEEDS_REVIEW = "needs_review"
FIELD_STATUS_LOW_CONFIDENCE = "low_confidence"
FIELD_STATUS_CONFLICT = "conflict"
FIELD_STATUS_NON_APPLICABLE = "non_applicable"
FIELD_STATUS_NOT_APPLICABLE = "not_applicable"

REVIEWABLE_STATUSES = {
    FIELD_STATUS_RESOLVED,
    FIELD_STATUS_NEEDS_REVIEW,
    FIELD_STATUS_LOW_CONFIDENCE,
}

HIGH_CONFIDENCE_STATUSES = {FIELD_STATUS_RESOLVED}

POLICY_VERSION = "ratecon_core_field_policy_v1"

BROKER_IDENTITY_FIELDS = ("broker_name", "customer_name", "customer_or_broker")
LOAD_IDENTIFIER_FIELDS = (
    "load_number",
    "order_number",
    "pro_number",
    "tender_id",
    "tender_number",
    "shipment_number",
)
RATE_FIELDS = ("rate", "payment_amount", "total_carrier_pay", "agreed_amount")
NORMAL_STOP_FIELDS = (
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
)
STOP_TIME_FIELDS = ("pickup_time", "delivery_time")
OPERATIONAL_REVIEW_FIELDS = (
    "equipment",
    "weight",
    "commodity",
    "special_requirement",
)
REFERENCE_FIELDS = ("reference", "customer_reference", "po_number", "bol_number")

INTAKE_CORE_FIELD_GROUPS = {
    "broker_identity": BROKER_IDENTITY_FIELDS,
    "load_identifier": LOAD_IDENTIFIER_FIELDS,
    "rate": RATE_FIELDS,
    "pickup_location": ("pickup_location",),
    "pickup_date": ("pickup_date",),
    "delivery_location": ("delivery_location",),
    "delivery_date": ("delivery_date",),
}

DISPATCH_DECISION_FIELDS = (
    "broker_name",
    "broker_mc",
    "load_number",
    "rate",
    "pickup_location",
    "pickup_date",
    "pickup_time",
    "delivery_location",
    "delivery_date",
    "delivery_time",
    "equipment",
    "weight",
    "commodity",
    "special_requirement",
)

LEGACY_CRITICAL_FIELDS = (
    "document_id",
    "broker_name",
    "load_number",
    "rate",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "commodity",
    "weight",
)

KNOWN_POLICY_FIELDS = tuple(
    dict.fromkeys(
        BROKER_IDENTITY_FIELDS
        + ("broker_mc",)
        + LOAD_IDENTIFIER_FIELDS
        + RATE_FIELDS
        + NORMAL_STOP_FIELDS
        + STOP_TIME_FIELDS
        + OPERATIONAL_REVIEW_FIELDS
        + REFERENCE_FIELDS
    )
)


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _boolish(value):
    return _token(value) in {"1", "true", "yes", "y"}


def _bool_field(row, *keys, default=False):
    for key in keys:
        if key not in row:
            continue
        value = row.get(key)
        if isinstance(value, bool):
            return value
        if value is None:
            continue
        return _boolish(value)
    return default


def _normalize_requirement(value):
    token = _token(value)
    return token if token in FIELD_REQUIREMENT_LEVELS else FIELD_REQUIREMENT_OPTIONAL


def normalize_field_policy_role(value):
    token = _token(value)
    return token if token in FIELD_POLICY_ROLES else FIELD_POLICY_ROLE_INTAKE_CORE


def normalize_field_status(value):
    token = _token(value)
    if token == FIELD_STATUS_NOT_APPLICABLE:
        return FIELD_STATUS_NON_APPLICABLE
    return token


def build_document_context(row=None, field_statuses=None):
    row = row or {}
    document_type = _text(row.get("document_type") or row.get("Document Type")).upper()
    extraction_status = _text(row.get("extraction_status") or row.get("Extraction Status")).upper()
    classification_status = _token(row.get("classification_status") or row.get("Classification Status"))
    extraction_relevant = _bool_field(row, "extraction_relevant", "Extraction Relevant")
    ratecon_eligible = _bool_field(row, "ratecon_eligible", "RateCon Eligible", default=True)
    context = {
        "normal_load_movement": _bool_field(
            row,
            "normal_load_movement",
            "Normal Load Movement",
        ),
        "tonu": document_type == "TRUCK_ORDER_NOT_USED" or _boolish(row.get("TONU")),
        "ocr_needed": extraction_status == "EMPTY_TEXT" or _boolish(row.get("OCR Needed")),
        "supplemental_only": _bool_field(
            row,
            "supplemental_only",
            "Supplemental Only",
        )
        or classification_status == "supplemental_only",
        "non_ratecon": classification_status in {
            "non_ratecon",
            "unknown_review_required",
        }
        or (not ratecon_eligible and not extraction_relevant),
        "extraction_relevant": extraction_relevant,
        "document_type": document_type,
        "field_statuses": {
            _token(key): normalize_field_status(value)
            for key, value in (field_statuses or {}).items()
            if _token(key)
        },
    }
    return context


def build_field_policy(
    field_name,
    extraction_review_requirement=FIELD_REQUIREMENT_REVIEW_REQUIRED,
    intake_core_requirement=FIELD_REQUIREMENT_OPTIONAL,
    dispatch_decision_requirement=FIELD_REQUIREMENT_OPTIONAL,
    normal_load_movement_applicable=True,
    tonu_applicable=True,
    supplemental_applicable=False,
    ocr_applicable=False,
    notes=None,
):
    return {
        "field_name": _token(field_name),
        "extraction_review_requirement": _normalize_requirement(
            extraction_review_requirement
        ),
        "intake_core_requirement": _normalize_requirement(intake_core_requirement),
        "dispatch_decision_requirement": _normalize_requirement(
            dispatch_decision_requirement
        ),
        "normal_load_movement_applicable": bool(normal_load_movement_applicable),
        "tonu_applicable": bool(tonu_applicable),
        "supplemental_applicable": bool(supplemental_applicable),
        "ocr_applicable": bool(ocr_applicable),
        "notes": list(notes or []),
        "policy_version": POLICY_VERSION,
    }


_POLICIES = {
    field: build_field_policy(
        field,
        intake_core_requirement=FIELD_REQUIREMENT_REQUIRED,
        dispatch_decision_requirement=FIELD_REQUIREMENT_REQUIRED,
        notes=["broker_or_customer_identity"],
    )
    for field in BROKER_IDENTITY_FIELDS
}
_POLICIES.update(
    {
        "broker_mc": build_field_policy(
            "broker_mc",
            intake_core_requirement=FIELD_REQUIREMENT_OPTIONAL,
            dispatch_decision_requirement=FIELD_REQUIREMENT_CONDITIONAL,
            notes=["risk_review_when_identity_uncertain"],
        )
    }
)
_POLICIES.update(
    {
        field: build_field_policy(
            field,
            intake_core_requirement=FIELD_REQUIREMENT_REQUIRED,
            dispatch_decision_requirement=FIELD_REQUIREMENT_REQUIRED,
            notes=["typed_load_identifier"],
        )
        for field in LOAD_IDENTIFIER_FIELDS
    }
)
_POLICIES.update(
    {
        field: build_field_policy(
            field,
            intake_core_requirement=FIELD_REQUIREMENT_REQUIRED,
            dispatch_decision_requirement=FIELD_REQUIREMENT_REQUIRED,
            notes=["payment_candidate"],
        )
        for field in RATE_FIELDS
    }
)
_POLICIES.update(
    {
        field: build_field_policy(
            field,
            intake_core_requirement=FIELD_REQUIREMENT_REQUIRED,
            dispatch_decision_requirement=FIELD_REQUIREMENT_REQUIRED,
            normal_load_movement_applicable=True,
            tonu_applicable=False,
            notes=["normal_load_stop_core"],
        )
        for field in NORMAL_STOP_FIELDS
    }
)
_POLICIES.update(
    {
        field: build_field_policy(
            field,
            intake_core_requirement=FIELD_REQUIREMENT_REVIEW_REQUIRED,
            dispatch_decision_requirement=FIELD_REQUIREMENT_REQUIRED,
            normal_load_movement_applicable=True,
            tonu_applicable=False,
            notes=["appointment_window_review"],
        )
        for field in STOP_TIME_FIELDS
    }
)
_POLICIES.update(
    {
        field: build_field_policy(
            field,
            intake_core_requirement=FIELD_REQUIREMENT_REVIEW_REQUIRED,
            dispatch_decision_requirement=FIELD_REQUIREMENT_REQUIRED,
            notes=["operational_review_field"],
        )
        for field in OPERATIONAL_REVIEW_FIELDS
    }
)
_POLICIES.update(
    {
        field: build_field_policy(
            field,
            intake_core_requirement=FIELD_REQUIREMENT_OPTIONAL,
            dispatch_decision_requirement=FIELD_REQUIREMENT_REVIEW_REQUIRED,
            notes=["reference_review_field"],
        )
        for field in REFERENCE_FIELDS
    }
)


def get_field_policy(field_name):
    field = _token(field_name)
    return _POLICIES.get(
        field,
        build_field_policy(
            field or "unknown",
            extraction_review_requirement=FIELD_REQUIREMENT_OPTIONAL,
            intake_core_requirement=FIELD_REQUIREMENT_OPTIONAL,
            dispatch_decision_requirement=FIELD_REQUIREMENT_OPTIONAL,
            notes=["unknown_field"],
        ),
    )


def _is_context_applicable(policy, context):
    context = context or {}
    if context.get("ocr_needed"):
        return bool(policy.get("ocr_applicable"))
    if context.get("supplemental_only") or (
        context.get("non_ratecon") and not context.get("extraction_relevant")
    ):
        return bool(policy.get("supplemental_applicable"))
    if context.get("tonu"):
        return bool(policy.get("tonu_applicable"))
    if context.get("normal_load_movement"):
        return bool(policy.get("normal_load_movement_applicable"))
    return bool(policy.get("normal_load_movement_applicable"))


def get_field_requirement(field_name, readiness_level, document_context=None):
    role = normalize_field_policy_role(readiness_level)
    policy = get_field_policy(field_name)
    if not _is_context_applicable(policy, document_context or {}):
        return FIELD_REQUIREMENT_NON_APPLICABLE
    return policy.get(f"{role}_requirement", FIELD_REQUIREMENT_OPTIONAL)


def get_required_fields_for_readiness(readiness_level, document_context=None):
    role = normalize_field_policy_role(readiness_level)
    return [
        field_name
        for field_name in KNOWN_POLICY_FIELDS
        if get_field_requirement(field_name, role, document_context)
        == FIELD_REQUIREMENT_REQUIRED
    ]


def get_review_fields_for_readiness(readiness_level, document_context=None):
    role = normalize_field_policy_role(readiness_level)
    return [
        field_name
        for field_name in KNOWN_POLICY_FIELDS
        if get_field_requirement(field_name, role, document_context)
        == FIELD_REQUIREMENT_REVIEW_REQUIRED
    ]


def get_readiness_required_fields():
    """Return the default intake readiness required fields.

    This is a compatibility-oriented alias for the current intake-core
    readiness behavior. Use ``get_required_fields_for_readiness`` when a caller
    needs an explicit readiness role or document context.
    """
    return tuple(get_required_fields_for_readiness(FIELD_POLICY_ROLE_INTAKE_CORE))


def get_dispatch_critical_fields():
    """Return the dispatch-decision critical field order."""
    return tuple(DISPATCH_DECISION_FIELDS)


def get_intake_core_fields():
    """Return the default intake-core required field order."""
    return tuple(get_required_fields_for_readiness(FIELD_POLICY_ROLE_INTAKE_CORE))


def get_extraction_review_fields():
    """Return the default extraction-review field order."""
    return tuple(get_review_fields_for_readiness(FIELD_POLICY_ROLE_EXTRACTION_REVIEW))


def get_legacy_critical_fields():
    """Return legacy intake ``CRITICAL_FIELDS`` values in stable order."""
    return tuple(LEGACY_CRITICAL_FIELDS)


def _broker_identity_uncertain(document_context):
    statuses = (document_context or {}).get("field_statuses", {}) or {}
    return not any(
        statuses.get(field_name) == FIELD_STATUS_RESOLVED
        for field_name in BROKER_IDENTITY_FIELDS
    )


def is_field_blocker_for_level(
    field_name,
    status,
    readiness_level,
    document_context=None,
):
    role = normalize_field_policy_role(readiness_level)
    requirement = get_field_requirement(field_name, role, document_context)
    normalized_status = normalize_field_status(status)
    if requirement in {FIELD_REQUIREMENT_NON_APPLICABLE, FIELD_REQUIREMENT_OPTIONAL}:
        return False
    if requirement == FIELD_REQUIREMENT_CONDITIONAL:
        if _token(field_name) == "broker_mc" and role == FIELD_POLICY_ROLE_DISPATCH_DECISION:
            return _broker_identity_uncertain(document_context) and normalized_status not in HIGH_CONFIDENCE_STATUSES
        return normalized_status not in HIGH_CONFIDENCE_STATUSES
    if role == FIELD_POLICY_ROLE_DISPATCH_DECISION:
        return normalized_status not in HIGH_CONFIDENCE_STATUSES
    if requirement == FIELD_REQUIREMENT_REQUIRED:
        return normalized_status not in REVIEWABLE_STATUSES
    return False


def classify_field_policy_gap(
    field_name,
    status,
    readiness_level,
    document_context=None,
):
    requirement = get_field_requirement(field_name, readiness_level, document_context)
    normalized_status = normalize_field_status(status)
    if requirement == FIELD_REQUIREMENT_NON_APPLICABLE:
        return "non_applicable"
    if requirement == FIELD_REQUIREMENT_OPTIONAL and normalized_status == FIELD_STATUS_MISSING:
        return "optional_missing_field"
    if (
        requirement == FIELD_REQUIREMENT_REVIEW_REQUIRED
        and normalized_status == FIELD_STATUS_MISSING
    ):
        return "review_field_missing"
    if is_field_blocker_for_level(
        field_name,
        normalized_status,
        readiness_level,
        document_context,
    ):
        return f"{normalize_field_policy_role(readiness_level)}_blocker"
    return "not_blocking"
