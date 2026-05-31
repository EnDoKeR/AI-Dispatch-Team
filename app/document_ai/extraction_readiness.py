"""RateCon extraction readiness contracts.

Readiness is a review/evaluation status only. It does not create DispatchCases,
call business decision systems, or imply production automation readiness.
"""

from app.document_ai.ratecon_candidates import normalize_list
from app.document_ai.ratecon_core_field_policy import (
    DISPATCH_DECISION_FIELDS,
    FIELD_POLICY_ROLE_DISPATCH_DECISION,
    FIELD_POLICY_ROLE_INTAKE_CORE,
    FIELD_REQUIREMENT_NON_APPLICABLE,
    FIELD_REQUIREMENT_OPTIONAL,
    FIELD_REQUIREMENT_REVIEW_REQUIRED,
    INTAKE_CORE_FIELD_GROUPS,
    KNOWN_POLICY_FIELDS,
    REVIEWABLE_STATUSES,
    build_document_context,
    get_field_requirement,
    is_field_blocker_for_level,
    normalize_field_status,
)


READINESS_LEVEL_NOT_READY = "not_ready"
READINESS_LEVEL_EXTRACTION_REVIEW_READY = "extraction_review_ready"
READINESS_LEVEL_INTAKE_CORE_READY = "intake_core_ready"
READINESS_LEVEL_DISPATCH_DECISION_READY = "dispatch_decision_ready"

READINESS_LEVELS = {
    READINESS_LEVEL_NOT_READY,
    READINESS_LEVEL_EXTRACTION_REVIEW_READY,
    READINESS_LEVEL_INTAKE_CORE_READY,
    READINESS_LEVEL_DISPATCH_DECISION_READY,
}

READINESS_FIELD_STATUS_RESOLVED = "resolved"
READINESS_FIELD_STATUS_MISSING = "missing"
READINESS_FIELD_STATUS_LOW_CONFIDENCE = "low_confidence"
READINESS_FIELD_STATUS_CONFLICT = "conflict"
READINESS_FIELD_STATUS_NEEDS_REVIEW = "needs_review"
READINESS_FIELD_STATUS_NON_APPLICABLE = "non_applicable"

READINESS_FIELD_STATUSES = {
    READINESS_FIELD_STATUS_RESOLVED,
    READINESS_FIELD_STATUS_MISSING,
    READINESS_FIELD_STATUS_LOW_CONFIDENCE,
    READINESS_FIELD_STATUS_CONFLICT,
    READINESS_FIELD_STATUS_NEEDS_REVIEW,
    READINESS_FIELD_STATUS_NON_APPLICABLE,
}

HIGH_CONFIDENCE_STATUSES = {READINESS_FIELD_STATUS_RESOLVED}

READINESS_ASSESSMENT_VERSION = "extraction_readiness_v1"


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def normalize_readiness_level(value):
    token = _token(value)
    return token if token in READINESS_LEVELS else READINESS_LEVEL_NOT_READY


def normalize_readiness_field_status(value):
    token = _token(value)
    return token if token in READINESS_FIELD_STATUSES else READINESS_FIELD_STATUS_MISSING


def build_readiness_assessment(
    document_alias="",
    readiness_level=READINESS_LEVEL_NOT_READY,
    extraction_review_ready=False,
    intake_core_ready=False,
    dispatch_decision_ready=False,
    blocking_fields=None,
    extraction_review_blockers=None,
    intake_core_blockers=None,
    dispatch_decision_blockers=None,
    review_fields=None,
    optional_missing_fields=None,
    non_applicable_fields=None,
    reasons=None,
    warning_codes=None,
):
    level = normalize_readiness_level(readiness_level)
    return {
        "document_alias": _text(document_alias),
        "readiness_level": level,
        "extraction_review_ready": bool(extraction_review_ready),
        "intake_core_ready": bool(intake_core_ready),
        "dispatch_decision_ready": bool(dispatch_decision_ready),
        "blocking_fields": sorted(set(normalize_list(blocking_fields))),
        "extraction_review_blockers": sorted(set(normalize_list(extraction_review_blockers))),
        "intake_core_blockers": sorted(set(normalize_list(intake_core_blockers))),
        "dispatch_decision_blockers": sorted(set(normalize_list(dispatch_decision_blockers))),
        "review_fields": sorted(set(normalize_list(review_fields))),
        "optional_missing_fields": sorted(set(normalize_list(optional_missing_fields))),
        "non_applicable_fields": sorted(set(normalize_list(non_applicable_fields))),
        "reasons": normalize_list(reasons),
        "warning_codes": normalize_list(warning_codes),
        "assessment_version": READINESS_ASSESSMENT_VERSION,
    }


def _field_status_map(row):
    statuses = {}
    for field in (row or {}).get("field_statuses", []) or []:
        if not isinstance(field, dict):
            continue
        name = _token(field.get("field_name"))
        if name:
            statuses[name] = normalize_field_status(field.get("status"))
    for field_name in (row or {}).get("missing_fields", []) or []:
        statuses.setdefault(_token(field_name), READINESS_FIELD_STATUS_MISSING)
    for field_name in (row or {}).get("needs_check_fields", []) or []:
        statuses.setdefault(_token(field_name), READINESS_FIELD_STATUS_NEEDS_REVIEW)
    for field_name in (row or {}).get("conflict_fields", []) or []:
        statuses[_token(field_name)] = READINESS_FIELD_STATUS_CONFLICT
    for field_name in (row or {}).get("non_applicable_fields", []) or []:
        statuses[_token(field_name)] = READINESS_FIELD_STATUS_NON_APPLICABLE
    return {key: value for key, value in statuses.items() if key}


def _has_review_evidence(row, statuses):
    if statuses:
        return True
    if int((row or {}).get("span_normalized_stop_count", 0) or 0) > 0:
        return True
    return bool((row or {}).get("candidate_counts_by_field"))


def _group_status(statuses, field_names, allowed_statuses):
    for field_name in field_names:
        status = statuses.get(field_name)
        if status in allowed_statuses:
            return True
    return False


def _missing_core_groups(statuses, context):
    missing = []
    for group_name, field_names in INTAKE_CORE_FIELD_GROUPS.items():
        required_fields = [
            field_name
            for field_name in field_names
            if get_field_requirement(
                field_name,
                FIELD_POLICY_ROLE_INTAKE_CORE,
                context,
            )
            != FIELD_REQUIREMENT_NON_APPLICABLE
        ]
        if required_fields and not _group_status(statuses, required_fields, REVIEWABLE_STATUSES):
            missing.append(group_name)
    return missing


def _dispatch_blocking_fields(statuses, context):
    blocking = []
    for field_name in DISPATCH_DECISION_FIELDS:
        if is_field_blocker_for_level(
            field_name,
            statuses.get(field_name, READINESS_FIELD_STATUS_MISSING),
            FIELD_POLICY_ROLE_DISPATCH_DECISION,
            context,
        ):
            blocking.append(field_name)
    return blocking


def _policy_non_applicable_fields(statuses, context):
    fields = set()
    for field_name in set(KNOWN_POLICY_FIELDS) | set(statuses):
        if (
            get_field_requirement(
                field_name,
                FIELD_POLICY_ROLE_INTAKE_CORE,
                context,
            )
            == FIELD_REQUIREMENT_NON_APPLICABLE
        ):
            fields.add(field_name)
    return sorted(fields)


def _optional_missing_fields(statuses, context):
    fields = []
    for field_name, status in sorted(statuses.items()):
        requirement = get_field_requirement(
            field_name,
            FIELD_POLICY_ROLE_INTAKE_CORE,
            context,
        )
        if status == READINESS_FIELD_STATUS_MISSING and requirement in {
            FIELD_REQUIREMENT_OPTIONAL,
            FIELD_REQUIREMENT_REVIEW_REQUIRED,
        }:
            fields.append(field_name)
    return fields


def _review_fields(statuses, context):
    dispatch_review_statuses = {
        READINESS_FIELD_STATUS_MISSING,
        READINESS_FIELD_STATUS_LOW_CONFIDENCE,
        READINESS_FIELD_STATUS_NEEDS_REVIEW,
        READINESS_FIELD_STATUS_CONFLICT,
    }
    return [
        field_name
        for field_name, status in sorted(statuses.items())
        if status in dispatch_review_statuses
        and get_field_requirement(
            field_name,
            FIELD_POLICY_ROLE_INTAKE_CORE,
            context,
        )
        != FIELD_REQUIREMENT_NON_APPLICABLE
    ]


def assess_extraction_readiness(row):
    statuses = _field_status_map(row)
    context = build_document_context(row, field_statuses=statuses)
    non_applicable = [
        field
        for field, status in statuses.items()
        if status == READINESS_FIELD_STATUS_NON_APPLICABLE
    ]
    non_applicable.extend(_policy_non_applicable_fields(statuses, context))
    reasons = []
    warnings = []
    extraction_review_blockers = []
    review_ready = False if context.get("ocr_needed") else _has_review_evidence(row, statuses)
    if review_ready:
        reasons.append("extraction_signals_available_for_review")
    else:
        reasons.append("no_extraction_signals_available")
        extraction_review_blockers.append(
            "ocr_needed" if context.get("ocr_needed") else "extraction_signals"
        )

    if context.get("tonu"):
        reasons.append("tonu_stop_fields_not_required_for_core_readiness")
    intake_blockers = _missing_core_groups(statuses, context)

    intake_ready = review_ready and not intake_blockers
    dispatch_blockers = _dispatch_blocking_fields(statuses, context)
    dispatch_ready = intake_ready and not dispatch_blockers

    if dispatch_ready:
        level = READINESS_LEVEL_DISPATCH_DECISION_READY
    elif intake_ready:
        level = READINESS_LEVEL_INTAKE_CORE_READY
    elif review_ready:
        level = READINESS_LEVEL_EXTRACTION_REVIEW_READY
    else:
        level = READINESS_LEVEL_NOT_READY

    blocking_fields = list(intake_blockers)
    if intake_ready and not dispatch_ready:
        warnings.append("dispatch_decision_requires_stricter_operational_fields")
        blocking_fields.extend(dispatch_blockers)
    optional_missing_fields = _optional_missing_fields(statuses, context)

    return build_readiness_assessment(
        document_alias=(row or {}).get("document_alias", ""),
        readiness_level=level,
        extraction_review_ready=review_ready,
        intake_core_ready=intake_ready,
        dispatch_decision_ready=dispatch_ready,
        blocking_fields=blocking_fields,
        extraction_review_blockers=extraction_review_blockers,
        intake_core_blockers=intake_blockers,
        dispatch_decision_blockers=dispatch_blockers,
        review_fields=_review_fields(statuses, context),
        optional_missing_fields=optional_missing_fields,
        non_applicable_fields=non_applicable,
        reasons=reasons,
        warning_codes=warnings,
    )
