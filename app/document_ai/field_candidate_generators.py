"""Shadow-mode FieldCandidate generator orchestration.

These adapters make existing deterministic candidate/template outputs visible to
the vertical-slice document pipeline. They do not replace the legacy private
measurement result.
"""

from collections import Counter
from dataclasses import dataclass
import re

from app.document_ai.field_candidate_provenance import (
    SOURCE_LEGACY_PARSER,
    SOURCE_NATIVE_LAYOUT,
    SOURCE_NATIVE_TEXT,
    build_field_candidate,
    adapt_candidate_result_to_field_candidates,
    adapt_ratecon_candidate_to_field_candidate,
)
from app.document_ai.field_candidate_resolver import (
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_DELIVERY_STOPS,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_STOPS,
    FIELD_TOTAL_CARRIER_RATE,
)
from app.document_ai.load_identifier_candidates import classify_identifier_label
from app.document_ai.layout_candidate_extraction import extract_ratecon_layout_candidates
from app.document_ai.layout_shadow_candidates import (
    GENERATOR_LAYOUT_LOAD_PAIRING,
    GENERATOR_LAYOUT_STOP_TABLE,
    generate_layout_load_identity_candidates,
    generate_layout_stop_table_candidates,
    summarize_tables_for_shadow,
)
from app.document_ai.ratecon_candidate_context_features import enrich_candidates_context
from app.document_ai.load_identity_forensics import (
    analyze_load_identity_label_hits,
    candidate_value_shape,
    identifier_value_rejection_reason,
    summarize_load_identity_forensics,
)
from app.document_ai.ratecon_canonical_fields import (
    FIELD_DELIVERY_COUNT,
    FIELD_PICKUP_COUNT,
    MAPPING_UNMAPPED,
    canonical_field_mapping,
    value_shape,
)
from app.document_ai.ratecon_candidate_extraction import extract_ratecon_candidates
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_RATE,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from app.document_ai.stop_evidence_assembler import (
    GENERATOR_STOP_EVIDENCE_ASSEMBLER,
    assemble_stop_candidates,
    extract_stop_evidence_from_candidates,
    summarize_stop_assembly,
)


GENERATOR_TEXT_CANDIDATES = "document_text_candidate_extractor"
GENERATOR_LOAD_ID_LINES = "load_identifier_line_candidate_generator"
GENERATOR_LEGACY_CANDIDATE_RESULT = "legacy_candidate_result_adapter"
GENERATOR_LEGACY_RESOLUTION_CANDIDATES = "legacy_resolution_candidate_adapter"
GENERATOR_LEGACY_STOP_SET = "legacy_stop_set_adapter"
GENERATOR_LEGACY_FINAL_OUTPUT = "legacy_final_output_adapter"
GENERATOR_LAYOUT_CANDIDATE_RESULT = "layout_candidate_result_adapter"
GENERATOR_HEADER_LOAD_IDENTITY = "header_load_identity_candidate_generator"

SOURCE_LEGACY_FINAL_OUTPUT = "legacy_final_output"

LOAD_CANDIDATE_PROFILE_BASELINE = "baseline"
LOAD_CANDIDATE_PROFILE_HEADER_RECALL_V1 = "header_recall_v1"
LOAD_CANDIDATE_PROFILES = {
    LOAD_CANDIDATE_PROFILE_BASELINE,
    LOAD_CANDIDATE_PROFILE_HEADER_RECALL_V1,
}

_IDENTIFIER_LABEL_CORE = (
    r"rate\s+confirmation|load|shipment|order|tender|confirmation|trip|dispatch|"
    r"reference|ref|po|bol|pickup|delivery"
)
LOAD_IDENTIFIER_LINE_PATTERN = re.compile(
    r"^\s*(?P<label>(?:"
    + _IDENTIFIER_LABEL_CORE
    + r")(?:\s*(?:#|no\.?|number|id))?)"
    r"(?:\s*[:#-]\s*|\s+)"
    r"(?P<value>[A-Za-z0-9][A-Za-z0-9_./-]{2,})\s*$",
    re.IGNORECASE,
)
LOAD_IDENTIFIER_LABEL_ONLY_PATTERN = re.compile(
    r"^\s*(?P<label>(?:"
    + _IDENTIFIER_LABEL_CORE
    + r")(?:\s*(?:#|no\.?|number|id))?)\s*[:#-]?\s*$",
    re.IGNORECASE,
)
HEADER_LOAD_IDENTITY_PATTERN = re.compile(
    r"(?P<label>"
    r"carrier\s+rate\s+and\s+load\s+confirmation\s+load\s+number|"
    r"carrier\s+load\s+tender\s+load\s*#?|"
    r"long\s+haul\s+load\s*#?|"
    r"rate\s+confirmation\s*#?|"
    r"confirmation\s*#?|"
    r"load\s*(?:#|number|no\.?|id)|"
    r"order(?:\(s\))?\s*(?:#|number|no\.?)|"
    r"shipment\s*(?:id|#|number)|"
    r"freight\s+bill\s*#?|"
    r"pro\s*#?|"
    r"(?:p\.?\s*o\.?|po)\s*#?"
    r")\s*(?:[:#-]|\s)\s*"
    r"(?P<value>[A-Za-z0-9][A-Za-z0-9_./-]{2,})",
    re.IGNORECASE,
)
HEADER_STOP_REFERENCE_PATTERN = re.compile(
    r"(?P<label>"
    r"pu\s*#?|pickup\s*#?|pickup\s+number|delivery\s*#?|del\s*#?|"
    r"bol\s*#?|b\.o\.l\.?\s*#?|customer\s+ref(?:erence)?|reference\s*#?|ref\s*#?|"
    r"driver\s*#?|truck\s*#?|tractor\s*#?|trailer\s*#?"
    r")\s*(?:[:#-]|\s)\s*"
    r"(?P<value>[A-Za-z0-9][A-Za-z0-9_./-]{2,})",
    re.IGNORECASE,
)
HEADER_TITLE_TERMS = (
    "rate confirmation",
    "load confirmation",
    "carrier load tender",
    "carrier rate and load confirmation",
    "truck order not used",
)
HEADER_LOAD_INFO_TERMS = (
    "load information",
    "shipment information",
    "carrier load tender",
    "carrier rate and load confirmation",
)
HEADER_FOOTER_TERMS = ("signature", "signed by", "driver signature", "carrier signature")



@dataclass(frozen=True)
class FieldCandidateGenerator:
    name: str
    source_type: str
    generate_candidates: object


def _text(value):
    return str(value or "").strip()


def _page_text_pages(artifact):
    return [
        {
            "page_number": page.get("page_number", index),
            "text": page.get("text", ""),
            "source_method": artifact.get("source", "native"),
        }
        for index, page in enumerate((artifact or {}).get("pages", []) or [], start=1)
    ]


def _has_coordinate_layout_data(artifact):
    summary = (artifact or {}).get("layout_provider_summary") or {}
    if summary.get("status") != "success":
        return False
    return bool(
        int(summary.get("word_count") or 0)
        or int(summary.get("table_count") or 0)
        or int(summary.get("table_cell_count") or 0)
    )


def _candidate_artifact(artifact):
    return build_text_extraction_artifact_for_candidates(
        artifact_id=f"SHADOW-CAND-{(artifact or {}).get('document_id', '')}",
        document_id=(artifact or {}).get("document_id", ""),
        source_name="shadow_document_artifact",
        pages=_page_text_pages(artifact or {}),
        full_text=(artifact or {}).get("full_text", ""),
        source_method=(artifact or {}).get("source", "native"),
        contains_private_text=bool((artifact or {}).get("full_text", "")),
    )


def _annotate(candidate, generator_name, independent=True):
    item = dict(candidate or {})
    metadata = dict(item.get("metadata") or {})
    metadata["generator_name"] = generator_name
    metadata["independent_candidate"] = bool(independent)
    item["metadata"] = metadata
    if not item.get("parser_name"):
        item["parser_name"] = generator_name
    return item


def _dedupe(candidates):
    seen = set()
    result = []
    for candidate in candidates or []:
        metadata = candidate.get("metadata") or {}
        structured_stop_identity = ()
        if metadata.get("structured_stop_candidate"):
            structured_stop_identity = (
                _text(metadata.get("stop_role")),
                _text(metadata.get("pairing_method")),
                _text(metadata.get("source_stop_set")),
                _text(metadata.get("table_index")),
                _text(metadata.get("row_index")),
                ",".join(_text(value) for value in metadata.get("cell_indices", []) or []),
                ",".join(_text(value) for value in metadata.get("page_span", []) or []),
                _text(metadata.get("proximity_cluster_line_span")),
                _text(metadata.get("evidence_count")),
                _text(metadata.get("has_location")),
                _text(metadata.get("has_date")),
                _text(metadata.get("has_time")),
            )
        identity = (
            _text(candidate.get("field")),
            _text(candidate.get("normalized_value") or candidate.get("value")).lower(),
            _text(candidate.get("label")).lower(),
            _text(candidate.get("source")),
            _text(candidate.get("parser_name")),
            structured_stop_identity,
        )
        if identity in seen:
            continue
        seen.add(identity)
        result.append(candidate)
    return result


def _summary(generator_name, source_type, candidates=None, warnings=None, diagnostics=None):
    counts = Counter()
    raw_counts = Counter()
    unmapped_counts = Counter()
    canonical_counts = Counter()
    for candidate in candidates or []:
        field = _text(candidate.get("field"))
        metadata = candidate.get("metadata") or {}
        raw_field = _text(metadata.get("raw_field")) or field
        strength = _text(metadata.get("canonical_mapping_strength")) or MAPPING_UNMAPPED
        if field:
            counts[field] += 1
            canonical_counts[field] += 1
        if raw_field:
            raw_counts[raw_field] += 1
        if strength == MAPPING_UNMAPPED and raw_field:
            unmapped_counts[raw_field] += 1
    return {
        "generator_name": generator_name,
        "source_type": source_type,
        "candidate_count": len(candidates or []),
        "fields": dict(sorted(counts.items())),
        "canonical_candidate_count": sum(canonical_counts.values()),
        "critical_candidate_count": sum(
            count
            for field_name, count in counts.items()
            if field_name
            in {
                FIELD_LOAD_NUMBER,
                FIELD_TOTAL_CARRIER_RATE,
                FIELD_PICKUP_STOPS,
                FIELD_DELIVERY_STOPS,
                FIELD_BROKER_NAME,
                FIELD_CARRIER_NAME,
            }
        ),
        "unmapped_candidate_count": sum(unmapped_counts.values()),
        "top_raw_fields": dict(raw_counts.most_common(10)),
        "top_canonical_fields": dict(canonical_counts.most_common(10)),
        "warnings": list(warnings or []),
        "diagnostics": dict(diagnostics or {}),
    }


def _build_result(candidates=None, summaries=None, errors=None):
    return {
        "candidates": _dedupe(candidates or []),
        "generator_summaries": list(summaries or []),
        "errors": list(errors or []),
        "result_version": "field_candidate_generation_result_v1",
    }


def _text_candidate_generator(artifact, triage=None, legacy_context=None):
    if not _text((artifact or {}).get("full_text")):
        return [], ["artifact_full_text_missing"]
    result = extract_ratecon_candidates(_candidate_artifact(artifact or {}))
    candidates = [
        _annotate(candidate, GENERATOR_TEXT_CANDIDATES, independent=True)
        for candidate in adapt_candidate_result_to_field_candidates(
            result,
            parser_name=GENERATOR_TEXT_CANDIDATES,
        )
    ]
    return candidates, list(result.get("warnings", []) or [])


def _line_context(lines, index):
    before = lines[index - 1].strip() if index > 0 else ""
    after = lines[index + 1].strip() if index + 1 < len(lines) else ""
    return before, after


def _identifier_context(lines, index):
    window = " ".join(
        lines[position].strip().lower()
        for position in range(max(0, index - 2), min(len(lines), index + 3))
        if lines[position].strip()
    )
    return {"window": window}


def _id_type_hint(identifier_type):
    token = _text(identifier_type).lower()
    for prefix in ["load", "shipment", "order", "tender", "confirmation", "trip"]:
        if prefix in token:
            return prefix
    if "primary_reference" in token:
        return "reference"
    if "po" in token:
        return "po"
    if "bol" in token:
        return "bol"
    return "unknown"


def _label_for_identifier_classification(label):
    normalized = _text(label).lower().replace(".", "")
    if normalized.startswith("rate confirmation"):
        return normalized.replace("rate confirmation", "confirmation", 1)
    if normalized == "shipment id":
        return "shipment number"
    if normalized in {"load", "shipment", "order", "tender", "confirmation", "trip", "dispatch"}:
        return f"{normalized} number"
    return label


def _label_strength(confidence):
    try:
        score = float(confidence)
    except (TypeError, ValueError):
        score = None
    if score is not None:
        if score >= 0.80:
            return "strong"
        if score >= 0.60:
            return "medium"
        return "weak"
    if confidence == CANDIDATE_CONFIDENCE_HIGH:
        return "strong"
    if confidence == CANDIDATE_CONFIDENCE_MEDIUM:
        return "medium"
    return "weak"


def _artifact_page_lines(artifact):
    pages = []
    for page in (artifact or {}).get("pages", []) or []:
        page_number = page.get("page_number", "")
        line_items = []
        for item in page.get("lines", []) or []:
            text = _text(item.get("text") if isinstance(item, dict) else item)
            if text:
                line_items.append(text)
        if not line_items:
            line_items = [
                line.strip()
                for line in str(page.get("text") or "").splitlines()
                if line.strip()
            ]
        pages.append((page_number, line_items))
    if not pages and _text((artifact or {}).get("full_text")):
        pages.append(
            (
                1,
                [
                    line.strip()
                    for line in str((artifact or {}).get("full_text") or "").splitlines()
                    if line.strip()
                ],
            )
        )
    return pages


def _next_nonempty_line(lines, index):
    for position in range(index + 1, min(len(lines), index + 4)):
        value = _text(lines[position])
        if value:
            return value
    return ""


def _previous_nonempty_line(lines, index):
    for position in range(index - 1, max(-1, index - 4), -1):
        value = _text(lines[position])
        if value:
            return value
    return ""


def _identifier_value_skip_reason(value):
    return identifier_value_rejection_reason(value)


def _looks_like_identifier_value(value):
    return not _identifier_value_skip_reason(value)


def _candidate_value_from_line_window(lines, index):
    candidates = []
    previous_line = _previous_nonempty_line(lines, index)
    next_line = _next_nonempty_line(lines, index)
    if next_line:
        candidates.append(("adjacent_next", next_line))
    if previous_line:
        candidates.append(("adjacent_previous", previous_line))
    for position in range(max(0, index - 2), min(len(lines), index + 3)):
        if position == index:
            continue
        value = _text(lines[position])
        if value:
            method = "line_window_previous" if position < index else "line_window_next"
            candidates.append((method, value))
    for method, value in candidates:
        if _looks_like_identifier_value(value):
            return method, value
    return ("adjacent_line_missing", next_line or previous_line or "")


def _load_identifier_candidate(
    label,
    value,
    evidence,
    page_number,
    lines,
    index,
    match_kind,
    label_hit_type="unknown",
    section_context="unknown",
):
    context = _identifier_context(lines, index)
    classification = classify_identifier_label(
        _label_for_identifier_classification(label),
        context,
    )
    primary = bool(classification.get("primary_load_identifier_candidate"))
    id_hint = _id_type_hint(classification.get("identifier_type"))
    confidence = 0.45
    if primary and id_hint == "load" and match_kind == "same_line":
        confidence = 0.84
    elif primary and match_kind == "same_line":
        confidence = 0.72
    elif primary and match_kind in {"adjacent_next", "adjacent_previous"}:
        confidence = 0.62
    elif primary and match_kind in {"line_window_next", "line_window_previous", "full_text_window"}:
        confidence = 0.55
    elif not primary:
        confidence = 0.45
    before, after = _line_context(lines, index)
    return _annotate(
        build_field_candidate(
            field=FIELD_LOAD_NUMBER if primary else "reference_numbers",
            value=value,
            normalized_value=value,
            label=label,
            evidence_text=evidence,
            page=page_number,
            source=SOURCE_NATIVE_TEXT,
            parser_name=GENERATOR_LOAD_ID_LINES,
            confidence=confidence,
            metadata={
                "id_type_hint": _id_type_hint(classification.get("identifier_type")),
                "identifier_type": classification.get("identifier_type", ""),
                "label_strength": _label_strength(confidence),
                "is_primary_identifier_candidate": primary,
                "confidence_reasons": list(
                    classification.get("confidence_reasons", []) or []
                ),
                "warnings": list(classification.get("warning_codes", []) or []),
                "context_before_present": bool(before),
                "context_after_present": bool(after),
                "match_kind": match_kind,
                "value_extraction_method": match_kind,
                "label_hit_reason": "load_identity_label_hit",
                "label_hit_type": label_hit_type,
                "candidate_value_shape": candidate_value_shape(value),
                "label_confidence": confidence,
                "section_context": section_context,
                "forensic_rejection_reason": None,
                "skip_reason": None,
            },
        ),
        GENERATOR_LOAD_ID_LINES,
        independent=True,
    )


def _load_identifier_line_generator(artifact, triage=None, legacy_context=None):
    candidates = []
    page_lines = {
        page_number: lines
        for page_number, lines in _artifact_page_lines(artifact)
    }
    forensic_records = analyze_load_identity_label_hits(artifact or {})
    diagnostics = {
        "lines_scanned_count": sum(len(lines) for lines in page_lines.values()),
        "label_hits_count": len(forensic_records),
        "candidates_emitted_count": 0,
        "skipped_reason_counts": {},
        "emitted_by_method": {},
        "load_identity_forensics": {},
    }
    skipped = Counter()
    emitted_by_method = Counter()
    for record in forensic_records:
        page_number = record.get("page_number", "")
        index = int(record.get("line_index", 0) or 0)
        lines = page_lines.get(page_number, [])
        label = record.get("_label", "")
        value = record.get("_accepted_value", "")
        match_kind = record.get("accepted_method", "")
        if not value:
            skipped[record.get("_rejection_reason") or record.get("final_outcome", "unknown")] += 1
            continue
        skip_reason = _identifier_value_skip_reason(value)
        if skip_reason:
            skipped[skip_reason] += 1
            continue
        evidence = f"{label} [{match_kind}-value-present]"
        candidates.append(
            _load_identifier_candidate(
                label,
                value,
                evidence,
                page_number,
                lines,
                index,
                match_kind,
                label_hit_type=record.get("hit_type", "unknown"),
                section_context=record.get("section_context", "unknown"),
            )
        )
        emitted_by_method[match_kind] += 1
    diagnostics["candidates_emitted_count"] = len(candidates)
    diagnostics["skipped_reason_counts"] = dict(sorted(skipped.items()))
    diagnostics["emitted_by_method"] = dict(sorted(emitted_by_method.items()))
    diagnostics["load_identity_forensics"] = summarize_load_identity_forensics(
        forensic_records,
        emitted_candidates=len(candidates),
    )
    return candidates, [], diagnostics


def _header_line_rows(artifact):
    rows = []
    for page in (artifact or {}).get("pages", []) or []:
        try:
            page_number = int(page.get("page_number") or len(rows) + 1)
        except (TypeError, ValueError):
            page_number = len(rows) + 1
        page_height = page.get("height") or 0
        line_items = page.get("lines", []) or []
        if not line_items:
            line_items = [
                {"text": line.strip(), "line_index": index}
                for index, line in enumerate(str(page.get("text") or "").splitlines())
                if line.strip()
            ]
        context = "unknown"
        for index, item in enumerate(line_items):
            if not isinstance(item, dict):
                item = {"text": item, "line_index": index}
            text = _text(item.get("text"))
            if not text:
                continue
            context = _header_section_context(text, context)
            bbox = item.get("bbox") if isinstance(item.get("bbox"), list) else None
            y0 = bbox[1] if bbox and len(bbox) >= 2 else None
            rows.append(
                {
                    "page": page_number,
                    "line_index": int(item.get("line_index", index) or 0),
                    "text": text,
                    "bbox": bbox,
                    "page_height": page_height,
                    "section_context": context,
                    "source": _text(item.get("source")) or SOURCE_NATIVE_TEXT,
                    "top_region": (
                        page_number == 1
                        and (
                            int(item.get("line_index", index) or 0) <= 14
                            or (
                                isinstance(y0, (int, float))
                                and float(page_height or 0) > 0
                                and y0 <= float(page_height) * 0.28
                            )
                        )
                    ),
                }
            )
    if not rows and _text((artifact or {}).get("full_text")):
        context = "unknown"
        for index, line in enumerate(str((artifact or {}).get("full_text") or "").splitlines()):
            text = _text(line)
            if not text:
                continue
            context = _header_section_context(text, context)
            rows.append(
                {
                    "page": 1,
                    "line_index": index,
                    "text": text,
                    "bbox": None,
                    "page_height": 0,
                    "section_context": context,
                    "source": SOURCE_NATIVE_TEXT,
                    "top_region": index <= 14,
                }
            )
    return rows


def _header_section_context(text, previous_context="unknown"):
    lower = _text(text).lower()
    if any(term in lower for term in HEADER_FOOTER_TERMS):
        return "footer_signature"
    if any(term in lower for term in ["pickup", "pick up", "delivery", "shipper", "consignee", "stop"]):
        return "stop_section"
    if any(term in lower for term in HEADER_LOAD_INFO_TERMS):
        return "load_info"
    if any(term in lower for term in ["reference", "customer ref", "bol", "pu#", "pu #"]):
        return "reference_section"
    if any(term in lower for term in ["instructions", "terms", "notes"]):
        return "instructions"
    if any(term in lower for term in ["rate", "charges", "carrier pay"]) and "confirmation" not in lower:
        return "payment"
    return previous_context or "unknown"


def _header_document_region(row, label):
    text = _text(row.get("text")).lower()
    section = _text(row.get("section_context"))
    if section in {"stop_section", "reference_section", "instructions", "footer_signature"}:
        return section
    if row.get("top_region") and any(term in text for term in HEADER_TITLE_TERMS):
        return "document_title"
    if section == "load_info":
        return "load_info"
    if row.get("top_region"):
        return "header"
    return "unknown"


def _header_id_hint(label):
    lower = _text(label).lower().replace(".", "")
    if "freight bill" in lower:
        return "freight_bill"
    if "pro" in lower:
        return "pro"
    if "po" in lower:
        return "po"
    if "order" in lower:
        return "order"
    if "shipment" in lower:
        return "shipment"
    if "confirmation" in lower:
        return "confirmation"
    if "load" in lower:
        return "load"
    if "pickup" in lower or lower.startswith("pu"):
        return "pickup_ref"
    if "delivery" in lower or lower.startswith("del"):
        return "delivery_ref"
    if "bol" in lower:
        return "bol"
    if "driver" in lower or "truck" in lower or "tractor" in lower or "trailer" in lower:
        return "vehicle_noise"
    if "ref" in lower:
        return "reference"
    return "unknown"


def _header_label_strength(id_hint, document_region, text):
    token_count = len(_text(text).split())
    if document_region in {"stop_section", "reference_section", "footer_signature", "instructions"}:
        return "weak"
    if id_hint in {"load", "order", "shipment", "confirmation"}:
        return "strong"
    if id_hint in {"po"} and document_region in {"document_title", "header", "load_info"} and any(
        term in text.lower() for term in ["rate confirmation", "load confirmation", "load information"]
    ):
        return "strong"
    if id_hint == "po" and document_region in {"header", "document_title", "load_info"} and token_count <= 4:
        return "medium"
    if id_hint in {"freight_bill", "pro"} and document_region in {"document_title", "header", "load_info"}:
        return "medium"
    return "weak"


def _header_candidate_confidence(label_strength, method, id_hint):
    if label_strength == "strong":
        return 0.84 if id_hint in {"load", "order", "shipment", "po"} else 0.78
    if label_strength == "medium":
        return 0.72 if method in {"title_line", "header_key_value", "load_info_key_value"} else 0.66
    return 0.45


def _header_context_penalty(id_hint, document_region):
    if id_hint == "vehicle_noise":
        return "driver_truck_trailer_noise"
    if id_hint in {"pickup_ref", "delivery_ref"}:
        return "pickup_delivery_reference"
    if document_region == "stop_section":
        return "stop_level_reference"
    if document_region == "reference_section" and id_hint in {"bol", "reference"}:
        return "reference_section_id"
    if document_region == "footer_signature":
        return "footer_signature_id"
    if id_hint == "bol":
        return "bol_reference"
    return None


def _header_load_candidate(row, label, value, method, diagnostics):
    diagnostics["candidate_attempt_count"] += 1
    skip_reason = _identifier_value_skip_reason(value)
    if skip_reason:
        diagnostics["rejection_reason_counts"][skip_reason] += 1
        return None
    document_region = _header_document_region(row, label)
    id_hint = _header_id_hint(label)
    penalty = _header_context_penalty(id_hint, document_region)
    if penalty == "driver_truck_trailer_noise":
        diagnostics["rejection_reason_counts"][penalty] += 1
        return None
    label_strength = _header_label_strength(id_hint, document_region, row.get("text", ""))
    primary = bool(
        label_strength in {"strong", "medium"}
        and document_region in {"document_title", "header", "load_info"}
        and id_hint not in {"bol", "reference", "pickup_ref", "delivery_ref", "vehicle_noise"}
    )
    confidence = _header_candidate_confidence(label_strength, method, id_hint)
    if not primary:
        confidence = min(confidence, 0.50)
    diagnostics["candidate_emitted_count"] += 1
    diagnostics["emitted_by_method"][method] += 1
    diagnostics["emitted_by_id_type"][id_hint] += 1
    diagnostics["emitted_by_region"][document_region] += 1
    source = SOURCE_NATIVE_LAYOUT if row.get("bbox") else SOURCE_NATIVE_TEXT
    return _annotate(
        build_field_candidate(
            field=FIELD_LOAD_NUMBER if primary else "reference_numbers",
            value=value,
            normalized_value=value,
            label=label,
            evidence_text=f"{label} [{method}-header-value-present]",
            page=row.get("page"),
            bbox=row.get("bbox"),
            source=source,
            parser_name=GENERATOR_HEADER_LOAD_IDENTITY,
            confidence=confidence,
            metadata={
                "generator_name": GENERATOR_HEADER_LOAD_IDENTITY,
                "document_region": document_region,
                "section_context": row.get("section_context", "unknown"),
                "id_type_hint": id_hint,
                "is_primary_identifier_candidate": primary,
                "is_document_title_or_header_id": document_region in {"document_title", "header", "load_info"},
                "label_strength": label_strength,
                "value_extraction_method": method,
                "pairing_method": method,
                "context_penalty_reason": penalty or "",
                "candidate_value_shape": candidate_value_shape(value),
                "gold_recall_debug": False,
                "header_load_identity_candidate": True,
            },
        ),
        GENERATOR_HEADER_LOAD_IDENTITY,
        independent=True,
    )


def _header_load_identity_generator(artifact, triage=None, legacy_context=None):
    candidates = []
    diagnostics = {
        "rows_scanned_count": 0,
        "label_hits_count": 0,
        "candidate_attempt_count": 0,
        "candidate_emitted_count": 0,
        "rejection_reason_counts": Counter(),
        "emitted_by_method": Counter(),
        "emitted_by_region": Counter(),
        "emitted_by_id_type": Counter(),
    }
    for row in _header_line_rows(artifact):
        diagnostics["rows_scanned_count"] += 1
        row_text = _text(row.get("text"))
        region = _header_document_region(row, "")
        if region not in {"document_title", "header", "load_info", "stop_section", "reference_section", "footer_signature"}:
            continue
        for pattern, stop_reference in [
            (HEADER_LOAD_IDENTITY_PATTERN, False),
            (HEADER_STOP_REFERENCE_PATTERN, True),
        ]:
            for match in pattern.finditer(row_text):
                diagnostics["label_hits_count"] += 1
                label = match.group("label")
                value = match.group("value")
                method = (
                    "title_line"
                    if region == "document_title"
                    else "load_info_key_value"
                    if region == "load_info"
                    else "same_line"
                    if stop_reference
                    else "header_key_value"
                )
                candidate = _header_load_candidate(
                    row,
                    label,
                    value,
                    method,
                    diagnostics,
                )
                if candidate:
                    candidates.append(candidate)
    diagnostics = {
        key: dict(value.most_common()) if isinstance(value, Counter) else value
        for key, value in diagnostics.items()
    }
    return candidates, [], {"header_load_identity_summary": diagnostics}


def _context_candidate_result(legacy_context):
    context = legacy_context or {}
    result = {}
    for key in ["resolution_candidate_result", "candidate_result", "resolver_candidate_result"]:
        value = context.get(key)
        if isinstance(value, dict) and value.get("candidates"):
            result[key] = value
    return result


def _legacy_candidate_result_generator(artifact, triage=None, legacy_context=None):
    candidates = []
    warnings = []
    for key, result in _context_candidate_result(legacy_context).items():
        adapted = adapt_candidate_result_to_field_candidates(
            result,
            parser_name=f"{GENERATOR_LEGACY_CANDIDATE_RESULT}:{key}",
        )
        for candidate in adapted:
            candidates.append(
                _annotate(candidate, GENERATOR_LEGACY_CANDIDATE_RESULT, independent=True)
            )
        warnings.extend(result.get("warnings", []) or [])
    return candidates, warnings


def _legacy_resolution_candidate_generator(artifact, triage=None, legacy_context=None):
    candidates = []
    resolution = (legacy_context or {}).get("resolution_result", {}) or {}
    for item in resolution.get("resolutions", []) or []:
        if not isinstance(item, dict):
            continue
        for candidate in [item.get("selected_candidate", {})] + list(
            item.get("rejected_candidates", []) or []
        ):
            if isinstance(candidate, dict) and candidate:
                adapted = adapt_ratecon_candidate_to_field_candidate(
                    candidate,
                    parser_name=GENERATOR_LEGACY_RESOLUTION_CANDIDATES,
                )
                candidates.append(
                    _annotate(
                        adapted,
                        GENERATOR_LEGACY_RESOLUTION_CANDIDATES,
                        independent=True,
                    )
                )
    return candidates, []


def _legacy_stop_set_generator(artifact, triage=None, legacy_context=None):
    candidates = []
    stop_set = (legacy_context or {}).get("normalized_stop_set", {}) or {}
    span_stop_set = (legacy_context or {}).get("span_normalized_stop_set", {}) or {}
    for source_name, source in [
        ("normalized_stop_set", stop_set),
        ("span_normalized_stop_set", span_stop_set),
    ]:
        if not isinstance(source, dict):
            continue
        stops = [stop for stop in source.get("stops", []) or [] if isinstance(stop, dict)]
        for stop in stops:
            stop_type = _text(stop.get("stop_type"))
            if stop_type not in {"pickup", "delivery"}:
                continue
            field_name = FIELD_PICKUP_STOPS if stop_type == "pickup" else FIELD_DELIVERY_STOPS
            fields = [item for item in stop.get("fields", []) or [] if isinstance(item, dict)]
            field_names = {_text(item.get("field_name")) for item in fields}
            has_location = bool(field_names & {"location", "address", "city_state"})
            has_date = "date" in field_names
            has_time = bool(field_names & {"time", "appointment_window"})
            candidates.append(
                _annotate(
                    build_field_candidate(
                        field=field_name,
                        value=f"{stop_type}_stop_present",
                        normalized_value=f"{stop_type}_stop_present",
                        label=f"{stop_type}_stop",
                        evidence_text=f"{stop_type}_stop: structured evidence present",
                        page=(stop.get("page_numbers") or [""])[0],
                        source=SOURCE_LEGACY_PARSER,
                        parser_name=GENERATOR_LEGACY_STOP_SET,
                        confidence=0.72 if has_location or has_date else 0.6,
                        metadata={
                            "source_stop_set": source_name,
                            "stop_candidate_kind": "structured_stop",
                            "stop_role": stop_type,
                            "stop_count": 1,
                            "has_location": has_location,
                            "has_date": has_date,
                            "has_time": has_time,
                            "structured_stop_candidate": True,
                            "diagnostic_fallback": False,
                        },
                    ),
                    GENERATOR_LEGACY_STOP_SET,
                    independent=True,
                )
            )
        for field_name, count_key in [
            (FIELD_PICKUP_STOPS, "pickup_count"),
            (FIELD_DELIVERY_STOPS, "delivery_count"),
        ]:
            count = int(source.get(count_key, 0) or 0)
            if count <= 0:
                continue
            candidates.append(
                _annotate(
                    build_field_candidate(
                        field=field_name,
                        value=str(count),
                        normalized_value=str(count),
                        label=count_key,
                        evidence_text=f"{count_key}: present",
                        source=SOURCE_LEGACY_PARSER,
                        parser_name=GENERATOR_LEGACY_STOP_SET,
                        confidence=0.68,
                        metadata={
                            "source_stop_set": source_name,
                            "stop_candidate_kind": "count",
                            "stop_role": "pickup"
                            if field_name == FIELD_PICKUP_STOPS
                            else "delivery",
                            "stop_count": count,
                            "structured_stop_candidate": False,
                        },
                    ),
                    GENERATOR_LEGACY_STOP_SET,
                    independent=True,
                )
            )
        for partial_field, count_key in [
            (FIELD_PICKUP_COUNT, "pickup_count"),
            (FIELD_DELIVERY_COUNT, "delivery_count"),
        ]:
            count = int(source.get(count_key, 0) or 0)
            if count <= 0:
                continue
            candidates.append(
                _annotate(
                    build_field_candidate(
                        field=partial_field,
                        value=str(count),
                        normalized_value=str(count),
                        label=count_key,
                        evidence_text=f"{count_key}: present",
                        source=SOURCE_LEGACY_PARSER,
                        parser_name=GENERATOR_LEGACY_STOP_SET,
                        confidence=0.62,
                        metadata={
                            "source_stop_set": source_name,
                            "stop_candidate_kind": "partial_count",
                            "stop_role": "pickup"
                            if partial_field == FIELD_PICKUP_COUNT
                            else "delivery",
                            "stop_count": count,
                            "structured_stop_candidate": False,
                        },
                    ),
                    GENERATOR_LEGACY_STOP_SET,
                    independent=True,
                )
            )
    return candidates, []


def _legacy_final_output_generator(artifact, triage=None, legacy_context=None):
    legacy_summary = (legacy_context or {}).get("legacy_summary", {}) or {}
    values = legacy_summary.get("_comparison_values", {}) or {}
    field_map = {
        "load_number": FIELD_LOAD_NUMBER,
        "total_carrier_rate": FIELD_TOTAL_CARRIER_RATE,
        "broker_name": FIELD_BROKER_NAME,
        "carrier_name": FIELD_CARRIER_NAME,
        "pickup_count": FIELD_PICKUP_STOPS,
        "delivery_count": FIELD_DELIVERY_STOPS,
        "pickup_date": FIELD_PICKUP_STOPS,
        "delivery_date": FIELD_DELIVERY_STOPS,
    }
    candidates = []
    for legacy_field, field_name in field_map.items():
        value = values.get(legacy_field)
        if value in ["", None, 0]:
            continue
        candidates.append(
            _annotate(
                build_field_candidate(
                    field=field_name,
                    value=value,
                    normalized_value=value,
                    label=legacy_field,
                    evidence_text=f"{legacy_field}: legacy final output present",
                    source=SOURCE_LEGACY_FINAL_OUTPUT,
                    parser_name=GENERATOR_LEGACY_FINAL_OUTPUT,
                    confidence=0.55,
                    metadata={
                        "diagnostic_fallback": True,
                        "not_independent_candidate": True,
                        "legacy_field": legacy_field,
                    },
                ),
                GENERATOR_LEGACY_FINAL_OUTPUT,
                independent=False,
            )
        )
    return candidates, []


def _layout_candidate_result_generator(artifact, triage=None, legacy_context=None):
    layout_artifact = (artifact or {}).get("layout_artifact") or {}
    if not layout_artifact.get("pages"):
        return [], ["layout_artifact_missing"], {
            "table_extraction_summary": summarize_tables_for_shadow(artifact or {}),
        }
    result = extract_ratecon_layout_candidates(layout_artifact, classification_result=None)
    candidates = [
        _annotate(candidate, GENERATOR_LAYOUT_CANDIDATE_RESULT, independent=True)
        for candidate in adapt_candidate_result_to_field_candidates(
            result,
            parser_name=GENERATOR_LAYOUT_CANDIDATE_RESULT,
        )
    ]
    return candidates, list(result.get("warnings", []) or []), {
        "layout_candidate_counts_by_field": result.get("candidate_counts_by_field", {}),
        "layout_pages_considered": result.get("layout_pages_considered", []),
        "table_extraction_summary": summarize_tables_for_shadow(artifact or {}),
    }


def _layout_load_pairing_generator(artifact, triage=None, legacy_context=None):
    if not _has_coordinate_layout_data(artifact):
        return [], ["coordinate_layout_data_missing"], {
            "layout_load_pairing_summary": generate_layout_load_identity_candidates({})[1]
        }
    candidates, diagnostics = generate_layout_load_identity_candidates(artifact or {})
    candidates = [
        _annotate(candidate, GENERATOR_LAYOUT_LOAD_PAIRING, independent=True)
        for candidate in candidates
    ]
    return candidates, [], {"layout_load_pairing_summary": diagnostics}


def _layout_stop_table_generator(artifact, triage=None, legacy_context=None):
    if not _has_coordinate_layout_data(artifact):
        return [], ["coordinate_layout_data_missing"], {
            "layout_stop_pairing_summary": generate_layout_stop_table_candidates({})[1]
        }
    candidates, diagnostics = generate_layout_stop_table_candidates(artifact or {})
    candidates = [
        _annotate(candidate, GENERATOR_LAYOUT_STOP_TABLE, independent=True)
        for candidate in candidates
    ]
    return candidates, [], {"layout_stop_pairing_summary": diagnostics}


DEFAULT_GENERATORS = (
    FieldCandidateGenerator(
        GENERATOR_TEXT_CANDIDATES,
        "native_text",
        _text_candidate_generator,
    ),
    FieldCandidateGenerator(
        GENERATOR_LOAD_ID_LINES,
        "native_text",
        _load_identifier_line_generator,
    ),
    FieldCandidateGenerator(
        GENERATOR_LAYOUT_CANDIDATE_RESULT,
        "native_layout",
        _layout_candidate_result_generator,
    ),
    FieldCandidateGenerator(
        GENERATOR_LAYOUT_LOAD_PAIRING,
        "native_layout",
        _layout_load_pairing_generator,
    ),
    FieldCandidateGenerator(
        GENERATOR_LAYOUT_STOP_TABLE,
        "native_layout",
        _layout_stop_table_generator,
    ),
    FieldCandidateGenerator(
        GENERATOR_LEGACY_CANDIDATE_RESULT,
        "legacy_intermediate",
        _legacy_candidate_result_generator,
    ),
    FieldCandidateGenerator(
        GENERATOR_LEGACY_RESOLUTION_CANDIDATES,
        "legacy_intermediate",
        _legacy_resolution_candidate_generator,
    ),
    FieldCandidateGenerator(
        GENERATOR_LEGACY_STOP_SET,
        "legacy_intermediate",
        _legacy_stop_set_generator,
    ),
)


def generate_field_candidates(
    artifact,
    triage=None,
    legacy_context=None,
    include_legacy_final_candidates=True,
    strict=False,
    generators=None,
    load_candidate_profile=LOAD_CANDIDATE_PROFILE_BASELINE,
):
    active_generators = list(generators or DEFAULT_GENERATORS)
    if generators is None and load_candidate_profile == LOAD_CANDIDATE_PROFILE_HEADER_RECALL_V1:
        active_generators.insert(
            2,
            FieldCandidateGenerator(
                GENERATOR_HEADER_LOAD_IDENTITY,
                "native_text_layout_header",
                _header_load_identity_generator,
            ),
        )

    candidates = []
    summaries = []
    errors = []
    for generator in active_generators:
        try:
            generated_result = generator.generate_candidates(
                artifact,
                triage,
                legacy_context or {},
            )
            if isinstance(generated_result, tuple) and len(generated_result) == 3:
                generated, warnings, diagnostics = generated_result
            else:
                generated, warnings = generated_result
                diagnostics = {}
        except Exception as exc:
            if strict:
                raise
            generated = []
            warnings = []
            diagnostics = {}
            errors.append(
                {
                    "generator_name": generator.name,
                    "error_type": exc.__class__.__name__,
                }
            )
        candidates.extend(generated)
        summaries.append(
            _summary(
                generator.name,
                generator.source_type,
                generated,
                warnings,
                diagnostics=diagnostics,
            )
        )

    if generators is None:
        try:
            stop_evidence = extract_stop_evidence_from_candidates(
                candidates,
                artifact=artifact,
                triage=triage,
            )
            generated = assemble_stop_candidates(
                stop_evidence,
                artifact=artifact,
                triage=triage,
            )
            diagnostics = summarize_stop_assembly(stop_evidence, generated)
            warnings = []
        except Exception as exc:
            if strict:
                raise
            generated = []
            warnings = []
            diagnostics = {}
            errors.append(
                {
                    "generator_name": GENERATOR_STOP_EVIDENCE_ASSEMBLER,
                    "error_type": exc.__class__.__name__,
                }
            )
        candidates.extend(generated)
        summaries.append(
            _summary(
                GENERATOR_STOP_EVIDENCE_ASSEMBLER,
                "shadow_evidence_assembly",
                generated,
                warnings,
                diagnostics=diagnostics,
            )
        )

    if include_legacy_final_candidates:
        generator = FieldCandidateGenerator(
            GENERATOR_LEGACY_FINAL_OUTPUT,
            "legacy_final_output",
            _legacy_final_output_generator,
        )
        try:
            generated, warnings = generator.generate_candidates(
                artifact,
                triage,
                legacy_context or {},
            )
            diagnostics = {}
        except Exception as exc:
            if strict:
                raise
            generated = []
            warnings = []
            diagnostics = {}
            errors.append(
                {
                    "generator_name": generator.name,
                    "error_type": exc.__class__.__name__,
                }
            )
        candidates.extend(generated)
        summaries.append(
            _summary(
                generator.name,
                generator.source_type,
                generated,
                warnings,
                diagnostics=diagnostics,
            )
        )

    candidates = enrich_candidates_context(candidates)
    return _build_result(candidates=candidates, summaries=summaries, errors=errors)
