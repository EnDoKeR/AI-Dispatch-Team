from app.market_intelligence.decision_engine.marketload_adapter import (
    category_from_load,
    decision_result_from_market_load,
    normalize_status,
    reason_fields,
    value_from,
)


def safe_text(value):
    return str(value or "").strip()


def safe_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        items = value
    elif isinstance(value, (tuple, set)):
        items = list(value)
    else:
        items = [value]

    cleaned = []

    for item in items:
        text = safe_text(item)

        if text:
            cleaned.append(text)

    return cleaned


def original_reasons_from_load(load):
    reasons = []

    for values in reason_fields(load):
        reasons.extend(safe_list(values))

    deduped = []
    seen = set()

    for reason in reasons:
        key = reason.lower()

        if key in seen:
            continue

        seen.add(key)
        deduped.append(reason)

    return deduped


def comparison_warnings(load, original_decision, original_category):
    warnings = []

    if not safe_text(value_from(load, "driver_match_status", "")):
        warnings.append("missing_original_decision")

    if not safe_text(original_category):
        warnings.append("missing_original_category")

    if not safe_text(value_from(load, "reference_id", "")):
        warnings.append("missing_reference_id")

    if original_decision == "NO_ACTION":
        warnings.append("unknown_or_empty_decision")

    return warnings


def build_decision_comparison(load):
    adapter_result = decision_result_from_market_load(load)
    original_decision = normalize_status(value_from(load, "driver_match_status", ""))
    original_category = category_from_load(load, original_decision)
    decision_matches = original_decision == adapter_result["decision"]
    category_matches = safe_text(original_category) == safe_text(adapter_result["category"])

    return {
        "load_id": safe_text(value_from(load, "load_id", "") or value_from(load, "id", "")),
        "reference_id": safe_text(value_from(load, "reference_id", "")),
        "original_decision": original_decision,
        "original_category": safe_text(original_category),
        "adapter_decision": adapter_result["decision"],
        "adapter_category": adapter_result["category"],
        "decision_matches": decision_matches,
        "category_matches": category_matches,
        "original_reasons": original_reasons_from_load(load),
        "adapter_review_reasons": adapter_result["review_reasons"],
        "adapter_block_reasons": adapter_result["block_reasons"],
        "adapter_risk_flags": adapter_result["risk_flags"],
        "warnings": comparison_warnings(load, original_decision, original_category),
    }


def increment_counts(counts, items):
    for item in items:
        counts[item] = counts.get(item, 0) + 1


def build_decision_comparison_report(loads):
    comparisons = [
        build_decision_comparison(load)
        for load in loads or []
    ]

    risk_flag_summary = {}

    for comparison in comparisons:
        increment_counts(risk_flag_summary, comparison["adapter_risk_flags"])

    decision_match_count = len(
        [item for item in comparisons if item["decision_matches"]]
    )
    category_match_count = len(
        [item for item in comparisons if item["category_matches"]]
    )

    return {
        "dry_run": True,
        "total": len(comparisons),
        "decision_match_count": decision_match_count,
        "decision_mismatch_count": len(comparisons) - decision_match_count,
        "category_match_count": category_match_count,
        "category_mismatch_count": len(comparisons) - category_match_count,
        "comparisons": comparisons,
        "risk_flag_summary": dict(sorted(risk_flag_summary.items())),
    }
