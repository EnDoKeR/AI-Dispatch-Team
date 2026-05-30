"""Candidate source fusion contracts and conservative helpers."""

from collections import defaultdict

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    SOURCE_BROKER_TEMPLATE_FUTURE,
    SOURCE_LABEL_PATTERN,
    SOURCE_MANUAL_REVIEW,
    SOURCE_REGEX,
    SOURCE_SECTION_PATTERN,
    SOURCE_SYNTHETIC_FIXTURE,
    SOURCE_TABLE_PATTERN_FUTURE,
    normalize_confidence,
    normalize_field_name,
    normalize_list,
)


SOURCE_PRIORITY_MANUAL_REVIEW = "manual_review"
SOURCE_PRIORITY_BROKER_TEMPLATE = "broker_template"
SOURCE_PRIORITY_LAYOUT_TABLE = "layout_table"
SOURCE_PRIORITY_LAYOUT_LABEL_VALUE = "layout_label_value"
SOURCE_PRIORITY_LAYOUT_SECTION = "layout_section"
SOURCE_PRIORITY_TEXT_REGEX = "text_regex"
SOURCE_PRIORITY_TEXT_SECTION = "text_section"
SOURCE_PRIORITY_SYNTHETIC_FIXTURE = "synthetic_fixture"
SOURCE_PRIORITY_UNKNOWN = "unknown"

CANDIDATE_SOURCE_PRIORITIES = (
    SOURCE_PRIORITY_MANUAL_REVIEW,
    SOURCE_PRIORITY_BROKER_TEMPLATE,
    SOURCE_PRIORITY_LAYOUT_TABLE,
    SOURCE_PRIORITY_LAYOUT_LABEL_VALUE,
    SOURCE_PRIORITY_LAYOUT_SECTION,
    SOURCE_PRIORITY_TEXT_REGEX,
    SOURCE_PRIORITY_TEXT_SECTION,
    SOURCE_PRIORITY_SYNTHETIC_FIXTURE,
    SOURCE_PRIORITY_UNKNOWN,
)

FUSION_STATUS_RESOLVED = "resolved"
FUSION_STATUS_MISSING = "missing"
FUSION_STATUS_CONFLICT = "conflict"
FUSION_STATUS_NEEDS_REVIEW = "needs_review"

FUSION_VERSION = "candidate_fusion_v1"
NO_REGRESSION_WARNING = "layout_candidate_rejected_to_prevent_regression"

PROTECTED_CRITICAL_FIELDS = {
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
}

_CONFIDENCE_SCORE = {
    CANDIDATE_CONFIDENCE_HIGH: 30,
    CANDIDATE_CONFIDENCE_MEDIUM: 20,
    CANDIDATE_CONFIDENCE_LOW: 10,
}

_SOURCE_SCORE = {
    SOURCE_PRIORITY_MANUAL_REVIEW: 9,
    SOURCE_PRIORITY_BROKER_TEMPLATE: 8,
    SOURCE_PRIORITY_LAYOUT_TABLE: 7,
    SOURCE_PRIORITY_LAYOUT_LABEL_VALUE: 6,
    SOURCE_PRIORITY_LAYOUT_SECTION: 5,
    SOURCE_PRIORITY_TEXT_SECTION: 4,
    SOURCE_PRIORITY_TEXT_REGEX: 3,
    SOURCE_PRIORITY_SYNTHETIC_FIXTURE: 2,
    SOURCE_PRIORITY_UNKNOWN: 0,
}

_UNRESOLVED_BASELINE_STATUSES = {
    "",
    "missing",
    "needs_review",
    "low_confidence",
    "conflict",
    "unknown",
    "not_applicable",
}


def _text(value):
    return str(value or "").strip()


def _candidate_id(candidate, index):
    candidate_id = _text((candidate or {}).get("candidate_id"))
    if candidate_id:
        return candidate_id
    field_name = normalize_field_name((candidate or {}).get("field_name"))
    return f"{field_name}_{index + 1}"


def _candidate_value(candidate):
    candidate = candidate or {}
    return _text(candidate.get("normalized_value") or candidate.get("raw_value")).lower()


def classify_candidate_source_priority(candidate):
    candidate = candidate or {}
    source = _text(candidate.get("source")).lower()
    evidence_type = _text(
        (candidate.get("layout_evidence_ref") or {}).get("evidence_type")
        if isinstance(candidate.get("layout_evidence_ref"), dict)
        else ""
    )

    if source == SOURCE_MANUAL_REVIEW:
        return SOURCE_PRIORITY_MANUAL_REVIEW
    if source == SOURCE_BROKER_TEMPLATE_FUTURE:
        return SOURCE_PRIORITY_BROKER_TEMPLATE
    if (
        source == SOURCE_TABLE_PATTERN_FUTURE
        or _text(candidate.get("layout_table_id"))
        or evidence_type in {"table_cell", "same_row"}
    ):
        return SOURCE_PRIORITY_LAYOUT_TABLE
    if _text(candidate.get("layout_proximity_type")):
        return SOURCE_PRIORITY_LAYOUT_LABEL_VALUE
    if _text(candidate.get("layout_section_role")):
        return SOURCE_PRIORITY_LAYOUT_SECTION
    if source == SOURCE_SECTION_PATTERN:
        return SOURCE_PRIORITY_TEXT_SECTION
    if source in {SOURCE_REGEX, SOURCE_LABEL_PATTERN}:
        return SOURCE_PRIORITY_TEXT_REGEX
    if source == SOURCE_SYNTHETIC_FIXTURE:
        return SOURCE_PRIORITY_SYNTHETIC_FIXTURE
    return SOURCE_PRIORITY_UNKNOWN


def _candidate_score(candidate):
    confidence = normalize_confidence((candidate or {}).get("confidence"))
    source_priority = classify_candidate_source_priority(candidate)
    return _CONFIDENCE_SCORE.get(confidence, 0) + _SOURCE_SCORE.get(source_priority, 0)


def _is_strong(candidate):
    confidence = normalize_confidence((candidate or {}).get("confidence"))
    return confidence in {CANDIDATE_CONFIDENCE_HIGH, CANDIDATE_CONFIDENCE_MEDIUM}


def build_candidate_fusion_decision(
    field_name,
    selected_candidate_id="",
    selected_source="",
    baseline_status="",
    fused_status=FUSION_STATUS_NEEDS_REVIEW,
    confidence=0.0,
    reasons=None,
    rejected_candidate_ids=None,
    conflict_candidate_ids=None,
    did_improve_baseline=False,
    did_worsen_baseline=False,
    review_required=True,
    warning_codes=None,
):
    return {
        "field_name": normalize_field_name(field_name),
        "selected_candidate_id": _text(selected_candidate_id),
        "selected_source": _text(selected_source),
        "baseline_status": _text(baseline_status),
        "fused_status": _text(fused_status) or FUSION_STATUS_NEEDS_REVIEW,
        "confidence": float(confidence or 0.0),
        "reasons": normalize_list(reasons),
        "rejected_candidate_ids": normalize_list(rejected_candidate_ids),
        "conflict_candidate_ids": normalize_list(conflict_candidate_ids),
        "did_improve_baseline": bool(did_improve_baseline),
        "did_worsen_baseline": bool(did_worsen_baseline),
        "review_required": bool(review_required),
        "warning_codes": normalize_list(warning_codes),
    }


def build_candidate_fusion_result(
    decisions=None,
    fused_candidates=None,
    improved_fields=None,
    worsened_fields=None,
    unchanged_fields=None,
    conflict_fields=None,
    warning_codes=None,
):
    return {
        "decisions": [decision for decision in decisions or [] if isinstance(decision, dict)],
        "fused_candidates": [
            candidate for candidate in fused_candidates or [] if isinstance(candidate, dict)
        ],
        "improved_fields": normalize_list(improved_fields),
        "worsened_fields": normalize_list(worsened_fields),
        "unchanged_fields": normalize_list(unchanged_fields),
        "conflict_fields": normalize_list(conflict_fields),
        "warning_codes": normalize_list(warning_codes),
        "fusion_version": FUSION_VERSION,
    }


def fuse_field_candidates(field_name, candidates, baseline_status=""):
    safe_candidates = [
        dict(candidate)
        for candidate in candidates or []
        if isinstance(candidate, dict)
        and normalize_field_name(candidate.get("field_name")) == normalize_field_name(field_name)
    ]
    normalized_field = normalize_field_name(field_name)
    baseline = _text(baseline_status)

    if not safe_candidates:
        fused_status = FUSION_STATUS_MISSING
        return build_candidate_fusion_decision(
            field_name=normalized_field,
            baseline_status=baseline,
            fused_status=fused_status,
            reasons=["no_candidates"],
            did_improve_baseline=False,
            did_worsen_baseline=baseline == "resolved",
            review_required=True,
            warning_codes=["fusion_no_candidates"],
        )

    ranked = sorted(
        enumerate(safe_candidates),
        key=lambda item: (_candidate_score(item[1]), _candidate_id(item[1], item[0])),
        reverse=True,
    )
    selected_index, selected = ranked[0]
    selected_id = _candidate_id(selected, selected_index)
    selected_value = _candidate_value(selected)

    conflict_ids = []
    for index, candidate in ranked[1:]:
        if not _is_strong(candidate) or not _is_strong(selected):
            continue
        if _candidate_value(candidate) and _candidate_value(candidate) != selected_value:
            score_gap = _candidate_score(selected) - _candidate_score(candidate)
            if score_gap <= 5:
                conflict_ids.extend([selected_id, _candidate_id(candidate, index)])

    if conflict_ids:
        fused_status = FUSION_STATUS_CONFLICT
        review_required = True
        warning_codes = ["fusion_conflicting_strong_candidates"]
    else:
        fused_status = FUSION_STATUS_RESOLVED
        review_required = False
        warning_codes = []

    did_improve = (
        baseline in _UNRESOLVED_BASELINE_STATUSES
        and fused_status == FUSION_STATUS_RESOLVED
    )
    did_worsen = baseline == "resolved" and fused_status != FUSION_STATUS_RESOLVED

    rejected_ids = [
        _candidate_id(candidate, index)
        for index, candidate in ranked[1:]
        if _candidate_id(candidate, index) not in conflict_ids
    ]

    return build_candidate_fusion_decision(
        field_name=normalized_field,
        selected_candidate_id=selected_id if fused_status == FUSION_STATUS_RESOLVED else "",
        selected_source=classify_candidate_source_priority(selected),
        baseline_status=baseline,
        fused_status=fused_status,
        confidence=min(_candidate_score(selected) / 40.0, 1.0),
        reasons=[
            f"selected_source:{classify_candidate_source_priority(selected)}",
            f"candidate_score:{_candidate_score(selected)}",
        ],
        rejected_candidate_ids=rejected_ids,
        conflict_candidate_ids=sorted(set(conflict_ids)),
        did_improve_baseline=did_improve,
        did_worsen_baseline=did_worsen,
        review_required=review_required,
        warning_codes=warning_codes,
    )


def fuse_candidates_by_field(candidates, baseline_statuses=None):
    baseline_statuses = baseline_statuses or {}
    grouped = defaultdict(list)
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        grouped[normalize_field_name(candidate.get("field_name"))].append(candidate)

    decisions = []
    fused_candidates = []
    improved_fields = []
    worsened_fields = []
    unchanged_fields = []
    conflict_fields = []
    warnings = []

    for field_name in sorted(grouped):
        decision = fuse_field_candidates(
            field_name,
            grouped[field_name],
            baseline_status=baseline_statuses.get(field_name, ""),
        )
        decisions.append(decision)
        warnings.extend(decision["warning_codes"])
        if decision["did_improve_baseline"]:
            improved_fields.append(field_name)
        elif decision["did_worsen_baseline"]:
            worsened_fields.append(field_name)
        else:
            unchanged_fields.append(field_name)
        if decision["fused_status"] == FUSION_STATUS_CONFLICT:
            conflict_fields.append(field_name)
            continue
        selected_id = decision["selected_candidate_id"]
        if selected_id:
            for index, candidate in enumerate(grouped[field_name]):
                if _candidate_id(candidate, index) == selected_id:
                    fused_candidates.append(candidate)
                    break

    return build_candidate_fusion_result(
        decisions=decisions,
        fused_candidates=fused_candidates,
        improved_fields=sorted(set(improved_fields)),
        worsened_fields=sorted(set(worsened_fields)),
        unchanged_fields=sorted(set(unchanged_fields)),
        conflict_fields=sorted(set(conflict_fields)),
        warning_codes=sorted(set(warnings)),
    )


def apply_no_regression_guard(
    fusion_result,
    baseline_statuses=None,
    protected_fields=None,
    allow_layout_regression_for_debug=False,
):
    result = dict(fusion_result or {})
    if allow_layout_regression_for_debug:
        return result

    baseline_statuses = baseline_statuses or {}
    protected = {
        normalize_field_name(field)
        for field in (protected_fields or PROTECTED_CRITICAL_FIELDS)
    }
    worsened = {
        normalize_field_name(field)
        for field in result.get("worsened_fields", []) or []
    }
    unchanged = {
        normalize_field_name(field)
        for field in result.get("unchanged_fields", []) or []
    }
    warnings = set(normalize_list(result.get("warning_codes")))

    prevented = sorted(
        field
        for field in worsened
        if field in protected and _text(baseline_statuses.get(field)) == "resolved"
    )
    if not prevented:
        return result

    worsened -= set(prevented)
    unchanged |= set(prevented)
    warnings.add(NO_REGRESSION_WARNING)
    result["worsened_fields"] = sorted(worsened)
    result["unchanged_fields"] = sorted(unchanged)
    result["prevented_regression_fields"] = prevented
    result["warning_codes"] = sorted(warnings)

    guarded_decisions = []
    for decision in result.get("decisions", []) or []:
        if not isinstance(decision, dict):
            continue
        item = dict(decision)
        field_name = normalize_field_name(item.get("field_name"))
        if field_name in prevented:
            item["did_worsen_baseline"] = False
            item["review_required"] = True
            item["warning_codes"] = sorted(
                set(normalize_list(item.get("warning_codes"))) | {NO_REGRESSION_WARNING}
            )
        guarded_decisions.append(item)
    if guarded_decisions:
        result["decisions"] = guarded_decisions

    return result
