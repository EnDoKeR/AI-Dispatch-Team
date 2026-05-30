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
    DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED,
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
from app.document_ai.layout_pipeline import extract_layout_candidates_from_pdf
from app.document_ai.layout_provider_diagnostics import (
    build_layout_provider_diagnostics,
    classify_layout_provider_diagnostic_issue,
)
from app.document_ai.candidate_fusion import (
    NO_REGRESSION_WARNING,
    PROTECTED_CRITICAL_FIELDS,
    apply_no_regression_guard,
)
from app.document_ai.operational_fusion import fuse_operational_detail_candidates
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
from app.document_ai.rate_fusion import fuse_rate_candidates
from app.document_ai.ratecon_candidates import (
    FIELD_ACCESSORIAL_TERM,
    FIELD_COMMODITY,
    FIELD_EQUIPMENT,
    FIELD_RATE,
    FIELD_SPECIAL_REQUIREMENT,
    FIELD_WEIGHT,
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
from app.document_ai.stop_association import (
    build_stop_association_result,
    build_stop_groups_from_layout_sections,
    build_stop_groups_from_layout_tables,
    fuse_stop_candidates,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from app.market_intelligence.intake.rate_confirmation_validation import (
    validate_rate_confirmation_intake,
)


PRIVATE_RATECON_MEASUREMENT_PIPELINE_VERSION = "private_ratecon_measurement_pipeline_v1"

LAYOUT_STATUS_SKIPPED_NON_DIGITAL = "skipped_non_digital"
LAYOUT_STATUS_SKIPPED_NOT_RELEVANT = "skipped_not_extraction_relevant"
LAYOUT_STATUS_SKIPPED_NOT_NORMAL_LOAD = "skipped_not_normal_load_movement"

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


def _evidence_type_counts(candidates):
    counts = {}
    for candidate in candidates or []:
        evidence_ref = candidate.get("layout_evidence_ref", {})
        evidence_type = ""
        if isinstance(evidence_ref, dict):
            evidence_type = str(evidence_ref.get("evidence_type") or "").strip()
        if evidence_type:
            counts[evidence_type] = counts.get(evidence_type, 0) + 1
    return dict(sorted(counts.items()))


def _candidate_count_deltas(text_counts, layout_counts):
    fields = sorted(set((text_counts or {}).keys()).union((layout_counts or {}).keys()))
    improved = []
    worsened = []
    unchanged = []
    for field_name in fields:
        text_count = int((text_counts or {}).get(field_name, 0) or 0)
        layout_count = int((layout_counts or {}).get(field_name, 0) or 0)
        if layout_count > text_count:
            improved.append(field_name)
        elif layout_count < text_count:
            worsened.append(field_name)
        else:
            unchanged.append(field_name)
    return improved, worsened, unchanged


def _template_result_uses_adjusted_candidates(template_result):
    template_selection = (template_result or {}).get("template_selection_result", {})
    return (
        template_selection.get("status") == "matched"
        and bool((template_result or {}).get("template_scoring_applied", False))
    )


def _candidate_result_for_resolution(template_result):
    if _template_result_uses_adjusted_candidates(template_result):
        return (template_result or {}).get("adjusted_candidate_result", {})
    return (template_result or {}).get("base_candidate_result", {})


def _resolution_status_map(resolution_result):
    statuses = {}
    for resolution in (resolution_result or {}).get("resolutions", []) or []:
        if not isinstance(resolution, dict):
            continue
        field_name = str(resolution.get("field_name") or "").strip()
        status = str(resolution.get("status") or "").strip()
        if field_name:
            statuses[field_name] = status
    return statuses


def _candidate_ids(candidates):
    return {
        str(candidate.get("candidate_id") or candidate.get("evidence_ref") or "").strip()
        for candidate in candidates or []
        if isinstance(candidate, dict)
    }


def _filter_candidates_by_field(candidates, fields):
    fields = set(fields or [])
    return [
        candidate
        for candidate in candidates or []
        if isinstance(candidate, dict)
        and str(candidate.get("field_name") or "").strip() in fields
    ]


def _combine_stop_association_results(*results):
    groups = []
    unresolved = []
    conflicts = []
    warnings = []
    for result in results:
        groups.extend((result or {}).get("stop_groups", []) or [])
        unresolved.extend((result or {}).get("unresolved_stop_fields", []) or [])
        conflicts.extend((result or {}).get("conflict_stop_fields", []) or [])
        warnings.extend((result or {}).get("warning_codes", []) or [])
    return build_stop_association_result(
        stop_groups=groups,
        unresolved_stop_fields=sorted(set(unresolved)),
        conflict_stop_fields=sorted(set(conflicts)),
        warning_codes=sorted(set(warnings)),
    )


def _default_fusion_fields(enable_layout_fusion=False):
    return {
        "fusion_enabled": bool(enable_layout_fusion),
        "fusion_attempted": False,
        "fusion_improved_fields": [],
        "fusion_worsened_fields": [],
        "fusion_unchanged_fields": [],
        "fusion_conflict_fields": [],
        "prevented_regression_fields": [],
        "stop_group_count": 0,
        "fusion_warning_codes": [],
        "fused_candidate_result": None,
    }


def _build_fused_candidate_result(text_candidate_result, layout_candidates, allowed_fields, warnings):
    base_candidates = list((text_candidate_result or {}).get("candidates", []) or [])
    existing_ids = _candidate_ids(base_candidates)
    added = []
    for candidate in _filter_candidates_by_field(layout_candidates, allowed_fields):
        candidate_id = str(candidate.get("candidate_id") or candidate.get("evidence_ref") or "").strip()
        if candidate_id and candidate_id in existing_ids:
            continue
        added.append(candidate)

    return {
        "document_id": (text_candidate_result or {}).get("document_id", ""),
        "artifact_id": (text_candidate_result or {}).get("artifact_id", ""),
        "candidates": base_candidates + added,
        "missing_candidate_fields": (text_candidate_result or {}).get("missing_candidate_fields", []),
        "warnings": sorted(
            set(list((text_candidate_result or {}).get("warnings", []) or []) + list(warnings or []))
        ),
        "extractor_version": "layout_fused_candidate_result_v1",
    }


def _template_result_with_fused_candidates(template_result, fused_candidate_result):
    fused = dict(template_result or {})
    if _template_result_uses_adjusted_candidates(template_result):
        fused["adjusted_candidate_result"] = fused_candidate_result
    else:
        fused["base_candidate_result"] = fused_candidate_result
    return fused


def _layout_fusion_fields(
    text_candidate_result,
    layout_fields,
    baseline_resolution_result,
    document_type="",
    enable_layout_fusion=False,
    allow_layout_regression_for_debug=False,
):
    defaults = _default_fusion_fields(enable_layout_fusion=enable_layout_fusion)
    if not enable_layout_fusion:
        return defaults
    if layout_fields.get("layout_provider_status") != "success":
        defaults["fusion_warning_codes"] = ["layout_fusion_skipped_without_successful_layout"]
        return defaults

    layout_candidate_result = layout_fields.get("layout_candidate_result") or {}
    layout_candidates = layout_candidate_result.get("candidates", []) or []
    layout_artifact = layout_fields.get("layout_artifact") or {}
    baseline_statuses = _resolution_status_map(baseline_resolution_result)
    text_candidates = (text_candidate_result or {}).get("candidates", []) or []

    table_stops = build_stop_groups_from_layout_tables(layout_artifact)
    section_stops = build_stop_groups_from_layout_sections(layout_artifact)
    stop_association = _combine_stop_association_results(table_stops, section_stops)
    stop_fusion = fuse_stop_candidates(
        text_candidate_result,
        stop_association,
        baseline_resolution_result={"field_statuses": baseline_statuses},
    )

    rate_fusion = fuse_rate_candidates(
        text_candidates=_filter_candidates_by_field(
            text_candidates,
            {FIELD_RATE, FIELD_ACCESSORIAL_TERM},
        ),
        layout_candidates=_filter_candidates_by_field(
            layout_candidates,
            {FIELD_RATE, FIELD_ACCESSORIAL_TERM},
        ),
        baseline_status=baseline_statuses.get(FIELD_RATE, ""),
        document_type=document_type,
    )

    operational_fusion = fuse_operational_detail_candidates(
        text_candidates=_filter_candidates_by_field(
            text_candidates,
            {FIELD_EQUIPMENT, FIELD_WEIGHT, FIELD_COMMODITY, FIELD_SPECIAL_REQUIREMENT},
        ),
        layout_candidates=_filter_candidates_by_field(
            layout_candidates,
            {FIELD_EQUIPMENT, FIELD_WEIGHT, FIELD_COMMODITY, FIELD_SPECIAL_REQUIREMENT},
        ),
        baseline_statuses=baseline_statuses,
    )

    improved = sorted(
        set(stop_fusion.get("improved_fields", []))
        | set(operational_fusion.get("improved_fields", []))
        | ({FIELD_RATE} if rate_fusion.get("did_improve_baseline") else set())
    )
    worsened = sorted(
        set(stop_fusion.get("worsened_fields", []))
        | set(operational_fusion.get("worsened_fields", []))
        | ({FIELD_RATE} if rate_fusion.get("did_worsen_baseline") else set())
    )
    unchanged = sorted(
        set(stop_fusion.get("unchanged_fields", []))
        | set(operational_fusion.get("unchanged_fields", []))
        | ({FIELD_RATE} if rate_fusion.get("fused_status") == "resolved" and not rate_fusion.get("did_improve_baseline") else set())
    )
    conflicts = sorted(
        set(stop_fusion.get("conflict_stop_fields", []))
        | set(operational_fusion.get("conflict_fields", []))
        | ({FIELD_RATE} if rate_fusion.get("fused_status") == "conflict" else set())
    )
    allowed_fields = set(improved) | set(conflicts)
    if rate_fusion.get("selected_candidate_id") and rate_fusion.get("did_improve_baseline"):
        allowed_fields.add(FIELD_RATE)

    fusion_warnings = sorted(
        set(
            stop_fusion.get("warning_codes", [])
            + rate_fusion.get("warning_codes", [])
            + operational_fusion.get("warning_codes", [])
        )
    )
    guard_result = apply_no_regression_guard(
        {
            "worsened_fields": worsened,
            "unchanged_fields": unchanged,
            "warning_codes": fusion_warnings,
        },
        baseline_statuses=baseline_statuses,
        protected_fields=PROTECTED_CRITICAL_FIELDS,
        allow_layout_regression_for_debug=allow_layout_regression_for_debug,
    )
    worsened = guard_result.get("worsened_fields", worsened)
    unchanged = guard_result.get("unchanged_fields", unchanged)
    prevented_regressions = guard_result.get("prevented_regression_fields", [])
    fusion_warnings = guard_result.get("warning_codes", fusion_warnings)
    if prevented_regressions:
        fusion_warnings = sorted(set(fusion_warnings) | {NO_REGRESSION_WARNING})

    defaults.update(
        {
            "fusion_attempted": True,
            "fusion_improved_fields": improved,
            "fusion_worsened_fields": worsened,
            "fusion_unchanged_fields": unchanged,
            "fusion_conflict_fields": conflicts,
            "prevented_regression_fields": prevented_regressions,
            "stop_group_count": len(stop_association.get("stop_groups", [])),
            "fusion_warning_codes": fusion_warnings,
            "fused_candidate_result": _build_fused_candidate_result(
                text_candidate_result,
                layout_candidates,
                allowed_fields=allowed_fields,
                warnings=fusion_warnings,
            ),
        }
    )
    return defaults


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
    if (classification_result or {}).get("document_type") == DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED:
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


def _extraction_scope_counts(classification_result):
    return count_values([
        scope
        for page in (classification_result or {}).get("page_results", [])
        for section in page.get("section_summaries", [])
        if isinstance(section, dict)
        for scope in section.get("extraction_scopes", [])
    ])


def _classification_fields(classification_result):
    result = classification_result or {}
    document_type = result.get("document_type", "UNKNOWN")
    ratecon_eligible = result.get("ratecon_eligible", False)
    return {
        "document_type": document_type,
        "ratecon_eligible": ratecon_eligible,
        "extraction_relevant": ratecon_eligible,
        "normal_load_movement": (
            bool(ratecon_eligible)
            and document_type != DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED
        ),
        "supplemental_only": result.get("supplemental_only", False),
        "page_role_counts": _page_role_counts(result),
        "section_role_counts": _section_role_counts(result),
        "extraction_scope_counts": _extraction_scope_counts(result),
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
        layout_provider_status="",
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


def _layout_measurement_fields(
    pdf_path,
    document_alias,
    route,
    classification_fields,
    classification_result,
    text_candidate_counts,
    layout_provider_name="",
    enable_layout_candidates=False,
    compare_layout_to_text_baseline=False,
    pdfplumber_table_profile="default",
):
    empty_diagnostics = {
        "layout_quality_bucket": "",
        "layout_total_word_count": 0,
        "layout_total_line_count": 0,
        "layout_total_table_count": 0,
        "layout_total_table_cell_count": 0,
        "layout_stop_signal_counts": {},
        "layout_likely_issue_bucket": "",
        "layout_table_settings_profile": "",
        "layout_provider_diagnostics": {},
    }
    if not enable_layout_candidates:
        return {
            "layout_provider_status": "",
            "layout_candidate_counts_by_field": {},
            "layout_evidence_type_counts": {},
            "layout_improved_fields": [],
            "layout_worsened_fields": [],
            "layout_unchanged_fields": [],
            "layout_warning_codes": [],
            "layout_candidate_result": {},
            "layout_artifact": {},
            **empty_diagnostics,
        }

    if route != DIGITAL_TEXT:
        return {
            "layout_provider_status": LAYOUT_STATUS_SKIPPED_NON_DIGITAL,
            "layout_candidate_counts_by_field": {},
            "layout_evidence_type_counts": {},
            "layout_improved_fields": [],
            "layout_worsened_fields": [],
            "layout_unchanged_fields": [],
            "layout_warning_codes": ["layout_provider_skipped_non_digital"],
            "layout_candidate_result": {},
            "layout_artifact": {},
            **empty_diagnostics,
        }

    if not classification_fields.get("extraction_relevant"):
        return {
            "layout_provider_status": LAYOUT_STATUS_SKIPPED_NOT_RELEVANT,
            "layout_candidate_counts_by_field": {},
            "layout_evidence_type_counts": {},
            "layout_improved_fields": [],
            "layout_worsened_fields": [],
            "layout_unchanged_fields": [],
            "layout_warning_codes": ["layout_provider_skipped_not_extraction_relevant"],
            "layout_candidate_result": {},
            "layout_artifact": {},
            **empty_diagnostics,
        }

    if not classification_fields.get("normal_load_movement"):
        return {
            "layout_provider_status": LAYOUT_STATUS_SKIPPED_NOT_NORMAL_LOAD,
            "layout_candidate_counts_by_field": {},
            "layout_evidence_type_counts": {},
            "layout_improved_fields": [],
            "layout_worsened_fields": [],
            "layout_unchanged_fields": [],
            "layout_warning_codes": ["layout_provider_skipped_not_normal_load_movement"],
            "layout_candidate_result": {},
            "layout_artifact": {},
            **empty_diagnostics,
        }

    layout_result = extract_layout_candidates_from_pdf(
        pdf_path,
        provider_name=layout_provider_name,
        classification_result=classification_result,
        document_id=document_alias,
        include_artifact=True,
        table_settings_profile=pdfplumber_table_profile,
    )
    candidate_result = layout_result.get("candidate_result") or {}
    layout_candidates = candidate_result.get("candidates", [])
    layout_counts = layout_result.get("candidate_counts_by_field", {})
    improved, worsened, unchanged = ([], [], [])
    if compare_layout_to_text_baseline:
        improved, worsened, unchanged = _candidate_count_deltas(text_candidate_counts, layout_counts)
    provider_diagnostics = build_layout_provider_diagnostics(
        {
            "document_alias": document_alias,
            "provider_name": layout_result.get("provider_name", layout_provider_name),
            "status": layout_result.get("provider_status", ""),
            "artifact": layout_result.get("layout_artifact", {}),
            "page_count": layout_result.get("provider_page_count", 0),
            "warning_codes": layout_result.get("provider_warning_codes", []),
            "table_settings_profile": layout_result.get("table_settings_profile", ""),
        },
        classification_result=classification_result,
    )

    return {
        "layout_provider_status": layout_result.get("provider_status", ""),
        "layout_candidate_counts_by_field": layout_counts,
        "layout_evidence_type_counts": _evidence_type_counts(layout_candidates),
        "layout_improved_fields": improved,
        "layout_worsened_fields": worsened,
        "layout_unchanged_fields": unchanged,
        "layout_warning_codes": layout_result.get("warning_codes", []),
        "layout_candidate_result": candidate_result,
        "layout_artifact": layout_result.get("layout_artifact", {}),
        "layout_quality_bucket": provider_diagnostics.get("layout_quality_bucket", ""),
        "layout_total_word_count": provider_diagnostics.get("total_word_count", 0),
        "layout_total_line_count": provider_diagnostics.get("total_line_count", 0),
        "layout_total_table_count": provider_diagnostics.get("total_table_count", 0),
        "layout_total_table_cell_count": provider_diagnostics.get("total_table_cell_count", 0),
        "layout_stop_signal_counts": provider_diagnostics.get("stop_evidence_signals", {}),
        "layout_likely_issue_bucket": classify_layout_provider_diagnostic_issue(
            provider_diagnostics
        ),
        "layout_table_settings_profile": provider_diagnostics.get("table_settings_profile", ""),
        "layout_provider_diagnostics": provider_diagnostics,
    }


def measure_private_ratecon_pdf(
    pdf_path,
    document_alias,
    registry_or_templates=None,
    output_policy=None,
    layout_provider_name="",
    enable_layout_candidates=False,
    enable_layout_fusion=False,
    enable_no_regression_fusion=True,
    allow_layout_regression_for_debug=False,
    compare_layout_to_text_baseline=False,
    pdfplumber_table_profile="default",
):
    """Measure a local private RateCon PDF and return safe status summaries only."""
    policy = output_policy or build_safe_measurement_output_policy()
    if policy.get("include_raw_text") or policy.get("include_private_values"):
        raise ValueError("private measurement rows cannot include raw text or private values")

    triage_result = triage_pdf(pdf_path, document_id=document_alias)
    route = triage_result.get("recommended_route", "")
    if route == UNSUPPORTED or triage_result.get("broken"):
        row = _base_triage_row(
            document_alias,
            triage_result,
            EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED,
        )
        if enable_layout_candidates:
            row["layout_provider_status"] = LAYOUT_STATUS_SKIPPED_NON_DIGITAL
        if enable_layout_fusion:
            row["fusion_enabled"] = True
        return row

    extraction = _extract_text_in_memory(pdf_path)
    combined_warnings = sorted(
        set(triage_result.get("warnings", []) + extraction.get("warnings", []))
    )
    extraction_status = extraction.get("extraction_status", EXTRACTION_STATUS_TRIAGE_ONLY)

    if extraction_status != EXTRACTION_STATUS_TEXT_EXTRACTED:
        row = _base_triage_row(
            document_alias,
            triage_result,
            extraction_status,
            warnings=combined_warnings,
        )
        if enable_layout_candidates:
            row["layout_provider_status"] = LAYOUT_STATUS_SKIPPED_NON_DIGITAL
        if enable_layout_fusion:
            row["fusion_enabled"] = True
        return row

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
            skipped_by_scope=True,
            layout_provider_status=(
                LAYOUT_STATUS_SKIPPED_NOT_RELEVANT if enable_layout_candidates else ""
            ),
            fusion_enabled=enable_layout_fusion,
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
    resolver_candidate_result = _candidate_result_for_resolution(template_result)
    layout_fields = _layout_measurement_fields(
        pdf_path=pdf_path,
        document_alias=document_alias,
        route=triage_result.get("recommended_route", DIGITAL_TEXT),
        classification_fields=classification_fields,
        classification_result=classification_result,
        text_candidate_counts=candidate_counts,
        layout_provider_name=layout_provider_name,
        enable_layout_candidates=enable_layout_candidates,
        compare_layout_to_text_baseline=compare_layout_to_text_baseline,
        pdfplumber_table_profile=pdfplumber_table_profile,
    )
    baseline_resolution_result = resolve_ratecon_fields_with_template_context(template_result)
    fusion_fields = _layout_fusion_fields(
        resolver_candidate_result,
        layout_fields,
        baseline_resolution_result,
        document_type=classification_result.get("document_type", ""),
        enable_layout_fusion=enable_layout_fusion,
        allow_layout_regression_for_debug=(
            allow_layout_regression_for_debug or not enable_no_regression_fusion
        ),
    )
    layout_likely_issue_bucket = classify_layout_provider_diagnostic_issue(
        layout_fields.get("layout_provider_diagnostics", {}),
        stop_group_count=fusion_fields.get("stop_group_count", 0),
    )
    resolution_template_result = template_result
    if fusion_fields.get("fused_candidate_result"):
        resolution_template_result = _template_result_with_fused_candidates(
            template_result,
            fusion_fields["fused_candidate_result"],
        )
    resolution_result = (
        resolve_ratecon_fields_with_template_context(resolution_template_result)
        if fusion_fields.get("fused_candidate_result")
        else baseline_resolution_result
    )
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
            + layout_fields.get("layout_warning_codes", [])
            + fusion_fields.get("fusion_warning_codes", [])
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
        skipped_by_scope=False,
        layout_provider_status=layout_fields.get("layout_provider_status", ""),
        layout_candidate_counts_by_field=layout_fields.get("layout_candidate_counts_by_field", {}),
        layout_evidence_type_counts=layout_fields.get("layout_evidence_type_counts", {}),
        layout_improved_fields=layout_fields.get("layout_improved_fields", []),
        layout_worsened_fields=layout_fields.get("layout_worsened_fields", []),
        layout_unchanged_fields=layout_fields.get("layout_unchanged_fields", []),
        layout_quality_bucket=layout_fields.get("layout_quality_bucket", ""),
        layout_total_word_count=layout_fields.get("layout_total_word_count", 0),
        layout_total_line_count=layout_fields.get("layout_total_line_count", 0),
        layout_total_table_count=layout_fields.get("layout_total_table_count", 0),
        layout_total_table_cell_count=layout_fields.get("layout_total_table_cell_count", 0),
        layout_stop_signal_counts=layout_fields.get("layout_stop_signal_counts", {}),
        layout_likely_issue_bucket=layout_likely_issue_bucket,
        layout_table_settings_profile=layout_fields.get("layout_table_settings_profile", ""),
        fusion_enabled=fusion_fields.get("fusion_enabled", False),
        fusion_attempted=fusion_fields.get("fusion_attempted", False),
        fusion_improved_fields=fusion_fields.get("fusion_improved_fields", []),
        fusion_worsened_fields=fusion_fields.get("fusion_worsened_fields", []),
        fusion_unchanged_fields=fusion_fields.get("fusion_unchanged_fields", []),
        fusion_conflict_fields=fusion_fields.get("fusion_conflict_fields", []),
        prevented_regression_fields=fusion_fields.get("prevented_regression_fields", []),
        stop_group_count=fusion_fields.get("stop_group_count", 0),
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
