"""Dry-run IntakeRecord to DispatchCase candidate helpers."""

from copy import deepcopy

from app.market_intelligence.intake.record import normalize_dict, normalize_list, source_value


LINK_EXISTING = "LINK_EXISTING"
CREATE_CASE_REVIEW = "CREATE_CASE_REVIEW"
KEEP_UNLINKED = "KEEP_UNLINKED"
NEEDS_REVIEW = "NEEDS_REVIEW"

RECOMMENDED_ACTIONS = [
    LINK_EXISTING,
    CREATE_CASE_REVIEW,
    KEEP_UNLINKED,
    NEEDS_REVIEW,
]

HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
UNKNOWN = "UNKNOWN"

CRITICAL_CONFIDENCE_FIELDS = [
    "reference_id",
    "broker_mc",
    "broker_name",
    "pickup_location",
    "delivery_location",
    "pickup_date",
    "delivery_date",
    "rate",
    "equipment",
]

INTAKE_EVIDENCE_FIELDS = [
    "intake_id",
    "reference_id",
    "load_id",
    "broker_name",
    "broker_mc",
    "pickup_location",
    "delivery_location",
    "pickup_date",
    "delivery_date",
    "rate",
    "equipment",
    "field_confidence",
    "source_type",
    "source_file_name",
]

CASE_EVIDENCE_FIELDS = [
    "case_id",
    "load_id",
    "reference_id",
    "broker_name",
    "broker_mc",
    "pickup",
    "delivery",
    "rate",
]


def _text(value):
    return str(value or "").strip()


def _key(value):
    return " ".join(_text(value).lower().split())


def _has_value(value):
    return bool(_text(value))


def _source_value(source, field_name, default=""):
    return source_value(source, field_name, default)


def _case_value(case_record, field_name, *aliases):
    value = _source_value(case_record, field_name, "")

    if _has_value(value):
        return value

    for alias in aliases:
        value = _source_value(case_record, alias, "")
        if _has_value(value):
            return value

    return ""


def _add_once(values, value):
    if value and value not in values:
        values.append(value)


def _compare_text(intake_value, case_value):
    if not _has_value(intake_value) or not _has_value(case_value):
        return None

    return _key(intake_value) == _key(case_value)


def _identity_missing(intake):
    return not _has_value(intake.get("reference_id", "")) and not _has_value(
        intake.get("load_id", "")
    )


def _normalized_confidence(field_confidence):
    normalized = {}

    for field_name, confidence in normalize_dict(field_confidence).items():
        key = _text(field_name)
        value = _text(confidence).upper()

        if key:
            normalized[key] = value if value in {HIGH, MEDIUM, LOW, UNKNOWN} else UNKNOWN

    return normalized


def _low_confidence_critical_fields(field_confidence):
    normalized = _normalized_confidence(field_confidence)

    return [
        field_name
        for field_name in CRITICAL_CONFIDENCE_FIELDS
        if normalized.get(field_name) == LOW
    ]


def _build_intake_evidence(intake_record):
    evidence = {
        field_name: deepcopy(_source_value(intake_record, field_name, ""))
        for field_name in INTAKE_EVIDENCE_FIELDS
    }
    evidence["field_confidence"] = _normalized_confidence(
        evidence.get("field_confidence", {})
    )
    return evidence


def _build_case_evidence(case_record):
    if case_record is None:
        return {}

    return {
        "case_id": _case_value(case_record, "case_id"),
        "load_id": _case_value(case_record, "load_id"),
        "reference_id": _case_value(case_record, "reference_id"),
        "broker_name": _case_value(case_record, "broker_name", "broker"),
        "broker_mc": _case_value(case_record, "broker_mc"),
        "pickup": _case_value(case_record, "pickup", "pickup_location"),
        "delivery": _case_value(case_record, "delivery", "delivery_location"),
        "rate": _case_value(case_record, "rate"),
    }


def _compare_evidence(intake, case_evidence):
    comparison = {
        "reference_match": False,
        "load_id_match": False,
        "broker_mc_match": False,
        "broker_name_match": False,
        "lane_match": False,
        "rate_match": False,
    }
    match_reasons = []
    mismatch_reasons = []
    score = 0

    if not case_evidence:
        return comparison, match_reasons, mismatch_reasons, score

    reference_match = _compare_text(
        intake.get("reference_id", ""),
        case_evidence.get("reference_id", ""),
    )
    if reference_match is True:
        comparison["reference_match"] = True
        _add_once(match_reasons, "reference_id_match")
        score += 40
    elif reference_match is False:
        _add_once(mismatch_reasons, "reference_id_mismatch")

    load_id_match = _compare_text(
        intake.get("load_id", ""),
        case_evidence.get("load_id", ""),
    )
    if load_id_match is True:
        comparison["load_id_match"] = True
        _add_once(match_reasons, "load_id_match")
        score += 40
    elif load_id_match is False:
        _add_once(mismatch_reasons, "load_id_mismatch")

    broker_mc_match = _compare_text(
        intake.get("broker_mc", ""),
        case_evidence.get("broker_mc", ""),
    )
    if broker_mc_match is True:
        comparison["broker_mc_match"] = True
        _add_once(match_reasons, "broker_mc_match")
        score += 20
    elif broker_mc_match is False:
        _add_once(mismatch_reasons, "broker_mc_mismatch")

    broker_name_match = _compare_text(
        intake.get("broker_name", ""),
        case_evidence.get("broker_name", ""),
    )
    if broker_name_match is True:
        comparison["broker_name_match"] = True
        _add_once(match_reasons, "broker_name_match")
        score += 10
    elif broker_name_match is False:
        _add_once(mismatch_reasons, "broker_name_mismatch")

    pickup_match = _compare_text(
        intake.get("pickup_location", ""),
        case_evidence.get("pickup", ""),
    )
    delivery_match = _compare_text(
        intake.get("delivery_location", ""),
        case_evidence.get("delivery", ""),
    )
    if pickup_match is True and delivery_match is True:
        comparison["lane_match"] = True
        _add_once(match_reasons, "lane_match")
        score += 20
    elif pickup_match is False or delivery_match is False:
        _add_once(mismatch_reasons, "lane_mismatch")

    rate_match = _compare_text(intake.get("rate", ""), case_evidence.get("rate", ""))
    if rate_match is True:
        comparison["rate_match"] = True
        _add_once(match_reasons, "rate_match")
        score += 10
    elif rate_match is False:
        _add_once(mismatch_reasons, "rate_mismatch")

    return comparison, match_reasons, mismatch_reasons, min(score, 100)


def _complete_for_case_review(intake, missing_fields, needs_check_fields):
    required = [
        "reference_id",
        "rate",
        "pickup_location",
        "delivery_location",
        "pickup_date",
        "delivery_date",
        "equipment",
    ]

    has_broker_identity = _has_value(intake.get("broker_name", "")) or _has_value(
        intake.get("broker_mc", "")
    )

    return (
        has_broker_identity
        and all(_has_value(intake.get(field_name, "")) for field_name in required)
        and not missing_fields
        and not needs_check_fields
    )


def _recommend_action(
    case_evidence,
    missing_fields,
    needs_check_fields,
    low_confidence_fields,
    mismatch_reasons,
    match_reasons,
    intake,
):
    if missing_fields or needs_check_fields or low_confidence_fields:
        return NEEDS_REVIEW

    if not case_evidence and _identity_missing(intake):
        return KEEP_UNLINKED

    if mismatch_reasons:
        return NEEDS_REVIEW

    if case_evidence:
        strong_identity = (
            "reference_id_match" in match_reasons
            or "load_id_match" in match_reasons
        )
        supporting_match = (
            "broker_mc_match" in match_reasons
            or "broker_name_match" in match_reasons
            or "lane_match" in match_reasons
        )

        if strong_identity and supporting_match:
            return LINK_EXISTING

        return KEEP_UNLINKED

    if _complete_for_case_review(intake, missing_fields, needs_check_fields):
        return CREATE_CASE_REVIEW

    return KEEP_UNLINKED


def _confidence_for_candidate(action, low_confidence_fields, mismatch_reasons):
    if low_confidence_fields or mismatch_reasons:
        return LOW

    if action == LINK_EXISTING:
        return HIGH

    if action == CREATE_CASE_REVIEW:
        return MEDIUM

    if action == KEEP_UNLINKED:
        return LOW

    return UNKNOWN


def build_intake_case_link_candidate(intake_record, case_record=None):
    intake = _build_intake_evidence(intake_record)
    case_evidence = _build_case_evidence(case_record)
    missing_fields = normalize_list(_source_value(intake_record, "missing_fields", []))
    needs_check_fields = normalize_list(
        _source_value(intake_record, "needs_check_fields", [])
    )
    low_confidence_fields = _low_confidence_critical_fields(
        intake.get("field_confidence", {})
    )
    comparison, match_reasons, mismatch_reasons, match_score = _compare_evidence(
        intake,
        case_evidence,
    )

    if _identity_missing(intake):
        _add_once(mismatch_reasons, "missing_identity_evidence")

    for field_name in low_confidence_fields:
        _add_once(mismatch_reasons, f"low_confidence_{field_name}")

    action = _recommend_action(
        case_evidence,
        missing_fields,
        needs_check_fields,
        low_confidence_fields,
        mismatch_reasons,
        match_reasons,
        intake,
    )
    confidence = _confidence_for_candidate(action, low_confidence_fields, mismatch_reasons)

    return {
        "intake_id": _text(intake.get("intake_id", "")),
        "candidate_case_id": _text(case_evidence.get("case_id", "")),
        "match_score": match_score,
        "match_reasons": match_reasons,
        "mismatch_reasons": mismatch_reasons,
        "missing_fields": missing_fields,
        "needs_check_fields": needs_check_fields,
        "confidence": confidence,
        "recommended_action": action,
        "approval_required": True,
        "evidence": {
            "intake": intake,
            "candidate_case": case_evidence,
            "comparison": comparison,
        },
    }
