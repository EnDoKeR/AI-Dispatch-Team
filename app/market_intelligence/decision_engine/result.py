from copy import deepcopy

from app.market_intelligence.decision_engine.risk_flags import dedupe_risk_flags


DECISION_MATCH = "MATCH"
DECISION_REVIEW_ONCE = "REVIEW_ONCE"
DECISION_BLOCK = "BLOCK"
DECISION_NO_ACTION = "NO_ACTION"

DECISIONS = (
    DECISION_MATCH,
    DECISION_REVIEW_ONCE,
    DECISION_BLOCK,
    DECISION_NO_ACTION,
)

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_UNKNOWN = "UNKNOWN"

CONFIDENCE_LEVELS = (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_UNKNOWN,
)

RESULT_FIELDS = (
    "decision",
    "category",
    "risk_flags",
    "missing_fields",
    "needs_check_fields",
    "review_reasons",
    "block_reasons",
    "positive_signals",
    "explanation",
    "confidence",
    "source_signals",
    "approval_required",
    "recommended_next_action",
    "linked_load_id",
    "reference_id",
)


def value_from(source, key, default=None):
    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    return str(value)


def normalize_decision(value):
    decision = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")

    if decision in DECISIONS:
        return decision

    return DECISION_NO_ACTION


def normalize_confidence(value):
    confidence = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")

    if confidence in CONFIDENCE_LEVELS:
        return confidence

    return CONFIDENCE_UNKNOWN


def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return [json_safe(item) for item in deepcopy(value) if json_safe(item) not in ["", None]]

    if isinstance(value, (tuple, set)):
        return [json_safe(item) for item in value if json_safe(item) not in ["", None]]

    text = str(value).strip()

    if not text:
        return []

    return [text]


def normalize_dict(value):
    if isinstance(value, dict):
        return json_safe(deepcopy(value))

    return {}


def default_approval_required(decision):
    if decision in [DECISION_MATCH, DECISION_REVIEW_ONCE]:
        return True

    return False


def build_decision_result(source=None, **overrides):
    source = source or {}
    merged = {}

    for field in RESULT_FIELDS:
        merged[field] = value_from(source, field, None)

    for key, value in overrides.items():
        if key in RESULT_FIELDS:
            merged[key] = value

    decision = normalize_decision(merged.get("decision"))
    approval_required = merged.get("approval_required")

    if approval_required is None:
        approval_required = default_approval_required(decision)
    else:
        approval_required = bool(approval_required)

    result = {
        "decision": decision,
        "category": str(merged.get("category") or "").strip(),
        "risk_flags": dedupe_risk_flags(merged.get("risk_flags")),
        "missing_fields": normalize_list(merged.get("missing_fields")),
        "needs_check_fields": normalize_list(merged.get("needs_check_fields")),
        "review_reasons": normalize_list(merged.get("review_reasons")),
        "block_reasons": normalize_list(merged.get("block_reasons")),
        "positive_signals": normalize_list(merged.get("positive_signals")),
        "explanation": str(merged.get("explanation") or "").strip(),
        "confidence": normalize_confidence(merged.get("confidence")),
        "source_signals": normalize_dict(merged.get("source_signals")),
        "approval_required": approval_required,
        "recommended_next_action": str(merged.get("recommended_next_action") or "").strip(),
        "linked_load_id": str(merged.get("linked_load_id") or "").strip(),
        "reference_id": str(merged.get("reference_id") or "").strip(),
    }

    return result
