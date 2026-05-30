"""Safe per-document private RateCon measurement pipeline."""

from contextlib import redirect_stderr
from importlib import import_module
from io import StringIO
from pathlib import Path

from app.document_ai.broker_template_candidate_extraction import (
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.broker_template_matcher import build_safe_template_selection_summary
from app.document_ai.pdf_triage import triage_pdf
from app.document_ai.pdf_triage_contract import (
    DIGITAL_TEXT,
    UNSUPPORTED,
)
from app.document_ai.private_measurement import (
    CONFIDENCE_BUCKET_HIGH,
    CONFIDENCE_BUCKET_LOW,
    CONFIDENCE_BUCKET_MEDIUM,
    CONFIDENCE_BUCKET_NONE,
    CONFIDENCE_BUCKET_UNKNOWN,
    EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED,
    EXTRACTION_STATUS_EMPTY_TEXT,
    EXTRACTION_STATUS_EXTRACTION_FAILED,
    EXTRACTION_STATUS_TEXT_EXTRACTED,
    EXTRACTION_STATUS_TRIAGE_ONLY,
    FIELD_STATUS_CONFLICT,
    FIELD_STATUS_LOW_CONFIDENCE,
    FIELD_STATUS_MISSING,
    FIELD_STATUS_NEEDS_REVIEW,
    FIELD_STATUS_NOT_APPLICABLE,
    FIELD_STATUS_RESOLVED,
    build_field_status_summary,
    build_private_ratecon_measurement_row,
    build_safe_measurement_output_policy,
)
from app.document_ai.private_measurement_blockers import (
    classify_private_ratecon_measurement_blockers,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
    FIELD_RESOLUTION_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
    FIELD_RESOLUTION_STATUS_RESOLVED,
    resolve_ratecon_fields_with_template_context,
)
from app.document_ai.ratecon_intake_draft import build_ratecon_intake_from_resolution
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from app.market_intelligence.intake.rate_confirmation_validation import (
    validate_rate_confirmation_intake,
)


PRIVATE_RATECON_MEASUREMENT_PIPELINE_VERSION = "private_ratecon_measurement_pipeline_v1"

RESOLUTION_STATUS_TO_FIELD_STATUS = {
    FIELD_RESOLUTION_STATUS_RESOLVED: FIELD_STATUS_RESOLVED,
    FIELD_RESOLUTION_STATUS_MISSING: FIELD_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_NEEDS_REVIEW: FIELD_STATUS_NEEDS_REVIEW,
    FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE: FIELD_STATUS_LOW_CONFIDENCE,
    FIELD_RESOLUTION_STATUS_CONFLICT: FIELD_STATUS_CONFLICT,
}


def _load_pypdf_reader():
    module = import_module("pypdf")
    return module.PdfReader


def _safe_pages(reader):
    pages = getattr(reader, "pages", [])
    if pages is None:
        return []
    return list(pages)


def _extract_text_in_memory(pdf_path):
    """Extract text for measurement without saving or printing it."""
    result = {
        "text": "",
        "page_count": 0,
        "char_count": 0,
        "extraction_status": EXTRACTION_STATUS_EXTRACTION_FAILED,
        "warnings": [],
    }
    path = Path(pdf_path or "")

    try:
        reader_type = _load_pypdf_reader()
    except Exception as exc:
        result["warnings"].append(f"pypdf_unavailable:{exc.__class__.__name__}")
        return result

    try:
        with redirect_stderr(StringIO()):
            reader = reader_type(str(path))
            pages = _safe_pages(reader)
        result["page_count"] = len(pages)
    except Exception as exc:
        result["warnings"].append(f"pdf_text_read_failed:{exc.__class__.__name__}")
        result["extraction_status"] = EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED
        return result

    page_text = []
    for index, page in enumerate(pages, start=1):
        try:
            with redirect_stderr(StringIO()):
                page_text.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover - extractor-specific failure
            result["warnings"].append(f"page_{index}_text_extract_failed:{exc.__class__.__name__}")

    text = "\n".join(part.strip() for part in page_text if str(part or "").strip())
    result["text"] = text
    result["char_count"] = len(text)
    result["extraction_status"] = (
        EXTRACTION_STATUS_TEXT_EXTRACTED if text else EXTRACTION_STATUS_EMPTY_TEXT
    )
    if not text:
        result["warnings"].append("no_extractable_text")
    return result


def _candidate_counts(candidates):
    counts = {}
    for candidate in candidates or []:
        field_name = str(candidate.get("field_name") or "").strip()
        if field_name:
            counts[field_name] = counts.get(field_name, 0) + 1
    return dict(sorted(counts.items()))


def _confidence_bucket(value):
    text = str(value or "").strip().upper()
    if text == "HIGH":
        return CONFIDENCE_BUCKET_HIGH
    if text == "MEDIUM":
        return CONFIDENCE_BUCKET_MEDIUM
    if text == "LOW":
        return CONFIDENCE_BUCKET_LOW
    if not text:
        return CONFIDENCE_BUCKET_NONE
    return CONFIDENCE_BUCKET_UNKNOWN


def _field_statuses(resolution_result, candidate_counts):
    statuses = []
    seen_fields = set()

    for resolution in resolution_result.get("resolutions", []):
        field_name = str(resolution.get("field_name") or "").strip()
        if not field_name:
            continue

        seen_fields.add(field_name)
        statuses.append(
            build_field_status_summary(
                field_name=field_name,
                status=RESOLUTION_STATUS_TO_FIELD_STATUS.get(
                    resolution.get("status"),
                    FIELD_STATUS_NOT_APPLICABLE,
                ),
                confidence_bucket=_confidence_bucket(resolution.get("confidence", "")),
                candidate_count=candidate_counts.get(field_name, 0),
                selected_candidate_present=bool(resolution.get("selected_candidate")),
                warning_codes=resolution.get("warning_codes", resolution.get("warnings", [])),
                safe_reasons=resolution.get("reasons", []),
            )
        )

    for field_name, count in candidate_counts.items():
        if field_name in seen_fields:
            continue
        statuses.append(
            build_field_status_summary(
                field_name=field_name,
                status=FIELD_STATUS_NOT_APPLICABLE,
                confidence_bucket=CONFIDENCE_BUCKET_UNKNOWN,
                candidate_count=count,
            )
        )

    return statuses


def _merged_list(*values):
    merged = []
    for value in values:
        for item in value or []:
            text = str(item or "").strip()
            if text and text not in merged:
                merged.append(text)
    return merged


def _base_triage_row(document_alias, triage_result, extraction_status, warnings=None):
    return build_private_ratecon_measurement_row(
        document_alias=document_alias,
        page_count=triage_result.get("page_count", 0),
        char_count=triage_result.get("char_count", 0),
        triage_route=triage_result.get("recommended_route", ""),
        extraction_status=extraction_status,
        has_text_layer=triage_result.get("has_text_layer", False),
        likely_image_based=triage_result.get("likely_image_based", False),
        template_status="unknown",
        warning_codes=warnings or triage_result.get("warnings", []),
        blocker_categories=classify_private_ratecon_measurement_blockers(
            triage_route=triage_result.get("recommended_route", ""),
            extraction_status=extraction_status,
            broken=triage_result.get("broken", False),
            likely_image_based=triage_result.get("likely_image_based", False),
        ),
        review_required=True,
    )


def measure_private_ratecon_pdf(
    pdf_path,
    document_alias,
    registry_or_templates=None,
    output_policy=None,
):
    """Measure a local private RateCon PDF and return safe status summaries only."""
    policy = output_policy or build_safe_measurement_output_policy()
    if policy.get("include_raw_text") or policy.get("include_private_values"):
        raise ValueError("private measurement rows cannot include raw text or private values")

    triage_result = triage_pdf(pdf_path, document_id=document_alias)
    route = triage_result.get("recommended_route", "")
    if route == UNSUPPORTED or triage_result.get("broken"):
        return _base_triage_row(
            document_alias,
            triage_result,
            EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED,
        )

    extraction = _extract_text_in_memory(pdf_path)
    combined_warnings = sorted(
        set(triage_result.get("warnings", []) + extraction.get("warnings", []))
    )
    extraction_status = extraction.get("extraction_status", EXTRACTION_STATUS_TRIAGE_ONLY)

    if extraction_status != EXTRACTION_STATUS_TEXT_EXTRACTED:
        return _base_triage_row(
            document_alias,
            triage_result,
            extraction_status,
            warnings=combined_warnings,
        )

    text = extraction.get("text", "")
    artifact = build_text_extraction_artifact_for_candidates(
        artifact_id=f"ART-{document_alias}",
        document_id=document_alias,
        source_name=document_alias,
        full_text=text,
        source_method="private_measurement_in_memory",
        contains_private_text=True,
        warnings=["private_text_in_memory_only"],
    )
    template_result = extract_ratecon_candidates_with_template_context(
        artifact,
        registry_or_templates or [],
    )
    candidate_result = template_result.get("adjusted_candidate_result", {})
    candidate_counts = _candidate_counts(candidate_result.get("candidates", []))
    resolution_result = resolve_ratecon_fields_with_template_context(template_result)
    intake = build_ratecon_intake_from_resolution(resolution_result)
    validation = validate_rate_confirmation_intake(intake)
    template_selection = template_result.get("template_selection_result", {})
    safe_template_summary = build_safe_template_selection_summary(template_selection)
    template_status = template_selection.get("status", "unknown")
    field_statuses = _field_statuses(resolution_result, candidate_counts)
    all_warnings = sorted(
        set(
            combined_warnings
            + template_result.get("warnings", [])
            + candidate_result.get("warnings", [])
            + resolution_result.get("warnings", [])
            + validation.get("warnings", [])
        )
    )

    return build_private_ratecon_measurement_row(
        document_alias=document_alias,
        page_count=triage_result.get("page_count", extraction.get("page_count", 0)),
        char_count=extraction.get("char_count", triage_result.get("char_count", 0)),
        triage_route=triage_result.get("recommended_route", DIGITAL_TEXT),
        extraction_status=extraction_status,
        has_text_layer=triage_result.get("has_text_layer", False),
        likely_image_based=triage_result.get("likely_image_based", False),
        template_status=template_status,
        selected_template_id=safe_template_summary.get("selected_template_safe_id", ""),
        template_source=safe_template_summary.get("template_source", ""),
        template_confidence_bucket=safe_template_summary.get("template_confidence_bucket", ""),
        candidate_counts_by_field=candidate_counts,
        field_statuses=field_statuses,
        missing_fields=_merged_list(
            validation.get("missing_fields", []),
            resolution_result.get("missing_fields", []),
        ),
        needs_check_fields=_merged_list(
            validation.get("needs_check_fields", []),
            resolution_result.get("needs_check_fields", []),
        ),
        conflict_fields=_merged_list(
            validation.get("conflict_fields", []),
            resolution_result.get("conflict_fields", []),
        ),
        warning_codes=all_warnings,
        blocker_categories=classify_private_ratecon_measurement_blockers(
            triage_route=triage_result.get("recommended_route", DIGITAL_TEXT),
            extraction_status=extraction_status,
            template_status=template_status,
            missing_fields=_merged_list(
                validation.get("missing_fields", []),
                resolution_result.get("missing_fields", []),
            ),
            needs_check_fields=_merged_list(
                validation.get("needs_check_fields", []),
                resolution_result.get("needs_check_fields", []),
            ),
            conflict_fields=_merged_list(
                validation.get("conflict_fields", []),
                resolution_result.get("conflict_fields", []),
            ),
            review_required=validation.get("review_required", intake.get("review_required", True)),
            candidate_counts_by_field=candidate_counts,
            broken=triage_result.get("broken", False),
            likely_image_based=triage_result.get("likely_image_based", False),
        ),
        intake_status=validation.get("status", intake.get("status", "")),
        review_required=validation.get("review_required", intake.get("review_required", True)),
    )
