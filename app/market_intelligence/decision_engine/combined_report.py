from copy import deepcopy

from app.market_intelligence.case_event_normalizer import normalize_case_event
from app.market_intelligence.decision_engine.comparison_report import (
    build_decision_comparison,
)
from app.market_intelligence.decision_engine.marketload_adapter import (
    decision_result_from_market_load,
    value_from,
)
from app.market_intelligence.decision_engine.timeline_preview import (
    build_decision_result_timeline_preview,
)


PREVIEW_SOURCE = "decision_engine_timeline_combined_report"


def safe_text(value):
    return str(value or "").strip()


def add_unique(items, value):
    if value and value not in items:
        items.append(value)


def increment_count(counts, key):
    counts[key] = counts.get(key, 0) + 1


def load_id_from(load):
    return safe_text(value_from(load, "load_id", "") or value_from(load, "id", ""))


def reference_id_from(load):
    return safe_text(value_from(load, "reference_id", ""))


def case_id_from(load):
    return safe_text(value_from(load, "case_id", ""))


def timestamp_from(load):
    return safe_text(
        value_from(load, "timestamp_utc", "")
        or value_from(load, "decision_timestamp_utc", "")
    )


def related_ids_for(load, decision_result):
    related_ids = {}
    load_id = safe_text(decision_result.get("linked_load_id") or load_id_from(load))
    reference_id = safe_text(
        decision_result.get("reference_id") or reference_id_from(load)
    )

    if load_id:
        related_ids["load_id"] = load_id

    if reference_id:
        related_ids["reference_id"] = reference_id

    return related_ids


def preview_payload_as_event(preview_payload):
    related_ids = preview_payload.get("related_ids") or {}

    return {
        "event_type": preview_payload.get("event_type", ""),
        "case_id": preview_payload.get("case_id", ""),
        "timestamp_utc": preview_payload.get("timestamp_utc", ""),
        "source": preview_payload.get("source", ""),
        "load_id": related_ids.get("load_id", ""),
        "reference_id": related_ids.get("reference_id", ""),
        "payload": preview_payload.get("details", {}),
    }


def combined_warnings(comparison, normalized_event_view):
    warnings = []

    for warning in comparison.get("warnings", []):
        add_unique(warnings, warning)

    for warning in normalized_event_view.get("warnings", []):
        add_unique(warnings, warning)

    return warnings


def build_decision_timeline_comparison(load):
    comparison = build_decision_comparison(load)
    decision_result = decision_result_from_market_load(load)
    timeline_preview = build_decision_result_timeline_preview(
        decision_result,
        case_id=case_id_from(load),
        timestamp_utc=timestamp_from(load),
        source=PREVIEW_SOURCE,
        related_ids=related_ids_for(load, decision_result),
    )
    normalized_event_view = normalize_case_event(
        preview_payload_as_event(timeline_preview)
    )

    return {
        "load_id": load_id_from(load),
        "reference_id": reference_id_from(load),
        "original_decision": comparison["original_decision"],
        "original_category": comparison["original_category"],
        "decision_result": decision_result,
        "timeline_preview_payload": timeline_preview,
        "normalized_event_view": normalized_event_view,
        "warnings": combined_warnings(comparison, normalized_event_view),
    }


def build_decision_timeline_comparison_report(loads):
    items = [
        build_decision_timeline_comparison(load)
        for load in deepcopy(list(loads or []))
    ]
    decisions_by_type = {}
    risk_flag_summary = {}
    warning_count = 0
    preview_event_count = 0

    for item in items:
        decision = item["decision_result"].get("decision", "")
        increment_count(decisions_by_type, decision)

        for flag in item["decision_result"].get("risk_flags", []) or []:
            increment_count(risk_flag_summary, flag)

        warning_count += len(item["warnings"])

        if item["timeline_preview_payload"].get("event_type") == "AI_DECISION_CREATED":
            preview_event_count += 1

    return {
        "dry_run": True,
        "total": len(items),
        "decisions_by_type": dict(sorted(decisions_by_type.items())),
        "risk_flag_summary": dict(sorted(risk_flag_summary.items())),
        "warning_count": warning_count,
        "preview_event_count": preview_event_count,
        "items": items,
    }
