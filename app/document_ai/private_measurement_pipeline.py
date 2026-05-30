"""Safe per-document private RateCon measurement pipeline."""

from contextlib import redirect_stderr
from importlib import import_module
from io import StringIO
from pathlib import Path

from app.document_ai.broker_template_candidate_extraction import (
    extract_ratecon_candidates_with_template_context,
)
from app.document_ai.broker_template_matcher import build_safe_template_selection_summary
from app.document_ai.document_classification import (
    CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
    classify_document_from_text_artifact,
)
from app.document_ai.extraction_scope import (
    extraction_scope_warning_codes,
    select_pages_for_rate_candidates,
    select_pages_for_ratecon_core,
    select_pages_for_requirements_candidates,
    select_pages_for_stop_candidates,
    should_skip_ratecon_extraction,
)
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
    count_values,
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

CRITICAL_MEASUREMENT_FIELDS = (
    "broker_name",
    "broker_mc",
    "rate",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "equipment",
    "weight",
)

TONU_NON_APPLICABLE_FIELDS = (
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "equipment",
    "weight",
)

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


def _fields_with_resolution_status(resolution_result, statuses):
    wanted = set(statuses)
    fields = []
    for resolution in resolution_result.get("resolutions", []):
        field_name = str(resolution.get("field_name") or "").strip()
        if field_name and resolution.get("status") in wanted:
            fields.append(field_name)
    return fields


def _merged_list(*values):
    merged = []
    for value in values:
        for item in value or []:
            text = str(item or "").strip()
            if text and text not in merged:
                merged.append(text)
    return merged


def _non_applicable_fields_for_classification(classification_result):
    if (classification_result or {}).get("document_type") == "TRUCK_ORDER_NOT_USED":
        return list(TONU_NON_APPLICABLE_FIELDS)
    if not (classification_result or {}).get("ratecon_eligible"):
        return list(CRITICAL_MEASUREMENT_FIELDS)
    return []


def _page_role_counts(classification_result):
    return count_values([
        role
        for page in (classification_result or {}).get("page_results", [])
        for role in page.get("page_roles", [])
    ])


def _section_role_counts(classification_result):
    return count_values([
        section.get("section_role", "")
        for page in (classification_result or {}).get("page_results", [])
        for section in page.get("section_summaries", [])
        if isinstance(section, dict)
    ])


def _classification_fields(classification_result):
    result = classification_result or {}
    return {
        "document_type": result.get("document_type", "UNKNOWN"),
        "ratecon_eligible": result.get("ratecon_eligible", False),
        "supplemental_only": result.get("supplemental_only", False),
        "page_role_counts": _page_role_counts(result),
        "section_role_counts": _section_role_counts(result),
        "classification_status": result.get(
            "classification_status",
            CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
        ),
        "classification_warning_codes": result.get("warning_codes", []),
    }


def _selected_candidate_pages(classification_result, artifact):
    pages_by_number = {}
    for page in artifact.get("pages", []):
        pages_by_number[int(page.get("page_number", 0) or 0)] = page

    selected_numbers = []
    for page in (
        select_pages_for_ratecon_core(classification_result, artifact)
        + select_pages_for_rate_candidates(classification_result, artifact)
        + select_pages_for_stop_candidates(classification_result, artifact)
        + select_pages_for_requirements_candidates(classification_result, artifact)
    ):
        page_number = int(page.get("page_number", 0) or 0)
        if page_number and page_number not in selected_numbers:
            selected_numbers.append(page_number)

    return [
        pages_by_number[number]
        for number in selected_numbers
        if number in pages_by_number
    ]


def _scoped_artifact_for_pages(artifact, pages):
    return build_text_extraction_artifact_for_candidates(
        artifact_id=f"{artifact.get('artifact_id', '')}-SCOPED",
        document_id=artifact.get("document_id", ""),
        source_name=artifact.get("source_name", ""),
        pages=pages,
        source_method=artifact.get("source_method", "private_measurement_in_memory"),
        warnings=_merged_list(
            artifact.get("warnings", []),
            ["classification_extraction_scope_applied"],
        ),
        contains_private_text=artifact.get("contains_private_text", False),
    )


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
            ratecon_eligible=False,
            classification_status=CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
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
    classification_result = classify_document_from_text_artifact(artifact)
    classification_fields = _classification_fields(classification_result)
    scope_warnings = extraction_scope_warning_codes(classification_result)

    if should_skip_ratecon_extraction(classification_result):
        review_required = (
            classification_result.get("classification_status")
            == CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED
        )
        all_warnings = sorted(
            set(
                combined_warnings
                + classification_result.get("warning_codes", [])
                + scope_warnings
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
            template_status="unknown",
            candidate_counts_by_field={},
            field_statuses=[],
            missing_fields=[],
            unresolved_fields=[],
            needs_check_fields=[],
            low_confidence_fields=[],
            conflict_fields=[],
            non_applicable_fields=_non_applicable_fields_for_classification(classification_result),
            skipped_fields=_non_applicable_fields_for_classification(classification_result),
            warning_codes=all_warnings,
            blocker_categories=classify_private_ratecon_measurement_blockers(
                triage_route=triage_result.get("recommended_route", DIGITAL_TEXT),
                extraction_status=extraction_status,
                review_required=review_required,
                broken=triage_result.get("broken", False),
                likely_image_based=triage_result.get("likely_image_based", False),
                ratecon_eligible=classification_result.get("ratecon_eligible", False),
                supplemental_only=classification_result.get("supplemental_only", False),
                classification_status=classification_result.get("classification_status", ""),
            ),
            intake_status="CLASSIFICATION_SKIPPED_RATECON_EXTRACTION",
            review_required=review_required,
            **classification_fields,
        )

    selected_pages = _selected_candidate_pages(classification_result, artifact)
    scoped_artifact = _scoped_artifact_for_pages(artifact, selected_pages or artifact.get("pages", []))
    template_result = extract_ratecon_candidates_with_template_context(
        scoped_artifact,
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
    low_confidence_fields = _fields_with_resolution_status(
        resolution_result,
        [FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE],
    )
    unresolved_fields = _merged_list(
        _fields_with_resolution_status(
            resolution_result,
            [
                FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
                FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
                FIELD_RESOLUTION_STATUS_CONFLICT,
            ],
        ),
        resolution_result.get("needs_check_fields", []),
        resolution_result.get("conflict_fields", []),
    )
    all_warnings = sorted(
            set(
                combined_warnings
                + classification_result.get("warning_codes", [])
                + scope_warnings
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
        **classification_fields,
        candidate_counts_by_field=candidate_counts,
        field_statuses=field_statuses,
        missing_fields=_merged_list(
            validation.get("missing_fields", []),
            resolution_result.get("missing_fields", []),
        ),
        unresolved_fields=unresolved_fields,
        needs_check_fields=_merged_list(
            validation.get("needs_check_fields", []),
            resolution_result.get("needs_check_fields", []),
        ),
        low_confidence_fields=low_confidence_fields,
        conflict_fields=_merged_list(
            validation.get("conflict_fields", []),
            resolution_result.get("conflict_fields", []),
        ),
        non_applicable_fields=_non_applicable_fields_for_classification(classification_result),
        skipped_fields=[],
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
            ratecon_eligible=classification_result.get("ratecon_eligible", False),
            supplemental_only=classification_result.get("supplemental_only", False),
            classification_status=classification_result.get("classification_status", ""),
        ),
        intake_status=validation.get("status", intake.get("status", "")),
        review_required=validation.get("review_required", intake.get("review_required", True)),
    )
