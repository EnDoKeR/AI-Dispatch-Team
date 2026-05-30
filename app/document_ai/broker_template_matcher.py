"""Deterministic broker template matching for fake/anonymized text artifacts."""

from app.document_ai.broker_templates import build_template_match_result
from app.document_ai.broker_templates import (
    TEMPLATE_SOURCE_PRIVATE_LOCAL,
    TEMPLATE_SOURCE_PRIVATE_LOCAL_DRAFT,
)
from app.document_ai.ratecon_candidates import FIELD_BROKER_MC, FIELD_BROKER_NAME


TEMPLATE_SELECTION_STATUS_MATCHED = "matched"
TEMPLATE_SELECTION_STATUS_UNKNOWN = "unknown"
TEMPLATE_SELECTION_STATUS_CONFLICT = "conflict"
TEMPLATE_SELECTION_STATUS_LOW_CONFIDENCE = "low_confidence"

TEMPLATE_MATCHER_VERSION = "broker_template_matcher_v1"
MIN_TEMPLATE_CONFIDENCE = 0.35
CONFLICT_CONFIDENCE_GAP = 0.15


def _text(value):
    return str(value or "").strip()


def _normalize(value):
    return _text(value).lower()


def _normalize_mc(value):
    return _text(value).upper().replace(" ", "").replace("#", "")


def _unique(values):
    seen = set()
    result = []

    for value in values:
        text = _text(value)
        if not text or text in seen:
            continue

        seen.add(text)
        result.append(text)

    return result


def _confidence_bucket(confidence):
    score = float(confidence or 0.0)
    if score >= 0.75:
        return "high"
    if score >= MIN_TEMPLATE_CONFIDENCE:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def _is_private_match(match):
    return bool(match.get("is_private_local")) or match.get("template_source") in [
        TEMPLATE_SOURCE_PRIVATE_LOCAL,
        TEMPLATE_SOURCE_PRIVATE_LOCAL_DRAFT,
    ]


def _private_template_alias(matches, template_id):
    private_ids = sorted(
        _text(match.get("template_id", ""))
        for match in matches or []
        if _is_private_match(match) and _text(match.get("template_id", ""))
    )
    for index, private_id in enumerate(private_ids, start=1):
        if private_id == template_id:
            return f"PRIVATE_TEMPLATE_{index:03d}"
    return "PRIVATE_TEMPLATE_001" if template_id else ""


def build_safe_template_selection_summary(template_selection):
    """Return a shareable template summary without private identifiers."""
    status = _text((template_selection or {}).get("status", "")) or TEMPLATE_SELECTION_STATUS_UNKNOWN
    selected_id = _text((template_selection or {}).get("selected_template_id", ""))
    selected_source = _text((template_selection or {}).get("selected_template_source", ""))
    confidence = float((template_selection or {}).get("selected_confidence", 0.0) or 0.0)
    matches = (template_selection or {}).get("matches", [])
    is_private = selected_source in [TEMPLATE_SOURCE_PRIVATE_LOCAL, TEMPLATE_SOURCE_PRIVATE_LOCAL_DRAFT]

    if status != TEMPLATE_SELECTION_STATUS_MATCHED or not selected_id:
        safe_id = ""
    elif is_private:
        safe_id = _private_template_alias(matches, selected_id)
    else:
        safe_id = selected_id

    return {
        "template_status": status,
        "selected_template_safe_id": safe_id,
        "template_source": selected_source,
        "template_confidence_bucket": _confidence_bucket(confidence),
        "private_template_name_redacted": bool(is_private and safe_id),
    }


def _artifact_text(artifact):
    if isinstance(artifact, dict):
        full_text = artifact.get("full_text", "")
        if full_text:
            return _text(full_text)

        return "\n".join(_text(page.get("text", "")) for page in artifact.get("pages", []))

    full_text = getattr(artifact, "full_text", "")
    if full_text:
        return _text(full_text)

    return "\n".join(_text(getattr(page, "text", "")) for page in getattr(artifact, "pages", []))


def _candidate_values(candidate_result, field_name):
    return [
        _text(candidate.get("normalized_value") or candidate.get("raw_value"))
        for candidate in (candidate_result or {}).get("candidates", [])
        if candidate.get("field_name") == field_name
    ]


def _field_label_hits(template, normalized_text):
    labels = []

    for rule in template.get("field_label_rules", []):
        labels.extend(rule.get("labels", []))

    for rule in template.get("reference_type_rules", []):
        labels.extend(rule.get("labels", []))

    for rule in template.get("stop_section_rules", []):
        labels.extend(rule.get("pickup_labels", []))
        labels.extend(rule.get("delivery_labels", []))
        labels.extend(rule.get("appointment_labels", []))

    labels.extend(template.get("known_rate_labels", []))
    labels.extend(template.get("known_equipment_labels", []))
    labels.extend(template.get("known_special_requirement_labels", []))

    return [
        label
        for label in _unique(labels)
        if _normalize(label) and _normalize(label) in normalized_text
    ]


def match_template(artifact, template, candidate_result=None):
    text = _artifact_text(artifact)
    normalized_text = _normalize(text)
    matched_keywords = []
    excluded_keywords = []
    reasons = []
    warnings = list(template.get("warnings", []))
    confidence = 0.0

    for rule in template.get("match_rules", []):
        rule_terms = _unique(rule.get("keywords", []) + rule.get("aliases", []))
        rule_hits = [
            term
            for term in rule_terms
            if _normalize(term) and _normalize(term) in normalized_text
        ]
        matched_keywords.extend(rule_hits)

        exclude_hits = [
            term
            for term in rule.get("exclude_keywords", [])
            if _normalize(term) and _normalize(term) in normalized_text
        ]
        excluded_keywords.extend(exclude_hits)

        if len(rule_hits) >= int(rule.get("min_keyword_hits", 1) or 1):
            confidence += float(rule.get("confidence_boost", 0.0))
            confidence += min(0.25, 0.1 * len(rule_hits))
            reasons.append("keyword_rule_hit")

        if exclude_hits:
            confidence -= float(rule.get("confidence_penalty", 0.0) or 0.5)
            reasons.append("exclude_keyword_hit")

        candidate_mcs = {_normalize_mc(value) for value in _candidate_values(candidate_result, FIELD_BROKER_MC)}
        template_mcs = {_normalize_mc(value) for value in rule.get("mc_numbers", [])}
        if candidate_mcs and template_mcs and candidate_mcs.intersection(template_mcs):
            confidence += 0.35
            reasons.append("fake_mc_exact_match")

    broker_values = [
        _normalize(value)
        for value in _candidate_values(candidate_result, FIELD_BROKER_NAME)
    ]
    broker_terms = [_normalize(template.get("display_name", "")), _normalize(template.get("broker_key", ""))]
    if broker_values and any(term and any(term in value for value in broker_values) for term in broker_terms):
        confidence += 0.2
        reasons.append("broker_name_candidate_match")

    label_hits = _field_label_hits(template, normalized_text)
    if label_hits:
        confidence += min(0.2, 0.025 * len(label_hits))
        reasons.append("field_label_hits")
        matched_keywords.extend(label_hits)

    confidence = max(0.0, min(1.0, round(confidence, 3)))

    if excluded_keywords:
        warnings.append("template_exclude_keyword_seen")

    return build_template_match_result(
        template_id=template.get("template_id", ""),
        broker_key=template.get("broker_key", ""),
        confidence=confidence,
        matched_keywords=_unique(matched_keywords),
        excluded_keywords=_unique(excluded_keywords),
        reasons=_unique(reasons),
        warnings=_unique(warnings),
        template_source=template.get("source", ""),
        is_private_local=template.get("is_private_local", False),
    )


def select_broker_template(artifact, templates, candidate_result=None):
    active_templates = [
        template
        for template in templates or []
        if template.get("active", True)
    ]
    matches = [
        match_template(artifact, template, candidate_result=candidate_result)
        for template in active_templates
    ]
    matches = sorted(matches, key=lambda item: item["confidence"], reverse=True)
    warnings = []
    reasons = []
    selected = matches[0] if matches else {}
    second = matches[1] if len(matches) > 1 else {}

    selected_confidence = selected.get("confidence", 0.0)
    selected_template_id = selected.get("template_id", "")
    selected_broker_key = selected.get("broker_key", "")
    selected_template_source = selected.get("template_source", "")
    status = TEMPLATE_SELECTION_STATUS_UNKNOWN

    selected_reasons = set(selected.get("reasons", []))
    has_identity_signal = bool(
        selected_reasons.intersection(
            {"keyword_rule_hit", "fake_mc_exact_match", "broker_name_candidate_match"}
        )
    )

    if not matches or selected_confidence <= 0 or not has_identity_signal:
        warnings.append("no_template_evidence")
    elif selected_confidence < MIN_TEMPLATE_CONFIDENCE:
        status = TEMPLATE_SELECTION_STATUS_LOW_CONFIDENCE
        reasons.append("template_evidence_below_threshold")
        warnings.append("template_low_confidence")
    elif second and second.get("confidence", 0.0) >= MIN_TEMPLATE_CONFIDENCE and (
        selected_confidence - second.get("confidence", 0.0)
    ) <= CONFLICT_CONFIDENCE_GAP:
        status = TEMPLATE_SELECTION_STATUS_CONFLICT
        reasons.append("template_scores_too_close")
        warnings.append("template_conflict")
        selected_template_id = ""
        selected_broker_key = ""
        selected_template_source = ""
    else:
        status = TEMPLATE_SELECTION_STATUS_MATCHED
        reasons.append("template_selected")

    return {
        "selected_template_id": selected_template_id if status == TEMPLATE_SELECTION_STATUS_MATCHED else "",
        "selected_broker_key": selected_broker_key if status == TEMPLATE_SELECTION_STATUS_MATCHED else "",
        "selected_template_source": selected_template_source if status == TEMPLATE_SELECTION_STATUS_MATCHED else "",
        "selected_confidence": selected_confidence,
        "matches": matches,
        "status": status,
        "reasons": _unique(reasons),
        "warnings": _unique(warnings),
        "matcher_version": TEMPLATE_MATCHER_VERSION,
    }
