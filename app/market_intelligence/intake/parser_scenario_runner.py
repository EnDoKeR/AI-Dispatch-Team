from app.market_intelligence.intake.parser_confidence import normalize_field_confidence
from app.market_intelligence.intake.parser_contract import normalize_parser_output
from app.market_intelligence.intake.summary import build_intake_record_summary


def increment_count(counts, field_names):
    for field_name in field_names:
        counts[field_name] = counts.get(field_name, 0) + 1


def increment_confidence_count(counts, field_confidence):
    for confidence in normalize_field_confidence(field_confidence).values():
        counts[confidence] = counts.get(confidence, 0) + 1


def expected_list(scenario, field_name):
    return list(scenario.get(field_name, []))


def parser_scenario_passed(result):
    return (
        result["missing_fields"] == result["expected_missing_fields"]
        and result["needs_check_fields"] == result["expected_needs_check_fields"]
        and result["confidence_keys"] == result["expected_confidence_keys"]
        and result["special_requirements"] == result["expected_special_requirements"]
    )


def build_parser_scenario_result(scenario):
    scenario = scenario or {}
    record = normalize_parser_output(scenario.get("raw_parser_output", {}))
    summary = build_intake_record_summary(record)
    confidence_keys = sorted(record.get("field_confidence", {}).keys())
    expected_confidence_keys = sorted(
        expected_list(scenario, "expected_confidence_keys")
    )
    result = {
        "scenario_id": scenario.get("scenario_id", ""),
        "name": scenario.get("name", ""),
        "status": summary["status"],
        "missing_fields": summary["missing_fields"],
        "expected_missing_fields": expected_list(
            scenario,
            "expected_missing_fields",
        ),
        "needs_check_fields": summary["needs_check_fields"],
        "expected_needs_check_fields": expected_list(
            scenario,
            "expected_needs_check_fields",
        ),
        "confidence_keys": confidence_keys,
        "expected_confidence_keys": expected_confidence_keys,
        "field_confidence": normalize_field_confidence(
            record.get("field_confidence", {})
        ),
        "special_requirements": list(record.get("special_requirements", [])),
        "expected_special_requirements": expected_list(
            scenario,
            "expected_special_requirements",
        ),
    }
    result["passed"] = parser_scenario_passed(result)

    return result


def build_parser_scenario_report(scenarios):
    scenario_results = []
    missing_field_summary = {}
    needs_check_summary = {}
    confidence_summary = {}

    for scenario in scenarios or []:
        result = build_parser_scenario_result(scenario)
        scenario_results.append(result)
        increment_count(missing_field_summary, result["missing_fields"])
        increment_count(needs_check_summary, result["needs_check_fields"])
        increment_confidence_count(confidence_summary, result["field_confidence"])

    passed_count = sum(1 for result in scenario_results if result["passed"])
    total = len(scenario_results)

    return {
        "total_scenarios": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "scenario_results": scenario_results,
        "missing_field_summary": missing_field_summary,
        "needs_check_summary": needs_check_summary,
        "confidence_summary": confidence_summary,
    }
