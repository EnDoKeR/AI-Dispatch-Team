"""Coverage reporting for anonymized synthetic RateCon scenarios."""

from collections import Counter
from copy import deepcopy

from app.market_intelligence.intake.ratecon_parser_coverage import (
    build_ratecon_parser_coverage_report,
)


FIELD_TO_SIGNAL_CATEGORY = {
    "broker_name": "broker_name",
    "broker_mc": "broker_mc",
    "rate": "rate",
    "pickup_location": "pickup_location",
    "pickup_date": "pickup_date",
    "pickup_time": "pickup_date",
    "delivery_location": "delivery_location",
    "delivery_date": "delivery_date",
    "delivery_time": "delivery_date",
    "commodity": "commodity",
    "weight": "weight",
    "reference_id": "reference_id",
    "equipment": "equipment",
    "special_requirements": "special_requirements",
}


EXTRACTED_STATUSES = {"yes", "partial"}


def _scenario_value(scenario, field_name, default=None):
    return deepcopy(dict(scenario).get(field_name, default))


def _field_status(coverage_report, field_name):
    category = FIELD_TO_SIGNAL_CATEGORY.get(field_name, field_name)
    return coverage_report.get("extracted_field_status", {}).get(category, "no")


def _extracted_fields(expected_fields, coverage_report):
    extracted = []

    for field_name in expected_fields:
        if _field_status(coverage_report, field_name) in EXTRACTED_STATUSES:
            extracted.append(field_name)

    return extracted


def _missing_expected_fields(expected_fields, coverage_report):
    missing = []

    for field_name in expected_fields:
        if _field_status(coverage_report, field_name) not in EXTRACTED_STATUSES:
            missing.append(field_name)

    return missing


def _scenario_result(scenario):
    safe_scenario = deepcopy(scenario)
    coverage = build_ratecon_parser_coverage_report(safe_scenario.get("text", ""))
    expected_fields = _scenario_value(
        safe_scenario,
        "expected_present_fields",
        [],
    )
    extracted_fields = _extracted_fields(expected_fields, coverage)
    fields_missing = _missing_expected_fields(expected_fields, coverage)

    return {
        "scenario_id": str(safe_scenario.get("scenario_id", "")),
        "scenario_name": str(safe_scenario.get("scenario_name", "")),
        "fields_expected": list(expected_fields),
        "fields_extracted": extracted_fields,
        "fields_missing": fields_missing,
        "expected_missing_fields": _scenario_value(
            safe_scenario,
            "expected_missing_fields",
            [],
        ),
        "expected_needs_check_fields": _scenario_value(
            safe_scenario,
            "expected_needs_check_fields",
            [],
        ),
        "signal_counts": coverage["signal_counts"],
        "suspected_parser_gap_fields": list(
            coverage.get("suspected_parser_gap_fields", [])
        ),
        "result_category": coverage.get("result_category", ""),
        "warnings": list(coverage.get("warnings", [])),
    }


def _counter_from_values(results, field_name):
    counts = Counter()

    for result in results:
        for value in result.get(field_name, []):
            counts[str(value)] += 1

    return dict(sorted(counts.items()))


def _result_category_counts(results):
    counts = Counter(str(result.get("result_category", "")) for result in results)
    return dict(sorted(counts.items()))


def build_anonymized_ratecon_scenario_report(scenarios=None):
    results = [_scenario_result(scenario) for scenario in scenarios or []]

    return {
        "total_scenarios": len(results),
        "fields_expected": _counter_from_values(results, "fields_expected"),
        "fields_extracted": _counter_from_values(results, "fields_extracted"),
        "fields_missing": _counter_from_values(results, "fields_missing"),
        "suspected_parser_gap_fields": _counter_from_values(
            results,
            "suspected_parser_gap_fields",
        ),
        "counts_by_gap_field": _counter_from_values(
            results,
            "suspected_parser_gap_fields",
        ),
        "counts_by_result_category": _result_category_counts(results),
        "scenario_results": results,
    }
