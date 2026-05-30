"""Redacted parser coverage diagnostics for RateCon text."""

from app.market_intelligence.intake.ratecon_field_diagnostics import (
    FIELD_SIGNAL_CATEGORIES,
    detect_ratecon_field_signals,
)
from app.market_intelligence.intake.ratecon_text_dry_run import (
    run_ratecon_text_dry_run,
)


CATEGORY_TO_PARSER_FIELD = {
    "broker_name": ["broker_name", "customer_name"],
    "broker_mc": ["broker_mc"],
    "rate": ["rate"],
    "pickup_location": ["pickup_location"],
    "delivery_location": ["delivery_location"],
    "pickup_date": ["pickup_date"],
    "delivery_date": ["delivery_date"],
    "weight": ["weight"],
    "commodity": ["commodity"],
    "reference_id": ["reference_id", "load_number"],
    "equipment": ["equipment"],
    "special_requirements": ["special_requirements"],
    "accessorials": ["special_requirements"],
}


def _field_present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return True


def _status_for_field(parser_output, missing_fields, needs_check_fields, field_names):
    fields = list(field_names)

    if all(field_name in missing_fields for field_name in fields):
        return "missing"

    if any(field_name in needs_check_fields for field_name in fields):
        return "partial" if any(
            _field_present(parser_output.get(field_name))
            for field_name in fields
        ) else "missing"

    return "yes" if any(
        _field_present(parser_output.get(field_name))
        for field_name in fields
    ) else "no"


def _field_statuses(dry_run_result):
    parser_output = dry_run_result.get("parser_output", {})
    intake_summary = dry_run_result.get("intake_summary", {})
    missing_fields = set(intake_summary.get("missing_fields", []))
    needs_check_fields = set(intake_summary.get("needs_check_fields", []))
    statuses = {}

    for category in FIELD_SIGNAL_CATEGORIES:
        field_name = CATEGORY_TO_PARSER_FIELD[category]
        statuses[category] = _status_for_field(
            parser_output,
            missing_fields,
            needs_check_fields,
            field_name,
        )

    return statuses


def _suspected_parser_gaps(signals, field_statuses):
    gaps = []

    for category in FIELD_SIGNAL_CATEGORIES:
        if signals["signal_counts"].get(category, 0) <= 0:
            continue

        if field_statuses.get(category) in {"missing", "no"}:
            gaps.append(category)

    return gaps


def _result_category(dry_run_result, suspected_gaps):
    if suspected_gaps:
        return "PARSER_GAPS_DETECTED"
    return str(dry_run_result.get("status", "") or "NO_TEXT")


def build_ratecon_parser_coverage_report(text, dry_run_result=None):
    signals = detect_ratecon_field_signals(text)
    safe_dry_run = dry_run_result or run_ratecon_text_dry_run(text)
    intake_summary = safe_dry_run.get("intake_summary", {})
    field_statuses = _field_statuses(safe_dry_run)
    suspected_gaps = _suspected_parser_gaps(signals, field_statuses)

    return {
        "text_present": signals["text_present"],
        "char_count": signals["char_count"],
        "line_count": signals["line_count"],
        "signal_counts": signals["signal_counts"],
        "detected_signal_categories": signals["detected_categories"],
        "missing_signal_categories": signals["missing_signal_categories"],
        "extracted_field_status": field_statuses,
        "missing_fields": list(intake_summary.get("missing_fields", [])),
        "needs_check_fields": list(intake_summary.get("needs_check_fields", [])),
        "suspected_parser_gap_fields": suspected_gaps,
        "result_category": _result_category(safe_dry_run, suspected_gaps),
        "warnings": list(signals.get("warnings", [])),
    }
