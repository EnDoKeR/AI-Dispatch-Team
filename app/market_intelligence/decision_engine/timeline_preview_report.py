from copy import deepcopy

from app.market_intelligence.case_event_types import is_known_event_type


def safe_payload(preview_payload):
    if isinstance(preview_payload, dict):
        return deepcopy(preview_payload)

    return {}


def increment_count(counts, key):
    counts[key] = counts.get(key, 0) + 1


def add_unique(items, value):
    if value and value not in items:
        items.append(value)


def decision_result_from_preview(preview_payload):
    details = preview_payload.get("details", {}) or {}
    decision_result = details.get("decision_result", {}) or {}

    if isinstance(decision_result, dict):
        return decision_result

    return {}


def preview_validation_warnings(preview_payload):
    warnings = []
    details = preview_payload.get("details", {}) or {}

    if preview_payload.get("event_type") != "AI_DECISION_CREATED":
        warnings.append("unexpected_event_type")

    if not is_known_event_type(preview_payload.get("event_type", "")):
        warnings.append("unknown_event_type")

    if details.get("preview_only") is not True:
        warnings.append("preview_only_not_true")

    if details.get("runtime_wired") is not False:
        warnings.append("runtime_wired_not_false")

    if not decision_result_from_preview(preview_payload):
        warnings.append("missing_decision_result")

    if not preview_payload.get("case_id", ""):
        warnings.append("missing_case_id")

    return warnings


def build_decision_result_timeline_preview_report(preview_payloads):
    previews = [
        safe_payload(preview)
        for preview in preview_payloads or []
    ]
    counts_by_decision = {}
    counts_by_risk_flag = {}
    counts_by_case_id = {}
    unknown_event_types = []
    validation_warnings = []

    for index, preview in enumerate(previews):
        event_type = preview.get("event_type", "")
        case_id = preview.get("case_id", "")
        decision_result = decision_result_from_preview(preview)
        decision = decision_result.get("decision", "")

        increment_count(counts_by_decision, decision)
        increment_count(counts_by_case_id, case_id)

        for flag in decision_result.get("risk_flags", []) or []:
            increment_count(counts_by_risk_flag, flag)

        if not is_known_event_type(event_type):
            add_unique(unknown_event_types, event_type)

        warnings = preview_validation_warnings(preview)

        if warnings:
            validation_warnings.append(
                {
                    "index": index,
                    "case_id": case_id,
                    "event_type": event_type,
                    "warnings": warnings,
                }
            )

    return {
        "total_previews": len(previews),
        "counts_by_decision": dict(sorted(counts_by_decision.items())),
        "counts_by_risk_flag": dict(sorted(counts_by_risk_flag.items())),
        "counts_by_case_id": dict(sorted(counts_by_case_id.items())),
        "preview_payloads": previews,
        "unknown_event_types": unknown_event_types,
        "validation_warnings": validation_warnings,
    }
