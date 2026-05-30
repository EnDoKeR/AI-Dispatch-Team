"""Manual RateCon pasted-text dry-run pipeline."""

from copy import deepcopy

from app.market_intelligence.intake.case_link_candidate import (
    build_intake_case_link_candidate,
)
from app.market_intelligence.intake.parser_contract import normalize_parser_output
from app.market_intelligence.intake.pasted_text_parser_adapter import (
    parse_pasted_text_to_parser_output,
)
from app.market_intelligence.intake.ratecon_core_fields import (
    build_ratecon_core_field_summary,
)
from app.market_intelligence.intake.summary import build_intake_record_summary


def _text(value):
    return str(value or "").strip()


def _low_confidence_warnings(parser_output):
    field_confidence = parser_output.get("field_confidence", {})

    if not isinstance(field_confidence, dict):
        return []

    return [
        f"low_confidence_{field_name}"
        for field_name, confidence in sorted(field_confidence.items())
        if str(confidence or "").strip().upper() == "LOW"
    ]


def _build_warnings(text, parser_output):
    warnings = []

    if not _text(text):
        warnings.append("empty_text")

    warnings.extend(_low_confidence_warnings(parser_output))

    return warnings


def _status_from_core_summary(core_summary):
    if core_summary.get("ready_for_review"):
        return "READY_FOR_REVIEW"

    return "MISSING_FIELDS"


def run_ratecon_text_dry_run(text, case_record=None, intake_id=""):
    parser_output = parse_pasted_text_to_parser_output(text)
    intake_record = normalize_parser_output(
        parser_output,
        intake_id=intake_id,
    )
    intake_summary = build_intake_record_summary(intake_record)
    core_summary = build_ratecon_core_field_summary(intake_record)
    status = _status_from_core_summary(core_summary)
    link_candidate = None

    if case_record is not None:
        link_candidate = build_intake_case_link_candidate(
            intake_record,
            deepcopy(case_record),
        )

    return {
        "parser_output": parser_output,
        "intake_record": intake_record,
        "intake_summary": intake_summary,
        "ratecon_core_summary": core_summary,
        "link_candidate": link_candidate,
        "status": status,
        "core_fields_present": core_summary["core_fields_present"],
        "missing_core_fields": list(core_summary["missing_core_fields"]),
        "optional_missing_fields": list(core_summary["optional_missing_fields"]),
        "deferred_fields": list(core_summary["deferred_fields"]),
        "miles_status": core_summary["miles_status"],
        "miles_source": core_summary["miles_source"],
        "warnings": _build_warnings(text, parser_output),
        "dry_run_only": True,
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }
