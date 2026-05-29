from app.market_intelligence.intake.summary import (
    build_intake_record_summary,
)


def increment_count(counts, field_names):
    for field_name in field_names:
        counts[field_name] = counts.get(field_name, 0) + 1


def scenario_passed(summary, scenario):
    return (
        summary["status"] == scenario["expected_status"]
        and summary["missing_fields"] == scenario["expected_missing_fields"]
        and summary["needs_check_fields"] == scenario["expected_needs_check_fields"]
    )


def build_scenario_result(scenario):
    summary = build_intake_record_summary(scenario.get("source", {}))
    passed = scenario_passed(summary, scenario)

    return {
        "scenario_id": scenario.get("scenario_id", ""),
        "name": scenario.get("name", ""),
        "status": summary["status"],
        "expected_status": scenario.get("expected_status", ""),
        "missing_fields": summary["missing_fields"],
        "expected_missing_fields": scenario.get("expected_missing_fields", []),
        "needs_check_fields": summary["needs_check_fields"],
        "expected_needs_check_fields": scenario.get(
            "expected_needs_check_fields",
            [],
        ),
        "passed": passed,
    }


def build_intake_scenario_report(scenarios):
    scenario_results = []
    missing_field_summary = {}
    needs_check_summary = {}

    for scenario in scenarios:
        result = build_scenario_result(scenario)
        scenario_results.append(result)
        increment_count(missing_field_summary, result["missing_fields"])
        increment_count(needs_check_summary, result["needs_check_fields"])

    passed_count = sum(1 for result in scenario_results if result["passed"])
    total = len(scenario_results)

    return {
        "total_scenarios": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "scenario_results": scenario_results,
        "missing_field_summary": missing_field_summary,
        "needs_check_summary": needs_check_summary,
    }


def field_list_text(field_names):
    if not field_names:
        return "none"

    return ", ".join(field_names)


def format_intake_scenario_report(report):
    lines = [
        "INTAKE SCENARIO DRY RUN",
        f"Total scenarios: {report['total_scenarios']}",
        f"Passed: {report['passed']}",
        f"Failed: {report['failed']}",
        "",
        "Scenario results:",
    ]

    for result in report["scenario_results"]:
        outcome = "PASS" if result["passed"] else "FAIL"
        lines.extend(
            [
                f"- {result['scenario_id']} ({result['name']}): {outcome}",
                f"  Status: {result['status']}",
                "  Missing fields: " + field_list_text(result["missing_fields"]),
                "  Needs check fields: "
                + field_list_text(result["needs_check_fields"]),
            ]
        )

    lines.extend(
        [
            "",
            "Missing field summary:",
        ]
    )

    if report["missing_field_summary"]:
        for field_name, count in sorted(report["missing_field_summary"].items()):
            lines.append(f"- {field_name}: {count}")
    else:
        lines.append("- none")

    lines.append("Needs-check summary:")

    if report["needs_check_summary"]:
        for field_name, count in sorted(report["needs_check_summary"].items()):
            lines.append(f"- {field_name}: {count}")
    else:
        lines.append("- none")

    lines.append("DRY RUN ONLY - synthetic intake scenarios only")

    return "\n".join(lines)
