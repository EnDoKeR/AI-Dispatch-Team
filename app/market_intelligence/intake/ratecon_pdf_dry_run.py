"""Local-only PDF-to-RateCon dry-run pipeline."""

from copy import deepcopy

from app.market_intelligence.intake.pdf_text_extraction import (
    EMPTY_TEXT,
    EXTRACTION_FAILED,
    TEXT_EXTRACTED,
    UNSUPPORTED,
    extract_pdf_text_local,
)
from app.market_intelligence.intake.ratecon_text_dry_run import (
    run_ratecon_text_dry_run,
)


READY_FOR_REVIEW = "READY_FOR_REVIEW"
NEEDS_FIELD_FIX = "NEEDS_FIELD_FIX"
NEEDS_PARSER_FIX = "NEEDS_PARSER_FIX"
BAD_TEXT_EXTRACTION = "BAD_TEXT_EXTRACTION"
NOT_READY_FOR_PDF = "NOT_READY_FOR_PDF"


def _extraction_metadata(extraction):
    return {
        "extractor_name": extraction.get("extractor_name", ""),
        "page_count": extraction.get("page_count", 0),
        "char_count": extraction.get("char_count", 0),
        "extraction_status": extraction.get("extraction_status", ""),
        "warnings": list(extraction.get("warnings", [])),
        "private_text_saved": False,
    }


def _status_from_text_dry_run(dry_run_result):
    intake_status = str(dry_run_result.get("status", "")).strip().upper()

    if intake_status == READY_FOR_REVIEW:
        return READY_FOR_REVIEW

    if intake_status == "MISSING_FIELDS":
        return NEEDS_FIELD_FIX

    if intake_status == "NEEDS_CHECK":
        return NEEDS_PARSER_FIX

    return NEEDS_PARSER_FIX


def _status_from_extraction(extraction_status):
    if extraction_status == EMPTY_TEXT:
        return BAD_TEXT_EXTRACTION

    if extraction_status in {EXTRACTION_FAILED, UNSUPPORTED}:
        return NOT_READY_FOR_PDF

    return NOT_READY_FOR_PDF


def run_ratecon_pdf_dry_run(
    file_path,
    case_record=None,
    anonymized_label="",
    intake_id="",
):
    extraction = extract_pdf_text_local(file_path)
    extraction_status = extraction.get("extraction_status", "")
    metadata = _extraction_metadata(extraction)
    dry_run_result = None
    warnings = list(metadata["warnings"])

    if extraction_status == TEXT_EXTRACTED:
        dry_run_result = run_ratecon_text_dry_run(
            extraction.get("text", ""),
            case_record=deepcopy(case_record) if case_record is not None else None,
            intake_id=intake_id,
        )
        status = _status_from_text_dry_run(dry_run_result)
        warnings.extend(f"text_dry_run:{warning}" for warning in dry_run_result["warnings"])
    else:
        status = _status_from_extraction(extraction_status)

    return {
        "anonymized_label": str(anonymized_label or ""),
        "extraction_status": extraction_status,
        "extraction_metadata": metadata,
        "dry_run_result": dry_run_result,
        "status": status,
        "warnings": warnings,
        "dry_run_only": True,
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }
