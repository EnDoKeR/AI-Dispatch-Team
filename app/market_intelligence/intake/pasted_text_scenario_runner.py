from app.market_intelligence.intake.parser_confidence import normalize_field_confidence
from app.market_intelligence.intake.parser_contract import normalize_parser_output
from app.market_intelligence.intake.pasted_text_parser_adapter import (
    parse_pasted_text_to_parser_output,
)
from app.market_intelligence.intake.summary import build_intake_record_summary


def increment_count(counts, field_names):
    for field_name in field_names:
        counts[field_name] = counts.get(field_name, 0) + 1


def increment_confidence_count(counts, field_confidence):
    for confidence in normalize_field_confidence(field_confidence).values():
        counts[confidence] = counts.get(confidence, 0) + 1


def expected_list(scenario, field_name):
    return list(scenario.get(field_name, []))


def expected_confidence_subset_matches(actual_confidence, expected_confidence):
    for field_name, confidence in (expected_confidence or {}).items():
        if actual_confidence.get(field_name) != confidence:
            return False

    return True


def pasted_text_scenario_passed(result):
    return (
        result["missing_fields"] == result["expected_missing_fields"]
        and result["needs_check_fields"] == result["expected_needs_check_fields"]
        and expected_confidence_subset_matches(
            result["field_confidence"],
            result["expected_confidence"],
        )
        and result["special_requirements"] == result["expected_special_requirements"]
    )


def build_pasted_text_scenario_result(scenario):
    scenario = scenario or {}
    parser_output = parse_pasted_text_to_parser_output(scenario.get("pasted_text", ""))
    record = normalize_parser_output(parser_output)
    summary = build_intake_record_summary(record)
    field_confidence = normalize_field_confidence(record.get("field_confidence", {}))
    result = {
        "scenario_id": scenario.get("scenario_id", ""),
        "scenario_name": scenario.get("scenario_name", ""),
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
        "field_confidence": field_confidence,
        "expected_confidence": dict(scenario.get("expected_confidence", {})),
        "special_requirements": list(record.get("special_requirements", [])),
        "expected_special_requirements": expected_list(
            scenario,
            "expected_special_requirements",
        ),
        "parser_warnings": build_parser_warnings(parser_output),
    }
    result["passed"] = pasted_text_scenario_passed(result)

    return result


def build_parser_warnings(parser_output):
    warnings = []

    if "RATE_NEEDS_REVIEW" in parser_output.get("special_requirements", []):
        warnings.append("RATE_NEEDS_REVIEW")

    if "BROKER_IDENTITY_NEEDS_REVIEW" in parser_output.get(
        "special_requirements",
        [],
    ):
        warnings.append("BROKER_IDENTITY_NEEDS_REVIEW")

    if "MULTI_STOP_NEEDS_REVIEW" in parser_output.get("special_requirements", []):
        warnings.append("MULTI_STOP_NEEDS_REVIEW")

    return warnings


def build_pasted_text_scenario_report(scenarios):
    scenario_results = []
    missing_field_summary = {}
    needs_check_summary = {}
    confidence_summary = {}
    parser_warning_summary = {}

    for scenario in scenarios or []:
        result = build_pasted_text_scenario_result(scenario)
        scenario_results.append(result)
        increment_count(missing_field_summary, result["missing_fields"])
        increment_count(needs_check_summary, result["needs_check_fields"])
        increment_confidence_count(confidence_summary, result["field_confidence"])
        increment_count(parser_warning_summary, result["parser_warnings"])

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
        "parser_warning_summary": parser_warning_summary,
    }


def field_list_text(field_names):
    if not field_names:
        return "none"

    return ", ".join(field_names)


def count_summary_lines(counts):
    if not counts:
        return ["- none"]

    return [
        f"- {key}: {counts[key]}"
        for key in sorted(counts)
    ]


def format_pasted_text_scenario_report(report):
    report = report or {}
    lines = [
        "PASTED TEXT SCENARIO DRY RUN",
        f"Total scenarios: {report.get('total_scenarios', 0)}",
        f"Passed: {report.get('passed', 0)}",
        f"Failed: {report.get('failed', 0)}",
        "",
        "Scenario results:",
    ]

    for result in report.get("scenario_results", []):
        outcome = "PASS" if result.get("passed") else "FAIL"
        scenario_name = result.get("scenario_name", "")
        label = result.get("scenario_id", "")
        if scenario_name:
            label = f"{label} ({scenario_name})"
        lines.extend(
            [
                f"- {label}: {outcome}",
                f"  Status: {result.get('status', '')}",
                "  Missing fields: "
                + field_list_text(result.get("missing_fields", [])),
                "  Needs-check fields: "
                + field_list_text(result.get("needs_check_fields", [])),
                "  Parser warnings: "
                + field_list_text(result.get("parser_warnings", [])),
            ]
        )

    lines.extend(["", "Missing field summary:"])
    lines.extend(count_summary_lines(report.get("missing_field_summary", {})))
    lines.append("Needs-check summary:")
    lines.extend(count_summary_lines(report.get("needs_check_summary", {})))
    lines.append("Confidence summary:")
    lines.extend(count_summary_lines(report.get("confidence_summary", {})))
    lines.append("Parser warning summary:")
    lines.extend(count_summary_lines(report.get("parser_warning_summary", {})))
    lines.append("DRY RUN ONLY - synthetic pasted-text scenarios only")

    return "\n".join(lines)
