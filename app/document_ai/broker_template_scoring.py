"""Template-aware candidate scoring for fake/anonymized BrokerTemplate rules."""

from copy import deepcopy

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    CANDIDATE_CONFIDENCE_UNKNOWN,
)


TEMPLATE_CANDIDATE_SCORER_VERSION = "broker_template_candidate_scorer_v1"

CONFIDENCE_TO_SCORE = {
    CANDIDATE_CONFIDENCE_HIGH: 0.9,
    CANDIDATE_CONFIDENCE_MEDIUM: 0.6,
    CANDIDATE_CONFIDENCE_LOW: 0.3,
    CANDIDATE_CONFIDENCE_UNKNOWN: 0.0,
}


def _text(value):
    return str(value or "").strip()


def _normalize(value):
    return _text(value).lower()


def _clamp_score(value):
    return max(0.0, min(1.0, round(float(value or 0.0), 3)))


def _score_to_confidence(score):
    if score >= 0.75:
        return CANDIDATE_CONFIDENCE_HIGH

    if score >= 0.45:
        return CANDIDATE_CONFIDENCE_MEDIUM

    if score > 0:
        return CANDIDATE_CONFIDENCE_LOW

    return CANDIDATE_CONFIDENCE_UNKNOWN


def _candidate_text(candidate):
    return " ".join(
        _text(candidate.get(key, ""))
        for key in ["label", "context_before", "context_after", "raw_value", "normalized_value"]
    )


def _field_rules(template, field_name):
    return [
        rule
        for rule in template.get("field_label_rules", [])
        if rule.get("field_name") == field_name
    ]


def _stop_section_label_delta(candidate, template):
    field_name = candidate.get("field_name", "")
    context = _normalize(_candidate_text(candidate))
    delta = 0.0
    reasons = []

    for rule in template.get("stop_section_rules", []):
        if field_name.startswith("pickup_"):
            labels = rule.get("pickup_labels", []) + rule.get("appointment_labels", [])
        elif field_name.startswith("delivery_"):
            labels = rule.get("delivery_labels", []) + rule.get("appointment_labels", [])
        else:
            labels = []

        for label in labels:
            if _normalize(label) and _normalize(label) in context:
                delta += 0.1
                _append_once(reasons, f"template_stop_label:{label}")

    return delta, reasons


def _append_once(values, value):
    if value and value not in values:
        values.append(value)


def build_candidate_score_adjustment(
    candidate_id="",
    field_name="",
    original_confidence="",
    adjusted_confidence="",
    original_score=0.0,
    adjusted_score=0.0,
    delta=0.0,
    reasons=None,
    template_id="",
    warnings=None,
):
    return {
        "candidate_id": _text(candidate_id),
        "field_name": _text(field_name),
        "original_confidence": _text(original_confidence),
        "adjusted_confidence": _text(adjusted_confidence),
        "original_score": _clamp_score(original_score),
        "adjusted_score": _clamp_score(adjusted_score),
        "delta": round(float(delta or 0.0), 3),
        "reasons": [_text(reason) for reason in reasons or [] if _text(reason)],
        "template_id": _text(template_id),
        "warnings": [_text(warning) for warning in warnings or [] if _text(warning)],
    }


def build_template_candidate_scoring_result(
    template_id="",
    broker_key="",
    adjusted_candidates=None,
    adjustments=None,
    warnings=None,
    scorer_version=TEMPLATE_CANDIDATE_SCORER_VERSION,
):
    return {
        "template_id": _text(template_id),
        "broker_key": _text(broker_key),
        "adjusted_candidates": [
            candidate
            for candidate in adjusted_candidates or []
            if isinstance(candidate, dict)
        ],
        "adjustments": [
            adjustment
            for adjustment in adjustments or []
            if isinstance(adjustment, dict)
        ],
        "warnings": [_text(warning) for warning in warnings or [] if _text(warning)],
        "scorer_version": _text(scorer_version or TEMPLATE_CANDIDATE_SCORER_VERSION),
    }


def _candidate_delta(candidate, template):
    field_name = candidate.get("field_name", "")
    context = _normalize(_candidate_text(candidate))
    delta = 0.0
    reasons = []
    warnings = []

    for rule in _field_rules(template, field_name):
        for label in rule.get("labels", []):
            if _normalize(label) and _normalize(label) in context:
                delta += float(rule.get("confidence_boost", 0.0) or 0.0)
                _append_once(reasons, f"template_label:{label}")

        for label in rule.get("negative_labels", []):
            if _normalize(label) and _normalize(label) in context:
                delta -= float(rule.get("confidence_penalty", 0.0) or 0.25)
                _append_once(reasons, f"template_negative_label:{label}")
                _append_once(warnings, "template_negative_label_seen")

    if field_name == "rate":
        for label in template.get("known_rate_labels", []):
            if _normalize(label) and _normalize(label) in context:
                delta += 0.1
                _append_once(reasons, f"template_known_rate_label:{label}")

        for label in template.get("known_accessorial_labels", []):
            if _normalize(label) and _normalize(label) in context:
                delta -= 0.3
                _append_once(reasons, f"template_accessorial_label:{label}")
                _append_once(warnings, "accessorial_label_not_main_rate")

    stop_delta, stop_reasons = _stop_section_label_delta(candidate, template)
    delta += stop_delta
    for reason in stop_reasons:
        _append_once(reasons, reason)

    return delta, reasons, warnings


def apply_template_candidate_scoring(candidate_result, template):
    template_id = _text((template or {}).get("template_id", ""))
    broker_key = _text((template or {}).get("broker_key", ""))
    base_candidates = [
        candidate
        for candidate in (candidate_result or {}).get("candidates", [])
        if isinstance(candidate, dict)
    ]

    if not template_id:
        return build_template_candidate_scoring_result(
            adjusted_candidates=deepcopy(base_candidates),
            warnings=["no_template_for_scoring"],
        )

    adjusted_candidates = []
    adjustments = []

    for candidate in base_candidates:
        adjusted = deepcopy(candidate)
        original_confidence = _text(candidate.get("confidence", CANDIDATE_CONFIDENCE_UNKNOWN))
        original_score = CONFIDENCE_TO_SCORE.get(original_confidence, 0.0)
        delta, reasons, warnings = _candidate_delta(candidate, template)
        adjusted_score = _clamp_score(original_score + delta)
        adjusted_confidence = _score_to_confidence(adjusted_score)

        if reasons or warnings:
            adjusted["confidence"] = adjusted_confidence
            adjusted.setdefault("confidence_reasons", [])
            for reason in reasons:
                _append_once(adjusted["confidence_reasons"], reason)
            adjusted.setdefault("warnings", [])
            for warning in warnings:
                _append_once(adjusted["warnings"], warning)

            adjustments.append(
                build_candidate_score_adjustment(
                    candidate_id=candidate.get("candidate_id", ""),
                    field_name=candidate.get("field_name", ""),
                    original_confidence=original_confidence,
                    adjusted_confidence=adjusted_confidence,
                    original_score=original_score,
                    adjusted_score=adjusted_score,
                    delta=adjusted_score - original_score,
                    reasons=reasons,
                    template_id=template_id,
                    warnings=warnings,
                )
            )

        adjusted_candidates.append(adjusted)

    return build_template_candidate_scoring_result(
        template_id=template_id,
        broker_key=broker_key,
        adjusted_candidates=adjusted_candidates,
        adjustments=adjustments,
        warnings=[],
    )
