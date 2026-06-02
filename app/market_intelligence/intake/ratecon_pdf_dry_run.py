"""Local-only PDF-to-RateCon dry-run pipeline."""

from copy import deepcopy

from app.document_ai.pdf_triage import triage_document
from app.document_ai.ratecon_document_pipeline import extract_ratecon_document
from app.document_ai.ratecon_shadow_audit import (
    build_ratecon_shadow_audit_record,
    build_ratecon_shadow_error_record,
)
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


def _safe_triage(file_path, document_id=""):
    try:
        result = triage_document(file_path, document_id=document_id)
    except Exception as exc:  # pragma: no cover - defensive around optional extractors
        return {
            "document_id": str(document_id or ""),
            "routing_decision": "needs_review",
            "quality_flags": ["UNKNOWN_PDF_TYPE"],
            "warnings": [f"triage_failed:{exc.__class__.__name__}"],
        }
    return {
        "document_id": result.get("document_id", ""),
        "file_hash": result.get("file_hash", ""),
        "page_count": result.get("page_count", 0),
        "pdf_type": result.get("pdf_type", "unknown"),
        "native_text_available": result.get("native_text_available", False),
        "native_text_token_count": result.get("native_text_token_count", 0),
        "native_text_density_by_page": result.get("native_text_density_by_page", []),
        "image_coverage_by_page": result.get("image_coverage_by_page", []),
        "layout_extraction_required": result.get("layout_extraction_required", False),
        "quality_flags": result.get("quality_flags", []),
        "routing_decision": result.get("routing_decision", "needs_review"),
        "triage_version": result.get("triage_version", ""),
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


def _legacy_summary_from_dry_run(dry_run_result, include_values=False):
    parser_output = (dry_run_result or {}).get("parser_output", {}) or {}
    intake_summary = (dry_run_result or {}).get("intake_summary", {}) or {}
    fields = {
        "load_number": parser_output.get("load_number", ""),
        "total_carrier_rate": parser_output.get("rate", ""),
        "broker_name": parser_output.get("broker_name", ""),
        "carrier_name": parser_output.get("carrier_name", ""),
        "pickup_date": parser_output.get("pickup_date", ""),
        "delivery_date": parser_output.get("delivery_date", ""),
    }
    fields_present = sorted(field_name for field_name, value in fields.items() if value)
    return {
        "load_number": fields["load_number"] if include_values else "",
        "total_carrier_rate": fields["total_carrier_rate"] if include_values else "",
        "broker_name": fields["broker_name"] if include_values else "",
        "carrier_name": fields["carrier_name"] if include_values else "",
        "pickup_count": 1 if parser_output.get("pickup") or parser_output.get("pickup_location") else 0,
        "delivery_count": 1 if parser_output.get("delivery") or parser_output.get("delivery_location") else 0,
        "fields_present": fields_present,
        "_comparison_values": fields,
        "legacy_status": intake_summary.get("status", ""),
    }


def _attach_shadow_document_pipeline(
    result,
    file_path,
    anonymized_label="",
    include_debug=False,
    strict=False,
):
    legacy_summary = _legacy_summary_from_dry_run(
        result.get("dry_run_result"),
        include_values=include_debug,
    )
    try:
        shadow_result = extract_ratecon_document(
            file_path,
            document_id=anonymized_label or "",
            include_debug=True,
            legacy_context={"legacy_summary": legacy_summary},
            include_legacy_final_candidates=True,
            strict_candidate_generators=strict,
        )
        record = build_ratecon_shadow_audit_record(
            document_alias=anonymized_label or "",
            pdf_path=file_path,
            shadow_result=shadow_result,
            legacy_summary=legacy_summary,
            include_values=include_debug,
            include_file_name=False,
            include_file_hash=False,
        )
    except Exception as exc:
        if strict:
            raise
        record = build_ratecon_shadow_error_record(
            document_alias=anonymized_label or "",
            pdf_path=file_path,
            error=exc,
            legacy_summary=legacy_summary,
            include_file_name=False,
            include_file_hash=False,
        )

    result["ratecon_shadow_audit_record"] = record
    result["ratecon_shadow_enabled"] = True
    return result


def run_ratecon_pdf_dry_run(
    file_path,
    case_record=None,
    anonymized_label="",
    intake_id="",
    ratecon_shadow_document_pipeline=False,
    include_document_ai_debug=False,
    strict_ratecon_shadow_document_pipeline=False,
):
    triage = _safe_triage(file_path, document_id=anonymized_label or intake_id)
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

    result = {
        "anonymized_label": str(anonymized_label or ""),
        "extraction_status": extraction_status,
        "extraction_metadata": metadata,
        "document_triage": triage,
        "dry_run_result": dry_run_result,
        "status": status,
        "warnings": warnings,
        "dry_run_only": True,
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }
    if ratecon_shadow_document_pipeline:
        result = _attach_shadow_document_pipeline(
            result,
            file_path,
            anonymized_label=anonymized_label or intake_id,
            include_debug=include_document_ai_debug,
            strict=strict_ratecon_shadow_document_pipeline,
        )
    return result
