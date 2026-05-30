"""Build RateConfirmationIntake drafts from resolved RateCon candidates."""

from app.document_ai.ratecon_candidates import (
    FIELD_BROKER_MC,
    FIELD_BROKER_NAME,
    FIELD_COMMODITY,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_TIME,
    FIELD_EQUIPMENT,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_TIME,
    FIELD_RATE,
    FIELD_WEIGHT,
)
from app.document_ai.ratecon_field_resolution import (
    FIELD_RESOLUTION_STATUS_CONFLICT,
    FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
    FIELD_RESOLUTION_STATUS_MISSING,
    FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
    FIELD_RESOLUTION_STATUS_RESOLVED,
)
from app.market_intelligence.intake.rate_confirmation_intake import (
    CRITICAL_FIELDS,
    build_extracted_field_evidence,
    build_rate_confirmation_intake,
)


RATECON_INTAKE_DRAFT_BUILDER_VERSION = "ratecon_intake_draft_from_resolution_v1"

FIELD_TO_INTAKE_KEY = {
    FIELD_BROKER_NAME: "broker_name",
    FIELD_BROKER_MC: "broker_mc",
    FIELD_LOAD_NUMBER: "load_number",
    FIELD_RATE: "rate",
    FIELD_PICKUP_LOCATION: "pickup_location",
    FIELD_PICKUP_DATE: "pickup_date",
    FIELD_PICKUP_TIME: "pickup_time",
    FIELD_DELIVERY_LOCATION: "delivery_location",
    FIELD_DELIVERY_DATE: "delivery_date",
    FIELD_DELIVERY_TIME: "delivery_time",
    FIELD_EQUIPMENT: "equipment",
    FIELD_WEIGHT: "weight",
    FIELD_COMMODITY: "commodity",
}


def _selected_value(resolution):
    candidate = resolution.get("selected_candidate", {})
    if not isinstance(candidate, dict):
        return ""

    return str(candidate.get("normalized_value") or candidate.get("raw_value") or "").strip()


def _candidate_source_method(resolution):
    candidate = resolution.get("selected_candidate", {})
    if not isinstance(candidate, dict):
        return ""

    return str(candidate.get("source") or "").strip()


def _append_once(values, value):
    if value and value not in values:
        values.append(value)


def _evidence_for_resolution(document_id, field_name, resolution):
    evidence_refs = resolution.get("evidence_refs", [])
    evidence = []

    for index, evidence_ref in enumerate(evidence_refs, start=1):
        evidence.append(
            build_extracted_field_evidence(
                evidence_id=evidence_ref,
                document_id=document_id,
                page="",
                source_method=_candidate_source_method(resolution),
                redacted_context="",
                confidence=resolution.get("confidence", ""),
            )
        )

    if not evidence and resolution.get("selected_candidate"):
        evidence.append(
            build_extracted_field_evidence(
                evidence_id=f"{field_name}-candidate-{index if evidence_refs else 1}",
                document_id=document_id,
                page="",
                source_method=_candidate_source_method(resolution),
                redacted_context="",
                confidence=resolution.get("confidence", ""),
            )
        )

    return evidence


def build_ratecon_intake_from_resolution(
    resolution_result,
    document_id="",
    source_method="candidate_resolution",
):
    resolved_document_id = (
        str(document_id or resolution_result.get("document_id", "") or "").strip()
    )
    source = {
        "document_id": resolved_document_id,
        "field_confidences": {},
        "evidence_refs": {},
        "field_evidence": [],
        "missing_fields": [],
        "needs_check_fields": [],
        "extractor_version": resolution_result.get("resolver_version", ""),
        "source_method": source_method,
        "parser_version": RATECON_INTAKE_DRAFT_BUILDER_VERSION,
        "extraction_context": {},
    }

    if "template_match_status" in resolution_result:
        source["extraction_context"] = {
            "extraction_template_id": resolution_result.get("selected_template_id", ""),
            "extraction_template_version": "",
            "template_match_confidence": resolution_result.get("template_match_confidence", 0.0),
            "template_match_status": resolution_result.get("template_match_status", ""),
            "template_context_used": bool(resolution_result.get("template_context_used", False)),
        }

    for resolution in resolution_result.get("resolutions", []):
        field_name = str(resolution.get("field_name") or "").strip()
        intake_key = FIELD_TO_INTAKE_KEY.get(field_name)
        status = resolution.get("status")

        if not intake_key:
            continue

        if status == FIELD_RESOLUTION_STATUS_RESOLVED:
            source[intake_key] = _selected_value(resolution)
            source["field_confidences"][intake_key] = resolution.get("confidence", "")
            evidence_refs = resolution.get("evidence_refs", [])
            source["evidence_refs"][intake_key] = evidence_refs
            source["field_evidence"].extend(
                _evidence_for_resolution(resolved_document_id, intake_key, resolution)
            )
        elif status == FIELD_RESOLUTION_STATUS_MISSING:
            if intake_key in CRITICAL_FIELDS:
                _append_once(source["missing_fields"], intake_key)
        elif status in [
            FIELD_RESOLUTION_STATUS_LOW_CONFIDENCE,
            FIELD_RESOLUTION_STATUS_NEEDS_REVIEW,
            FIELD_RESOLUTION_STATUS_CONFLICT,
        ]:
            if intake_key in CRITICAL_FIELDS:
                _append_once(source["needs_check_fields"], intake_key)

    for field_name in resolution_result.get("missing_fields", []):
        intake_key = FIELD_TO_INTAKE_KEY.get(field_name, field_name)
        if intake_key in CRITICAL_FIELDS:
            _append_once(source["missing_fields"], intake_key)

    for field_name in resolution_result.get("needs_check_fields", []):
        intake_key = FIELD_TO_INTAKE_KEY.get(field_name, field_name)
        if intake_key in CRITICAL_FIELDS:
            _append_once(source["needs_check_fields"], intake_key)

    for field_name in resolution_result.get("conflict_fields", []):
        intake_key = FIELD_TO_INTAKE_KEY.get(field_name, field_name)
        if intake_key in CRITICAL_FIELDS:
            _append_once(source["needs_check_fields"], intake_key)

    return build_rate_confirmation_intake(
        source,
        document_id=resolved_document_id,
        extractor_version=resolution_result.get("resolver_version", ""),
        source_method=source_method,
    )
