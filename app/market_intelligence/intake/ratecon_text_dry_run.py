"""Manual RateCon pasted-text dry-run pipeline."""

from copy import deepcopy

from app.market_intelligence.intake.case_link_candidate import (
    build_intake_case_link_candidate,
)
from app.market_intelligence.intake.parser_contract import normalize_parser_output
from app.market_intelligence.intake.pasted_text_parser_adapter import (
    parse_pasted_text_to_parser_output,
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


def run_ratecon_text_dry_run(text, case_record=None, intake_id=""):
    parser_output = parse_pasted_text_to_parser_output(text)
    intake_record = normalize_parser_output(
        parser_output,
        intake_id=intake_id,
    )
    intake_summary = build_intake_record_summary(intake_record)
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
        "link_candidate": link_candidate,
        "status": intake_summary["status"],
        "warnings": _build_warnings(text, parser_output),
        "dry_run_only": True,
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }
