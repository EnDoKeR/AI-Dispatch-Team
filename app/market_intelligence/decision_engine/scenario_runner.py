from app.market_intelligence.decision_engine.result import build_decision_result
from app.market_intelligence.decision_engine.risk_flags import (
    dedupe_risk_flags,
    is_known_risk_flag,
)
from app.market_intelligence.decision_engine.signals import (
    build_decision_signal_bundle,
)


def expected_result_from_scenario(scenario):
    return build_decision_result(
        decision=scenario.get("expected_decision", ""),
        category=scenario.get("expected_category", ""),
        risk_flags=scenario.get("expected_risk_flags", []),
        missing_fields=scenario.get("expected_missing_fields", []),
        needs_check_fields=scenario.get("expected_needs_check_fields", []),
        review_reasons=scenario.get("expected_review_reasons", []),
        block_reasons=scenario.get("expected_block_reasons", []),
        approval_required=scenario.get("expected_approval_required", None),
        source_signals=build_decision_signal_bundle(
            scenario.get("input_signals", {})
        ),
    )


def validate_scenario(scenario):
    issues = []
    input_signals = scenario.get("input_signals", {})
    signal_bundle = build_decision_signal_bundle(input_signals)
    expected_result = expected_result_from_scenario(scenario)
    expected_flags = dedupe_risk_flags(scenario.get("expected_risk_flags", []))

    unknown_flags = [
        flag
        for flag in expected_flags
        if not is_known_risk_flag(flag)
    ]

    if unknown_flags:
        issues.append(
            "Unknown risk flags: " + ", ".join(unknown_flags)
        )

    if expected_result["risk_flags"] != expected_flags:
        issues.append("Expected risk flags did not normalize consistently.")

    for field_name in [
        "expected_missing_fields",
        "expected_needs_check_fields",
        "expected_review_reasons",
        "expected_block_reasons",
    ]:
        if not isinstance(scenario.get(field_name, []), list):
            issues.append(f"{field_name} must be a list.")

    return {
        "scenario_id": scenario.get("scenario_id", ""),
        "scenario_name": scenario.get("scenario_name", ""),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "decision": expected_result["decision"],
        "category": expected_result["category"],
        "risk_flags": expected_result["risk_flags"],
        "missing_fields": expected_result["missing_fields"],
        "needs_check_fields": expected_result["needs_check_fields"],
        "approval_required": expected_result["approval_required"],
        "signal_bundle": signal_bundle,
        "expected_result": expected_result,
    }


def increment_counts(counts, items):
    for item in items:
        counts[item] = counts.get(item, 0) + 1


def run_decision_engine_scenarios(scenarios):
    scenario_results = [
        validate_scenario(scenario)
        for scenario in scenarios or []
    ]

    decision_summary = {}
    risk_flag_summary = {}

    for result in scenario_results:
        decision = result["decision"]
        decision_summary[decision] = decision_summary.get(decision, 0) + 1
        increment_counts(risk_flag_summary, result["risk_flags"])

    passed = len([item for item in scenario_results if item["status"] == "PASS"])
    failed = len(scenario_results) - passed

    return {
        "dry_run": True,
        "total": len(scenario_results),
        "passed": passed,
        "failed": failed,
        "scenario_results": scenario_results,
        "risk_flag_summary": dict(sorted(risk_flag_summary.items())),
        "decision_summary": dict(sorted(decision_summary.items())),
    }
