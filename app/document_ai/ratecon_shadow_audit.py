"""Shadow diagnostics for the vertical-slice RateCon document pipeline.

These helpers run beside the legacy private measurement path. They attribute
failures to triage/text/candidate/resolver/validation layers without changing
the legacy extraction result.
"""

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)
from app.document_ai.ratecon_canonical_fields import (
    MAPPING_UNMAPPED,
    value_shape,
)
from app.document_ai.ratecon_candidates import (
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_DELIVERY_DATE,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_DATE,
    FIELD_RATE,
)
from app.document_ai.structured_stop_values import (
    FIELD_DELIVERY_STOPS,
    FIELD_PICKUP_STOPS,
    normalize_stop_candidate_value,
)


RATECON_SHADOW_AUDIT_VERSION = "ratecon_shadow_document_pipeline_audit_v1"
RATECON_SHADOW_AUDIT_JSONL = "ratecon_shadow_document_pipeline_audit.jsonl"
RATECON_SHADOW_AUDIT_SUMMARY_JSON = "ratecon_shadow_document_pipeline_summary.json"

LAYER_INGESTION = "ingestion"
LAYER_TEXT_EXTRACTION = "text_extraction"
LAYER_CANDIDATE_GENERATION = "candidate_generation"
LAYER_RESOLUTION = "resolution"
LAYER_VALIDATION = "validation"
LAYER_LEGACY_PARSER = "legacy_parser"
LAYER_UNKNOWN = "unknown"

CODE_DOC_TRIAGE_FAILED = "DOC_TRIAGE_FAILED"
CODE_DOC_NOT_PDF = "DOC_NOT_PDF"
CODE_DOC_EMPTY_OR_LOW_TEXT = "DOC_EMPTY_OR_LOW_TEXT"
CODE_DOC_IMAGE_HEAVY = "DOC_IMAGE_HEAVY"
CODE_DOC_SCANNED_OR_OCR_REQUIRED = "DOC_SCANNED_OR_OCR_REQUIRED"
CODE_DOC_MULTI_PAGE = "DOC_MULTI_PAGE"
CODE_DOC_NATIVE_TEXT_SUSPICIOUS = "DOC_NATIVE_TEXT_SUSPICIOUS"
CODE_ARTIFACT_EMPTY = "ARTIFACT_EMPTY"
CODE_ARTIFACT_LOW_TEXT = "ARTIFACT_LOW_TEXT"
CODE_ARTIFACT_NO_LINES = "ARTIFACT_NO_LINES"
CODE_TEXT_EXTRACTION_FAILED = "TEXT_EXTRACTION_FAILED"
CODE_LAYOUT_NOT_AVAILABLE = "LAYOUT_NOT_AVAILABLE"
CODE_TABLE_EXTRACTION_NOT_AVAILABLE = "TABLE_EXTRACTION_NOT_AVAILABLE"
CODE_NO_CANDIDATES = "NO_CANDIDATES"
CODE_MISSING_LOAD_NUMBER_CANDIDATE = "MISSING_LOAD_NUMBER_CANDIDATE"
CODE_MISSING_TOTAL_RATE_CANDIDATE = "MISSING_TOTAL_RATE_CANDIDATE"
CODE_MISSING_PICKUP_CANDIDATE = "MISSING_PICKUP_CANDIDATE"
CODE_MISSING_DELIVERY_CANDIDATE = "MISSING_DELIVERY_CANDIDATE"
CODE_LOW_CANDIDATE_COVERAGE = "LOW_CANDIDATE_COVERAGE"
CODE_MISSING_STOP_EVIDENCE = "MISSING_STOP_EVIDENCE"
CODE_PARTIAL_STOP_EVIDENCE_ONLY = "PARTIAL_STOP_EVIDENCE_ONLY"
CODE_STOP_ASSEMBLY_FAILED = "STOP_ASSEMBLY_FAILED"
CODE_AMBIGUOUS_STOP_ASSEMBLY = "AMBIGUOUS_STOP_ASSEMBLY"
CODE_MISSING_LOAD_LABEL_HIT = "MISSING_LOAD_LABEL_HIT"
CODE_LOAD_LABEL_HIT_NO_VALUE = "LOAD_LABEL_HIT_NO_VALUE"
CODE_LOAD_LABEL_HIT_VALUE_REJECTED = "LOAD_LABEL_HIT_VALUE_REJECTED"
CODE_LOAD_ID_CANDIDATE_WEAK_ONLY = "LOAD_ID_CANDIDATE_WEAK_ONLY"
CODE_LOAD_LABEL_HIT_VALUE_NOT_NEARBY = "LOAD_LABEL_HIT_VALUE_NOT_NEARBY"
CODE_LOAD_LABEL_HIT_VALUE_SHAPE_REJECTED = "LOAD_LABEL_HIT_VALUE_SHAPE_REJECTED"
CODE_LOAD_LABEL_HIT_COLUMNAR_PAIRING_NEEDED = "LOAD_LABEL_HIT_COLUMNAR_PAIRING_NEEDED"
CODE_LOAD_LABEL_HIT_SECTION_AMBIGUOUS = "LOAD_LABEL_HIT_SECTION_AMBIGUOUS"
CODE_LOAD_ID_ONLY_WEAK_AMBIGUOUS_CANDIDATES = "LOAD_ID_ONLY_WEAK_AMBIGUOUS_CANDIDATES"
CODE_LOAD_ID_FORENSIC_VALUE_ABSENT = "LOAD_ID_FORENSIC_VALUE_ABSENT"
CODE_STOP_PROXIMITY_MISSING_LINE_INDEX = "STOP_PROXIMITY_MISSING_LINE_INDEX"
CODE_STOP_PROXIMITY_NO_LOCATION_DATE_PAIR = "STOP_PROXIMITY_NO_LOCATION_DATE_PAIR"
CODE_STOP_PROXIMITY_MULTI_STOP_AMBIGUOUS = "STOP_PROXIMITY_MULTI_STOP_AMBIGUOUS"
CODE_STOP_PROXIMITY_SECTION_AMBIGUOUS = "STOP_PROXIMITY_SECTION_AMBIGUOUS"
CODE_STOP_PROXIMITY_CLUSTER_PARTIAL_ONLY = "STOP_PROXIMITY_CLUSTER_PARTIAL_ONLY"
CODE_LINE_SEGMENTATION_INSUFFICIENT = "LINE_SEGMENTATION_INSUFFICIENT"
CODE_COLUMNAR_LAYOUT_REQUIRES_COORDINATES = "COLUMNAR_LAYOUT_REQUIRES_COORDINATES"
CODE_TABLE_LAYOUT_REQUIRES_COORDINATES = "TABLE_LAYOUT_REQUIRES_COORDINATES"
CODE_LAYOUT_PROVIDER_UNAVAILABLE = "LAYOUT_PROVIDER_UNAVAILABLE"
CODE_LAYOUT_PROVIDER_FAILED = "LAYOUT_PROVIDER_FAILED"
CODE_LAYOUT_PROVIDER_PARTIAL = "LAYOUT_PROVIDER_PARTIAL"
CODE_LAYOUT_WORDS_UNAVAILABLE = "LAYOUT_WORDS_UNAVAILABLE"
CODE_LAYOUT_LINES_UNAVAILABLE = "LAYOUT_LINES_UNAVAILABLE"
CODE_LAYOUT_TABLES_UNAVAILABLE = "LAYOUT_TABLES_UNAVAILABLE"
CODE_TABLE_EXTRACTION_EMPTY = "TABLE_EXTRACTION_EMPTY"
CODE_TABLE_EXTRACTION_FAILED = "TABLE_EXTRACTION_FAILED"
CODE_TABLE_HEADERS_UNRECOGNIZED = "TABLE_HEADERS_UNRECOGNIZED"
CODE_TABLE_HEADER_ROW_NOT_FOUND = "TABLE_HEADER_ROW_NOT_FOUND"
CODE_TABLE_KEY_VALUE_PATTERN_NOT_FOUND = "TABLE_KEY_VALUE_PATTERN_NOT_FOUND"
CODE_TABLE_LOAD_LABEL_FOUND_VALUE_MISSING = "TABLE_LOAD_LABEL_FOUND_VALUE_MISSING"
CODE_TABLE_LOAD_VALUE_SHAPE_REJECTED = "TABLE_LOAD_VALUE_SHAPE_REJECTED"
CODE_TABLE_STOP_COLUMNS_NOT_FOUND = "TABLE_STOP_COLUMNS_NOT_FOUND"
CODE_TABLE_RATE_COLUMNS_NOT_FOUND = "TABLE_RATE_COLUMNS_NOT_FOUND"
CODE_TABLE_STOP_ROLE_COLUMN_NOT_FOUND = "TABLE_STOP_ROLE_COLUMN_NOT_FOUND"
CODE_TABLE_STOP_LOCATION_COLUMN_NOT_FOUND = "TABLE_STOP_LOCATION_COLUMN_NOT_FOUND"
CODE_TABLE_STOP_DATE_TIME_COLUMN_NOT_FOUND = "TABLE_STOP_DATE_TIME_COLUMN_NOT_FOUND"
CODE_TABLE_STOP_ROW_AMBIGUOUS = "TABLE_STOP_ROW_AMBIGUOUS"
CODE_TABLE_STOP_ROW_PARTIAL_ONLY = "TABLE_STOP_ROW_PARTIAL_ONLY"
CODE_LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE = "LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE"
CODE_LAYOUT_LOAD_LABEL_NO_NEARBY_VALUE = "LAYOUT_LOAD_LABEL_NO_NEARBY_VALUE"
CODE_LAYOUT_LOAD_TABLE_PAIRING_FAILED = "LAYOUT_LOAD_TABLE_PAIRING_FAILED"
CODE_LAYOUT_LOAD_VALUE_SHAPE_REJECTED = "LAYOUT_LOAD_VALUE_SHAPE_REJECTED"
CODE_LAYOUT_LOAD_COORDINATES_MISSING = "LAYOUT_LOAD_COORDINATES_MISSING"
CODE_LAYOUT_STOP_TABLE_NOT_FOUND = "LAYOUT_STOP_TABLE_NOT_FOUND"
CODE_LAYOUT_STOP_ROW_PAIRING_FAILED = "LAYOUT_STOP_ROW_PAIRING_FAILED"
CODE_LAYOUT_STOP_ROLE_AMBIGUOUS = "LAYOUT_STOP_ROLE_AMBIGUOUS"
CODE_LAYOUT_STOP_DATE_LOCATION_NOT_PAIRED = "LAYOUT_STOP_DATE_LOCATION_NOT_PAIRED"
CODE_LAYOUT_STOP_COORDINATES_MISSING = "LAYOUT_STOP_COORDINATES_MISSING"
CODE_ONLY_WEAK_LOAD_ID_CANDIDATES = "ONLY_WEAK_LOAD_ID_CANDIDATES"
CODE_ONLY_AMBIGUOUS_STOP_CANDIDATES = "ONLY_AMBIGUOUS_STOP_CANDIDATES"
CODE_LAYOUT_CANDIDATES_DUPLICATIVE = "LAYOUT_CANDIDATES_DUPLICATIVE"
CODE_LAYOUT_CANDIDATES_NOISY = "LAYOUT_CANDIDATES_NOISY"
CODE_TABLE_PROFILE_NO_USEFUL_TABLES = "TABLE_PROFILE_NO_USEFUL_TABLES"
CODE_TABLE_PROFILE_EXTRACTION_FRAGMENTED = "TABLE_PROFILE_EXTRACTION_FRAGMENTED"
CODE_TABLE_PROFILE_CELLS_EMPTY = "TABLE_PROFILE_CELLS_EMPTY"
CODE_RESOLVER_INPUT_HAS_HIGH_QUALITY_CANDIDATE = "RESOLVER_INPUT_HAS_HIGH_QUALITY_CANDIDATE"
CODE_RESOLVER_IGNORED_HIGH_QUALITY_CANDIDATE = "RESOLVER_IGNORED_HIGH_QUALITY_CANDIDATE"
CODE_RESOLVER_CANDIDATE_INELIGIBLE = "RESOLVER_CANDIDATE_INELIGIBLE"
CODE_RESOLVER_UNSUPPORTED_STRUCTURED_VALUE = "RESOLVER_UNSUPPORTED_STRUCTURED_VALUE"
CODE_RESOLVER_FIELD_NOT_SUPPORTED = "RESOLVER_FIELD_NOT_SUPPORTED"
CODE_RESOLVER_SELECTED_LEGACY_FALLBACK_OVER_LAYOUT = "RESOLVER_SELECTED_LEGACY_FALLBACK_OVER_LAYOUT"
CODE_RESOLVER_ALL_CANDIDATES_WEAK = "RESOLVER_ALL_CANDIDATES_WEAK"
CODE_RESOLVER_ALL_CANDIDATES_AMBIGUOUS = "RESOLVER_ALL_CANDIDATES_AMBIGUOUS"
CODE_LOAD_HIGH_QUALITY_CANDIDATE_NOT_SELECTED = "LOAD_HIGH_QUALITY_CANDIDATE_NOT_SELECTED"
CODE_LOAD_ONLY_WEAK_AMBIGUOUS_CANDIDATES = "LOAD_ONLY_WEAK_AMBIGUOUS_CANDIDATES"
CODE_LOAD_NO_ELIGIBLE_CANDIDATES = "LOAD_NO_ELIGIBLE_CANDIDATES"
CODE_LOAD_MISSING_LAYOUT_LABEL_VALUE = "LOAD_MISSING_LAYOUT_LABEL_VALUE"
CODE_STOP_STRUCTURED_CANDIDATE_NOT_SELECTED = "STOP_STRUCTURED_CANDIDATE_NOT_SELECTED"
CODE_STOP_STRUCTURED_VALUE_UNSUPPORTED = "STOP_STRUCTURED_VALUE_UNSUPPORTED"
CODE_STOP_CANDIDATES_PARTIAL_ONLY = "STOP_CANDIDATES_PARTIAL_ONLY"
CODE_STOP_CANDIDATES_AMBIGUOUS_ONLY = "STOP_CANDIDATES_AMBIGUOUS_ONLY"
CODE_STOP_TABLE_ROW_CANDIDATE_NOT_SELECTED = "STOP_TABLE_ROW_CANDIDATE_NOT_SELECTED"
CODE_STOP_NO_COMPLETE_CANDIDATE = "STOP_NO_COMPLETE_CANDIDATE"
CODE_REVIEW_GATE_LOAD_MISSING = "REVIEW_GATE_LOAD_MISSING"
CODE_REVIEW_GATE_RATE_MISSING = "REVIEW_GATE_RATE_MISSING"
CODE_REVIEW_GATE_STOP_MISSING = "REVIEW_GATE_STOP_MISSING"
CODE_REVIEW_GATE_LOW_CONFIDENCE_FIELD = "REVIEW_GATE_LOW_CONFIDENCE_FIELD"
CODE_REVIEW_GATE_CONFLICTING_FIELD = "REVIEW_GATE_CONFLICTING_FIELD"
CODE_STOP_STRUCTURED_SELECTED_COMPLETE = "STOP_STRUCTURED_SELECTED_COMPLETE"
CODE_STOP_STRUCTURED_SELECTED_PARTIAL_REVIEW = "STOP_STRUCTURED_SELECTED_PARTIAL_REVIEW"
CODE_STOP_STRUCTURED_SELECTED_BUT_LOW_CONFIDENCE = "STOP_STRUCTURED_SELECTED_BUT_LOW_CONFIDENCE"
CODE_STOP_STRUCTURED_UNSUPPORTED_VALUE = "STOP_STRUCTURED_UNSUPPORTED_VALUE"
CODE_STOP_STRUCTURED_EMPTY_AFTER_NORMALIZATION = "STOP_STRUCTURED_EMPTY_AFTER_NORMALIZATION"
CODE_STOP_STRUCTURED_DUPLICATES_COLLAPSED = "STOP_STRUCTURED_DUPLICATES_COLLAPSED"
CODE_STOP_STRUCTURED_TRUE_CONFLICT = "STOP_STRUCTURED_TRUE_CONFLICT"
CODE_STOP_STRUCTURED_PARTIAL_OVERLAP = "STOP_STRUCTURED_PARTIAL_OVERLAP"
CODE_STOP_STRUCTURED_ONLY_NOISY_PARTIALS = "STOP_STRUCTURED_ONLY_NOISY_PARTIALS"
CODE_STOP_STRUCTURED_REVIEW_GATE_PARTIAL = "STOP_STRUCTURED_REVIEW_GATE_PARTIAL"
CODE_STOP_CONFLICT_DUPLICATE_ONLY = "STOP_CONFLICT_DUPLICATE_ONLY"
CODE_STOP_CONFLICT_TRUE_DATE = "STOP_CONFLICT_TRUE_DATE"
CODE_STOP_CONFLICT_TRUE_TIME = "STOP_CONFLICT_TRUE_TIME"
CODE_STOP_CONFLICT_TRUE_LOCATION = "STOP_CONFLICT_TRUE_LOCATION"
CODE_STOP_CONFLICT_TRUE_ROLE = "STOP_CONFLICT_TRUE_ROLE"
CODE_STOP_CONFLICT_LEGACY_VS_LAYOUT = "STOP_CONFLICT_LEGACY_VS_LAYOUT"
CODE_STOP_CONFLICT_TABLE_VS_TEXT = "STOP_CONFLICT_TABLE_VS_TEXT"
CODE_REVIEW_GATE_STOP_PRESENT_PARTIAL = "REVIEW_GATE_STOP_PRESENT_PARTIAL"
CODE_REVIEW_GATE_STOP_PRESENT_CONFLICT = "REVIEW_GATE_STOP_PRESENT_CONFLICT"
CODE_REVIEW_GATE_STOP_PRESENT_UNSUPPORTED = "REVIEW_GATE_STOP_PRESENT_UNSUPPORTED"
CODE_REVIEW_GATE_RATE_TRACE_MISMATCH = "REVIEW_GATE_RATE_TRACE_MISMATCH"
CODE_CONFLICTING_LOAD_NUMBER_CANDIDATES = "CONFLICTING_LOAD_NUMBER_CANDIDATES"
CODE_CONFLICTING_TOTAL_RATE_CANDIDATES = "CONFLICTING_TOTAL_RATE_CANDIDATES"
CODE_LOW_CONFIDENCE_LOAD_NUMBER = "LOW_CONFIDENCE_LOAD_NUMBER"
CODE_LOW_CONFIDENCE_TOTAL_RATE = "LOW_CONFIDENCE_TOTAL_RATE"
CODE_LOW_CONFIDENCE_STOPS = "LOW_CONFIDENCE_STOPS"
CODE_RESOLVER_NO_DECISION = "RESOLVER_NO_DECISION"
CODE_MISSING_CRITICAL_FIELD = "MISSING_CRITICAL_FIELD"
CODE_VALIDATION_FAILED = "VALIDATION_FAILED"
CODE_NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
CODE_LEGACY_SHADOW_FIELD_MISMATCH = "LEGACY_SHADOW_FIELD_MISMATCH"
CODE_LEGACY_ONLY_FIELD = "LEGACY_ONLY_FIELD"
CODE_SHADOW_ONLY_FIELD = "SHADOW_ONLY_FIELD"
CODE_LEGACY_AND_SHADOW_BOTH_MISSING = "LEGACY_AND_SHADOW_BOTH_MISSING"
CODE_SHADOW_PIPELINE_FAILED = "SHADOW_PIPELINE_FAILED"

COMPARISON_SAME = "same"
COMPARISON_DIFFERENT = "different"
COMPARISON_LEGACY_ONLY = "legacy_only"
COMPARISON_SHADOW_ONLY = "shadow_only"
COMPARISON_BOTH_MISSING = "both_missing"
COMPARISON_NORMALIZATION_UNAVAILABLE = "normalization_unavailable"

COMPARE_FIELDS = (
    FIELD_LOAD_NUMBER,
    "total_carrier_rate",
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    "pickup_count",
    "delivery_count",
    FIELD_PICKUP_DATE,
    FIELD_DELIVERY_DATE,
)

SHADOW_CANDIDATE_COVERAGE_FIELDS = (
    FIELD_LOAD_NUMBER,
    "total_carrier_rate",
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    "pickup_stops",
    "delivery_stops",
)


def _text(value):
    return str(value or "").strip()


def _safe_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]
    return [_text(item) for item in items if _text(item)]


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_bool(value):
    return bool(value)


def _snippet(value, limit=120):
    text = " ".join(_text(value).split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _resolution_by_field(resolution_result):
    return {
        _text(resolution.get("field_name")): resolution
        for resolution in (resolution_result or {}).get("resolutions", []) or []
        if isinstance(resolution, dict) and _text(resolution.get("field_name"))
    }


def _resolution_value(resolution_result, field_name):
    resolution = _resolution_by_field(resolution_result).get(field_name, {})
    return _text(resolution.get("selected_candidate_value"))


def _shadow_value(final_output, field_name):
    if field_name == "total_carrier_rate":
        return _text((final_output or {}).get("total_carrier_rate") or (final_output or {}).get("rate"))
    if field_name == "pickup_count":
        return len((final_output or {}).get("pickup_stops", []) or [])
    if field_name == "delivery_count":
        return len((final_output or {}).get("delivery_stops", []) or [])
    return _text((final_output or {}).get(field_name))


def build_legacy_summary_from_resolution(
    resolution_result=None,
    normalized_stop_set=None,
    row=None,
    include_values=False,
):
    """Build an internal legacy summary.

    The private measurement row is redacted; when the live resolution result is
    available, this function can compare private values in memory while only
    emitting values if the caller explicitly requested local debug output.
    """
    values = {
        FIELD_LOAD_NUMBER: _resolution_value(resolution_result, FIELD_LOAD_NUMBER),
        "total_carrier_rate": _resolution_value(resolution_result, FIELD_RATE),
        FIELD_BROKER_NAME: _resolution_value(resolution_result, FIELD_BROKER_NAME),
        FIELD_CARRIER_NAME: _resolution_value(resolution_result, FIELD_CARRIER_NAME),
        FIELD_PICKUP_DATE: _resolution_value(resolution_result, FIELD_PICKUP_DATE),
        FIELD_DELIVERY_DATE: _resolution_value(resolution_result, FIELD_DELIVERY_DATE),
    }
    stop_set = normalized_stop_set if isinstance(normalized_stop_set, dict) else {}
    pickup_count = _safe_int(stop_set.get("pickup_count", (row or {}).get("pickup_count", 0)))
    delivery_count = _safe_int(stop_set.get("delivery_count", (row or {}).get("delivery_count", 0)))
    fields_present = sorted(
        field_name
        for field_name, value in values.items()
        if _text(value)
    )
    return {
        "load_number": values[FIELD_LOAD_NUMBER] if include_values else "",
        "total_carrier_rate": values["total_carrier_rate"] if include_values else "",
        "broker_name": values[FIELD_BROKER_NAME] if include_values else "",
        "carrier_name": values[FIELD_CARRIER_NAME] if include_values else "",
        "pickup_count": pickup_count,
        "delivery_count": delivery_count,
        "fields_present": fields_present,
        "_comparison_values": {
            **values,
            "pickup_count": pickup_count,
            "delivery_count": delivery_count,
        },
    }


def _safe_legacy_summary(legacy_summary):
    legacy = dict(legacy_summary or {})
    legacy.pop("_comparison_values", None)
    return legacy


def _normalize_text_value(value):
    return " ".join(_text(value).lower().split())


def _normalize_load_number(value):
    return _normalize_text_value(value)


def _normalize_money(value):
    text = _text(value).replace("$", "").replace(",", "").strip()
    if not text:
        return ""
    try:
        return str(Decimal(text).quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        return _normalize_text_value(value)


def _normalize_for_compare(field_name, value):
    if field_name in {"pickup_count", "delivery_count"}:
        return str(_safe_int(value))
    if field_name == FIELD_LOAD_NUMBER:
        return _normalize_load_number(value)
    if field_name == "total_carrier_rate":
        return _normalize_money(value)
    return _normalize_text_value(value)


def compare_legacy_shadow(legacy_summary=None, shadow_final_output=None):
    legacy_values = (legacy_summary or {}).get("_comparison_values", {}) or {}
    statuses = {}
    for field_name in COMPARE_FIELDS:
        legacy_value = legacy_values.get(field_name, "")
        shadow_value = _shadow_value(shadow_final_output or {}, field_name)
        legacy_present = _text(legacy_value) or (
            field_name in {"pickup_count", "delivery_count"} and _safe_int(legacy_value) > 0
        )
        shadow_present = _text(shadow_value) or (
            field_name in {"pickup_count", "delivery_count"} and _safe_int(shadow_value) > 0
        )
        if not legacy_present and not shadow_present:
            statuses[field_name] = COMPARISON_BOTH_MISSING
        elif legacy_present and not shadow_present:
            statuses[field_name] = COMPARISON_LEGACY_ONLY
        elif shadow_present and not legacy_present:
            statuses[field_name] = COMPARISON_SHADOW_ONLY
        else:
            legacy_norm = _normalize_for_compare(field_name, legacy_value)
            shadow_norm = _normalize_for_compare(field_name, shadow_value)
            if not legacy_norm or not shadow_norm:
                statuses[field_name] = COMPARISON_NORMALIZATION_UNAVAILABLE
            elif legacy_norm == shadow_norm:
                statuses[field_name] = COMPARISON_SAME
            else:
                statuses[field_name] = COMPARISON_DIFFERENT
    return statuses


def _sanitize_triage(triage, include_file_name=False, include_file_hash=False):
    triage = triage if isinstance(triage, dict) else {}
    return {
        "pdf_type": _text(triage.get("pdf_type")),
        "page_count": _safe_int(triage.get("page_count")),
        "native_text_available": _safe_bool(triage.get("native_text_available")),
        "native_text_token_count": _safe_int(triage.get("native_text_token_count")),
        "native_text_density_by_page": [
            _safe_int(value)
            for value in triage.get("native_text_density_by_page", []) or []
        ],
        "image_coverage_by_page": [
            float(value or 0.0)
            for value in triage.get("image_coverage_by_page", []) or []
        ],
        "ocr_required": _safe_bool(triage.get("ocr_required")),
        "routing_decision": _text(triage.get("routing_decision")),
        "quality_flags": _safe_list(triage.get("quality_flags")),
        "file_name": _text(triage.get("file_name")) if include_file_name else "",
        "file_hash": _text(triage.get("file_hash"))[:16] if include_file_hash else "",
    }


def _artifact_summary(debug):
    summary = (debug or {}).get("artifact_summary", {}) or {}
    layout_summary = summary.get("layout_provider_summary", {}) or {}
    return {
        "source": _text(summary.get("source")),
        "page_count": _safe_int(summary.get("page_count")),
        "line_count": _safe_int(summary.get("line_count")),
        "word_count": _safe_int(summary.get("word_count")),
        "table_count": _safe_int(summary.get("table_count")),
        "full_text_length": _safe_int(summary.get("full_text_length")),
        "full_text_present": _safe_bool(summary.get("full_text_present")),
        "layout_provider_summary": {
            "provider_requested": _text(layout_summary.get("provider_requested")),
            "provider_used": _text(layout_summary.get("provider_used")),
            "available": _safe_bool(layout_summary.get("available")),
            "status": _text(layout_summary.get("status")),
            "pages_with_words": _safe_int(layout_summary.get("pages_with_words")),
            "pages_with_lines": _safe_int(layout_summary.get("pages_with_lines")),
            "pages_with_tables": _safe_int(layout_summary.get("pages_with_tables")),
            "word_count": _safe_int(layout_summary.get("word_count")),
            "line_count": _safe_int(layout_summary.get("line_count")),
            "table_count": _safe_int(layout_summary.get("table_count")),
            "table_cell_count": _safe_int(layout_summary.get("table_cell_count")),
            "table_settings_profile": _text(layout_summary.get("table_settings_profile")),
            "warnings": _safe_list(layout_summary.get("warnings")),
            "errors": _safe_list(layout_summary.get("errors")),
        },
    }


def _candidate_value_shape(candidate):
    shape = value_shape((candidate or {}).get("value"))
    return {
        "length_bucket": shape.get("length_bucket", ""),
        "has_digits": bool(shape.get("has_digits")),
        "has_letters": bool(shape.get("has_letters")),
        "has_currency_symbol": bool(shape.get("has_currency_symbol")),
        "looks_like_date": bool(shape.get("looks_like_date")),
        "looks_like_money": bool(shape.get("looks_like_money")),
        "is_structured": bool(shape.get("is_structured")),
    }


def build_candidate_summary(candidates, generator_summaries=None):
    by_field = Counter()
    by_source = Counter()
    by_generator = Counter()
    independent_by_field = Counter()
    fallback_by_field = Counter()
    mapped_by_strength = Counter()
    unmapped_raw_fields = Counter()
    raw_fields_by_generator = defaultdict(Counter)
    canonical_fields_by_generator = defaultdict(Counter)
    raw_to_canonical = {}
    critical_by_strength = defaultdict(Counter)
    independent_critical_by_strength = defaultdict(Counter)
    fallback_critical_by_strength = defaultdict(Counter)
    value_shape_by_raw = defaultdict(Counter)
    evidence_counts = Counter()
    label_counts = Counter()
    confidence_counts = Counter()
    structured_stop_by_field = Counter()
    partial_stop_by_field = Counter()
    quality_by_field = defaultdict(Counter)
    quality_reasons = defaultdict(Counter)
    duplicate_identities = Counter()
    seen_identities = set()
    independent_fields = set()
    fallback_fields = set()
    independent_count = 0
    fallback_count = 0
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        field_name = _text(candidate.get("field"))
        source = _text(candidate.get("source")) or "unknown"
        metadata = candidate.get("metadata") or {}
        identity = (
            field_name,
            _text(candidate.get("normalized_value") or candidate.get("value")).lower(),
            _text(candidate.get("source")),
            _text(candidate.get("parser_name")),
            _text(metadata.get("table_index")),
            _text(metadata.get("row_index")),
            _text(metadata.get("pairing_method")),
        )
        if identity in seen_identities:
            duplicate_identities[identity] += 1
        else:
            seen_identities.add(identity)
        generator = _text(metadata.get("generator_name")) or _text(candidate.get("parser_name")) or "unknown"
        raw_field = _text(metadata.get("raw_field")) or field_name or "unknown"
        strength = _text(metadata.get("canonical_mapping_strength")) or MAPPING_UNMAPPED
        raw_fields_by_generator[generator][raw_field] += 1
        if field_name:
            canonical_fields_by_generator[generator][field_name] += 1
        mapped_by_strength[strength] += 1
        raw_to_canonical.setdefault(
            raw_field,
            {
                "canonical_field": field_name,
                "strength": strength,
                "count": 0,
            },
        )
        raw_to_canonical[raw_field]["count"] += 1
        if strength == MAPPING_UNMAPPED:
            unmapped_raw_fields[raw_field] += 1
        shape = _candidate_value_shape(candidate)
        value_shape_by_raw[raw_field][f"length_bucket:{shape['length_bucket']}"] += 1
        for key in [
            "has_digits",
            "has_letters",
            "has_currency_symbol",
            "looks_like_date",
            "looks_like_money",
            "is_structured",
        ]:
            if shape[key]:
                value_shape_by_raw[raw_field][key] += 1
        if _text(candidate.get("evidence_text")):
            evidence_counts[raw_field] += 1
        if _text(candidate.get("label")):
            label_counts[raw_field] += 1
        if float(candidate.get("confidence") or 0.0) > 0:
            confidence_counts[raw_field] += 1
        if metadata.get("structured_stop_candidate"):
            structured_stop_by_field[field_name] += 1
        elif metadata.get("stop_candidate_kind") in {"partial_count", "count"} or field_name in {
            FIELD_PICKUP_DATE,
            FIELD_DELIVERY_DATE,
            "pickup_location",
            "delivery_location",
        }:
            partial_stop_by_field[field_name] += 1
        diagnostic_fallback = bool(metadata.get("diagnostic_fallback")) or bool(
            metadata.get("not_independent_candidate")
        )
        if field_name:
            by_field[field_name] += 1
            if field_name in SHADOW_CANDIDATE_COVERAGE_FIELDS:
                critical_by_strength[field_name][strength] += 1
            if diagnostic_fallback:
                fallback_by_field[field_name] += 1
                if field_name in SHADOW_CANDIDATE_COVERAGE_FIELDS:
                    fallback_critical_by_strength[field_name][strength] += 1
                fallback_fields.add(field_name)
            else:
                independent_by_field[field_name] += 1
                if field_name in SHADOW_CANDIDATE_COVERAGE_FIELDS:
                    independent_critical_by_strength[field_name][strength] += 1
                independent_fields.add(field_name)
        by_source[source] += 1
        by_generator[generator] += 1
        if diagnostic_fallback:
            fallback_count += 1
        else:
            independent_count += 1
        if field_name in SHADOW_CANDIDATE_COVERAGE_FIELDS:
            confidence = float(candidate.get("confidence") or 0.0)
            if diagnostic_fallback:
                quality_by_field[field_name]["legacy_fallback_candidates"] += 1
            elif confidence >= 0.80:
                quality_by_field[field_name]["high_quality_independent_candidates"] += 1
            elif confidence >= 0.60:
                quality_by_field[field_name]["medium_quality_independent_candidates"] += 1
            else:
                quality_by_field[field_name]["weak_or_ambiguous_candidates"] += 1
            if metadata.get("structured_stop_candidate"):
                if metadata.get("ambiguous_stop_candidate"):
                    quality_by_field[field_name]["ambiguous_structured_stop_candidates"] += 1
                    quality_reasons[field_name]["ambiguous_structured_stop"] += 1
                elif metadata.get("partial_stop_candidate"):
                    quality_by_field[field_name]["partial_structured_stop_candidates"] += 1
                    quality_reasons[field_name]["partial_structured_stop"] += 1
                else:
                    quality_by_field[field_name]["complete_structured_stop_candidates"] += 1
                    quality_reasons[field_name]["complete_structured_stop"] += 1
            if metadata.get("table_cell_candidate"):
                quality_reasons[field_name]["table_cell_candidate"] += 1

    fields_with_legacy_only = sorted(
        field for field in fallback_fields if field not in independent_fields
    )
    only_weak = {}
    only_legacy = {}
    high_quality = {}
    for field_name, counts in quality_by_field.items():
        high_quality[field_name] = counts.get("high_quality_independent_candidates", 0)
        if (
            counts.get("weak_or_ambiguous_candidates", 0) > 0
            and counts.get("high_quality_independent_candidates", 0) == 0
            and counts.get("medium_quality_independent_candidates", 0) == 0
        ):
            only_weak[field_name] = counts.get("weak_or_ambiguous_candidates", 0)
        if (
            counts.get("legacy_fallback_candidates", 0) > 0
            and sum(
                counts.get(key, 0)
                for key in [
                    "high_quality_independent_candidates",
                    "medium_quality_independent_candidates",
                    "weak_or_ambiguous_candidates",
                ]
            )
            == 0
        ):
            only_legacy[field_name] = counts.get("legacy_fallback_candidates", 0)
    raw_mapping_rows = [
        {
            "raw_field": raw_field,
            "canonical_field": details.get("canonical_field", ""),
            "strength": details.get("strength", MAPPING_UNMAPPED),
            "count": details.get("count", 0),
            "has_evidence_count": evidence_counts.get(raw_field, 0),
            "has_label_count": label_counts.get(raw_field, 0),
            "has_confidence_count": confidence_counts.get(raw_field, 0),
            "value_shape_counts": dict(value_shape_by_raw.get(raw_field, {})),
        }
        for raw_field, details in sorted(
            raw_to_canonical.items(),
            key=lambda item: (-_safe_int(item[1].get("count")), item[0]),
        )
    ][:50]
    stop_assembly_summary = {
        "stop_evidence_count": 0,
        "stop_evidence_by_role": {},
        "stop_evidence_by_type": {},
        "assembled_pickup_stop_candidate_count": 0,
        "assembled_delivery_stop_candidate_count": 0,
        "docs_with_assembled_pickup_stops": 0,
        "docs_with_assembled_delivery_stops": 0,
        "partial_stop_candidate_count": 0,
        "ambiguous_stop_candidate_count": 0,
    }
    load_identity_line_summary = {
        "lines_scanned": 0,
        "label_hits": 0,
        "emitted_candidates": 0,
        "skipped_by_reason": {},
        "emitted_by_method": {},
    }
    load_identity_forensics = {
        "label_hits": 0,
        "emitted_candidates": 0,
        "hit_type_counts": {},
        "rejection_reason_counts": {},
        "method_attempt_counts": {},
        "method_success_counts": {},
        "value_shape_counts": {},
        "docs_with_label_hits": 0,
        "docs_with_emitted_load_candidates": 0,
        "label_hit_records": [],
    }
    stop_proximity_summary = {
        "docs_with_proximity_clusters": 0,
        "proximity_cluster_count": 0,
        "ambiguous_cluster_count": 0,
        "clusters_with_location_and_date": 0,
        "clusters_with_location_only": 0,
        "clusters_with_date_only": 0,
        "ambiguity_reason_counts": {},
    }
    table_extraction_summary = {
        "docs_with_tables": 0,
        "tables_detected": 0,
        "tables_with_stop_like_headers": 0,
        "tables_with_rate_like_headers": 0,
        "tables_with_load_like_headers": 0,
        "recognized_stop_tables": 0,
        "recognized_load_tables": 0,
        "recognized_rate_tables": 0,
        "unrecognized_tables": 0,
        "table_header_role_counts": {},
        "table_row_role_counts": {},
        "table_rows_with_stop_role": 0,
        "table_rows_with_date_time_location": 0,
    }
    layout_load_pairing_summary = {
        "layout_label_hits": 0,
        "same_row_pairings": 0,
        "nearby_row_pairings": 0,
        "table_cell_pairings": 0,
        "header_block_pairings": 0,
        "layout_candidates_emitted": 0,
        "layout_rejection_reason_counts": {},
        "table_pairings_by_method": {},
        "table_load_label_hits": 0,
        "docs_with_table_load_candidates": 0,
    }
    layout_stop_pairing_summary = {
        "layout_stop_evidence_count": 0,
        "layout_structured_stop_candidates": 0,
        "table_row_stop_candidates": 0,
        "bbox_cluster_stop_candidates": 0,
        "table_stop_candidates_complete": 0,
        "table_stop_candidates_partial": 0,
        "table_stop_candidates_ambiguous": 0,
        "table_pairings_by_method": {},
        "layout_ambiguity_reason_counts": {},
    }
    for generator_summary in generator_summaries or []:
        generator_name = _text((generator_summary or {}).get("generator_name"))
        diagnostics = (generator_summary or {}).get("diagnostics", {}) or {}
        if generator_name == "stop_evidence_assembler":
            stop_assembly_summary["stop_evidence_count"] += _safe_int(
                diagnostics.get("stop_evidence_count")
            )
            for role, count in (diagnostics.get("stop_evidence_by_role", {}) or {}).items():
                stop_assembly_summary["stop_evidence_by_role"][role] = (
                    _safe_int(stop_assembly_summary["stop_evidence_by_role"].get(role))
                    + _safe_int(count)
                )
            for evidence_type, count in (
                diagnostics.get("stop_evidence_by_type", {}) or {}
            ).items():
                stop_assembly_summary["stop_evidence_by_type"][evidence_type] = (
                    _safe_int(
                        stop_assembly_summary["stop_evidence_by_type"].get(evidence_type)
                    )
                    + _safe_int(count)
                )
            pickup_count = _safe_int(
                diagnostics.get("assembled_pickup_stop_candidate_count")
            )
            delivery_count = _safe_int(
                diagnostics.get("assembled_delivery_stop_candidate_count")
            )
            stop_assembly_summary[
                "assembled_pickup_stop_candidate_count"
            ] += pickup_count
            stop_assembly_summary[
                "assembled_delivery_stop_candidate_count"
            ] += delivery_count
            stop_assembly_summary["docs_with_assembled_pickup_stops"] += (
                1 if pickup_count > 0 else 0
            )
            stop_assembly_summary["docs_with_assembled_delivery_stops"] += (
                1 if delivery_count > 0 else 0
            )
            stop_assembly_summary["partial_stop_candidate_count"] += _safe_int(
                diagnostics.get("partial_stop_candidate_count")
            )
            stop_assembly_summary["ambiguous_stop_candidate_count"] += _safe_int(
                diagnostics.get("ambiguous_stop_candidate_count")
            )
            proximity = diagnostics.get("stop_proximity_summary", {}) or {}
            stop_proximity_summary["docs_with_proximity_clusters"] += _safe_int(
                proximity.get("docs_with_proximity_clusters")
            )
            stop_proximity_summary["proximity_cluster_count"] += _safe_int(
                proximity.get("proximity_cluster_count")
            )
            stop_proximity_summary["ambiguous_cluster_count"] += _safe_int(
                proximity.get("ambiguous_cluster_count")
            )
            stop_proximity_summary["clusters_with_location_and_date"] += _safe_int(
                proximity.get("clusters_with_location_and_date")
            )
            stop_proximity_summary["clusters_with_location_only"] += _safe_int(
                proximity.get("clusters_with_location_only")
            )
            stop_proximity_summary["clusters_with_date_only"] += _safe_int(
                proximity.get("clusters_with_date_only")
            )
            for reason, count in (proximity.get("ambiguity_reason_counts", {}) or {}).items():
                stop_proximity_summary["ambiguity_reason_counts"][reason] = (
                    _safe_int(stop_proximity_summary["ambiguity_reason_counts"].get(reason))
                    + _safe_int(count)
                )
        if generator_name == "load_identifier_line_candidate_generator":
            load_identity_line_summary["lines_scanned"] += _safe_int(
                diagnostics.get("lines_scanned_count")
            )
            load_identity_line_summary["label_hits"] += _safe_int(
                diagnostics.get("label_hits_count")
            )
            load_identity_line_summary["emitted_candidates"] += _safe_int(
                diagnostics.get("candidates_emitted_count")
            )
            for reason, count in (
                diagnostics.get("skipped_reason_counts", {}) or {}
            ).items():
                load_identity_line_summary["skipped_by_reason"][reason] = (
                    _safe_int(load_identity_line_summary["skipped_by_reason"].get(reason))
                    + _safe_int(count)
                )
            for method, count in (diagnostics.get("emitted_by_method", {}) or {}).items():
                load_identity_line_summary["emitted_by_method"][method] = (
                    _safe_int(load_identity_line_summary["emitted_by_method"].get(method))
                    + _safe_int(count)
                )
            forensic = diagnostics.get("load_identity_forensics", {}) or {}
            load_identity_forensics["label_hits"] += _safe_int(forensic.get("label_hits"))
            load_identity_forensics["emitted_candidates"] += _safe_int(
                forensic.get("emitted_candidates")
            )
            load_identity_forensics["docs_with_label_hits"] += _safe_int(
                forensic.get("docs_with_label_hits")
            )
            load_identity_forensics["docs_with_emitted_load_candidates"] += _safe_int(
                forensic.get("docs_with_emitted_load_candidates")
            )
            for key in [
                "hit_type_counts",
                "rejection_reason_counts",
                "method_attempt_counts",
                "method_success_counts",
                "value_shape_counts",
            ]:
                for item, count in (forensic.get(key, {}) or {}).items():
                    load_identity_forensics[key][item] = (
                        _safe_int(load_identity_forensics[key].get(item))
                        + _safe_int(count)
                    )
            load_identity_forensics["label_hit_records"].extend(
                forensic.get("label_hit_records", []) or []
            )
        table_summary = diagnostics.get("table_extraction_summary", {}) or {}
        if table_summary:
            table_extraction_summary["docs_with_tables"] += _safe_int(
                table_summary.get("docs_with_tables")
            )
            for key in [
                "tables_detected",
                "tables_with_stop_like_headers",
                "tables_with_rate_like_headers",
                "tables_with_load_like_headers",
                "recognized_stop_tables",
                "recognized_load_tables",
                "recognized_rate_tables",
                "unrecognized_tables",
                "table_rows_with_stop_role",
                "table_rows_with_date_time_location",
            ]:
                table_extraction_summary[key] += _safe_int(table_summary.get(key))
            for role, count in (table_summary.get("table_header_role_counts", {}) or {}).items():
                table_extraction_summary["table_header_role_counts"][role] = (
                    _safe_int(table_extraction_summary["table_header_role_counts"].get(role))
                    + _safe_int(count)
                )
            for role, count in (table_summary.get("table_row_role_counts", {}) or {}).items():
                table_extraction_summary["table_row_role_counts"][role] = (
                    _safe_int(table_extraction_summary["table_row_role_counts"].get(role))
                    + _safe_int(count)
                )
        layout_load = diagnostics.get("layout_load_pairing_summary", {}) or {}
        if layout_load:
            for key in [
                "layout_label_hits",
                "same_row_pairings",
                "nearby_row_pairings",
                "table_cell_pairings",
                "header_block_pairings",
                "layout_candidates_emitted",
                "table_load_label_hits",
                "docs_with_table_load_candidates",
            ]:
                layout_load_pairing_summary[key] += _safe_int(layout_load.get(key))
            for reason, count in (
                layout_load.get("layout_rejection_reason_counts", {}) or {}
            ).items():
                layout_load_pairing_summary["layout_rejection_reason_counts"][reason] = (
                    _safe_int(
                        layout_load_pairing_summary[
                            "layout_rejection_reason_counts"
                        ].get(reason)
                    )
                    + _safe_int(count)
                )
            for method, count in (layout_load.get("table_pairings_by_method", {}) or {}).items():
                layout_load_pairing_summary["table_pairings_by_method"][method] = (
                    _safe_int(layout_load_pairing_summary["table_pairings_by_method"].get(method))
                    + _safe_int(count)
                )
        layout_stop = diagnostics.get("layout_stop_pairing_summary", {}) or {}
        if layout_stop:
            for key in [
                "layout_stop_evidence_count",
                "layout_structured_stop_candidates",
                "table_row_stop_candidates",
                "bbox_cluster_stop_candidates",
                "table_stop_candidates_complete",
                "table_stop_candidates_partial",
                "table_stop_candidates_ambiguous",
            ]:
                layout_stop_pairing_summary[key] += _safe_int(layout_stop.get(key))
            for reason, count in (
                layout_stop.get("layout_ambiguity_reason_counts", {}) or {}
            ).items():
                layout_stop_pairing_summary["layout_ambiguity_reason_counts"][reason] = (
                    _safe_int(
                        layout_stop_pairing_summary[
                            "layout_ambiguity_reason_counts"
                        ].get(reason)
                    )
                    + _safe_int(count)
                )
            for method, count in (layout_stop.get("table_pairings_by_method", {}) or {}).items():
                layout_stop_pairing_summary["table_pairings_by_method"][method] = (
                    _safe_int(layout_stop_pairing_summary["table_pairings_by_method"].get(method))
                    + _safe_int(count)
                )
    return {
        "total_candidates": sum(by_field.values()),
        "candidates_by_field": dict(sorted(by_field.items())),
        "candidates_by_source": dict(sorted(by_source.items())),
        "candidates_by_generator": dict(sorted(by_generator.items())),
        "independent_candidate_count": independent_count,
        "legacy_final_fallback_candidate_count": fallback_count,
        "independent_candidates_by_field": dict(sorted(independent_by_field.items())),
        "legacy_final_fallback_candidates_by_field": dict(sorted(fallback_by_field.items())),
        "fields_with_independent_candidates": sorted(independent_fields),
        "fields_with_legacy_final_only_candidates": fields_with_legacy_only,
        "canonical_mapping_summary": {
            "mapped_candidate_count": sum(
                count
                for strength, count in mapped_by_strength.items()
                if strength != MAPPING_UNMAPPED
            ),
            "unmapped_candidate_count": mapped_by_strength.get(MAPPING_UNMAPPED, 0),
            "mapped_by_strength": dict(sorted(mapped_by_strength.items())),
            "unmapped_raw_fields_top": dict(unmapped_raw_fields.most_common(25)),
            "critical_field_candidates_by_mapping_strength": {
                field: dict(sorted(counter.items()))
                for field, counter in sorted(critical_by_strength.items())
            },
            "independent_critical_field_candidates_by_mapping_strength": {
                field: dict(sorted(counter.items()))
                for field, counter in sorted(independent_critical_by_strength.items())
            },
            "legacy_final_critical_field_candidates_by_mapping_strength": {
                field: dict(sorted(counter.items()))
                for field, counter in sorted(fallback_critical_by_strength.items())
            },
            "raw_field_mappings_top": raw_mapping_rows,
        },
        "candidate_taxonomy": {
            "raw_fields_by_generator": {
                generator_name: dict(counter.most_common(25))
                for generator_name, counter in sorted(raw_fields_by_generator.items())
            },
            "canonical_fields_by_generator": {
                generator_name: dict(counter.most_common(25))
                for generator_name, counter in sorted(canonical_fields_by_generator.items())
            },
            "structured_stop_candidates_by_field": dict(sorted(structured_stop_by_field.items())),
            "partial_stop_candidates_by_field": dict(sorted(partial_stop_by_field.items())),
            "generator_summaries": list(generator_summaries or []),
        },
        "stop_assembly_summary": stop_assembly_summary,
        "load_identity_line_summary": load_identity_line_summary,
        "load_identity_forensics": load_identity_forensics,
        "stop_proximity_summary": stop_proximity_summary,
        "table_extraction_summary": table_extraction_summary,
        "table_profile_summary": table_extraction_summary,
        "layout_load_pairing_summary": layout_load_pairing_summary,
        "layout_stop_pairing_summary": layout_stop_pairing_summary,
        "candidate_quality_summary": {
            "duplicate_candidates_removed": sum(duplicate_identities.values()),
            "critical_fields_with_high_quality_independent_candidates": dict(
                sorted(high_quality.items())
            ),
            "critical_fields_with_only_weak_candidates": dict(sorted(only_weak.items())),
            "critical_fields_with_only_legacy_fallback": dict(sorted(only_legacy.items())),
            "candidate_quality_by_field": {
                field: dict(sorted(counter.items()))
                for field, counter in sorted(quality_by_field.items())
            },
            "candidate_quality_reasons": {
                field: dict(sorted(counter.items()))
                for field, counter in sorted(quality_reasons.items())
            },
        },
    }


def build_layout_candidate_effectiveness(candidates, resolved_fields=None):
    resolved_fields = resolved_fields if isinstance(resolved_fields, dict) else {}
    layout_load = {
        "emitted": 0,
        "by_pairing_method": Counter(),
        "by_id_type_hint": Counter(),
        "by_confidence_band": Counter(),
        "accepted_by_resolver": 0,
        "rejected_or_not_selected": 0,
        "not_selected_reasons": Counter(),
    }
    layout_stop = {
        "emitted": 0,
        "structured": 0,
        "partial": 0,
        "by_pairing_method": Counter(),
        "with_location": 0,
        "with_date": 0,
        "with_time": 0,
        "accepted_by_resolver": 0,
        "rejected_or_not_selected": 0,
        "ambiguity_reasons": Counter(),
    }

    selected_by_field = {}
    for field_name, resolution in resolved_fields.items():
        selected = (resolution or {}).get("selected_candidate") or {}
        selected_by_field[field_name] = (
            _text(selected.get("parser_name")),
            _text(selected.get("normalized_value") or selected.get("value")),
        )

    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        metadata = candidate.get("metadata") or {}
        parser = _text(candidate.get("parser_name"))
        field_name = _text(candidate.get("field"))
        value = _text(candidate.get("normalized_value") or candidate.get("value"))
        confidence = float(candidate.get("confidence") or 0.0)
        band = "high" if confidence >= 0.80 else "medium" if confidence >= 0.60 else "low"
        selected = selected_by_field.get(field_name) == (parser, value)
        if parser == "layout_load_identity_pairing_generator":
            layout_load["emitted"] += 1
            layout_load["by_pairing_method"][_text(metadata.get("pairing_method")) or "unknown"] += 1
            layout_load["by_id_type_hint"][_text(metadata.get("id_type_hint")) or "unknown"] += 1
            layout_load["by_confidence_band"][band] += 1
            if selected:
                layout_load["accepted_by_resolver"] += 1
            else:
                layout_load["rejected_or_not_selected"] += 1
                layout_load["not_selected_reasons"]["not_selected_by_resolver"] += 1
        if parser == "layout_stop_table_candidate_generator":
            layout_stop["emitted"] += 1
            layout_stop["by_pairing_method"][_text(metadata.get("pairing_method")) or "unknown"] += 1
            if metadata.get("structured_stop_candidate"):
                layout_stop["structured"] += 1
            if metadata.get("partial_stop_candidate"):
                layout_stop["partial"] += 1
            if metadata.get("has_location"):
                layout_stop["with_location"] += 1
            if metadata.get("has_date"):
                layout_stop["with_date"] += 1
            if metadata.get("has_time"):
                layout_stop["with_time"] += 1
            if selected:
                layout_stop["accepted_by_resolver"] += 1
            else:
                layout_stop["rejected_or_not_selected"] += 1
            if metadata.get("ambiguous_stop_candidate"):
                layout_stop["ambiguity_reasons"]["ambiguous_stop_candidate"] += 1
            if metadata.get("partial_stop_candidate"):
                layout_stop["ambiguity_reasons"]["partial_stop_candidate"] += 1

    def _finalize(payload):
        return {
            key: dict(value.most_common()) if isinstance(value, Counter) else value
            for key, value in payload.items()
        }

    return {
        "layout_load_candidates": _finalize(layout_load),
        "layout_stop_candidates": _finalize(layout_stop),
    }


def _quality_band_counts(trace):
    return (trace or {}).get("candidates_by_quality_band", {}) or {}


def _not_selected_reasons(trace):
    reasons = Counter()
    for item in (trace or {}).get("top_rejected_or_not_selected", []) or []:
        reason = _text(item.get("reason")) or "unknown"
        reasons[reason] += 1
    return reasons


def _trace_selected(trace):
    return bool((trace or {}).get("selected_candidate"))


def _trace_has_high_quality(trace):
    return _safe_int(_quality_band_counts(trace).get("high")) > 0


def _trace_has_medium_quality(trace):
    return _safe_int(_quality_band_counts(trace).get("medium")) > 0


def _trace_only_weak(trace):
    counts = _quality_band_counts(trace)
    return (
        _safe_int(counts.get("weak")) > 0
        and _safe_int(counts.get("high")) == 0
        and _safe_int(counts.get("medium")) == 0
        and _safe_int(counts.get("fallback")) == 0
    )


def _trace_only_fallback(trace):
    counts = _quality_band_counts(trace)
    return (
        _safe_int(counts.get("fallback")) > 0
        and _safe_int(counts.get("high")) == 0
        and _safe_int(counts.get("medium")) == 0
        and _safe_int(counts.get("weak")) == 0
    )


def build_resolver_selection_summary(resolver_traces):
    resolver_traces = resolver_traces if isinstance(resolver_traces, dict) else {}
    fields = {}
    for field_name, trace in sorted(resolver_traces.items()):
        trace = trace if isinstance(trace, dict) else {}
        not_selected = _not_selected_reasons(trace)
        high_not_selected = sum(
            1
            for item in trace.get("top_rejected_or_not_selected", []) or []
            if item.get("quality_band") == "high"
        )
        fields[field_name] = {
            "candidate_count_seen": _safe_int(trace.get("candidate_count_seen")),
            "eligible_count": _safe_int(trace.get("candidate_count_eligible")),
            "ineligible_count": _safe_int(trace.get("candidate_count_ineligible")),
            "selected": _trace_selected(trace),
            "selected_quality_band": _text(
                ((trace.get("selected_candidate") or {}).get("quality_band"))
            ),
            "selected_source": _text(((trace.get("selected_candidate") or {}).get("source"))),
            "selected_parser_name": _text(
                ((trace.get("selected_candidate") or {}).get("parser_name"))
            ),
            "decision_status": _text(trace.get("decision_status")),
            "not_selected_reason_counts": dict(not_selected.most_common()),
            "high_quality_not_selected_count": high_not_selected,
            "candidates_by_quality_band": dict(_quality_band_counts(trace)),
            "candidates_by_source": dict(trace.get("candidates_by_source", {}) or {}),
            "candidates_by_parser_name": dict(
                trace.get("candidates_by_parser_name", {}) or {}
            ),
        }
    return {"fields": fields}


def build_load_number_selection_summary(resolver_traces):
    trace = (resolver_traces or {}).get(FIELD_LOAD_NUMBER, {}) or {}
    selected = trace.get("selected_candidate", {}) or {}
    not_selected = _not_selected_reasons(trace)
    return {
        "docs_with_any_load_candidates": 1
        if _safe_int(trace.get("candidate_count_seen")) > 0
        else 0,
        "docs_with_high_quality_independent_load_candidates": 1
        if _trace_has_high_quality(trace)
        else 0,
        "docs_with_medium_quality_independent_load_candidates": 1
        if _trace_has_medium_quality(trace)
        else 0,
        "docs_with_only_weak_load_candidates": 1 if _trace_only_weak(trace) else 0,
        "docs_with_only_legacy_fallback_load_candidates": 1
        if _trace_only_fallback(trace)
        else 0,
        "docs_with_selected_load_number": 1 if _trace_selected(trace) else 0,
        "docs_with_load_candidates_but_no_selection": 1
        if _safe_int(trace.get("candidate_count_seen")) > 0 and not _trace_selected(trace)
        else 0,
        "not_selected_reason_counts": dict(not_selected.most_common()),
        "selected_source_counts": {
            _text(selected.get("source")): 1
        }
        if selected and _text(selected.get("source"))
        else {},
        "selected_pairing_method_counts": {
            _text((selected.get("metadata_summary") or {}).get("pairing_method")): 1
        }
        if selected and _text((selected.get("metadata_summary") or {}).get("pairing_method"))
        else {},
    }


def _stop_candidate_flags(trace):
    flags = {
        "complete": False,
        "partial": False,
        "ambiguous": False,
        "table_row": False,
        "bbox_cluster": False,
    }
    for item in [trace.get("selected_candidate", {})] + list(
        trace.get("top_rejected_or_not_selected", []) or []
    ):
        metadata = item.get("metadata_summary", {}) or {}
        if not metadata.get("structured_stop_candidate"):
            continue
        has_location = bool(metadata.get("has_location"))
        has_datetime = bool(metadata.get("has_date") or metadata.get("has_time"))
        if has_location and has_datetime and not metadata.get("ambiguous_stop_candidate"):
            flags["complete"] = True
        elif has_location or has_datetime or metadata.get("partial_stop_candidate"):
            flags["partial"] = True
        if metadata.get("ambiguous_stop_candidate"):
            flags["ambiguous"] = True
        pairing_method = _text(metadata.get("pairing_method"))
        if pairing_method.startswith("table_"):
            flags["table_row"] = True
        if pairing_method == "bbox_cluster":
            flags["bbox_cluster"] = True
    return flags


def build_stop_selection_summary(resolver_traces):
    resolver_traces = resolver_traces if isinstance(resolver_traces, dict) else {}
    payload = {}
    for role, field_name in [("pickup", "pickup_stops"), ("delivery", "delivery_stops")]:
        trace = resolver_traces.get(field_name, {}) or {}
        flags = _stop_candidate_flags(trace)
        not_selected = _not_selected_reasons(trace)
        payload[role] = {
            "docs_with_any_candidates": 1
            if _safe_int(trace.get("candidate_count_seen")) > 0
            else 0,
            "docs_with_complete_structured_candidates": 1 if flags["complete"] else 0,
            "docs_with_partial_structured_candidates": 1 if flags["partial"] else 0,
            "docs_with_ambiguous_candidates": 1 if flags["ambiguous"] else 0,
            "docs_with_table_row_candidates": 1 if flags["table_row"] else 0,
            "docs_with_bbox_cluster_candidates": 1 if flags["bbox_cluster"] else 0,
            "docs_with_selected_candidates": 1 if _trace_selected(trace) else 0,
            "docs_with_candidates_but_no_selection": 1
            if _safe_int(trace.get("candidate_count_seen")) > 0 and not _trace_selected(trace)
            else 0,
            "not_selected_reason_counts": dict(not_selected.most_common()),
        }
    return payload


def review_gate_trace_summary(review_gate_trace):
    review_gate_trace = review_gate_trace if isinstance(review_gate_trace, dict) else {}
    status_counts = Counter()
    source_counts = Counter()
    for field_name, status in (
        review_gate_trace.get("critical_field_status", {}) or {}
    ).items():
        status_counts[f"{field_name}:{_text(status.get('status')) or 'unknown'}"] += 1
    for source, items in (review_gate_trace.get("review_reason_sources", {}) or {}).items():
        source_counts[source] += len(items or [])
    return {
        "needs_review_count": 1 if review_gate_trace.get("needs_review") else 0,
        "critical_field_status_counts": dict(status_counts.most_common()),
        "review_reason_source_counts": dict(source_counts.most_common()),
    }


def build_structured_stop_resolution_summary(resolved_fields):
    resolved_fields = resolved_fields if isinstance(resolved_fields, dict) else {}
    payload = {}
    for role, field_name in [("pickup", "pickup_stops"), ("delivery", "delivery_stops")]:
        resolution = resolved_fields.get(field_name, {}) or {}
        conflict = resolution.get("structured_stop_conflict_summary", {}) or {}
        selected_status = _text(conflict.get("selected_status") or resolution.get("selected_status"))
        structure_status = _text(resolution.get("structure_status"))
        payload[role] = {
            "docs_with_structured_candidates": 1
            if _safe_int(conflict.get("normalized_candidate_count")) > 0
            else 0,
            "docs_selected_complete": 1
            if selected_status == "selected_complete" or structure_status == "complete"
            else 0,
            "docs_selected_partial": 1
            if selected_status == "selected_useful_partial"
            or structure_status in {"useful_partial", "partial_only"}
            else 0,
            "docs_missing_after_resolution": 1
            if not _text(resolution.get("value")) and not selected_status
            else 0,
            "docs_conflict_review": 1
            if selected_status == "conflict"
            or _safe_int(conflict.get("true_conflict_count")) > 0
            else 0,
            "docs_unsupported": 1
            if structure_status == "unsupported"
            else 0,
            "duplicates_collapsed": _safe_int(conflict.get("duplicates_collapsed")),
            "true_conflicts": _safe_int(conflict.get("true_conflict_count")),
            "partial_overlaps": _safe_int(conflict.get("partial_overlap_count")),
        }
    return payload


def build_structured_stop_conflict_summary(resolved_fields):
    resolved_fields = resolved_fields if isinstance(resolved_fields, dict) else {}
    payload = {}
    for field_name in ["pickup_stops", "delivery_stops"]:
        resolution = resolved_fields.get(field_name, {}) or {}
        conflict = resolution.get("structured_stop_conflict_summary", {}) or {}
        payload[field_name] = {
            "candidate_count": _safe_int(conflict.get("candidate_count")),
            "normalized_candidate_count": _safe_int(
                conflict.get("normalized_candidate_count")
            ),
            "duplicates_collapsed": _safe_int(conflict.get("duplicates_collapsed")),
            "true_conflict_count": _safe_int(conflict.get("true_conflict_count")),
            "partial_overlap_count": _safe_int(conflict.get("partial_overlap_count")),
            "selected_status": _text(conflict.get("selected_status")),
            "conflict_type_counts": dict(conflict.get("conflict_type_counts") or {}),
            "selected_source": _text(conflict.get("selected_source")),
            "selected_pairing_method": _text(conflict.get("selected_pairing_method")),
            "selected_completeness_score": round(
                float(conflict.get("selected_completeness_score") or 0.0),
                3,
            ),
        }
    return payload


def build_rate_review_sanity_summary(resolved_fields, review_gate_trace):
    resolved_fields = resolved_fields if isinstance(resolved_fields, dict) else {}
    review_gate_trace = review_gate_trace if isinstance(review_gate_trace, dict) else {}
    rate = resolved_fields.get("total_carrier_rate", {}) or {}
    gate = (
        (review_gate_trace.get("critical_field_status", {}) or {}).get(
            "total_carrier_rate",
            {},
        )
        or {}
    )
    selected_rate = bool(_text(rate.get("value")) or rate.get("selected_candidate"))
    gate_status = _text(gate.get("status"))
    conflict = "CONFLICTING_CANDIDATES" in set(_safe_list(rate.get("review_reasons")))
    mismatch_reasons = Counter()
    if selected_rate and gate_status == "missing":
        mismatch_reasons["selected_rate_marked_missing"] += 1
    if not selected_rate and gate_status == "passed":
        mismatch_reasons["missing_rate_marked_passed"] += 1
    if gate_status == "missing" and gate_status == "low_confidence":
        mismatch_reasons["missing_low_confidence_double_count"] += 1
    return {
        "docs_with_rate_candidates": 1 if _safe_int(rate.get("candidate_count")) > 0 else 0,
        "docs_with_selected_rate": 1 if selected_rate else 0,
        "docs_marked_rate_missing": 1 if gate_status == "missing" else 0,
        "docs_marked_rate_low_confidence": 1 if gate_status == "low_confidence" else 0,
        "docs_with_rate_conflict": 1 if conflict or gate_status == "conflict" else 0,
        "rate_review_mismatch_count": sum(mismatch_reasons.values()),
        "mismatch_reasons": dict(mismatch_reasons.most_common()),
    }


def _sanitize_resolved_field(field_name, resolution, include_values=False):
    resolution = resolution if isinstance(resolution, dict) else {}
    payload = {
        "value": _text(resolution.get("value")) if include_values else "",
        "confidence": round(float(resolution.get("confidence") or 0.0), 3),
        "evidence_text": _snippet(resolution.get("evidence_text")) if include_values else "",
        "page": resolution.get("page", ""),
        "source": _text(resolution.get("source")),
        "candidate_count": _safe_int(resolution.get("candidate_count")),
        "competing_candidate_count": len(resolution.get("competing_candidates", []) or []),
        "needs_review": _safe_bool(resolution.get("needs_review")),
        "review_reasons": _safe_list(resolution.get("review_reasons")),
    }
    if field_name in {"pickup_stops", "delivery_stops"}:
        payload["structure_status"] = _text(resolution.get("structure_status"))
        payload["selected_status"] = _text(resolution.get("selected_status"))
        payload["structured_stop_summary"] = dict(
            resolution.get("structured_stop_summary") or {}
        )
        conflict = resolution.get("structured_stop_conflict_summary") or {}
        payload["structured_stop_conflict_summary"] = {
            "field": _text(conflict.get("field")),
            "candidate_count": _safe_int(conflict.get("candidate_count")),
            "normalized_candidate_count": _safe_int(
                conflict.get("normalized_candidate_count")
            ),
            "duplicates_collapsed": _safe_int(conflict.get("duplicates_collapsed")),
            "true_conflict_count": _safe_int(conflict.get("true_conflict_count")),
            "partial_overlap_count": _safe_int(conflict.get("partial_overlap_count")),
            "selected_status": _text(conflict.get("selected_status")),
            "conflict_type_counts": dict(conflict.get("conflict_type_counts") or {}),
            "selected_source": _text(conflict.get("selected_source")),
            "selected_pairing_method": _text(conflict.get("selected_pairing_method")),
            "selected_completeness_score": round(
                float(conflict.get("selected_completeness_score") or 0.0),
                3,
            ),
        }
    return payload


def _sanitize_resolved_fields(resolved_fields, include_values=False):
    return {
        field_name: _sanitize_resolved_field(
            field_name,
            resolution,
            include_values=include_values,
        )
        for field_name, resolution in sorted((resolved_fields or {}).items())
        if isinstance(resolution, dict)
    }


PRIVATE_EVAL_SCALAR_FIELDS = (
    FIELD_LOAD_NUMBER,
    "total_carrier_rate",
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
)

PRIVATE_EVAL_STOP_FIELDS = (FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS)


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return _text(value)


def _metadata_eval_summary(metadata):
    metadata = metadata if isinstance(metadata, dict) else {}
    safe_keys = [
        "id_type_hint",
        "label_strength",
        "canonical_mapping_strength",
        "money_context",
        "is_total_rate_candidate",
        "diagnostic_fallback",
        "not_independent_candidate",
        "independent_candidate",
        "layout_provider",
        "pairing_method",
        "layout_table_pairing_method",
        "table_cell_candidate",
        "table_index",
        "row_index",
        "stop_role",
        "structured_stop_candidate",
        "partial_stop_candidate",
        "ambiguous_stop_candidate",
        "has_location",
        "has_date",
        "has_time",
        "has_facility",
        "has_address",
        "structure_status",
        "stop_structure_status",
    ]
    return {key: _json_safe(metadata.get(key)) for key in safe_keys if key in metadata}


def _has_real_stop_component(stop):
    if not isinstance(stop, dict):
        return False
    for key in ["facility", "address", "city", "state", "zip", "date", "time", "appointment_window"]:
        value = _text(stop.get(key))
        if value and value != "__present__":
            return True
    return False


def _private_stop_prediction(value, field_name, confidence=0.0, source="", parser_name="", metadata=None):
    metadata = metadata if isinstance(metadata, dict) else {}
    normalized = normalize_stop_candidate_value(value, field_name, metadata)
    stops = [
        {
            "role": _text(stop.get("role")),
            "stop_index": stop.get("stop_index") or 1,
            "facility": _text(stop.get("facility")),
            "address": _text(stop.get("address")),
            "city": _text(stop.get("city")),
            "state": _text(stop.get("state")),
            "zip": _text(stop.get("zip")),
            "date": _text(stop.get("date")),
            "time": _text(stop.get("time")),
            "appointment_window": _text(stop.get("appointment_window")),
            "confidence": round(float(confidence or 0.0), 3),
            "source": _text(source),
            "structure_status": _text(normalized.get("structure_status")),
        }
        for stop in normalized.get("stops", []) or []
        if isinstance(stop, dict)
    ]
    payload = {
        "value": stops if any(_has_real_stop_component(stop) for stop in stops) else "",
        "confidence": round(float(confidence or 0.0), 3),
        "source": _text(source),
        "parser_name": _text(parser_name),
        "structure_status": _text(normalized.get("structure_status")),
        "component_values_serialized": bool(any(_has_real_stop_component(stop) for stop in stops)),
        "metadata_summary": _metadata_eval_summary(metadata),
    }
    if stops and not payload["component_values_serialized"]:
        payload["source_status"] = "shadow_component_not_serialized"
    return payload


def _candidate_eval_prediction(candidate, field_name):
    candidate = candidate if isinstance(candidate, dict) else {}
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
    confidence = round(float(candidate.get("confidence") or 0.0), 3)
    source = _text(candidate.get("source"))
    parser_name = _text(candidate.get("parser_name"))
    value = candidate.get("value")
    if field_name in PRIVATE_EVAL_STOP_FIELDS:
        return _private_stop_prediction(
            value,
            field_name,
            confidence=confidence,
            source=source,
            parser_name=parser_name,
            metadata=metadata,
        )
    return {
        "value": _json_safe(value),
        "normalized_value": _json_safe(candidate.get("normalized_value")),
        "confidence": confidence,
        "source": source,
        "parser_name": parser_name,
        "label": _text(candidate.get("label")),
        "value_shape": value_shape(value),
        "metadata_summary": _metadata_eval_summary(metadata),
    }


def _resolved_eval_prediction(resolution, field_name):
    resolution = resolution if isinstance(resolution, dict) else {}
    selected = resolution.get("selected_candidate") if isinstance(resolution.get("selected_candidate"), dict) else {}
    metadata = selected.get("metadata") if isinstance(selected.get("metadata"), dict) else {}
    confidence = round(float(resolution.get("confidence") or selected.get("confidence") or 0.0), 3)
    source = _text(selected.get("source") or resolution.get("source"))
    parser_name = _text(selected.get("parser_name"))
    if field_name in PRIVATE_EVAL_STOP_FIELDS:
        value = selected.get("value") if selected else resolution.get("value")
        return _private_stop_prediction(
            value,
            field_name,
            confidence=confidence,
            source=source,
            parser_name=parser_name,
            metadata=metadata,
        )
    value = resolution.get("value")
    if value in ["", None] and selected:
        value = selected.get("value")
    return {
        "value": _json_safe(value),
        "normalized_value": _json_safe(selected.get("normalized_value")),
        "confidence": confidence,
        "source": source,
        "parser_name": parser_name,
        "label": _text(selected.get("label")),
        "value_shape": value_shape(value),
        "metadata_summary": _metadata_eval_summary(metadata),
    }


def _candidate_field(candidate):
    field_name = _text((candidate or {}).get("field"))
    if field_name == FIELD_RATE:
        return "total_carrier_rate"
    return field_name


def _candidate_is_layout(candidate):
    metadata = (candidate or {}).get("metadata") if isinstance((candidate or {}).get("metadata"), dict) else {}
    source = _text((candidate or {}).get("source")).lower()
    parser_name = _text((candidate or {}).get("parser_name")).lower()
    return (
        "layout" in source
        or "layout" in parser_name
        or bool(metadata.get("layout_provider"))
        or bool(metadata.get("table_cell_candidate"))
        or _text(metadata.get("pairing_method")).startswith("table_")
    )


def _candidate_is_fallback(candidate):
    metadata = (candidate or {}).get("metadata") if isinstance((candidate or {}).get("metadata"), dict) else {}
    return bool(metadata.get("diagnostic_fallback") or metadata.get("not_independent_candidate"))


def _candidate_rank(candidate):
    metadata = (candidate or {}).get("metadata") if isinstance((candidate or {}).get("metadata"), dict) else {}
    score = float((candidate or {}).get("confidence") or 0.0)
    if _candidate_is_layout(candidate):
        score += 0.03
    if _text(metadata.get("canonical_mapping_strength")) == "strong":
        score += 0.02
    if metadata.get("structured_stop_candidate") and metadata.get("has_location") and (
        metadata.get("has_date") or metadata.get("has_time")
    ):
        score += 0.04
    if _candidate_is_fallback(candidate):
        score -= 0.08
    return score


def _best_candidate(candidates, field_name, predicate=None):
    field_candidates = [
        candidate
        for candidate in candidates or []
        if isinstance(candidate, dict)
        and _candidate_field(candidate) == field_name
        and (predicate(candidate) if predicate else True)
    ]
    if not field_candidates:
        return None
    return sorted(field_candidates, key=_candidate_rank, reverse=True)[0]


def _stops_from_private_stop_set(stop_set, role):
    stop_set = stop_set if isinstance(stop_set, dict) else {}
    stops = []
    for index, stop in enumerate(stop_set.get("stops", []) or [], start=1):
        if not isinstance(stop, dict) or _text(stop.get("stop_type")) != role:
            continue
        fields = {
            _text(item.get("field_name")): item
            for item in stop.get("fields", []) or []
            if isinstance(item, dict)
        }
        # Normalized legacy stops usually contain field status/provenance, not
        # private component values. Preserve real values only if a local debug
        # source already put them there.
        def field_value(*names):
            for name in names:
                item = fields.get(name)
                if isinstance(item, dict):
                    value = item.get("value") or item.get("selected_value") or item.get("raw_value")
                    if _text(value):
                        return _text(value)
            return ""

        stops.append(
            {
                "role": role,
                "stop_index": stop.get("sequence") or index,
                "facility": field_value("facility_name"),
                "address": field_value("address"),
                "city": field_value("city", "city_state", "location"),
                "state": field_value("state"),
                "zip": field_value("zip"),
                "date": field_value("date"),
                "time": field_value("time"),
                "appointment_window": field_value("appointment_window"),
                "confidence": round(float(stop.get("confidence") or 0.0), 3),
                "source": "legacy_normalized_stop_set",
                "structure_status": "legacy_normalized_stop",
            }
        )
    return stops


def _legacy_eval_predictions(legacy_summary=None, private_eval_context=None):
    legacy_summary = legacy_summary if isinstance(legacy_summary, dict) else {}
    private_eval_context = private_eval_context if isinstance(private_eval_context, dict) else {}
    comparison = legacy_summary.get("_comparison_values", {}) or {}
    payload = {}
    for field_name in PRIVATE_EVAL_SCALAR_FIELDS:
        value = comparison.get(field_name, legacy_summary.get(field_name, ""))
        if _text(value):
            payload[field_name] = {
                "value": _json_safe(value),
                "confidence": None,
                "source": "legacy_measurement_resolution",
            }
        else:
            payload[field_name] = {
                "value": "",
                "confidence": None,
                "source_status": "legacy_extractor_missing",
            }
    stop_set = private_eval_context.get("normalized_stop_set", {}) or {}
    for field_name, role, count_key in [
        (FIELD_PICKUP_STOPS, "pickup", "pickup_count"),
        (FIELD_DELIVERY_STOPS, "delivery", "delivery_count"),
    ]:
        stops = _stops_from_private_stop_set(stop_set, role)
        if any(_has_real_stop_component(stop) for stop in stops):
            payload[field_name] = {
                "value": stops,
                "confidence": None,
                "source": "legacy_normalized_stop_set",
                "component_values_serialized": True,
            }
        elif _safe_int(legacy_summary.get(count_key) or comparison.get(count_key)) > 0:
            payload[field_name] = {
                "value": "",
                "confidence": None,
                "source_status": "legacy_field_not_serialized",
            }
        else:
            payload[field_name] = {
                "value": "",
                "confidence": None,
                "source_status": "legacy_extractor_missing",
            }
    return payload


def build_private_eval_values(raw_resolved=None, candidates=None, legacy_summary=None, private_eval_context=None):
    raw_resolved = raw_resolved if isinstance(raw_resolved, dict) else {}
    candidates = [candidate for candidate in candidates or [] if isinstance(candidate, dict)]
    payload = {
        "schema_version": "ratecon_private_eval_values_v1",
        "legacy_selected": _legacy_eval_predictions(
            legacy_summary=legacy_summary,
            private_eval_context=private_eval_context,
        ),
        "shadow_selected": {},
        "shadow_candidate_best": {},
        "shadow_best_independent_candidate": {},
        "shadow_best_layout_candidate": {},
        "legacy_fallback_candidate": {},
        "raw_text_included": False,
        "evidence_text_included": False,
    }
    for field_name in PRIVATE_EVAL_SCALAR_FIELDS + PRIVATE_EVAL_STOP_FIELDS:
        if field_name in raw_resolved:
            payload["shadow_selected"][field_name] = _resolved_eval_prediction(
                raw_resolved.get(field_name, {}),
                field_name,
            )
        for group_name, predicate in [
            ("shadow_candidate_best", None),
            ("shadow_best_independent_candidate", lambda candidate: not _candidate_is_fallback(candidate)),
            ("shadow_best_layout_candidate", _candidate_is_layout),
            ("legacy_fallback_candidate", _candidate_is_fallback),
        ]:
            candidate = _best_candidate(candidates, field_name, predicate=predicate)
            if candidate:
                payload[group_name][field_name] = _candidate_eval_prediction(candidate, field_name)
    return payload


def _field_resolution(resolved_fields, field_name):
    return (resolved_fields or {}).get(field_name, {}) or {}


def assign_failure_attribution(
    triage=None,
    artifact_summary=None,
    candidate_summary=None,
    resolved_result=None,
    legacy_result=None,
    comparison=None,
):
    triage = triage if isinstance(triage, dict) else {}
    artifact_summary = artifact_summary if isinstance(artifact_summary, dict) else {}
    candidate_summary = candidate_summary if isinstance(candidate_summary, dict) else {}
    resolved_result = resolved_result if isinstance(resolved_result, dict) else {}
    resolved_fields = resolved_result.get("resolved_fields", {}) or {}
    comparison = comparison if isinstance(comparison, dict) else {}
    codes = []

    quality_flags = set(_safe_list(triage.get("quality_flags")))
    if not triage:
        codes.append(CODE_DOC_TRIAGE_FAILED)
    if triage.get("ocr_required"):
        codes.append(CODE_DOC_SCANNED_OR_OCR_REQUIRED)
    if "EMPTY_OR_LOW_TEXT" in quality_flags:
        codes.append(CODE_DOC_EMPTY_OR_LOW_TEXT)
    if "IMAGE_HEAVY_PAGE" in quality_flags:
        codes.append(CODE_DOC_IMAGE_HEAVY)
    if "MULTI_PAGE_DOCUMENT" in quality_flags:
        codes.append(CODE_DOC_MULTI_PAGE)
    if "NATIVE_TEXT_SUSPICIOUS" in quality_flags:
        codes.append(CODE_DOC_NATIVE_TEXT_SUSPICIOUS)

    if not artifact_summary.get("full_text_present"):
        codes.append(CODE_ARTIFACT_EMPTY)
    if _safe_int(artifact_summary.get("full_text_length")) and _safe_int(
        artifact_summary.get("full_text_length")
    ) < 80:
        codes.append(CODE_ARTIFACT_LOW_TEXT)
    if _safe_int(artifact_summary.get("line_count")) == 0:
        codes.append(CODE_ARTIFACT_NO_LINES)
        codes.append(CODE_LAYOUT_NOT_AVAILABLE)
    if _safe_int(artifact_summary.get("table_count")) == 0:
        codes.append(CODE_TABLE_EXTRACTION_NOT_AVAILABLE)
    layout_provider = artifact_summary.get("layout_provider_summary", {}) or {}
    if layout_provider:
        if not layout_provider.get("available"):
            codes.append(CODE_LAYOUT_PROVIDER_UNAVAILABLE)
        if layout_provider.get("status") == "failed":
            codes.append(CODE_LAYOUT_PROVIDER_FAILED)
        if layout_provider.get("status") == "partial":
            codes.append(CODE_LAYOUT_PROVIDER_PARTIAL)
        if _safe_int(layout_provider.get("word_count")) == 0:
            codes.append(CODE_LAYOUT_WORDS_UNAVAILABLE)
        if _safe_int(layout_provider.get("line_count")) == 0:
            codes.append(CODE_LAYOUT_LINES_UNAVAILABLE)
        if _safe_int(layout_provider.get("table_count")) == 0:
            codes.append(CODE_LAYOUT_TABLES_UNAVAILABLE)

    field_counts = candidate_summary.get("candidates_by_field", {}) or {}
    if _safe_int(candidate_summary.get("total_candidates")) == 0:
        codes.append(CODE_NO_CANDIDATES)
    if _safe_int(field_counts.get(FIELD_LOAD_NUMBER)) == 0:
        codes.append(CODE_MISSING_LOAD_NUMBER_CANDIDATE)
    if _safe_int(field_counts.get("total_carrier_rate")) == 0 and _safe_int(
        field_counts.get(FIELD_RATE)
    ) == 0:
        codes.append(CODE_MISSING_TOTAL_RATE_CANDIDATE)
    if (
        _safe_int(field_counts.get("pickup_stops")) == 0
        and _safe_int(field_counts.get("pickup_location")) == 0
        and _safe_int(field_counts.get(FIELD_PICKUP_DATE)) == 0
    ):
        codes.append(CODE_MISSING_PICKUP_CANDIDATE)
    if (
        _safe_int(field_counts.get("delivery_stops")) == 0
        and _safe_int(field_counts.get("delivery_location")) == 0
        and _safe_int(field_counts.get(FIELD_DELIVERY_DATE)) == 0
    ):
        codes.append(CODE_MISSING_DELIVERY_CANDIDATE)
    stop_summary = candidate_summary.get("stop_assembly_summary", {}) or {}
    stop_evidence_count = _safe_int(stop_summary.get("stop_evidence_count"))
    assembled_stop_count = _safe_int(
        stop_summary.get("assembled_pickup_stop_candidate_count")
    ) + _safe_int(stop_summary.get("assembled_delivery_stop_candidate_count"))
    if (
        CODE_MISSING_PICKUP_CANDIDATE in codes
        or CODE_MISSING_DELIVERY_CANDIDATE in codes
    ):
        if stop_evidence_count <= 0:
            codes.append(CODE_MISSING_STOP_EVIDENCE)
        elif assembled_stop_count <= 0:
            codes.append(CODE_STOP_ASSEMBLY_FAILED)
    if _safe_int(stop_summary.get("partial_stop_candidate_count")) > 0:
        codes.append(CODE_PARTIAL_STOP_EVIDENCE_ONLY)
    if _safe_int(stop_summary.get("ambiguous_stop_candidate_count")) > 0:
        codes.append(CODE_AMBIGUOUS_STOP_ASSEMBLY)
    load_line_summary = candidate_summary.get("load_identity_line_summary", {}) or {}
    load_forensics = candidate_summary.get("load_identity_forensics", {}) or {}
    if _safe_int(field_counts.get(FIELD_LOAD_NUMBER)) == 0:
        label_hits = _safe_int(load_line_summary.get("label_hits"))
        emitted = _safe_int(load_line_summary.get("emitted_candidates"))
        skipped_by_reason = load_line_summary.get("skipped_by_reason", {}) or {}
        hit_types = load_forensics.get("hit_type_counts", {}) or {}
        rejection_counts = load_forensics.get("rejection_reason_counts", {}) or {}
        if label_hits <= 0:
            codes.append(CODE_MISSING_LOAD_LABEL_HIT)
            codes.append(CODE_LOAD_ID_FORENSIC_VALUE_ABSENT)
        elif emitted <= 0:
            no_value_count = sum(
                _safe_int(skipped_by_reason.get(reason))
                for reason in [
                    "no_value",
                    "no_value_on_same_line",
                    "adjacent_line_missing",
                ]
            )
            if no_value_count > 0:
                codes.append(CODE_LOAD_LABEL_HIT_NO_VALUE)
                codes.append(CODE_LOAD_LABEL_HIT_VALUE_NOT_NEARBY)
            else:
                codes.append(CODE_LOAD_LABEL_HIT_VALUE_REJECTED)
                codes.append(CODE_LOAD_LABEL_HIT_VALUE_SHAPE_REJECTED)
        if _safe_int(hit_types.get("columnar_value_possible")) > 0:
            codes.append(CODE_LOAD_LABEL_HIT_COLUMNAR_PAIRING_NEEDED)
            codes.append(CODE_COLUMNAR_LAYOUT_REQUIRES_COORDINATES)
        if _safe_int(hit_types.get("label_only_no_value_nearby")) > 0:
            codes.append(CODE_LOAD_ID_FORENSIC_VALUE_ABSENT)
        if _safe_int(hit_types.get("unsafe_identifier_shape")) > 0 or rejection_counts:
            codes.append(CODE_LOAD_LABEL_HIT_VALUE_SHAPE_REJECTED)
    load_strengths = (
        (candidate_summary.get("canonical_mapping_summary", {}) or {})
        .get("independent_critical_field_candidates_by_mapping_strength", {})
        .get(FIELD_LOAD_NUMBER, {})
        or {}
    )
    if (
        _safe_int(load_strengths.get("weak")) > 0
        and _safe_int(load_strengths.get("strong")) == 0
        and _safe_int(load_strengths.get("medium")) == 0
    ):
        codes.append(CODE_LOAD_ID_CANDIDATE_WEAK_ONLY)
        codes.append(CODE_LOAD_ID_ONLY_WEAK_AMBIGUOUS_CANDIDATES)
    proximity_summary = candidate_summary.get("stop_proximity_summary", {}) or {}
    ambiguity_reasons = proximity_summary.get("ambiguity_reason_counts", {}) or {}
    if _safe_int(ambiguity_reasons.get(CODE_STOP_PROXIMITY_MISSING_LINE_INDEX)) > 0:
        codes.append(CODE_STOP_PROXIMITY_MISSING_LINE_INDEX)
        codes.append(CODE_LINE_SEGMENTATION_INSUFFICIENT)
    if _safe_int(ambiguity_reasons.get(CODE_STOP_PROXIMITY_NO_LOCATION_DATE_PAIR)) > 0:
        codes.append(CODE_STOP_PROXIMITY_NO_LOCATION_DATE_PAIR)
    if _safe_int(ambiguity_reasons.get(CODE_STOP_PROXIMITY_MULTI_STOP_AMBIGUOUS)) > 0:
        codes.append(CODE_STOP_PROXIMITY_MULTI_STOP_AMBIGUOUS)
    if _safe_int(ambiguity_reasons.get(CODE_STOP_PROXIMITY_CLUSTER_PARTIAL_ONLY)) > 0:
        codes.append(CODE_STOP_PROXIMITY_CLUSTER_PARTIAL_ONLY)
    if _safe_int(proximity_summary.get("ambiguous_cluster_count")) > 0:
        codes.append(CODE_STOP_PROXIMITY_MULTI_STOP_AMBIGUOUS)
    table_summary = candidate_summary.get("table_extraction_summary", {}) or {}
    if _safe_int(table_summary.get("tables_detected")) == 0:
        codes.append(CODE_TABLE_EXTRACTION_EMPTY)
        codes.append(CODE_LAYOUT_STOP_TABLE_NOT_FOUND)
        codes.append(CODE_TABLE_PROFILE_NO_USEFUL_TABLES)
    elif _safe_int(table_summary.get("tables_with_stop_like_headers")) == 0:
        codes.append(CODE_TABLE_STOP_COLUMNS_NOT_FOUND)
    if _safe_int(table_summary.get("tables_detected")) > 0 and _safe_int(
        table_summary.get("recognized_stop_tables")
    ) == 0 and _safe_int(table_summary.get("recognized_load_tables")) == 0 and _safe_int(
        table_summary.get("recognized_rate_tables")
    ) == 0:
        codes.append(CODE_TABLE_HEADERS_UNRECOGNIZED)
    if _safe_int(table_summary.get("recognized_stop_tables")) > 0:
        header_roles = table_summary.get("table_header_role_counts", {}) or {}
        if _safe_int(header_roles.get("location")) == 0:
            codes.append(CODE_TABLE_STOP_LOCATION_COLUMN_NOT_FOUND)
        if _safe_int(header_roles.get("date")) == 0 and _safe_int(header_roles.get("time")) == 0:
            codes.append(CODE_TABLE_STOP_DATE_TIME_COLUMN_NOT_FOUND)
    if _safe_int(table_summary.get("tables_detected")) > 0 and _safe_int(
        table_summary.get("tables_with_rate_like_headers")
    ) == 0:
        codes.append(CODE_TABLE_RATE_COLUMNS_NOT_FOUND)
    layout_load = candidate_summary.get("layout_load_pairing_summary", {}) or {}
    layout_rejections = layout_load.get("layout_rejection_reason_counts", {}) or {}
    if _safe_int(layout_rejections.get(CODE_LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE)) > 0:
        codes.append(CODE_LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE)
    if _safe_int(layout_rejections.get(CODE_LAYOUT_LOAD_LABEL_NO_NEARBY_VALUE)) > 0:
        codes.append(CODE_LAYOUT_LOAD_LABEL_NO_NEARBY_VALUE)
    if _safe_int(layout_rejections.get(CODE_LAYOUT_LOAD_TABLE_PAIRING_FAILED)) > 0:
        codes.append(CODE_LAYOUT_LOAD_TABLE_PAIRING_FAILED)
    if _safe_int(layout_rejections.get(CODE_TABLE_LOAD_LABEL_FOUND_VALUE_MISSING)) > 0:
        codes.append(CODE_TABLE_LOAD_LABEL_FOUND_VALUE_MISSING)
    if _safe_int(layout_rejections.get(CODE_TABLE_LOAD_VALUE_SHAPE_REJECTED)) > 0:
        codes.append(CODE_TABLE_LOAD_VALUE_SHAPE_REJECTED)
    if any(
        _safe_int(layout_rejections.get(reason)) > 0
        for reason in [
            "candidate_failed_charset_shape",
            "candidate_looks_like_date",
            "candidate_looks_like_money",
            "candidate_looks_like_phone",
            "candidate_too_long",
            "candidate_too_short",
        ]
    ):
        codes.append(CODE_LAYOUT_LOAD_VALUE_SHAPE_REJECTED)
    layout_stop = candidate_summary.get("layout_stop_pairing_summary", {}) or {}
    layout_stop_rejections = layout_stop.get("layout_ambiguity_reason_counts", {}) or {}
    if _safe_int(layout_stop_rejections.get(CODE_LAYOUT_STOP_ROW_PAIRING_FAILED)) > 0:
        codes.append(CODE_LAYOUT_STOP_ROW_PAIRING_FAILED)
    if _safe_int(layout_stop_rejections.get(CODE_LAYOUT_STOP_ROLE_AMBIGUOUS)) > 0:
        codes.append(CODE_LAYOUT_STOP_ROLE_AMBIGUOUS)
        codes.append(CODE_TABLE_STOP_ROW_AMBIGUOUS)
    if _safe_int(layout_stop.get("table_stop_candidates_partial")) > 0:
        codes.append(CODE_TABLE_STOP_ROW_PARTIAL_ONLY)
    quality = candidate_summary.get("candidate_quality_summary", {}) or {}
    if _safe_int(quality.get("duplicate_candidates_removed")) > 0:
        codes.append(CODE_LAYOUT_CANDIDATES_DUPLICATIVE)
    only_weak = quality.get("critical_fields_with_only_weak_candidates", {}) or {}
    if _safe_int(only_weak.get(FIELD_LOAD_NUMBER)) > 0:
        codes.append(CODE_ONLY_WEAK_LOAD_ID_CANDIDATES)
    if _safe_int(only_weak.get("pickup_stops")) > 0 or _safe_int(only_weak.get("delivery_stops")) > 0:
        codes.append(CODE_ONLY_AMBIGUOUS_STOP_CANDIDATES)
    if 0 < _safe_int(candidate_summary.get("total_candidates")) < 3:
        codes.append(CODE_LOW_CANDIDATE_COVERAGE)

    resolver_selection = candidate_summary.get("resolver_selection_summary", {}) or {}
    resolver_fields = resolver_selection.get("fields", {}) or {}
    for field_name, details in resolver_fields.items():
        if _safe_int(details.get("candidate_count_seen")) > 0 and _safe_int(
            details.get("eligible_count")
        ) <= 0:
            codes.append(CODE_RESOLVER_CANDIDATE_INELIGIBLE)
            if field_name == FIELD_LOAD_NUMBER:
                codes.append(CODE_LOAD_NO_ELIGIBLE_CANDIDATES)
        if _safe_int(details.get("high_quality_not_selected_count")) > 0:
            selected = bool(details.get("selected"))
            stop_field = field_name in {"pickup_stops", "delivery_stops"}
            if not stop_field or not selected:
                codes.append(CODE_RESOLVER_INPUT_HAS_HIGH_QUALITY_CANDIDATE)
                codes.append(CODE_RESOLVER_IGNORED_HIGH_QUALITY_CANDIDATE)
            if field_name == FIELD_LOAD_NUMBER:
                codes.append(CODE_LOAD_HIGH_QUALITY_CANDIDATE_NOT_SELECTED)
            if stop_field and not selected:
                codes.append(CODE_STOP_STRUCTURED_CANDIDATE_NOT_SELECTED)
        if _safe_int(details.get("decision:no_eligible_candidates")) > 0:
            codes.append(CODE_RESOLVER_CANDIDATE_INELIGIBLE)
        if _safe_int(details.get("decision:review_required")) > 0:
            codes.append(CODE_RESOLVER_NO_DECISION)
        if _safe_int(details.get("selected_quality:fallback")) > 0:
            codes.append(CODE_RESOLVER_SELECTED_LEGACY_FALLBACK_OVER_LAYOUT)
        not_selected = details.get("not_selected_reason_counts", {}) or {}
        if _safe_int(not_selected.get("partial_only")) > 0:
            codes.append(CODE_STOP_CANDIDATES_PARTIAL_ONLY)
        if _safe_int(not_selected.get("ambiguous_role")) > 0:
            codes.append(CODE_STOP_CANDIDATES_AMBIGUOUS_ONLY)
            codes.append(CODE_RESOLVER_ALL_CANDIDATES_AMBIGUOUS)
        if _safe_int(not_selected.get("unsupported_value_type")) > 0:
            codes.append(CODE_RESOLVER_UNSUPPORTED_STRUCTURED_VALUE)
            if field_name in {"pickup_stops", "delivery_stops"}:
                codes.append(CODE_STOP_STRUCTURED_VALUE_UNSUPPORTED)
    load_selection = candidate_summary.get("load_number_selection_summary", {}) or {}
    if _safe_int(load_selection.get("docs_with_only_weak_load_candidates")) > 0:
        codes.append(CODE_LOAD_ONLY_WEAK_AMBIGUOUS_CANDIDATES)
        codes.append(CODE_RESOLVER_ALL_CANDIDATES_WEAK)
    if (
        _safe_int(load_selection.get("docs_with_any_load_candidates")) == 0
        and _safe_int(layout_load.get("layout_label_hits")) > 0
    ):
        codes.append(CODE_LOAD_MISSING_LAYOUT_LABEL_VALUE)
    stop_selection = candidate_summary.get("stop_selection_summary", {}) or {}
    for role in ["pickup", "delivery"]:
        role_summary = stop_selection.get(role, {}) or {}
        if (
            _safe_int(role_summary.get("docs_with_table_row_candidates")) > 0
            and _safe_int(role_summary.get("docs_with_selected_candidates")) == 0
        ):
            codes.append(CODE_STOP_TABLE_ROW_CANDIDATE_NOT_SELECTED)
        if (
            _safe_int(role_summary.get("docs_with_any_candidates")) > 0
            and _safe_int(role_summary.get("docs_with_complete_structured_candidates")) == 0
        ):
            codes.append(CODE_STOP_NO_COMPLETE_CANDIDATE)
        if (
            _safe_int(role_summary.get("docs_with_partial_structured_candidates")) > 0
            and _safe_int(role_summary.get("docs_with_complete_structured_candidates")) == 0
        ):
            codes.append(CODE_STOP_CANDIDATES_PARTIAL_ONLY)
        if _safe_int(role_summary.get("docs_with_ambiguous_candidates")) > 0:
            codes.append(CODE_STOP_CANDIDATES_AMBIGUOUS_ONLY)
    structured_resolution = candidate_summary.get("structured_stop_resolution_summary", {}) or {}
    for role in ["pickup", "delivery"]:
        role_summary = structured_resolution.get(role, {}) or {}
        if _safe_int(role_summary.get("docs_selected_complete")) > 0:
            codes.append(CODE_STOP_STRUCTURED_SELECTED_COMPLETE)
        if _safe_int(role_summary.get("docs_selected_partial")) > 0:
            codes.append(CODE_STOP_STRUCTURED_SELECTED_PARTIAL_REVIEW)
        if _safe_int(role_summary.get("docs_unsupported")) > 0:
            codes.append(CODE_STOP_STRUCTURED_UNSUPPORTED_VALUE)
        if _safe_int(role_summary.get("duplicates_collapsed")) > 0:
            codes.append(CODE_STOP_STRUCTURED_DUPLICATES_COLLAPSED)
        if _safe_int(role_summary.get("true_conflicts")) > 0:
            codes.append(CODE_STOP_STRUCTURED_TRUE_CONFLICT)
        if _safe_int(role_summary.get("partial_overlaps")) > 0:
            codes.append(CODE_STOP_STRUCTURED_PARTIAL_OVERLAP)
        if (
            _safe_int(role_summary.get("docs_with_structured_candidates")) > 0
            and _safe_int(role_summary.get("docs_selected_complete")) == 0
            and _safe_int(role_summary.get("docs_selected_partial")) == 0
            and _safe_int(role_summary.get("docs_conflict_review")) == 0
            and _safe_int(role_summary.get("docs_unsupported")) == 0
        ):
            codes.append(CODE_STOP_STRUCTURED_ONLY_NOISY_PARTIALS)
    structured_conflict = candidate_summary.get("structured_stop_conflict_summary", {}) or {}
    for field_name in ["pickup_stops", "delivery_stops"]:
        field_summary = structured_conflict.get(field_name, {}) or {}
        conflict_types = field_summary.get("conflict_type_counts", {}) or {}
        if _safe_int(field_summary.get("duplicates_collapsed")) > 0 and _safe_int(
            field_summary.get("true_conflict_count")
        ) == 0:
            codes.append(CODE_STOP_CONFLICT_DUPLICATE_ONLY)
        if _safe_int(conflict_types.get("date_conflict")) > 0:
            codes.append(CODE_STOP_CONFLICT_TRUE_DATE)
        if _safe_int(conflict_types.get("time_conflict")) > 0:
            codes.append(CODE_STOP_CONFLICT_TRUE_TIME)
        if _safe_int(conflict_types.get("location_conflict")) > 0:
            codes.append(CODE_STOP_CONFLICT_TRUE_LOCATION)
        if _safe_int(conflict_types.get("role_conflict")) > 0:
            codes.append(CODE_STOP_CONFLICT_TRUE_ROLE)
    gate_summary = candidate_summary.get("review_gate_trace_summary", {}) or {}
    gate_status = gate_summary.get("critical_field_status_counts", {}) or {}
    if _safe_int(gate_status.get("load_number:missing")) > 0:
        codes.append(CODE_REVIEW_GATE_LOAD_MISSING)
    if _safe_int(gate_status.get("total_carrier_rate:missing")) > 0:
        codes.append(CODE_REVIEW_GATE_RATE_MISSING)
    if (
        _safe_int(gate_status.get("pickup_stops:missing")) > 0
        or _safe_int(gate_status.get("delivery_stops:missing")) > 0
    ):
        codes.append(CODE_REVIEW_GATE_STOP_MISSING)
    if any(":low_confidence" in key for key in gate_status):
        codes.append(CODE_REVIEW_GATE_LOW_CONFIDENCE_FIELD)
    if any(":conflict" in key for key in gate_status):
        codes.append(CODE_REVIEW_GATE_CONFLICTING_FIELD)
    if (
        _safe_int(gate_status.get("pickup_stops:partial_review_required")) > 0
        or _safe_int(gate_status.get("delivery_stops:partial_review_required")) > 0
    ):
        codes.append(CODE_REVIEW_GATE_STOP_PRESENT_PARTIAL)
        codes.append(CODE_STOP_STRUCTURED_REVIEW_GATE_PARTIAL)
    if (
        _safe_int(gate_status.get("pickup_stops:conflict_review_required")) > 0
        or _safe_int(gate_status.get("delivery_stops:conflict_review_required")) > 0
    ):
        codes.append(CODE_REVIEW_GATE_STOP_PRESENT_CONFLICT)
    if (
        _safe_int(gate_status.get("pickup_stops:unsupported")) > 0
        or _safe_int(gate_status.get("delivery_stops:unsupported")) > 0
    ):
        codes.append(CODE_REVIEW_GATE_STOP_PRESENT_UNSUPPORTED)
    rate_sanity = candidate_summary.get("rate_review_sanity_summary", {}) or {}
    if _safe_int(rate_sanity.get("rate_review_mismatch_count")) > 0:
        codes.append(CODE_REVIEW_GATE_RATE_TRACE_MISMATCH)

    load_resolution = _field_resolution(resolved_fields, FIELD_LOAD_NUMBER)
    rate_resolution = _field_resolution(resolved_fields, "total_carrier_rate")
    pickup_resolution = _field_resolution(resolved_fields, "pickup_stops")
    delivery_resolution = _field_resolution(resolved_fields, "delivery_stops")
    load_reasons = set(_safe_list(load_resolution.get("review_reasons")))
    rate_reasons = set(_safe_list(rate_resolution.get("review_reasons")))
    if "CONFLICTING_CANDIDATES" in load_reasons:
        codes.append(CODE_CONFLICTING_LOAD_NUMBER_CANDIDATES)
    if "CONFLICTING_CANDIDATES" in rate_reasons:
        codes.append(CODE_CONFLICTING_TOTAL_RATE_CANDIDATES)
    if "LOW_CONFIDENCE_CRITICAL_FIELD" in load_reasons:
        codes.append(CODE_LOW_CONFIDENCE_LOAD_NUMBER)
    if "LOW_CONFIDENCE_CRITICAL_FIELD" in rate_reasons:
        codes.append(CODE_LOW_CONFIDENCE_TOTAL_RATE)
    stop_reasons = set(_safe_list(pickup_resolution.get("review_reasons"))) | set(
        _safe_list(delivery_resolution.get("review_reasons"))
    )
    if "LOW_CONFIDENCE_CRITICAL_FIELD" in stop_reasons:
        codes.append(CODE_LOW_CONFIDENCE_STOPS)
        if _text(pickup_resolution.get("value")) or _text(delivery_resolution.get("value")):
            codes.append(CODE_STOP_STRUCTURED_SELECTED_BUT_LOW_CONFIDENCE)
    if not _text(load_resolution.get("value")) or not _text(rate_resolution.get("value")):
        codes.append(CODE_RESOLVER_NO_DECISION)

    if resolved_result.get("needs_review"):
        codes.append(CODE_NEEDS_HUMAN_REVIEW)
    if any("MISSING_CRITICAL_FIELD" in reason for reason in _safe_list(resolved_result.get("review_reasons"))):
        codes.append(CODE_MISSING_CRITICAL_FIELD)

    if any(status == COMPARISON_DIFFERENT for status in comparison.values()):
        codes.append(CODE_LEGACY_SHADOW_FIELD_MISMATCH)
    if any(status == COMPARISON_LEGACY_ONLY for status in comparison.values()):
        codes.append(CODE_LEGACY_ONLY_FIELD)
    if any(status == COMPARISON_SHADOW_ONLY for status in comparison.values()):
        codes.append(CODE_SHADOW_ONLY_FIELD)
    if comparison and all(status == COMPARISON_BOTH_MISSING for status in comparison.values()):
        codes.append(CODE_LEGACY_AND_SHADOW_BOTH_MISSING)

    primary = LAYER_UNKNOWN
    if any(code in codes for code in [CODE_DOC_TRIAGE_FAILED, CODE_DOC_NOT_PDF]):
        primary = LAYER_INGESTION
    elif any(
        code in codes
        for code in [
            CODE_DOC_EMPTY_OR_LOW_TEXT,
            CODE_DOC_IMAGE_HEAVY,
            CODE_DOC_SCANNED_OR_OCR_REQUIRED,
            CODE_DOC_NATIVE_TEXT_SUSPICIOUS,
            CODE_ARTIFACT_EMPTY,
            CODE_ARTIFACT_LOW_TEXT,
            CODE_ARTIFACT_NO_LINES,
            CODE_TEXT_EXTRACTION_FAILED,
        ]
    ):
        primary = LAYER_TEXT_EXTRACTION
    elif any(
        code in codes
        for code in [
            CODE_RESOLVER_INPUT_HAS_HIGH_QUALITY_CANDIDATE,
            CODE_RESOLVER_IGNORED_HIGH_QUALITY_CANDIDATE,
            CODE_RESOLVER_CANDIDATE_INELIGIBLE,
            CODE_RESOLVER_UNSUPPORTED_STRUCTURED_VALUE,
            CODE_RESOLVER_FIELD_NOT_SUPPORTED,
            CODE_RESOLVER_SELECTED_LEGACY_FALLBACK_OVER_LAYOUT,
            CODE_LOAD_HIGH_QUALITY_CANDIDATE_NOT_SELECTED,
            CODE_LOAD_NO_ELIGIBLE_CANDIDATES,
            CODE_STOP_STRUCTURED_CANDIDATE_NOT_SELECTED,
            CODE_STOP_STRUCTURED_VALUE_UNSUPPORTED,
            CODE_STOP_TABLE_ROW_CANDIDATE_NOT_SELECTED,
            CODE_STOP_STRUCTURED_UNSUPPORTED_VALUE,
            CODE_STOP_STRUCTURED_EMPTY_AFTER_NORMALIZATION,
            CODE_STOP_STRUCTURED_TRUE_CONFLICT,
            CODE_STOP_CONFLICT_TRUE_DATE,
            CODE_STOP_CONFLICT_TRUE_TIME,
            CODE_STOP_CONFLICT_TRUE_LOCATION,
            CODE_STOP_CONFLICT_TRUE_ROLE,
        ]
    ):
        primary = LAYER_RESOLUTION
    elif any(
        code in codes
        for code in [
            CODE_STOP_STRUCTURED_SELECTED_COMPLETE,
            CODE_STOP_STRUCTURED_SELECTED_PARTIAL_REVIEW,
            CODE_STOP_STRUCTURED_SELECTED_BUT_LOW_CONFIDENCE,
            CODE_STOP_STRUCTURED_DUPLICATES_COLLAPSED,
            CODE_STOP_STRUCTURED_PARTIAL_OVERLAP,
            CODE_STOP_STRUCTURED_REVIEW_GATE_PARTIAL,
            CODE_STOP_CONFLICT_DUPLICATE_ONLY,
            CODE_REVIEW_GATE_STOP_PRESENT_PARTIAL,
            CODE_REVIEW_GATE_STOP_PRESENT_CONFLICT,
            CODE_REVIEW_GATE_STOP_PRESENT_UNSUPPORTED,
            CODE_REVIEW_GATE_RATE_TRACE_MISMATCH,
        ]
    ):
        primary = LAYER_VALIDATION
    elif any(
        code in codes
        for code in [
            CODE_NO_CANDIDATES,
            CODE_MISSING_LOAD_NUMBER_CANDIDATE,
            CODE_MISSING_TOTAL_RATE_CANDIDATE,
            CODE_MISSING_PICKUP_CANDIDATE,
            CODE_MISSING_DELIVERY_CANDIDATE,
            CODE_LOW_CANDIDATE_COVERAGE,
            CODE_MISSING_STOP_EVIDENCE,
            CODE_PARTIAL_STOP_EVIDENCE_ONLY,
            CODE_STOP_ASSEMBLY_FAILED,
            CODE_AMBIGUOUS_STOP_ASSEMBLY,
            CODE_MISSING_LOAD_LABEL_HIT,
            CODE_LOAD_LABEL_HIT_NO_VALUE,
            CODE_LOAD_LABEL_HIT_VALUE_REJECTED,
            CODE_LOAD_ID_CANDIDATE_WEAK_ONLY,
            CODE_LOAD_LABEL_HIT_VALUE_NOT_NEARBY,
            CODE_LOAD_LABEL_HIT_VALUE_SHAPE_REJECTED,
            CODE_LOAD_LABEL_HIT_COLUMNAR_PAIRING_NEEDED,
            CODE_LOAD_LABEL_HIT_SECTION_AMBIGUOUS,
            CODE_LOAD_ID_ONLY_WEAK_AMBIGUOUS_CANDIDATES,
            CODE_LOAD_ID_FORENSIC_VALUE_ABSENT,
            CODE_STOP_PROXIMITY_MISSING_LINE_INDEX,
            CODE_STOP_PROXIMITY_NO_LOCATION_DATE_PAIR,
            CODE_STOP_PROXIMITY_MULTI_STOP_AMBIGUOUS,
            CODE_STOP_PROXIMITY_SECTION_AMBIGUOUS,
            CODE_STOP_PROXIMITY_CLUSTER_PARTIAL_ONLY,
            CODE_LINE_SEGMENTATION_INSUFFICIENT,
            CODE_COLUMNAR_LAYOUT_REQUIRES_COORDINATES,
            CODE_TABLE_LAYOUT_REQUIRES_COORDINATES,
            CODE_LAYOUT_PROVIDER_UNAVAILABLE,
            CODE_LAYOUT_PROVIDER_FAILED,
            CODE_LAYOUT_PROVIDER_PARTIAL,
            CODE_LAYOUT_WORDS_UNAVAILABLE,
            CODE_LAYOUT_LINES_UNAVAILABLE,
            CODE_LAYOUT_TABLES_UNAVAILABLE,
            CODE_TABLE_EXTRACTION_EMPTY,
            CODE_TABLE_EXTRACTION_FAILED,
            CODE_TABLE_HEADERS_UNRECOGNIZED,
            CODE_TABLE_HEADER_ROW_NOT_FOUND,
            CODE_TABLE_KEY_VALUE_PATTERN_NOT_FOUND,
            CODE_TABLE_LOAD_LABEL_FOUND_VALUE_MISSING,
            CODE_TABLE_LOAD_VALUE_SHAPE_REJECTED,
            CODE_TABLE_STOP_COLUMNS_NOT_FOUND,
            CODE_TABLE_RATE_COLUMNS_NOT_FOUND,
            CODE_TABLE_STOP_ROLE_COLUMN_NOT_FOUND,
            CODE_TABLE_STOP_LOCATION_COLUMN_NOT_FOUND,
            CODE_TABLE_STOP_DATE_TIME_COLUMN_NOT_FOUND,
            CODE_TABLE_STOP_ROW_AMBIGUOUS,
            CODE_TABLE_STOP_ROW_PARTIAL_ONLY,
            CODE_LAYOUT_LOAD_LABEL_NO_RIGHT_VALUE,
            CODE_LAYOUT_LOAD_LABEL_NO_NEARBY_VALUE,
            CODE_LAYOUT_LOAD_TABLE_PAIRING_FAILED,
            CODE_LAYOUT_LOAD_VALUE_SHAPE_REJECTED,
            CODE_LAYOUT_LOAD_COORDINATES_MISSING,
            CODE_LAYOUT_STOP_TABLE_NOT_FOUND,
            CODE_LAYOUT_STOP_ROW_PAIRING_FAILED,
            CODE_LAYOUT_STOP_ROLE_AMBIGUOUS,
            CODE_LAYOUT_STOP_DATE_LOCATION_NOT_PAIRED,
            CODE_LAYOUT_STOP_COORDINATES_MISSING,
            CODE_ONLY_WEAK_LOAD_ID_CANDIDATES,
            CODE_ONLY_AMBIGUOUS_STOP_CANDIDATES,
            CODE_LAYOUT_CANDIDATES_DUPLICATIVE,
            CODE_LAYOUT_CANDIDATES_NOISY,
            CODE_TABLE_PROFILE_NO_USEFUL_TABLES,
            CODE_TABLE_PROFILE_EXTRACTION_FRAGMENTED,
            CODE_TABLE_PROFILE_CELLS_EMPTY,
            CODE_RESOLVER_ALL_CANDIDATES_WEAK,
            CODE_RESOLVER_ALL_CANDIDATES_AMBIGUOUS,
            CODE_LOAD_ONLY_WEAK_AMBIGUOUS_CANDIDATES,
            CODE_LOAD_MISSING_LAYOUT_LABEL_VALUE,
            CODE_STOP_CANDIDATES_PARTIAL_ONLY,
            CODE_STOP_CANDIDATES_AMBIGUOUS_ONLY,
            CODE_STOP_NO_COMPLETE_CANDIDATE,
            CODE_STOP_STRUCTURED_ONLY_NOISY_PARTIALS,
        ]
    ):
        primary = LAYER_CANDIDATE_GENERATION
    elif any(
        code in codes
        for code in [
            CODE_CONFLICTING_LOAD_NUMBER_CANDIDATES,
            CODE_CONFLICTING_TOTAL_RATE_CANDIDATES,
            CODE_LOW_CONFIDENCE_LOAD_NUMBER,
            CODE_LOW_CONFIDENCE_TOTAL_RATE,
            CODE_LOW_CONFIDENCE_STOPS,
            CODE_RESOLVER_NO_DECISION,
        ]
    ):
        primary = LAYER_RESOLUTION
    elif any(
        code in codes
        for code in [
            CODE_MISSING_CRITICAL_FIELD,
            CODE_NEEDS_HUMAN_REVIEW,
            CODE_VALIDATION_FAILED,
            CODE_REVIEW_GATE_LOAD_MISSING,
            CODE_REVIEW_GATE_RATE_MISSING,
            CODE_REVIEW_GATE_STOP_MISSING,
            CODE_REVIEW_GATE_LOW_CONFIDENCE_FIELD,
            CODE_REVIEW_GATE_CONFLICTING_FIELD,
            CODE_STOP_STRUCTURED_SELECTED_COMPLETE,
            CODE_STOP_STRUCTURED_SELECTED_PARTIAL_REVIEW,
            CODE_STOP_STRUCTURED_SELECTED_BUT_LOW_CONFIDENCE,
            CODE_STOP_STRUCTURED_DUPLICATES_COLLAPSED,
            CODE_STOP_STRUCTURED_PARTIAL_OVERLAP,
            CODE_STOP_STRUCTURED_REVIEW_GATE_PARTIAL,
            CODE_STOP_CONFLICT_DUPLICATE_ONLY,
            CODE_REVIEW_GATE_STOP_PRESENT_PARTIAL,
            CODE_REVIEW_GATE_STOP_PRESENT_CONFLICT,
            CODE_REVIEW_GATE_STOP_PRESENT_UNSUPPORTED,
            CODE_REVIEW_GATE_RATE_TRACE_MISMATCH,
        ]
    ):
        primary = LAYER_VALIDATION
    elif any(
        code in codes
        for code in [
            CODE_LEGACY_SHADOW_FIELD_MISMATCH,
            CODE_LEGACY_ONLY_FIELD,
            CODE_SHADOW_ONLY_FIELD,
        ]
    ):
        primary = LAYER_LEGACY_PARSER

    return {
        "codes": sorted(set(codes)),
        "primary_suspected_layer": primary,
        "details": {
            "candidate_count": _safe_int(candidate_summary.get("total_candidates")),
            "needs_review": bool(resolved_result.get("needs_review", False)),
        },
    }


def build_ratecon_shadow_audit_record(
    document_alias,
    pdf_path,
    shadow_result,
    legacy_summary=None,
    include_values=False,
    include_file_name=False,
    include_file_hash=False,
    include_private_eval_values=False,
    private_eval_context=None,
):
    debug = (shadow_result or {}).get("debug", {}) or {}
    final_output = (shadow_result or {}).get("final_output", {}) or {}
    triage = _sanitize_triage(
        debug.get("triage", {}),
        include_file_name=include_file_name,
        include_file_hash=include_file_hash,
    )
    artifact = _artifact_summary(debug)
    candidates = debug.get("candidates", []) or []
    generation_debug = debug.get("candidate_generation", {}) or {}
    candidate_summary = build_candidate_summary(
        candidates,
        generator_summaries=generation_debug.get("generator_summaries", []) or [],
    )
    candidate_summary["section_context_summary"] = (
        generation_debug.get("section_context_summary", {}) or {}
    )
    raw_resolved = debug.get("resolved_fields", {}) or {}
    resolver_traces = debug.get("resolver_decision_traces", {}) or {}
    review_gate_trace = debug.get("review_gate_trace", {}) or {}
    candidate_summary["layout_candidate_effectiveness"] = build_layout_candidate_effectiveness(
        candidates,
        resolved_fields=raw_resolved,
    )
    candidate_summary["resolver_selection_summary"] = build_resolver_selection_summary(
        resolver_traces,
    )
    candidate_summary["load_number_selection_summary"] = (
        build_load_number_selection_summary(resolver_traces)
    )
    candidate_summary["stop_selection_summary"] = build_stop_selection_summary(
        resolver_traces,
    )
    candidate_summary["review_gate_trace_summary"] = review_gate_trace_summary(
        review_gate_trace,
    )
    candidate_summary["structured_stop_resolution_summary"] = (
        build_structured_stop_resolution_summary(raw_resolved)
    )
    candidate_summary["structured_stop_conflict_summary"] = (
        build_structured_stop_conflict_summary(raw_resolved)
    )
    candidate_summary["rate_review_sanity_summary"] = build_rate_review_sanity_summary(
        raw_resolved,
        review_gate_trace,
    )
    resolved_fields = _sanitize_resolved_fields(
        raw_resolved,
        include_values=include_values,
    )
    comparison = compare_legacy_shadow(legacy_summary or {}, final_output)
    resolved_result = {
        "resolved_fields": raw_resolved,
        "needs_review": bool((shadow_result or {}).get("needs_review", True)),
        "review_reasons": _safe_list((shadow_result or {}).get("review_reasons")),
    }
    attribution = assign_failure_attribution(
        triage=triage,
        artifact_summary=artifact,
        candidate_summary=candidate_summary,
        resolved_result=resolved_result,
        legacy_result=legacy_summary,
        comparison=comparison,
    )
    file_path = Path(pdf_path or "")
    record = {
        "document_id": _text(document_alias),
        "file_name": file_path.name if include_file_name else "",
        "file_hash": triage.get("file_hash", ""),
        "legacy": _safe_legacy_summary(legacy_summary or {}),
        "shadow": {
            "success": True,
            "needs_review": bool((shadow_result or {}).get("needs_review", True)),
            "review_reasons": _safe_list((shadow_result or {}).get("review_reasons")),
            "resolved_fields": resolved_fields,
            "resolver_decision_traces": resolver_traces,
            "review_gate_trace": review_gate_trace,
        },
        "triage": triage,
        "artifact_summary": artifact,
        "candidate_summary": candidate_summary,
        "legacy_shadow_comparison": comparison,
        "failure_attribution": attribution,
        "analysis_version": RATECON_SHADOW_AUDIT_VERSION,
        "private_values_included": bool(include_values),
        "private_eval_values_included": bool(include_private_eval_values),
        "raw_text_included": False,
        "raw_text_printed": False,
    }
    if include_private_eval_values:
        record["private_eval_values"] = build_private_eval_values(
            raw_resolved=raw_resolved,
            candidates=candidates,
            legacy_summary=legacy_summary,
            private_eval_context=private_eval_context,
        )
    return record


def build_ratecon_shadow_error_record(
    document_alias,
    pdf_path,
    error,
    legacy_summary=None,
    include_file_name=False,
    include_file_hash=False,
):
    file_path = Path(pdf_path or "")
    return {
        "document_id": _text(document_alias),
        "file_name": file_path.name if include_file_name else "",
        "file_hash": "",
        "legacy": _safe_legacy_summary(legacy_summary or {}),
        "shadow": {
            "success": False,
            "needs_review": True,
            "review_reasons": [CODE_SHADOW_PIPELINE_FAILED],
            "resolved_fields": {},
            "error_type": error.__class__.__name__,
        },
        "triage": {},
        "artifact_summary": {},
        "candidate_summary": {
            "total_candidates": 0,
            "candidates_by_field": {},
            "candidates_by_source": {},
            "candidates_by_generator": {},
            "independent_candidate_count": 0,
            "legacy_final_fallback_candidate_count": 0,
            "independent_candidates_by_field": {},
            "legacy_final_fallback_candidates_by_field": {},
            "fields_with_independent_candidates": [],
            "fields_with_legacy_final_only_candidates": [],
            "canonical_mapping_summary": {
                "mapped_candidate_count": 0,
                "unmapped_candidate_count": 0,
                "mapped_by_strength": {},
                "unmapped_raw_fields_top": {},
                "critical_field_candidates_by_mapping_strength": {},
                "independent_critical_field_candidates_by_mapping_strength": {},
                "legacy_final_critical_field_candidates_by_mapping_strength": {},
                "raw_field_mappings_top": [],
            },
            "candidate_taxonomy": {
                "raw_fields_by_generator": {},
                "canonical_fields_by_generator": {},
                "structured_stop_candidates_by_field": {},
                "partial_stop_candidates_by_field": {},
                "generator_summaries": [],
            },
            "stop_assembly_summary": {
                "stop_evidence_count": 0,
                "stop_evidence_by_role": {},
                "stop_evidence_by_type": {},
                "assembled_pickup_stop_candidate_count": 0,
                "assembled_delivery_stop_candidate_count": 0,
                "docs_with_assembled_pickup_stops": 0,
                "docs_with_assembled_delivery_stops": 0,
                "partial_stop_candidate_count": 0,
                "ambiguous_stop_candidate_count": 0,
            },
            "load_identity_line_summary": {
                "lines_scanned": 0,
                "label_hits": 0,
                "emitted_candidates": 0,
                "skipped_by_reason": {},
                "emitted_by_method": {},
            },
            "load_identity_forensics": {
                "label_hits": 0,
                "emitted_candidates": 0,
                "hit_type_counts": {},
                "rejection_reason_counts": {},
                "method_attempt_counts": {},
                "method_success_counts": {},
                "value_shape_counts": {},
                "docs_with_label_hits": 0,
                "docs_with_emitted_load_candidates": 0,
                "label_hit_records": [],
            },
            "stop_proximity_summary": {
                "docs_with_proximity_clusters": 0,
                "proximity_cluster_count": 0,
                "ambiguous_cluster_count": 0,
                "clusters_with_location_and_date": 0,
                "clusters_with_location_only": 0,
                "clusters_with_date_only": 0,
                "ambiguity_reason_counts": {},
            },
            "section_context_summary": {
                "lines_with_section_context": 0,
                "section_counts": {},
                "unknown_section_lines": 0,
            },
        },
        "legacy_shadow_comparison": {},
        "failure_attribution": {
            "codes": [CODE_SHADOW_PIPELINE_FAILED],
            "primary_suspected_layer": LAYER_UNKNOWN,
            "details": {"error_type": error.__class__.__name__},
        },
        "analysis_version": RATECON_SHADOW_AUDIT_VERSION,
        "private_values_included": False,
        "private_eval_values_included": False,
        "raw_text_included": False,
        "raw_text_printed": False,
    }


def shadow_row_summary_fields(record):
    record = record if isinstance(record, dict) else {}
    shadow = record.get("shadow", {}) or {}
    triage = record.get("triage", {}) or {}
    candidate_summary = record.get("candidate_summary", {}) or {}
    failure = record.get("failure_attribution", {}) or {}
    comparisons = record.get("legacy_shadow_comparison", {}) or {}
    resolved_fields = shadow.get("resolved_fields", {}) or {}
    load_resolution = resolved_fields.get(FIELD_LOAD_NUMBER, {}) or {}
    rate_resolution = resolved_fields.get("total_carrier_rate", {}) or {}
    return {
        "ratecon_shadow_enabled": True,
        "ratecon_shadow_success": bool(shadow.get("success", False)),
        "shadow_needs_review": bool(shadow.get("needs_review", True)),
        "shadow_review_reasons": _safe_list(shadow.get("review_reasons")),
        "shadow_pdf_type": _text(triage.get("pdf_type")),
        "shadow_ocr_required": bool(triage.get("ocr_required", False)),
        "shadow_quality_flags": _safe_list(triage.get("quality_flags")),
        "shadow_candidate_count_load_number": _safe_int(
            (candidate_summary.get("candidates_by_field", {}) or {}).get(FIELD_LOAD_NUMBER)
        ),
        "shadow_candidate_count_total_rate": _safe_int(
            (candidate_summary.get("candidates_by_field", {}) or {}).get("total_carrier_rate")
        ),
        "shadow_independent_candidate_count_load_number": _safe_int(
            (candidate_summary.get("independent_candidates_by_field", {}) or {}).get(
                FIELD_LOAD_NUMBER
            )
        ),
        "shadow_legacy_final_candidate_count_load_number": _safe_int(
            (candidate_summary.get("legacy_final_fallback_candidates_by_field", {}) or {}).get(
                FIELD_LOAD_NUMBER
            )
        ),
        "shadow_load_number_confidence": load_resolution.get("confidence", 0.0),
        "shadow_total_rate_confidence": rate_resolution.get("confidence", 0.0),
        "shadow_failure_primary_layer": _text(failure.get("primary_suspected_layer")),
        "shadow_failure_codes": _safe_list(failure.get("codes")),
        "legacy_shadow_load_number_comparison": comparisons.get(FIELD_LOAD_NUMBER, ""),
        "legacy_shadow_total_rate_comparison": comparisons.get("total_carrier_rate", ""),
    }


def shadow_records_from_rows(rows):
    records = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for record in row.get("ratecon_shadow_audit_records", []) or []:
            if isinstance(record, dict):
                records.append(record)
    return records


def summarize_ratecon_shadow_audit_records(records):
    records = [record for record in records or [] if isinstance(record, dict)]
    pdf_type_counts = Counter()
    review_reason_counts = Counter()
    primary_layer_counts = Counter()
    code_counts = Counter()
    field_match_counts = defaultdict(Counter)
    candidate_coverage = {
        field_name: {
            "candidate_present_count": 0,
            "candidate_missing_count": 0,
        }
        for field_name in SHADOW_CANDIDATE_COVERAGE_FIELDS
    }
    independent_candidate_present_by_field = Counter()
    independent_candidate_missing_by_field = Counter()
    fallback_candidate_present_by_field = Counter()
    fallback_candidate_missing_by_field = Counter()
    generator_candidate_counts = Counter()
    mapping_strength_counts = Counter()
    unmapped_raw_fields = Counter()
    critical_by_strength = defaultdict(Counter)
    independent_critical_by_strength = defaultdict(Counter)
    fallback_critical_by_strength = defaultdict(Counter)
    raw_fields_by_generator = defaultdict(Counter)
    canonical_fields_by_generator = defaultdict(Counter)
    stop_evidence_by_role = Counter()
    stop_evidence_by_type = Counter()
    stop_assembly_counts = Counter()
    load_skipped_by_reason = Counter()
    load_emitted_by_method = Counter()
    load_line_counts = Counter()
    load_hit_types = Counter()
    load_rejections = Counter()
    load_method_attempts = Counter()
    load_method_successes = Counter()
    load_value_shapes = Counter()
    load_forensic_counts = Counter()
    stop_proximity_counts = Counter()
    stop_proximity_ambiguity = Counter()
    section_counts = Counter()
    section_context_totals = Counter()
    layout_provider_counts = Counter()
    layout_provider_totals = Counter()
    table_totals = Counter()
    table_header_roles = Counter()
    table_row_roles = Counter()
    layout_load_totals = Counter()
    layout_load_rejections = Counter()
    layout_load_methods = Counter()
    layout_stop_totals = Counter()
    layout_stop_rejections = Counter()
    layout_stop_methods = Counter()
    quality_totals = Counter()
    quality_high = Counter()
    quality_weak = Counter()
    quality_legacy = Counter()
    effect_load_totals = Counter()
    effect_load_methods = Counter()
    effect_load_hints = Counter()
    effect_load_bands = Counter()
    effect_stop_totals = Counter()
    effect_stop_methods = Counter()
    effect_stop_ambiguity = Counter()
    resolver_field_totals = defaultdict(Counter)
    resolver_not_selected_reasons = defaultdict(Counter)
    load_selection_totals = Counter()
    load_selection_not_selected = Counter()
    load_selected_sources = Counter()
    load_selected_pairing_methods = Counter()
    stop_selection_totals = {
        "pickup": Counter(),
        "delivery": Counter(),
    }
    stop_selection_not_selected = {
        "pickup": Counter(),
        "delivery": Counter(),
    }
    structured_stop_resolution_totals = {
        "pickup": Counter(),
        "delivery": Counter(),
    }
    structured_stop_conflict_totals = defaultdict(Counter)
    structured_stop_conflict_types = defaultdict(Counter)
    rate_review_sanity_totals = Counter()
    rate_review_mismatch_reasons = Counter()
    review_gate_status_counts = Counter()
    review_gate_source_counts = Counter()
    shadow_success = 0
    needs_review_count = 0
    ocr_required_count = 0
    low_text_count = 0
    suspicious_count = 0

    for record in records:
        shadow = record.get("shadow", {}) or {}
        triage = record.get("triage", {}) or {}
        candidate_summary = record.get("candidate_summary", {}) or {}
        comparison = record.get("legacy_shadow_comparison", {}) or {}
        failure = record.get("failure_attribution", {}) or {}
        artifact = record.get("artifact_summary", {}) or {}
        if shadow.get("success"):
            shadow_success += 1
        if shadow.get("needs_review"):
            needs_review_count += 1
        pdf_type_counts[_text(triage.get("pdf_type")) or "unknown"] += 1
        flags = set(_safe_list(triage.get("quality_flags")))
        if triage.get("ocr_required"):
            ocr_required_count += 1
        if "EMPTY_OR_LOW_TEXT" in flags:
            low_text_count += 1
        if "NATIVE_TEXT_SUSPICIOUS" in flags:
            suspicious_count += 1
        for reason in _safe_list(shadow.get("review_reasons")):
            review_reason_counts[reason] += 1
        field_counts = candidate_summary.get("candidates_by_field", {}) or {}
        independent_counts = candidate_summary.get("independent_candidates_by_field", {}) or {}
        fallback_counts = candidate_summary.get("legacy_final_fallback_candidates_by_field", {}) or {}
        for field_name in candidate_coverage:
            if _safe_int(field_counts.get(field_name)) > 0:
                candidate_coverage[field_name]["candidate_present_count"] += 1
            else:
                candidate_coverage[field_name]["candidate_missing_count"] += 1
            if _safe_int(independent_counts.get(field_name)) > 0:
                independent_candidate_present_by_field[field_name] += 1
            else:
                independent_candidate_missing_by_field[field_name] += 1
            if _safe_int(fallback_counts.get(field_name)) > 0:
                fallback_candidate_present_by_field[field_name] += 1
            else:
                fallback_candidate_missing_by_field[field_name] += 1
        generator_candidate_counts.update(
            candidate_summary.get("candidates_by_generator", {}) or {}
        )
        mapping_summary = candidate_summary.get("canonical_mapping_summary", {}) or {}
        mapping_strength_counts.update(mapping_summary.get("mapped_by_strength", {}) or {})
        unmapped_raw_fields.update(mapping_summary.get("unmapped_raw_fields_top", {}) or {})
        for field_name, strengths in (
            mapping_summary.get("critical_field_candidates_by_mapping_strength", {}) or {}
        ).items():
            critical_by_strength[field_name].update(strengths or {})
        for field_name, strengths in (
            mapping_summary.get(
                "independent_critical_field_candidates_by_mapping_strength",
                {},
            )
            or {}
        ).items():
            independent_critical_by_strength[field_name].update(strengths or {})
        for field_name, strengths in (
            mapping_summary.get(
                "legacy_final_critical_field_candidates_by_mapping_strength",
                {},
            )
            or {}
        ).items():
            fallback_critical_by_strength[field_name].update(strengths or {})
        taxonomy = candidate_summary.get("candidate_taxonomy", {}) or {}
        for generator_name, counts in (taxonomy.get("raw_fields_by_generator", {}) or {}).items():
            raw_fields_by_generator[generator_name].update(counts or {})
        for generator_name, counts in (
            taxonomy.get("canonical_fields_by_generator", {}) or {}
        ).items():
            canonical_fields_by_generator[generator_name].update(counts or {})
        stop_summary = candidate_summary.get("stop_assembly_summary", {}) or {}
        stop_assembly_counts["stop_evidence_count"] += _safe_int(
            stop_summary.get("stop_evidence_count")
        )
        stop_assembly_counts[
            "assembled_pickup_stop_candidate_count"
        ] += _safe_int(stop_summary.get("assembled_pickup_stop_candidate_count"))
        stop_assembly_counts[
            "assembled_delivery_stop_candidate_count"
        ] += _safe_int(stop_summary.get("assembled_delivery_stop_candidate_count"))
        stop_assembly_counts["docs_with_assembled_pickup_stops"] += _safe_int(
            stop_summary.get("docs_with_assembled_pickup_stops")
        )
        stop_assembly_counts["docs_with_assembled_delivery_stops"] += _safe_int(
            stop_summary.get("docs_with_assembled_delivery_stops")
        )
        stop_assembly_counts["partial_stop_candidate_count"] += _safe_int(
            stop_summary.get("partial_stop_candidate_count")
        )
        stop_assembly_counts["ambiguous_stop_candidate_count"] += _safe_int(
            stop_summary.get("ambiguous_stop_candidate_count")
        )
        stop_evidence_by_role.update(stop_summary.get("stop_evidence_by_role", {}) or {})
        stop_evidence_by_type.update(stop_summary.get("stop_evidence_by_type", {}) or {})
        load_summary = candidate_summary.get("load_identity_line_summary", {}) or {}
        load_line_counts["lines_scanned"] += _safe_int(load_summary.get("lines_scanned"))
        load_line_counts["label_hits"] += _safe_int(load_summary.get("label_hits"))
        load_line_counts["emitted_candidates"] += _safe_int(
            load_summary.get("emitted_candidates")
        )
        load_skipped_by_reason.update(load_summary.get("skipped_by_reason", {}) or {})
        load_emitted_by_method.update(load_summary.get("emitted_by_method", {}) or {})
        load_forensics = candidate_summary.get("load_identity_forensics", {}) or {}
        load_forensic_counts["label_hits"] += _safe_int(load_forensics.get("label_hits"))
        load_forensic_counts["emitted_candidates"] += _safe_int(
            load_forensics.get("emitted_candidates")
        )
        load_forensic_counts["docs_with_label_hits"] += _safe_int(
            load_forensics.get("docs_with_label_hits")
        )
        load_forensic_counts["docs_with_emitted_load_candidates"] += _safe_int(
            load_forensics.get("docs_with_emitted_load_candidates")
        )
        load_hit_types.update(load_forensics.get("hit_type_counts", {}) or {})
        load_rejections.update(load_forensics.get("rejection_reason_counts", {}) or {})
        load_method_attempts.update(load_forensics.get("method_attempt_counts", {}) or {})
        load_method_successes.update(load_forensics.get("method_success_counts", {}) or {})
        load_value_shapes.update(load_forensics.get("value_shape_counts", {}) or {})
        proximity = candidate_summary.get("stop_proximity_summary", {}) or {}
        for key in [
            "docs_with_proximity_clusters",
            "proximity_cluster_count",
            "ambiguous_cluster_count",
            "clusters_with_location_and_date",
            "clusters_with_location_only",
            "clusters_with_date_only",
        ]:
            stop_proximity_counts[key] += _safe_int(proximity.get(key))
        stop_proximity_ambiguity.update(proximity.get("ambiguity_reason_counts", {}) or {})
        section_summary = candidate_summary.get("section_context_summary", {}) or {}
        section_context_totals["lines_with_section_context"] += _safe_int(
            section_summary.get("lines_with_section_context")
        )
        section_context_totals["unknown_section_lines"] += _safe_int(
            section_summary.get("unknown_section_lines")
        )
        section_counts.update(section_summary.get("section_counts", {}) or {})
        layout_summary = artifact.get("layout_provider_summary", {}) or {}
        if layout_summary:
            layout_provider_counts[
                f"requested:{_text(layout_summary.get('provider_requested')) or 'unknown'}"
            ] += 1
            layout_provider_counts[
                f"used:{_text(layout_summary.get('provider_used')) or 'unknown'}"
            ] += 1
            layout_provider_counts[
                f"status:{_text(layout_summary.get('status')) or 'unknown'}"
            ] += 1
            for key in [
                "pages_with_words",
                "pages_with_lines",
                "pages_with_tables",
                "word_count",
                "line_count",
                "table_count",
                "table_cell_count",
            ]:
                layout_provider_totals[key] += _safe_int(layout_summary.get(key))
        table_summary = candidate_summary.get("table_extraction_summary", {}) or {}
        for key, value in (table_summary or {}).items():
            if isinstance(value, dict):
                continue
            table_totals[key] += _safe_int(value)
        table_header_roles.update(table_summary.get("table_header_role_counts", {}) or {})
        table_row_roles.update(table_summary.get("table_row_role_counts", {}) or {})
        layout_load = candidate_summary.get("layout_load_pairing_summary", {}) or {}
        for key in [
            "layout_label_hits",
            "same_row_pairings",
            "nearby_row_pairings",
            "table_cell_pairings",
            "header_block_pairings",
            "layout_candidates_emitted",
            "table_load_label_hits",
            "docs_with_table_load_candidates",
        ]:
            layout_load_totals[key] += _safe_int(layout_load.get(key))
        layout_load_rejections.update(
            layout_load.get("layout_rejection_reason_counts", {}) or {}
        )
        layout_load_methods.update(layout_load.get("table_pairings_by_method", {}) or {})
        layout_stop = candidate_summary.get("layout_stop_pairing_summary", {}) or {}
        for key in [
            "layout_stop_evidence_count",
            "layout_structured_stop_candidates",
            "table_row_stop_candidates",
            "bbox_cluster_stop_candidates",
            "table_stop_candidates_complete",
            "table_stop_candidates_partial",
            "table_stop_candidates_ambiguous",
        ]:
            layout_stop_totals[key] += _safe_int(layout_stop.get(key))
        layout_stop_rejections.update(
            layout_stop.get("layout_ambiguity_reason_counts", {}) or {}
        )
        layout_stop_methods.update(layout_stop.get("table_pairings_by_method", {}) or {})
        quality = candidate_summary.get("candidate_quality_summary", {}) or {}
        quality_totals["duplicate_candidates_removed"] += _safe_int(
            quality.get("duplicate_candidates_removed")
        )
        quality_high.update(
            quality.get("critical_fields_with_high_quality_independent_candidates", {}) or {}
        )
        quality_weak.update(quality.get("critical_fields_with_only_weak_candidates", {}) or {})
        quality_legacy.update(
            quality.get("critical_fields_with_only_legacy_fallback", {}) or {}
        )
        effectiveness = candidate_summary.get("layout_candidate_effectiveness", {}) or {}
        load_effect = effectiveness.get("layout_load_candidates", {}) or {}
        for key in ["emitted", "accepted_by_resolver", "rejected_or_not_selected"]:
            effect_load_totals[key] += _safe_int(load_effect.get(key))
        effect_load_methods.update(load_effect.get("by_pairing_method", {}) or {})
        effect_load_hints.update(load_effect.get("by_id_type_hint", {}) or {})
        effect_load_bands.update(load_effect.get("by_confidence_band", {}) or {})
        stop_effect = effectiveness.get("layout_stop_candidates", {}) or {}
        for key in [
            "emitted",
            "structured",
            "partial",
            "with_location",
            "with_date",
            "with_time",
            "accepted_by_resolver",
            "rejected_or_not_selected",
        ]:
            effect_stop_totals[key] += _safe_int(stop_effect.get(key))
        effect_stop_methods.update(stop_effect.get("by_pairing_method", {}) or {})
        effect_stop_ambiguity.update(stop_effect.get("ambiguity_reasons", {}) or {})
        resolver_summary = candidate_summary.get("resolver_selection_summary", {}) or {}
        for field_name, details in (resolver_summary.get("fields", {}) or {}).items():
            for key in [
                "candidate_count_seen",
                "eligible_count",
                "ineligible_count",
                "high_quality_not_selected_count",
            ]:
                resolver_field_totals[field_name][key] += _safe_int(details.get(key))
            if details.get("selected"):
                resolver_field_totals[field_name]["selected_count"] += 1
            decision_status = _text(details.get("decision_status"))
            if decision_status:
                resolver_field_totals[field_name][f"decision:{decision_status}"] += 1
            selected_quality = _text(details.get("selected_quality_band"))
            if selected_quality:
                resolver_field_totals[field_name][f"selected_quality:{selected_quality}"] += 1
            resolver_not_selected_reasons[field_name].update(
                details.get("not_selected_reason_counts", {}) or {}
            )
        load_selection = candidate_summary.get("load_number_selection_summary", {}) or {}
        for key in [
            "docs_with_any_load_candidates",
            "docs_with_high_quality_independent_load_candidates",
            "docs_with_medium_quality_independent_load_candidates",
            "docs_with_only_weak_load_candidates",
            "docs_with_only_legacy_fallback_load_candidates",
            "docs_with_selected_load_number",
            "docs_with_load_candidates_but_no_selection",
        ]:
            load_selection_totals[key] += _safe_int(load_selection.get(key))
        load_selection_not_selected.update(
            load_selection.get("not_selected_reason_counts", {}) or {}
        )
        load_selected_sources.update(load_selection.get("selected_source_counts", {}) or {})
        load_selected_pairing_methods.update(
            load_selection.get("selected_pairing_method_counts", {}) or {}
        )
        stop_selection = candidate_summary.get("stop_selection_summary", {}) or {}
        for role in ["pickup", "delivery"]:
            role_summary = stop_selection.get(role, {}) or {}
            for key in [
                "docs_with_any_candidates",
                "docs_with_complete_structured_candidates",
                "docs_with_partial_structured_candidates",
                "docs_with_ambiguous_candidates",
                "docs_with_table_row_candidates",
                "docs_with_bbox_cluster_candidates",
                "docs_with_selected_candidates",
                "docs_with_candidates_but_no_selection",
            ]:
                stop_selection_totals[role][key] += _safe_int(role_summary.get(key))
            stop_selection_not_selected[role].update(
                role_summary.get("not_selected_reason_counts", {}) or {}
            )
        structured_resolution = (
            candidate_summary.get("structured_stop_resolution_summary", {}) or {}
        )
        for role in ["pickup", "delivery"]:
            role_summary = structured_resolution.get(role, {}) or {}
            for key, value in role_summary.items():
                structured_stop_resolution_totals[role][key] += _safe_int(value)
        structured_conflicts = (
            candidate_summary.get("structured_stop_conflict_summary", {}) or {}
        )
        for field_name in ["pickup_stops", "delivery_stops"]:
            field_summary = structured_conflicts.get(field_name, {}) or {}
            for key, value in field_summary.items():
                if isinstance(value, dict):
                    continue
                if key in {"selected_status", "selected_source", "selected_pairing_method"}:
                    continue
                structured_stop_conflict_totals[field_name][key] += _safe_int(value)
            structured_stop_conflict_types[field_name].update(
                field_summary.get("conflict_type_counts", {}) or {}
            )
        rate_sanity = candidate_summary.get("rate_review_sanity_summary", {}) or {}
        for key, value in rate_sanity.items():
            if isinstance(value, dict):
                continue
            rate_review_sanity_totals[key] += _safe_int(value)
        rate_review_mismatch_reasons.update(rate_sanity.get("mismatch_reasons", {}) or {})
        gate_summary = candidate_summary.get("review_gate_trace_summary", {}) or {}
        review_gate_status_counts.update(
            gate_summary.get("critical_field_status_counts", {}) or {}
        )
        review_gate_source_counts.update(
            gate_summary.get("review_reason_source_counts", {}) or {}
        )
        primary_layer_counts[_text(failure.get("primary_suspected_layer")) or LAYER_UNKNOWN] += 1
        for code in _safe_list(failure.get("codes")):
            code_counts[code] += 1
        for field_name, status in comparison.items():
            field_match_counts[field_name][_text(status) or COMPARISON_NORMALIZATION_UNAVAILABLE] += 1

    legacy_vs_shadow = {
        "field_match_counts": {},
        "field_mismatch_counts": {},
        "legacy_only_counts": {},
        "shadow_only_counts": {},
        "both_missing_counts": {},
    }
    for field_name, counts in field_match_counts.items():
        legacy_vs_shadow["field_match_counts"][field_name] = counts.get(COMPARISON_SAME, 0)
        legacy_vs_shadow["field_mismatch_counts"][field_name] = counts.get(COMPARISON_DIFFERENT, 0)
        legacy_vs_shadow["legacy_only_counts"][field_name] = counts.get(COMPARISON_LEGACY_ONLY, 0)
        legacy_vs_shadow["shadow_only_counts"][field_name] = counts.get(COMPARISON_SHADOW_ONLY, 0)
        legacy_vs_shadow["both_missing_counts"][field_name] = counts.get(COMPARISON_BOTH_MISSING, 0)

    return {
        "documents_processed": len(records),
        "shadow_success": shadow_success,
        "shadow_failed": len(records) - shadow_success,
        "triage": {
            "pdf_type_counts": dict(sorted(pdf_type_counts.items())),
            "ocr_required_count": ocr_required_count,
            "low_text_count": low_text_count,
            "native_text_suspicious_count": suspicious_count,
        },
        "candidate_coverage": candidate_coverage,
        "candidate_generation": {
            "candidate_present_by_field": {
                field: values["candidate_present_count"]
                for field, values in candidate_coverage.items()
            },
            "candidate_missing_by_field": {
                field: values["candidate_missing_count"]
                for field, values in candidate_coverage.items()
            },
            "independent_candidate_present_by_field": dict(
                sorted(independent_candidate_present_by_field.items())
            ),
            "independent_candidate_missing_by_field": dict(
                sorted(independent_candidate_missing_by_field.items())
            ),
            "legacy_final_fallback_present_by_field": dict(
                sorted(fallback_candidate_present_by_field.items())
            ),
            "legacy_final_fallback_missing_by_field": dict(
                sorted(fallback_candidate_missing_by_field.items())
            ),
            "generator_candidate_counts": dict(
                sorted(generator_candidate_counts.items())
            ),
            "canonical_mapping_summary": {
                "mapped_candidate_count": sum(
                    count
                    for strength, count in mapping_strength_counts.items()
                    if strength != MAPPING_UNMAPPED
                ),
                "unmapped_candidate_count": mapping_strength_counts.get(
                    MAPPING_UNMAPPED,
                    0,
                ),
                "mapped_by_strength": dict(sorted(mapping_strength_counts.items())),
                "unmapped_raw_fields_top": dict(unmapped_raw_fields.most_common(25)),
                "critical_field_candidates_by_mapping_strength": {
                    field: dict(sorted(counter.items()))
                    for field, counter in sorted(critical_by_strength.items())
                },
                "independent_critical_field_candidates_by_mapping_strength": {
                    field: dict(sorted(counter.items()))
                    for field, counter in sorted(independent_critical_by_strength.items())
                },
                "legacy_final_critical_field_candidates_by_mapping_strength": {
                    field: dict(sorted(counter.items()))
                    for field, counter in sorted(fallback_critical_by_strength.items())
                },
            },
            "candidate_taxonomy": {
                "raw_fields_by_generator": {
                    generator_name: dict(counter.most_common(25))
                    for generator_name, counter in sorted(raw_fields_by_generator.items())
                },
                "canonical_fields_by_generator": {
                    generator_name: dict(counter.most_common(25))
                    for generator_name, counter in sorted(
                        canonical_fields_by_generator.items()
                    )
                },
            },
            "stop_assembly_summary": {
                "stop_evidence_count": stop_assembly_counts.get("stop_evidence_count", 0),
                "stop_evidence_by_role": dict(sorted(stop_evidence_by_role.items())),
                "stop_evidence_by_type": dict(sorted(stop_evidence_by_type.items())),
                "assembled_pickup_stop_candidate_count": stop_assembly_counts.get(
                    "assembled_pickup_stop_candidate_count",
                    0,
                ),
                "assembled_delivery_stop_candidate_count": stop_assembly_counts.get(
                    "assembled_delivery_stop_candidate_count",
                    0,
                ),
                "docs_with_assembled_pickup_stops": stop_assembly_counts.get(
                    "docs_with_assembled_pickup_stops",
                    0,
                ),
                "docs_with_assembled_delivery_stops": stop_assembly_counts.get(
                    "docs_with_assembled_delivery_stops",
                    0,
                ),
                "partial_stop_candidate_count": stop_assembly_counts.get(
                    "partial_stop_candidate_count",
                    0,
                ),
                "ambiguous_stop_candidate_count": stop_assembly_counts.get(
                    "ambiguous_stop_candidate_count",
                    0,
                ),
            },
            "load_identity_line_summary": {
                "lines_scanned": load_line_counts.get("lines_scanned", 0),
                "label_hits": load_line_counts.get("label_hits", 0),
                "emitted_candidates": load_line_counts.get("emitted_candidates", 0),
                "skipped_by_reason": dict(load_skipped_by_reason.most_common()),
                "emitted_by_method": dict(load_emitted_by_method.most_common()),
            },
            "load_identity_forensics": {
                "label_hits": load_forensic_counts.get("label_hits", 0),
                "emitted_candidates": load_forensic_counts.get("emitted_candidates", 0),
                "hit_type_counts": dict(load_hit_types.most_common()),
                "rejection_reason_counts": dict(load_rejections.most_common()),
                "method_attempt_counts": dict(load_method_attempts.most_common()),
                "method_success_counts": dict(load_method_successes.most_common()),
                "value_shape_counts": dict(load_value_shapes.most_common()),
                "docs_with_label_hits": load_forensic_counts.get("docs_with_label_hits", 0),
                "docs_with_emitted_load_candidates": load_forensic_counts.get(
                    "docs_with_emitted_load_candidates",
                    0,
                ),
            },
            "stop_proximity_summary": {
                "docs_with_proximity_clusters": stop_proximity_counts.get(
                    "docs_with_proximity_clusters",
                    0,
                ),
                "proximity_cluster_count": stop_proximity_counts.get(
                    "proximity_cluster_count",
                    0,
                ),
                "ambiguous_cluster_count": stop_proximity_counts.get(
                    "ambiguous_cluster_count",
                    0,
                ),
                "clusters_with_location_and_date": stop_proximity_counts.get(
                    "clusters_with_location_and_date",
                    0,
                ),
                "clusters_with_location_only": stop_proximity_counts.get(
                    "clusters_with_location_only",
                    0,
                ),
                "clusters_with_date_only": stop_proximity_counts.get(
                    "clusters_with_date_only",
                    0,
                ),
                "ambiguity_reason_counts": dict(stop_proximity_ambiguity.most_common()),
            },
            "section_context_summary": {
                "lines_with_section_context": section_context_totals.get(
                    "lines_with_section_context",
                    0,
                ),
                "section_counts": dict(section_counts.most_common()),
                "unknown_section_lines": section_context_totals.get(
                    "unknown_section_lines",
                    0,
                ),
            },
            "layout_provider_summary": {
                "provider_status_counts": dict(layout_provider_counts.most_common()),
                "pages_with_words": layout_provider_totals.get("pages_with_words", 0),
                "pages_with_lines": layout_provider_totals.get("pages_with_lines", 0),
                "pages_with_tables": layout_provider_totals.get("pages_with_tables", 0),
                "word_count": layout_provider_totals.get("word_count", 0),
                "line_count": layout_provider_totals.get("line_count", 0),
                "table_count": layout_provider_totals.get("table_count", 0),
                "table_cell_count": layout_provider_totals.get("table_cell_count", 0),
            },
            "table_extraction_summary": {
                **dict(sorted(table_totals.items())),
                "table_header_role_counts": dict(table_header_roles.most_common()),
                "table_row_role_counts": dict(table_row_roles.most_common()),
            },
            "table_profile_summary": {
                **dict(sorted(table_totals.items())),
                "table_header_role_counts": dict(table_header_roles.most_common()),
                "table_row_role_counts": dict(table_row_roles.most_common()),
            },
            "layout_load_pairing_summary": {
                **dict(sorted(layout_load_totals.items())),
                "layout_rejection_reason_counts": dict(layout_load_rejections.most_common()),
                "table_pairings_by_method": dict(layout_load_methods.most_common()),
            },
            "layout_stop_pairing_summary": {
                **dict(sorted(layout_stop_totals.items())),
                "layout_ambiguity_reason_counts": dict(layout_stop_rejections.most_common()),
                "table_pairings_by_method": dict(layout_stop_methods.most_common()),
            },
            "candidate_quality_summary": {
                **dict(sorted(quality_totals.items())),
                "critical_fields_with_high_quality_independent_candidates": dict(
                    quality_high.most_common()
                ),
                "critical_fields_with_only_weak_candidates": dict(quality_weak.most_common()),
                "critical_fields_with_only_legacy_fallback": dict(quality_legacy.most_common()),
            },
            "layout_candidate_effectiveness": {
                "layout_load_candidates": {
                    **dict(sorted(effect_load_totals.items())),
                    "by_pairing_method": dict(effect_load_methods.most_common()),
                    "by_id_type_hint": dict(effect_load_hints.most_common()),
                    "by_confidence_band": dict(effect_load_bands.most_common()),
                },
                "layout_stop_candidates": {
                    **dict(sorted(effect_stop_totals.items())),
                    "by_pairing_method": dict(effect_stop_methods.most_common()),
                    "ambiguity_reasons": dict(effect_stop_ambiguity.most_common()),
                },
            },
            "resolver_selection_summary": {
                "fields": {
                    field_name: {
                        **dict(sorted(counter.items())),
                        "not_selected_reason_counts": dict(
                            resolver_not_selected_reasons[field_name].most_common()
                        ),
                    }
                    for field_name, counter in sorted(resolver_field_totals.items())
                },
            },
            "load_number_selection_summary": {
                **dict(sorted(load_selection_totals.items())),
                "not_selected_reason_counts": dict(
                    load_selection_not_selected.most_common()
                ),
                "selected_source_counts": dict(load_selected_sources.most_common()),
                "selected_pairing_method_counts": dict(
                    load_selected_pairing_methods.most_common()
                ),
            },
            "stop_selection_summary": {
                role: {
                    **dict(sorted(counter.items())),
                    "not_selected_reason_counts": dict(
                        stop_selection_not_selected[role].most_common()
                    ),
                }
                for role, counter in sorted(stop_selection_totals.items())
            },
            "structured_stop_resolution_summary": {
                role: dict(sorted(counter.items()))
                for role, counter in sorted(structured_stop_resolution_totals.items())
            },
            "structured_stop_conflict_summary": {
                field_name: {
                    **dict(sorted(counter.items())),
                    "conflict_type_counts": dict(
                        structured_stop_conflict_types[field_name].most_common()
                    ),
                }
                for field_name, counter in sorted(structured_stop_conflict_totals.items())
            },
            "rate_review_sanity_summary": {
                **dict(sorted(rate_review_sanity_totals.items())),
                "mismatch_reasons": dict(rate_review_mismatch_reasons.most_common()),
            },
            "review_gate_trace_summary": {
                "needs_review_count": needs_review_count,
                "critical_field_status_counts": dict(
                    review_gate_status_counts.most_common()
                ),
                "review_reason_source_counts": dict(
                    review_gate_source_counts.most_common()
                ),
            },
        },
        "review_gate": {
            "needs_review_count": needs_review_count,
            "auto_accept_candidate_count": len(records) - needs_review_count,
            "review_reason_counts": dict(sorted(review_reason_counts.items())),
        },
        "legacy_vs_shadow": legacy_vs_shadow,
        "failure_attribution": {
            "primary_layer_counts": dict(sorted(primary_layer_counts.items())),
            "code_counts": dict(sorted(code_counts.items())),
        },
        "analysis_version": RATECON_SHADOW_AUDIT_VERSION,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def write_ratecon_shadow_audit_artifacts(
    records,
    output_dir=None,
    allow_custom_output_dir=False,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    safe_records = [record for record in records or [] if isinstance(record, dict)]
    jsonl_path = output_root / RATECON_SHADOW_AUDIT_JSONL
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in safe_records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    summary = summarize_ratecon_shadow_audit_records(safe_records)
    summary_path = output_root / RATECON_SHADOW_AUDIT_SUMMARY_JSON
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "files": {
            "ratecon_shadow_audit_jsonl": jsonl_path.name,
            "ratecon_shadow_summary_json": summary_path.name,
        },
        "aggregate": summary,
        "private_values_printed": False,
        "raw_text_printed": False,
        "money_values_printed": False,
    }
