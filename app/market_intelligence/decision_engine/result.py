from copy import deepcopy

from app.market_intelligence.decision_engine.risk_flags import dedupe_risk_flags


DECISION_MATCH = "MATCH"
DECISION_REVIEW_ONCE = "REVIEW_ONCE"
DECISION_REVIEW_REQUIRED = "REVIEW_REQUIRED"
DECISION_BLOCK = "BLOCK"
DECISION_NO_ACTION = "NO_ACTION"

DECISIONS = (
    DECISION_MATCH,
    DECISION_REVIEW_ONCE,
    DECISION_REVIEW_REQUIRED,
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

DECISION_VERSION = "decision_result_v1"

RESULT_FIELDS = (
    "decision",
    "recommendation",
    "category",
    "risk_flags",
    "missing_fields",
    "needs_check_fields",
    "reasons",
    "review_reasons",
    "block_reasons",
    "rules_fired",
    "evidence_refs",
    "positive_signals",
    "explanation",
    "confidence",
    "source_signals",
    "approval_required",
    "recommended_next_action",
    "linked_load_id",
    "reference_id",
    "decision_version",
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


def has_values(value):
    if value is None:
        return False

    if isinstance(value, dict):
        return bool(value)

    if isinstance(value, (list, tuple, set)):
        return any(has_values(item) for item in value)

    if isinstance(value, str):
        return bool(value.strip())

    return bool(value)


def has_conflict_signal(risk_flags, source_signals):
    for flag_name in risk_flags:
        if "CONFLICT" in str(flag_name or "").upper():
            return True

    for field_name in [
        "conflicts",
        "field_conflicts",
        "conflicting_fields",
        "conflict_fields",
    ]:
        if has_values(source_signals.get(field_name)):
            return True

    return False


def has_low_confidence_signal(confidence, source_signals):
    if confidence == CONFIDENCE_LOW:
        return True

    for field_name in [
        "field_confidence",
        "parser_field_confidence",
        "confidence_by_field",
    ]:
        field_confidence = source_signals.get(field_name)

        if not isinstance(field_confidence, dict):
            continue

        for value in field_confidence.values():
            if normalize_confidence(value) == CONFIDENCE_LOW:
                return True

    return has_values(source_signals.get("low_confidence_fields"))


def should_route_to_review(decision, missing_fields, needs_check_fields, risk_flags, confidence, source_signals):
    if decision not in [DECISION_MATCH, DECISION_NO_ACTION]:
        return False

    return any(
        [
            bool(missing_fields),
            bool(needs_check_fields),
            has_low_confidence_signal(confidence, source_signals),
            has_conflict_signal(risk_flags, source_signals),
        ]
    )


def default_approval_required(decision):
    if decision in [DECISION_MATCH, DECISION_REVIEW_ONCE, DECISION_REVIEW_REQUIRED]:
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
    risk_flags = dedupe_risk_flags(merged.get("risk_flags"))
    missing_fields = normalize_list(merged.get("missing_fields"))
    needs_check_fields = normalize_list(merged.get("needs_check_fields"))
    review_reasons = normalize_list(merged.get("review_reasons"))
    block_reasons = normalize_list(merged.get("block_reasons"))
    confidence = normalize_confidence(merged.get("confidence"))
    source_signals = normalize_dict(merged.get("source_signals"))

    if should_route_to_review(
        decision,
        missing_fields,
        needs_check_fields,
        risk_flags,
        confidence,
        source_signals,
    ):
        decision = DECISION_REVIEW_REQUIRED

    recommendation = normalize_decision(merged.get("recommendation") or decision)

    if decision == DECISION_REVIEW_REQUIRED and recommendation == DECISION_MATCH:
        recommendation = DECISION_REVIEW_REQUIRED

    approval_required = merged.get("approval_required")

    if approval_required is None:
        approval_required = default_approval_required(decision)
    else:
        approval_required = bool(approval_required)

    reasons = normalize_list(merged.get("reasons"))

    for reason in review_reasons + block_reasons:
        if reason not in reasons:
            reasons.append(reason)

    if decision == DECISION_REVIEW_REQUIRED and not reasons:
        reasons.append("review_required_due_to_missing_or_low_confidence_data")

    result = {
        "decision": decision,
        "recommendation": recommendation,
        "category": str(merged.get("category") or "").strip(),
        "risk_flags": risk_flags,
        "missing_fields": missing_fields,
        "needs_check_fields": needs_check_fields,
        "reasons": reasons,
        "review_reasons": review_reasons,
        "block_reasons": block_reasons,
        "rules_fired": normalize_list(merged.get("rules_fired")),
        "evidence_refs": normalize_list(merged.get("evidence_refs")),
        "positive_signals": normalize_list(merged.get("positive_signals")),
        "explanation": str(merged.get("explanation") or "").strip(),
        "confidence": confidence,
        "source_signals": source_signals,
        "approval_required": approval_required,
        "recommended_next_action": str(merged.get("recommended_next_action") or "").strip(),
        "linked_load_id": str(merged.get("linked_load_id") or "").strip(),
        "reference_id": str(merged.get("reference_id") or "").strip(),
        "decision_version": str(merged.get("decision_version") or DECISION_VERSION).strip(),
    }

    return result
