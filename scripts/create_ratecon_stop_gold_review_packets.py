"""Create local-only stop gold review packets from RateCon gold evaluation.

The output is private review material and must stay under .local_outputs.
This script does not modify gold labels.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.ratecon_gold_labels import (  # noqa: E402
    FIELD_DELIVERY_STOPS,
    FIELD_PICKUP_STOPS,
    STOP_GOLD_COMPLETENESS_COMPONENTS,
    SYSTEM_SHADOW,
    SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP,
    SYSTEM_SHADOW_REVIEW_FUSED_STOPS,
    SYSTEM_SHADOW_STOP_REVIEW_DRAFT,
    build_stop_gold_completeness_summary,
    evaluate_ratecon_against_gold,
    load_gold_labels,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_stop_gold_review_v2")
EVALUATION_SUMMARY_NAME = "ratecon_gold_evaluation_summary.json"
STOP_REVIEW_CATEGORIES = (
    "code_or_evaluator_issue",
    "extraction_candidate_issue",
    "true_gold_review_needed",
    "no_action_needed",
)

EXCLUSIVE_PACKET_CATEGORIES = (
    "code_or_evaluator_issue",
    "extraction_candidate_issue",
    "true_gold_review_needed",
    "known_absent_no_action",
    "other_no_action",
)

LOCAL_ONLY_STOP_COMPONENTS = (
    "raw_location_text_local_only",
    "unparsed_location_text_local_only",
)

KNOWN_ABSENT_REASONS = {
    "known_absent_in_document",
    "gold_uncertain_city_level_only",
    "gold_missing_optional_component_but_not_required",
    "gold_time_window_not_visible_in_source",
    "gold_component_absent_but_document_lacks_value",
}

STOP_COMPONENT_VALUE_KEYS = (
    *STOP_GOLD_COMPLETENESS_COMPONENTS,
    *LOCAL_ONLY_STOP_COMPONENTS,
)


def _text(value) -> str:
    return str(value or "").strip()


def _read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _evaluation_from_dir(eval_dir):
    if not eval_dir:
        return None
    summary = Path(eval_dir) / EVALUATION_SUMMARY_NAME
    if not summary.exists():
        return None
    return _read_json(summary)


def _is_under_local_outputs(path: Path) -> bool:
    resolved = path.resolve()
    local_outputs = (REPO_ROOT / ".local_outputs").resolve()
    return resolved == local_outputs or local_outputs in resolved.parents


def _gold_stop_completeness(stop):
    stop = stop if isinstance(stop, dict) else {}
    components = {
        component: bool(_text(stop.get(component)))
        for component in STOP_GOLD_COMPLETENESS_COMPONENTS
    }
    missing = [key for key, present in components.items() if not present]
    has_city_state = components["city"] and components["state"]
    has_location = has_city_state or components["address"] or components["facility"]
    complete_dispatch = bool(has_location and components["date"])
    complete_exact = bool(
        complete_dispatch
        and (components["time"] or components["appointment_window"])
    )
    return {
        "components_present": components,
        "missing_components": missing,
        "complete_for_exact": complete_exact,
        "complete_for_dispatch_usable": complete_dispatch,
        "incomplete_for_dispatch_usable": not complete_dispatch,
        "uncertain": bool(stop.get("uncertain")),
        "notes": _text(stop.get("notes")),
    }


def _gold_by_doc_field(gold_labels):
    lookup = {}
    for label in gold_labels or []:
        if _text(label.get("label_status")) in {"", "skipped", "unlabeled"}:
            continue
        gold = label.get("gold", {}) if isinstance(label.get("gold"), dict) else {}
        for field in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
            stops = gold.get(field, []) if isinstance(gold.get(field), list) else []
            lookup[(_text(label.get("document_id")), _text(label.get("file_hash")), field)] = {
                "file_name": _text(label.get("file_name")),
                "stops": stops,
                "completeness": [_gold_stop_completeness(stop) for stop in stops],
                "label_review_notes": _text(
                    (label.get("labeler") or {}).get("review_notes")
                    if isinstance(label.get("labeler"), dict)
                    else ""
                ),
            }
    return lookup


def _safe_row_summary(row):
    row = row if isinstance(row, dict) else {}
    return {
        "system": _text(row.get("system")),
        "raw_status": _text(row.get("status")),
        "dispatch_usability_tier": _text(row.get("dispatch_usability_tier") or row.get("stop_usability_tier")),
        "source_status": _text(row.get("source_status")),
        "source": _text(row.get("source")),
        "parser_name": _text(row.get("parser_name")),
        "pairing_method": _text(row.get("pairing_method")),
        "confidence": row.get("confidence"),
        "candidate_has_dispatch_components": bool(
            row.get("candidate_has_dispatch_components") or row.get("dispatch_usable")
        ),
        "gold_dispatch_usable_match": row.get("gold_dispatch_usable_match"),
        "candidate_review_tier": _text(row.get("candidate_review_tier")),
        "has_location": bool(row.get("has_location")),
        "has_date": bool(row.get("has_date")),
        "has_time": bool(row.get("has_time")),
        "stop_selection_policy": _text(row.get("stop_selection_policy")),
        "stop_abstention_reason": _text(row.get("stop_abstention_reason")),
        "serialization_gap_classification": _text(row.get("serialization_gap_classification")),
        "dispatch_usability_note": _text(row.get("dispatch_usability_note")),
        "issues": list(row.get("issues") or []),
    }


def _audit_by_doc_field(audit_records):
    lookup = {}
    for record in audit_records or []:
        if not isinstance(record, dict):
            continue
        document_id = _text(record.get("document_id"))
        file_hash = _text(record.get("file_hash"))
        file_name = _text(record.get("file_name"))
        for key in [
            (document_id, file_hash),
            (document_id, ""),
            ("", file_hash),
            (file_name, file_hash),
        ]:
            if key[0] or key[1]:
                lookup[key] = record
    return lookup


def _record_for_key(audit_lookup, key):
    document_id, file_hash, _field = key
    return (
        audit_lookup.get((document_id, file_hash))
        or audit_lookup.get((document_id, ""))
        or audit_lookup.get(("", file_hash))
        or {}
    )


def _private_eval_values(record):
    if not isinstance(record, dict):
        return {}
    values = record.get("private_eval_values")
    return values if isinstance(values, dict) else {}


def _private_prediction(record, system_name, field_name):
    private_values = _private_eval_values(record)
    group_name = system_name
    if system_name == SYSTEM_SHADOW:
        group_name = "shadow_selected_stop"
    group = private_values.get(group_name)
    if not isinstance(group, dict) and system_name == SYSTEM_SHADOW:
        group = private_values.get("shadow_selected")
    if not isinstance(group, dict):
        return {}
    prediction = group.get(field_name)
    return prediction if isinstance(prediction, dict) else {}


def _stop_component_values_from_prediction(prediction, include_private_values):
    if not include_private_values or not isinstance(prediction, dict):
        return {}
    value = prediction.get("value")
    if isinstance(value, dict):
        stops = [value]
    elif isinstance(value, list):
        stops = [item for item in value if isinstance(item, dict)]
    else:
        stops = []
    if not stops:
        return {}
    stop = stops[0]
    return {
        component: _text(stop.get(component))
        for component in [*STOP_GOLD_COMPLETENESS_COMPONENTS, *LOCAL_ONLY_STOP_COMPONENTS]
    }


def _first_stop_from_prediction(prediction):
    prediction = prediction if isinstance(prediction, dict) else {}
    value = prediction.get("value")
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), {})
    return {}


def _gold_component_values(gold_info, include_private_values):
    if not include_private_values:
        return {}
    stops = gold_info.get("stops", []) if isinstance(gold_info, dict) else []
    stop = next((item for item in stops if isinstance(item, dict)), {})
    return {
        component: _text(stop.get(component))
        for component in STOP_GOLD_COMPLETENESS_COMPONENTS
    }


def _gold_stop_index(gold_info):
    stops = gold_info.get("stops", []) if isinstance(gold_info, dict) else []
    stop = next((item for item in stops if isinstance(item, dict)), {})
    return stop.get("stop_index") or 1


def _source_hint_from_prediction(prediction):
    prediction = prediction if isinstance(prediction, dict) else {}
    metadata = prediction.get("metadata_summary")
    metadata = metadata if isinstance(metadata, dict) else {}
    return {
        "source": _text(prediction.get("source")),
        "parser_name": _text(prediction.get("parser_name")),
        "pairing_method": _text(metadata.get("pairing_method")),
        "page": _text(prediction.get("page")),
    }


def _selected_stop_side_by_side_items(evaluation, audit_lookup, gold_lookup, include_private_values):
    rows = []
    for row in evaluation.get("comparison_rows", []) or []:
        if row.get("system") != SYSTEM_SHADOW:
            continue
        if row.get("field") not in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
            continue
        key = (row.get("document_id"), row.get("file_hash"), row.get("field"))
        gold_info = gold_lookup.get(key, {})
        record = _record_for_key(audit_lookup, key)
        prediction = _private_prediction(record, SYSTEM_SHADOW, row.get("field"))
        selected_stop = _first_stop_from_prediction(prediction)
        selected_components = _stop_component_values_from_prediction(
            prediction,
            include_private_values,
        )
        gold_components = _gold_component_values(gold_info, include_private_values)
        metadata = prediction.get("metadata_summary", {}) if isinstance(prediction, dict) else {}
        gap_reason = (
            _text(row.get("serialization_gap_classification"))
            or _text(row.get("serialization_gap_reason"))
            or _text(metadata.get("serialization_gap_reason"))
        )
        fix_status = ""
        if row.get("source_status") == "shadow_component_not_serialized":
            fix_status = (
                "true_missing"
                if gap_reason == "selected_stop_really_missing"
                else "needs_private_eval_serialization"
            )
        elif row.get("source_status") in {
            "unsupported_unparsed_location",
            "selected_partial_not_comparable",
            "selected_partial_missing_required_components",
        }:
            fix_status = "unsupported_selected_partial"
        elif row.get("status") in {"extractor_missing", "shadow_extractor_missing"}:
            fix_status = "selected_missing_or_review_required"
        else:
            fix_status = "comparable"
        rows.append(
            {
                "document_id": _text(row.get("document_id")),
                "file_hash": _text(row.get("file_hash")),
                "file_name": _text(row.get("file_name")),
                "field": _text(row.get("field")),
                "stop_index": selected_stop.get("stop_index") or _gold_stop_index(gold_info),
                "selected_source": _text(prediction.get("source")) if isinstance(prediction, dict) else "",
                "selected_parser_name": _text(prediction.get("parser_name")) if isinstance(prediction, dict) else "",
                "selected_pairing_method": _text(metadata.get("pairing_method")),
                "raw_status": _text(row.get("status")),
                "dispatch_usability_tier": _text(
                    row.get("dispatch_usability_tier") or row.get("stop_usability_tier")
                ),
                "serialization_gap_reason": gap_reason,
                "fix_status": fix_status,
                "gold_components": gold_components,
                "selected_components": selected_components,
            }
        )
    return rows


def _missing_gold_components(gold_info):
    missing = set()
    for item in gold_info.get("completeness", []) or []:
        missing.update(item.get("missing_components", []) or [])
    return sorted(missing)


def _gold_notes_text(gold_info):
    parts = [_text(gold_info.get("label_review_notes"))]
    for stop in gold_info.get("stops", []) or []:
        if isinstance(stop, dict):
            parts.append(_text(stop.get("notes")))
    return " ".join(part for part in parts if part).lower()


def _gold_has_uncertain_city_level_stop(gold_info):
    notes = _gold_notes_text(gold_info)
    note_indicates_city_level = any(
        marker in notes
        for marker in [
            "city-level",
            "city/state",
            "only origin",
            "only destination",
            "only city",
            "no shipper/address",
            "no consignee/address",
            "no address",
        ]
    )
    for stop in gold_info.get("stops", []) or []:
        if not isinstance(stop, dict):
            continue
        has_city_state_date = bool(
            _text(stop.get("city")) and _text(stop.get("state")) and _text(stop.get("date"))
        )
        if stop.get("uncertain") and has_city_state_date and note_indicates_city_level:
            return True
    return False


def _notes_imply_missing_time_should_exist(gold_info):
    notes = _gold_notes_text(gold_info)
    return any(
        marker in notes
        for marker in [
            "time visible",
            "appointment visible",
            "window visible",
            "time/window visible",
            "source shows time",
            "document shows time",
            "visible time",
            "visible window",
        ]
    )


def _known_absent_reason(gold_info):
    missing = set(_missing_gold_components(gold_info))
    if not missing:
        return ""
    city_level_uncertain = _gold_has_uncertain_city_level_stop(gold_info)
    actionable_time_missing = (
        {"time", "appointment_window"}.issubset(missing)
        and _notes_imply_missing_time_should_exist(gold_info)
    )
    if city_level_uncertain and {"time", "appointment_window"}.issubset(missing):
        if not _notes_imply_missing_time_should_exist(gold_info):
            return "gold_time_window_not_visible_in_source"
    optional_location_missing = missing.intersection({"facility", "address", "zip"})
    required_dispatch_present = not missing.intersection({"city", "state", "date"})
    if actionable_time_missing:
        return ""
    if optional_location_missing and required_dispatch_present and city_level_uncertain:
        return "gold_uncertain_city_level_only"
    if optional_location_missing and required_dispatch_present:
        return "gold_missing_optional_component_but_not_required"
    return ""


def _reason_for_case(selected, dispatch, draft, gold_info):
    selected = selected if isinstance(selected, dict) else {}
    dispatch = dispatch if isinstance(dispatch, dict) else {}
    draft = draft if isinstance(draft, dict) else {}
    missing = set(_missing_gold_components(gold_info))
    if selected and selected.get("source_status") == "shadow_component_not_serialized":
        return (
            _text(selected.get("serialization_gap_classification"))
            or _text(selected.get("serialization_gap_reason"))
            or "evaluator_serialized_gap"
        )
    if selected and selected.get("source_status") == "unsupported_unparsed_location":
        return "unsupported_unparsed_location"
    if selected and selected.get("source_status") == "selected_partial_not_comparable":
        return "selected_partial_not_comparable"
    if selected and selected.get("source_status") == "selected_partial_missing_required_components":
        return "selected_partial_missing_required_components"
    if dispatch.get("status") == "partial_match" and dispatch.get("dispatch_usability_tier") == "unsafe_wrong":
        return "candidate_partial_match_but_unsafe_by_usability"
    if dispatch.get("predicted") and not dispatch.get("status"):
        return "candidate_not_compared"
    known_absent = _known_absent_reason(gold_info)
    if known_absent:
        return known_absent
    if dispatch.get("predicted") and missing:
        return "selected_has_dispatch_components_but_gold_incomplete"
    if "date" in missing:
        return "gold_missing_date"
    if "time" in missing and "appointment_window" in missing:
        return "gold_missing_time_or_window"
    if "city" in missing or "state" in missing:
        return "gold_missing_city_state"
    if draft.get("predicted"):
        return "candidate_is_review_draft_only"
    return "manual_review_needed"


def _secondary_reasons_for_case(selected, dispatch, draft, gold_info):
    selected = selected if isinstance(selected, dict) else {}
    dispatch = dispatch if isinstance(dispatch, dict) else {}
    draft = draft if isinstance(draft, dict) else {}
    missing = set(_missing_gold_components(gold_info))
    reasons = []
    if selected and selected.get("source_status") == "shadow_component_not_serialized":
        reasons.append(
            _text(selected.get("serialization_gap_classification"))
            or _text(selected.get("serialization_gap_reason"))
            or "evaluator_serialized_gap"
        )
    if selected and selected.get("source_status") in {
        "unsupported_unparsed_location",
        "selected_partial_not_comparable",
        "selected_partial_missing_required_components",
    }:
        reasons.append(_text(selected.get("source_status")))
    if dispatch.get("status") == "partial_match" and dispatch.get("dispatch_usability_tier") == "unsafe_wrong":
        reasons.append("candidate_partial_match_but_unsafe_by_usability")
    if dispatch.get("predicted") and missing:
        reasons.append("dispatch_candidate_compared_against_incomplete_gold")
    known_absent = _known_absent_reason(gold_info)
    if known_absent:
        reasons.append(known_absent)
        reasons.append("known_absent_in_document")
    if draft.get("predicted"):
        reasons.append("candidate_is_review_draft_only")
    return sorted(set(reasons))


def _true_gold_review_needed(gold_info):
    if _known_absent_reason(gold_info):
        return False
    for item in gold_info.get("completeness", []) or []:
        missing = set(item.get("missing_components", []) or [])
        if "date" in missing or "city" in missing or "state" in missing:
            return True
        if "time" in missing and "appointment_window" in missing:
            return True
        if item.get("incomplete_for_dispatch_usable"):
            return True
    return False


def _item_categories(selected, dispatch, draft, gold_info, primary_reason, secondary_reasons):
    selected = selected if isinstance(selected, dict) else {}
    dispatch = dispatch if isinstance(dispatch, dict) else {}
    draft = draft if isinstance(draft, dict) else {}
    reasons = {primary_reason, *(secondary_reasons or [])}
    categories = set()
    if reasons.intersection(KNOWN_ABSENT_REASONS):
        categories.add("no_action_needed")
    if any(
        reason in reasons
        for reason in {
            "evaluator_serialized_gap",
            "selected_stop_components_exist_but_not_in_resolved_output",
            "selected_candidate_components_exist_but_not_joined_to_selected",
            "selected_candidate_id_missing",
            "selected_candidate_id_mismatch",
            "resolver_selected_summary_lost_structured_value",
            "audit_redaction_removed_private_components",
            "private_eval_sidecar_missing_components",
            "evaluator_lookup_path_bug",
            "review_packet_lookup_path_bug",
        }
    ):
        categories.add("code_or_evaluator_issue")
    candidate_issues = set(dispatch.get("issues") or []) | set(draft.get("issues") or [])
    if (
        "candidate_partial_match_but_unsafe_by_usability" in reasons
        or "unsupported_unparsed_location" in reasons
        or "selected_partial_not_comparable" in reasons
        or "selected_partial_missing_required_components" in reasons
        or any(issue.startswith("wrong_") for issue in candidate_issues)
        or dispatch.get("dispatch_usability_tier") == "unsafe_wrong"
        or draft.get("dispatch_usability_tier") == "unsafe_wrong"
    ):
        categories.add("extraction_candidate_issue")
    if _true_gold_review_needed(gold_info):
        categories.add("true_gold_review_needed")
    if not categories:
        categories.add("no_action_needed")
    return sorted(categories, key=STOP_REVIEW_CATEGORIES.index)


def _primary_category(categories):
    for category in STOP_REVIEW_CATEGORIES:
        if category in categories:
            return category
    return "no_action_needed"


def _recommendation_for_reason(reason):
    if reason == "evaluator_serialized_gap":
        return "evaluator_bug_suspected"
    if reason in {
        "unsupported_unparsed_location",
        "selected_partial_not_comparable",
        "selected_partial_missing_required_components",
    }:
        return "candidate_is_review_draft_only"
    if reason in {
        "gold_missing_date",
        "gold_missing_time_or_window",
        "gold_missing_city_state",
        "selected_has_dispatch_components_but_gold_incomplete",
    }:
        return "manually_review_gold"
    if reason == "candidate_partial_match_but_unsafe_by_usability":
        return "candidate_is_review_draft_only"
    if reason in KNOWN_ABSENT_REASONS:
        return "leave_as_is"
    return "manual_review_needed"


def _comparison_rows_by_doc_field(evaluation):
    by_key = {}
    for row in evaluation.get("comparison_rows", []) or []:
        if row.get("field") not in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
            continue
        key = (row.get("document_id"), row.get("file_hash"), row.get("field"))
        by_key.setdefault(key, {})[row.get("system")] = row
    return by_key


def _known_absent_summary(review_items):
    known_items = [
        item
        for item in review_items or []
        if item.get("suspect_reason") in KNOWN_ABSENT_REASONS
        or set(item.get("secondary_reasons", []) or []).intersection(KNOWN_ABSENT_REASONS)
    ]
    by_reason = {}
    examples = []
    for item in known_items:
        reasons = [
            reason
            for reason in [item.get("suspect_reason"), *(item.get("secondary_reasons", []) or [])]
            if reason in KNOWN_ABSENT_REASONS
        ]
        for reason in sorted(set(reasons)):
            by_reason[reason] = by_reason.get(reason, 0) + 1
        if len(examples) < 5:
            examples.append(
                {
                    "document_id": item.get("document_id", ""),
                    "file_name": item.get("file_name", ""),
                    "field": item.get("field", ""),
                    "reason": item.get("suspect_reason", ""),
                }
            )
    return {
        "known_absent_items": len(known_items),
        "by_reason": by_reason,
        "patch_rows_suppressed": len(known_items),
        "examples": examples,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _item_has_known_absent_reason(item):
    reasons = {item.get("suspect_reason"), *(item.get("secondary_reasons", []) or [])}
    return bool(reasons.intersection(KNOWN_ABSENT_REASONS))


def _exclusive_category_for_item(item):
    categories = set(item.get("categories", []) or [])
    if "code_or_evaluator_issue" in categories:
        return "code_or_evaluator_issue"
    if "true_gold_review_needed" in categories:
        return "true_gold_review_needed"
    if "extraction_candidate_issue" in categories:
        return "extraction_candidate_issue"
    if _item_has_known_absent_reason(item):
        return "known_absent_no_action"
    return "other_no_action"


def _exclusive_category_counts(review_items):
    counts = {category: 0 for category in EXCLUSIVE_PACKET_CATEGORIES}
    for item in review_items or []:
        counts[_exclusive_category_for_item(item)] += 1
    counts["total_unique_items"] = len(review_items or [])
    counts["notes"] = (
        "exclusive_category_counts are mutually exclusive. category_counts and "
        "known_absent_summary may overlap because a row can have multiple diagnostic reasons."
    )
    return counts


def _row_issues(summary):
    summary = summary if isinstance(summary, dict) else {}
    return {_text(issue) for issue in summary.get("issues", []) or [] if _text(issue)}


def _component_presence(components, summary=None):
    components = components if isinstance(components, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    has_location = bool(summary.get("has_location")) or any(
        _text(components.get(component))
        for component in [
            "facility",
            "address",
            "city",
            "state",
            "zip",
            "raw_location_text_local_only",
            "unparsed_location_text_local_only",
        ]
    )
    has_date = bool(summary.get("has_date")) or bool(_text(components.get("date")))
    has_time = bool(summary.get("has_time")) or bool(
        _text(components.get("time")) or _text(components.get("appointment_window"))
    )
    return {"location": has_location, "date": has_date, "time": has_time}


def _prediction_component_payload(item, prefix):
    values = item.get(f"{prefix}_components", {}) or {}
    return {
        component: _text(values.get(component))
        for component in STOP_COMPONENT_VALUE_KEYS
    }


def _role_from_field(field_name, metadata=None):
    metadata = metadata if isinstance(metadata, dict) else {}
    role = _text(metadata.get("stop_role") or metadata.get("role"))
    if role in {"pickup", "delivery"}:
        return role
    field_name = _text(field_name)
    if field_name.startswith("pickup_") or field_name == FIELD_PICKUP_STOPS:
        return "pickup"
    if field_name.startswith("delivery_") or field_name == FIELD_DELIVERY_STOPS:
        return "delivery"
    return "unknown"


def _field_from_role(role):
    if role == "pickup":
        return FIELD_PICKUP_STOPS
    if role == "delivery":
        return FIELD_DELIVERY_STOPS
    return ""


def _component_values_from_stop(stop):
    stop = stop if isinstance(stop, dict) else {}
    city_state_zip = " ".join(
        part
        for part in [
            _text(stop.get("city")),
            _text(stop.get("state")),
            _text(stop.get("zip")),
        ]
        if part
    )
    raw_location = (
        _text(stop.get("raw_location_text_local_only"))
        or _text(stop.get("unparsed_location_text_local_only"))
        or _text(stop.get("location"))
        or _text(stop.get("value"))
    )
    return {
        "facility": _text(stop.get("facility")),
        "address": _text(stop.get("address")),
        "city_state_zip": city_state_zip,
        "date": _text(stop.get("date")),
        "time": _text(stop.get("time")),
        "appointment_window": _text(stop.get("appointment_window")),
        "raw_location": raw_location,
    }


def _component_values_from_inventory_item(item):
    item = item if isinstance(item, dict) else {}
    value = item.get("value")
    field = _text(item.get("field"))
    values = []
    if field.endswith("_location"):
        if isinstance(value, dict):
            component_values = _component_values_from_stop(value)
            for component in ["facility", "address", "city_state_zip", "raw_location"]:
                if _text(component_values.get(component)):
                    values.append((component, _text(component_values.get(component))))
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    component_values = _component_values_from_stop(entry)
                    for component in ["facility", "address", "city_state_zip", "raw_location"]:
                        if _text(component_values.get(component)):
                            values.append((component, _text(component_values.get(component))))
        elif _text(value):
            values.append(("raw_location", _text(value)))
    elif field.endswith("_date"):
        if _text(value):
            values.append(("date", _text(value)))
    elif field.endswith("_time"):
        if _text(value):
            values.append(("time", _text(value)))
    elif field in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
        stops = value if isinstance(value, list) else [value]
        for stop in stops:
            if not isinstance(stop, dict):
                continue
            component_values = _component_values_from_stop(stop)
            for component, component_value in component_values.items():
                if _text(component_value):
                    values.append((component, _text(component_value)))
    return values


def _metadata_page(metadata):
    for key in ["page", "page_number", "source_page"]:
        if metadata.get(key) not in {None, ""}:
            return metadata.get(key)
    line_span = metadata.get("line_span")
    if isinstance(line_span, dict):
        for key in ["page", "page_number"]:
            if line_span.get(key) not in {None, ""}:
                return line_span.get(key)
    return None


def _metadata_line_index(metadata):
    for key in ["line_index", "reading_order_index", "source_line_index"]:
        if metadata.get(key) not in {None, ""}:
            return metadata.get(key)
    offsets = metadata.get("component_line_offsets")
    if isinstance(offsets, dict):
        values = [value for value in offsets.values() if value not in {None, ""}]
        if values:
            return min(values)
    line_span = metadata.get("line_span")
    if isinstance(line_span, dict):
        for key in ["start", "start_line_index", "line_start"]:
            if line_span.get(key) not in {None, ""}:
                return line_span.get(key)
    return None


def _metadata_bbox(metadata):
    for key in ["bbox", "component_bboxes"]:
        value = metadata.get(key)
        if value is not None and value != "" and value != {}:
            return value
    return None


def _metadata_lineage(metadata, *keys):
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
    return []


def _component_sources_for_item(item, metadata, component):
    for value in [item.get("component_sources"), metadata.get("component_sources")]:
        if not isinstance(value, dict):
            continue
        refs = value.get(component)
        if isinstance(refs, list):
            return refs
        if isinstance(refs, dict):
            return [refs]
    return []


def _normalized_component_source(item, metadata):
    source = _text(item.get("source")).lower()
    parser = _text(item.get("parser_name")).lower()
    if metadata.get("assembled_from_column_geometry") or "ocr_stop_table_reconstructor" in parser:
        return "ocr_geometry_column"
    if metadata.get("ocr_candidate") or "ocr" in source or "ocr" in parser:
        if metadata.get("component_bboxes_available") or metadata.get("geometry_available"):
            return "ocr_tsv"
        return "ocr_text"
    if item.get("table_based") or metadata.get("table_cell_candidate"):
        return "pdfplumber_table" if "pdfplumber" in source or "pdfplumber" in parser else "native_layout"
    if item.get("layout_based") or "layout" in source or "layout" in parser:
        return "native_layout"
    if item.get("legacy_fallback") or "legacy" in source or "legacy" in parser:
        return "legacy_fallback"
    if "stop_evidence_assembler" in parser or "stop_evidence_assembler" in source:
        return "stop_evidence_assembler"
    if "text" in source:
        return "native_text"
    return _text(item.get("source")) or "unknown"


def _source_has_page_line_limitations(source, source_group):
    source = _text(source)
    source_group = _text(source_group)
    return bool(
        source == "legacy_fallback"
        or source_group == "legacy_fallback_stop_candidate"
        or source_group
        in {
            "shadow_selected_stop",
            "shadow_best_structured_stop_candidate",
            "shadow_best_dispatch_usable_stop_candidate",
            "shadow_best_ocr_column_stop_candidate",
            "shadow_best_native_layout_stop_candidate",
            "shadow_stop_review_draft",
            "review_fused_stops",
        }
    )


def _page_line_status(entry):
    explicit = _text(entry.get("page_line_status"))
    if explicit:
        return explicit
    if entry.get("safety_status") == "unsafe":
        return "unsafe_source"
    if entry.get("page") not in {None, ""} or entry.get("line_index") not in {None, ""} or entry.get("bbox"):
        return "available"
    if _source_has_page_line_limitations(entry.get("source"), entry.get("source_group")):
        return "unavailable_from_source"
    return "dropped_by_pipeline"


def _source_safety_status(item, metadata):
    warning_values = []
    for key in [
        "stop_alignment_warnings",
        "stop_geometry_warnings",
        "stop_column_warnings",
        "alignment_warnings",
        "warnings",
        "unsafe_reason",
        "abstention_reason",
        "stop_abstention_reason",
        "section_context",
        "document_region",
    ]:
        value = metadata.get(key)
        if isinstance(value, list):
            warning_values.extend(_text(entry) for entry in value)
        else:
            warning_values.append(_text(value))
    warning_text = " ".join(value for value in warning_values if value).lower()
    reference_flag = bool(
        metadata.get("is_stop_level_reference")
        or metadata.get("is_pickup_delivery_reference")
        or metadata.get("is_bol_or_po_or_customer_ref")
    )
    if reference_flag or any(
        token in warning_text
        for token in ["payment", "instruction", "footer", "terms", "reference"]
    ):
        return "unsafe", "component_from_payment_or_instruction"
    if _role_from_field(item.get("field"), metadata) == "unknown":
        return "risky", "role_unclear"
    if not _text(item.get("source")) and not _text(item.get("parser_name")):
        return "unknown", "missing_source"
    return "safe", None


def _provenance_status(entry):
    if entry.get("safety_status") == "unsafe":
        return "unsafe_source"
    if not _text(entry.get("role")) or entry.get("role") == "unknown":
        return "missing_role"
    if not _text(entry.get("candidate_id")):
        return "missing_candidate_id"
    if not _text(entry.get("source")) or entry.get("source") == "unknown":
        return "missing_source"
    page_line_status = _page_line_status(entry)
    if page_line_status == "unavailable_from_source":
        return "page_line_unavailable_from_source"
    if page_line_status == "dropped_by_pipeline":
        return "page_line_dropped_by_pipeline"
    return "complete"


def _inventory_entries_from_record(record, include_private_values):
    private_values = _private_eval_values(record)
    inventory = private_values.get("stop_component_candidate_inventory", [])
    entries = []
    def append_entries(item, source_group="candidate_inventory"):
        if not isinstance(item, dict):
            return
        metadata = item.get("metadata_summary") if isinstance(item.get("metadata_summary"), dict) else {}
        role = _role_from_field(item.get("field"), metadata)
        normalized_source = _normalized_component_source(item, metadata)
        safety_status, unsafe_reason = _source_safety_status(item, metadata)
        for component, value in _component_values_from_inventory_item(item):
            candidate_id = _text(item.get("candidate_id") or metadata.get("candidate_id"))
            component_source_refs = _component_sources_for_item(item, metadata, component)
            source_lineage = (
                component_source_refs
                if component_source_refs
                else (
                item.get("source_lineage")
                if isinstance(item.get("source_lineage"), list)
                else _metadata_lineage(metadata, "source_lineage", "component_source_list", "source_components")
                )
            )
            dedupe_lineage = (
                item.get("dedupe_lineage")
                if isinstance(item.get("dedupe_lineage"), list)
                else _metadata_lineage(metadata, "dedupe_lineage", "merged_candidate_ids")
            )
            merged_provenance = (
                item.get("merged_provenance")
                if isinstance(item.get("merged_provenance"), list)
                else _metadata_lineage(metadata, "merged_provenance")
            )
            entry = {
                "file_name": _text(record.get("file_name")),
                "document_id": _text(record.get("document_id")),
                "file_hash": _text(record.get("file_hash")),
                "field": _field_from_role(role) or _text(item.get("field")),
                "role": role,
                "component": component,
                "component_type": _text(item.get("component_type")) or component,
                "value_local_only": value if include_private_values else "",
                "source": normalized_source,
                "parser_name": _text(item.get("parser_name")),
                "generator_name": _text(metadata.get("source_generator_name")) or _text(item.get("parser_name")),
                "source_group": source_group,
                "page": item.get("page") if item.get("page") not in {None, ""} else _metadata_page(metadata),
                "line_index": (
                    item.get("line_index")
                    if item.get("line_index") not in {None, ""}
                    else _metadata_line_index(metadata)
                ),
                "bbox": (
                    item.get("bbox")
                    if item.get("bbox") is not None and item.get("bbox") != "" and item.get("bbox") != {}
                    else _metadata_bbox(metadata)
                ),
                "stop_index": item.get("stop_index") or metadata.get("stop_index") or 1,
                "candidate_id": candidate_id,
                "synthetic_candidate_id": (
                    candidate_id
                    or f"{source_group}:{_field_from_role(role) or _text(item.get('field'))}:1"
                ),
                "safety_status": safety_status,
                "unsafe_reason": unsafe_reason,
                "page_line_status": _text(item.get("page_line_status") or metadata.get("page_line_status")),
                "source_lineage": source_lineage,
                "component_sources": component_source_refs,
                "component_sources_available": bool(component_source_refs),
                "dedupe_lineage": dedupe_lineage,
                "merged_provenance": merged_provenance,
                "metadata_summary": metadata,
            }
            entry["page_line_status"] = _page_line_status(entry)
            entry["provenance_status"] = _provenance_status(entry)
            _apply_source_trust_metadata(entry)
            entries.append(entry)
    for item in inventory if isinstance(inventory, list) else []:
        append_entries(item)
    for group_name in [
        "shadow_selected_stop",
        "shadow_best_structured_stop_candidate",
        "shadow_best_dispatch_usable_stop_candidate",
        "shadow_best_ocr_column_stop_candidate",
        "shadow_best_native_layout_stop_candidate",
        "shadow_stop_review_draft",
        "review_fused_stops",
        "legacy_fallback_stop_candidate",
    ]:
        group = private_values.get(group_name)
        if not isinstance(group, dict):
            continue
        for field_name in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
            prediction = group.get(field_name)
            if not isinstance(prediction, dict):
                continue
            metadata = prediction.get("metadata_summary")
            metadata = metadata if isinstance(metadata, dict) else {}
            append_entries(
                {
                    "candidate_id": (
                        _text(prediction.get("candidate_id"))
                        or _text(metadata.get("candidate_id"))
                    ),
                    "field": field_name,
                    "value": prediction.get("value"),
                    "source": prediction.get("source"),
                    "parser_name": prediction.get("parser_name"),
                    "metadata_summary": {
                        **metadata,
                        "source_generator_name": group_name,
                    },
                },
                source_group=group_name,
            )
    return entries


def _inventory_key(entry):
    return (
        _text(entry.get("document_id")),
        _text(entry.get("file_hash")),
        _text(entry.get("field")),
    )


def _inventory_key_string(key):
    return "|".join(_text(part) for part in key)


def _hashes_match(left, right):
    left = _text(left)
    right = _text(right)
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    return len(shorter) >= 8 and longer.startswith(shorter)


def _candidate_counts_by_doc_field(audit_records):
    by_key = {}
    stop_fields = {
        FIELD_PICKUP_STOPS,
        FIELD_DELIVERY_STOPS,
        "pickup_location",
        "pickup_date",
        "pickup_time",
        "delivery_location",
        "delivery_date",
        "delivery_time",
    }
    for record in audit_records or []:
        if not isinstance(record, dict):
            continue
        counts = _candidate_counts_for_record(record)
        document_id = _text(record.get("document_id"))
        file_hash = _text(record.get("file_hash"))
        file_name = _text(record.get("file_name"))
        for field, count in counts.items():
            if field not in stop_fields:
                continue
            role = _role_from_field(field)
            normalized_field = _field_from_role(role) or field
            for key_parts in [
                (document_id, file_hash, normalized_field),
                ("", file_hash, normalized_field),
                (file_name, file_hash, normalized_field),
            ]:
                if not key_parts[0] and not key_parts[1]:
                    continue
                key = _inventory_key_string(key_parts)
                by_key[key] = by_key.get(key, 0) + int(count or 0)
    return by_key


def _candidate_counts_for_record(record):
    counts = record.get("candidate_counts_by_field") if isinstance(record, dict) else {}
    if isinstance(counts, dict) and counts:
        return counts
    candidate_summary = record.get("candidate_summary") if isinstance(record, dict) else {}
    candidate_summary = candidate_summary if isinstance(candidate_summary, dict) else {}
    counts = candidate_summary.get("candidates_by_field")
    if isinstance(counts, dict) and counts:
        return counts
    taxonomy = candidate_summary.get("candidate_taxonomy")
    taxonomy = taxonomy if isinstance(taxonomy, dict) else {}
    canonical_by_generator = taxonomy.get("canonical_fields_by_generator")
    if not isinstance(canonical_by_generator, dict):
        return {}
    merged = {}
    for fields in canonical_by_generator.values():
        if not isinstance(fields, dict):
            continue
        for field, count in fields.items():
            try:
                merged[field] = merged.get(field, 0) + int(count or 0)
            except (TypeError, ValueError):
                continue
    return merged


def _candidate_counts_stop_total(record):
    counts = _candidate_counts_for_record(record)
    stop_fields = {
        FIELD_PICKUP_STOPS,
        FIELD_DELIVERY_STOPS,
        "pickup_location",
        "pickup_date",
        "pickup_time",
        "delivery_location",
        "delivery_date",
        "delivery_time",
    }
    total = 0
    for field, count in counts.items():
        if field in stop_fields:
            try:
                total += int(count or 0)
            except (TypeError, ValueError):
                continue
    return total


def _build_source_inventory_items(audit_records, include_private_values):
    items = []
    for record in audit_records or []:
        if not isinstance(record, dict):
            continue
        items.extend(_inventory_entries_from_record(record, include_private_values))
    return items


def _matrix_for_entries(entries):
    matrix = {}
    for entry in entries:
        doc_key = f"{entry.get('document_id')}|{entry.get('file_hash')}"
        doc = matrix.setdefault(
            doc_key,
            {
                "document_id": entry.get("document_id", ""),
                "file_hash": entry.get("file_hash", ""),
                "file_name": entry.get("file_name", ""),
                "pickup": {},
                "delivery": {},
            },
        )
        role = entry.get("role") if entry.get("role") in {"pickup", "delivery"} else "unknown"
        if role == "unknown":
            continue
        role_matrix = doc.setdefault(role, {})
        component = entry.get("component")
        sources = set(role_matrix.get("sources", []))
        sources.add(_text(entry.get("source")) or "unknown")
        role_matrix["sources"] = sorted(sources)
        if component in {"facility", "address", "city_state_zip", "raw_location"}:
            role_matrix["has_location"] = True
        if component == "date":
            role_matrix["has_date"] = True
        if component in {"time", "appointment_window"}:
            role_matrix["has_time_or_window"] = True
        if component in {"facility", "address"}:
            role_matrix["has_facility_or_address"] = True
    for doc in matrix.values():
        for role in ["pickup", "delivery"]:
            role_matrix = doc.setdefault(role, {})
            role_matrix.setdefault("has_location", False)
            role_matrix.setdefault("has_date", False)
            role_matrix.setdefault("has_time_or_window", False)
            role_matrix.setdefault("has_facility_or_address", False)
            role_matrix.setdefault("sources", [])
            role_matrix["has_same_role_location_date"] = bool(
                role_matrix["has_location"] and role_matrix["has_date"]
            )
            role_matrix["has_same_role_location_time"] = bool(
                role_matrix["has_location"] and role_matrix["has_time_or_window"]
            )
            role_matrix["has_same_role_complete_candidate"] = bool(
                role_matrix["has_location"]
                and role_matrix["has_date"]
                and role_matrix["has_time_or_window"]
            )
    return matrix


def _source_inventory_summary(items, matrix):
    by_source = _counter(items, "source")
    by_component = _counter(items, "component")
    by_provenance = _counter(items, "provenance_status")
    docs_with_split_sources = 0
    pickup_complete = 0
    delivery_complete = 0
    role_ambiguity = 0
    missing_source_metadata = 0
    unsafe_source = 0
    for doc in matrix.values():
        for role in ["pickup", "delivery"]:
            role_matrix = doc.get(role, {}) or {}
            sources = role_matrix.get("sources", []) or []
            if len(sources) > 1:
                docs_with_split_sources += 1
            if role == "pickup" and role_matrix.get("has_same_role_complete_candidate"):
                pickup_complete += 1
            if role == "delivery" and role_matrix.get("has_same_role_complete_candidate"):
                delivery_complete += 1
    for item in items:
        if item.get("role") == "unknown" or item.get("provenance_status") == "missing_role":
            role_ambiguity += 1
        if item.get("provenance_status") in {
            "missing_source",
            "page_line_dropped_by_pipeline",
            "missing_candidate_id",
        }:
            missing_source_metadata += 1
        if item.get("safety_status") == "unsafe":
            unsafe_source += 1
    return {
        "inventory_item_count": len(items),
        "by_source": by_source,
        "by_component": by_component,
        "by_provenance_status": by_provenance,
        "component_availability_corpus_summary": {
            "docs_with_pickup_location_date_time": pickup_complete,
            "docs_with_delivery_location_date_time": delivery_complete,
            "docs_with_components_split_across_sources": docs_with_split_sources,
            "docs_blocked_by_role_ambiguity": role_ambiguity,
            "docs_blocked_by_missing_source_metadata": missing_source_metadata,
            "docs_blocked_by_unsafe_source": unsafe_source,
        },
    }


def _source_inventory_v2_summary(items):
    items = items or []
    page_line_available = sum(1 for item in items if item.get("page_line_status") == "available")
    page_line_unavailable = sum(
        1 for item in items if item.get("page_line_status") == "unavailable_from_source"
    )
    page_line_dropped = sum(
        1 for item in items if item.get("page_line_status") == "dropped_by_pipeline"
    )
    return {
        "total_items": len(items),
        "provenance_complete": sum(1 for item in items if item.get("provenance_status") == "complete"),
        "page_line_available": page_line_available,
        "page_line_unavailable_from_source": page_line_unavailable,
        "page_line_dropped_by_pipeline": page_line_dropped,
        "candidate_id_available": sum(1 for item in items if _text(item.get("candidate_id"))),
        "candidate_id_missing": sum(1 for item in items if not _text(item.get("candidate_id"))),
        "dedupe_lineage_available": sum(1 for item in items if item.get("dedupe_lineage")),
        "merged_provenance_available": sum(1 for item in items if item.get("merged_provenance")),
        "unsafe_source": sum(1 for item in items if item.get("safety_status") == "unsafe"),
    }


def _source_inventory_v3_summary(items):
    v2 = _source_inventory_v2_summary(items)
    structured_items = [
        item
        for item in items or []
        if item.get("source_group")
        in {
            "candidate_inventory",
            "shadow_selected_stop",
            "shadow_best_structured_stop_candidate",
            "shadow_best_dispatch_usable_stop_candidate",
            "shadow_best_ocr_column_stop_candidate",
            "shadow_best_native_layout_stop_candidate",
            "shadow_stop_review_draft",
            "review_fused_stops",
            "legacy_fallback_stop_candidate",
        }
        and item.get("field") in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}
    ]
    return {
        **v2,
        "component_sources_available": sum(
            1 for item in items or [] if item.get("component_sources_available")
        ),
        "structured_stops_with_component_sources": len(
            {
                (
                    item.get("document_id"),
                    item.get("file_hash"),
                    item.get("field"),
                    item.get("candidate_id") or item.get("synthetic_candidate_id"),
                )
                for item in structured_items
                if item.get("component_sources_available")
            }
        ),
    }


def _module_from_inventory_item(item):
    return (
        _text(item.get("generator_name"))
        or _text(item.get("parser_name"))
        or _text(item.get("source_group"))
        or _text(item.get("source"))
        or "unknown"
    )


def _loss_type_from_inventory_item(item):
    if item.get("safety_status") == "unsafe":
        if item.get("unsafe_reason") == "component_from_payment_or_instruction":
            return "component_from_payment_or_instruction"
        return "unsafe_source"
    if not _text(item.get("candidate_id")):
        if item.get("source_group") != "candidate_inventory":
            return "candidate_id_lost_during_adapter"
        return "generated_without_candidate_id"
    page_line_status = item.get("page_line_status")
    if page_line_status == "unavailable_from_source":
        if item.get("source") == "legacy_fallback":
            return "page_line_unavailable_from_legacy_source"
        if item.get("source_group") != "candidate_inventory":
            return "evaluator_inventory_lookup_missing"
        return "page_line_unavailable_from_aggregated_assembler"
    if page_line_status == "dropped_by_pipeline":
        if item.get("source") == "ocr_geometry_column":
            return "row_column_lost_from_ocr_table_reconstructor"
        if "geometry" in _module_from_inventory_item(item):
            return "bbox_lost_from_ocr_geometry"
        return "generated_with_page_line_then_dropped"
    if item.get("field") in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS} and not item.get("component_sources_available"):
        return "component_sources_lost_from_structured_stop"
    return "no_loss"


def _provenance_loss_root_cause_summary(items):
    by_module = Counter()
    by_loss_type = Counter()
    by_module_loss = Counter()
    for item in items or []:
        loss_type = _loss_type_from_inventory_item(item)
        if loss_type == "no_loss":
            continue
        module = _module_from_inventory_item(item)
        by_module[module] += 1
        by_loss_type[loss_type] += 1
        by_module_loss[f"{module}|{loss_type}"] += 1
    return {
        "by_module": dict(by_module.most_common()),
        "by_loss_type": dict(by_loss_type.most_common()),
        "by_module_and_loss_type": dict(by_module_loss.most_common()),
        "unknown": by_loss_type.get("unknown", 0),
    }


def _dedupe_provenance_loss_summary(audit_records, inventory_items):
    reported_total = sum(_candidate_counts_stop_total(record) for record in audit_records or [])
    post_total = len(inventory_items)
    return {
        "pre_dedupe_stop_components": reported_total,
        "post_dedupe_stop_components": post_total,
        "dropped_with_unique_source": max(reported_total - post_total, 0),
        "merged_without_source_metadata": sum(
            1 for item in inventory_items if item.get("provenance_status") == "missing_source"
        ),
        "lost_role_count": sum(
            1 for item in inventory_items if item.get("provenance_status") == "missing_role"
        ),
        "lost_page_line_count": sum(
            1 for item in inventory_items if item.get("provenance_status") == "page_line_dropped_by_pipeline"
        ),
        "lost_candidate_id_count": sum(
            1 for item in inventory_items if item.get("provenance_status") == "missing_candidate_id"
        ),
        "page_line_unavailable_from_source_count": sum(
            1 for item in inventory_items if item.get("page_line_status") == "unavailable_from_source"
        ),
        "dedupe_lineage_available_count": sum(
            1 for item in inventory_items if item.get("dedupe_lineage")
        ),
        "merged_provenance_available_count": sum(
            1 for item in inventory_items if item.get("merged_provenance")
        ),
    }


def build_stop_source_inventory_report(packet, audit_records, include_private_values=False):
    items = _build_source_inventory_items(audit_records, include_private_values)
    matrix = _matrix_for_entries(items)
    return {
        "schema_version": "ratecon_stop_source_inventory_v3",
        "items": items,
        "candidate_counts_by_doc_field": _candidate_counts_by_doc_field(audit_records),
        "source_inventory_summary": _source_inventory_summary(items, matrix),
        "source_inventory_v2_summary": _source_inventory_v2_summary(items),
        "source_inventory_v3_summary": _source_inventory_v3_summary(items),
        "stop_component_availability_matrix": matrix,
        "stop_dedupe_provenance_loss_summary": _dedupe_provenance_loss_summary(
            audit_records,
            items,
        ),
        "provenance_loss_root_cause_by_module": _provenance_loss_root_cause_summary(items),
        "stop_fusion_safety_model_summary": _fusion_safety_model_summary(items),
        "private_values_printed": bool(include_private_values),
        "raw_text_printed": False,
        "local_only": True,
    }


def _inventory_entries_for_residual_item(source_inventory_report, item):
    if not source_inventory_report:
        return []
    document_id = _text(item.get("document_id"))
    file_hash = _text(item.get("file_hash"))
    file_name = _text(item.get("file_name"))
    field = _text(item.get("field"))
    return [
        entry
        for entry in source_inventory_report.get("items", []) or []
        if _text(entry.get("field")) == field
        and (
            (
                _text(entry.get("document_id")) == document_id
                and _hashes_match(entry.get("file_hash"), file_hash)
            )
            or _hashes_match(entry.get("file_hash"), file_hash)
            or (
                _text(entry.get("file_name")) == file_name
                and _hashes_match(entry.get("file_hash"), file_hash)
                and file_name
            )
        )
    ]


def _inventory_candidate_count_for_residual_item(source_inventory_report, item):
    if not source_inventory_report:
        return 0
    counts = source_inventory_report.get("candidate_counts_by_doc_field", {})
    counts = counts if isinstance(counts, dict) else {}
    keys = [
        _inventory_key_string(
            (
                _text(item.get("document_id")),
                _text(item.get("file_hash")),
                _text(item.get("field")),
            )
        ),
        _inventory_key_string(("", _text(item.get("file_hash")), _text(item.get("field")))),
        _inventory_key_string(
            (
                _text(item.get("file_name")),
                _text(item.get("file_hash")),
                _text(item.get("field")),
            )
        ),
    ]
    for key in keys:
        try:
            count = int(counts.get(key, 0) or 0)
        except (TypeError, ValueError):
            count = 0
        if count:
            return count
    total = 0
    target_hash = _text(item.get("file_hash"))
    target_field = _text(item.get("field"))
    for key, raw_count in counts.items():
        parts = key.split("|")
        if len(parts) != 3:
            continue
        _doc_or_name, hash_value, field = parts
        if field != target_field or not _hashes_match(hash_value, target_hash):
            continue
        try:
            total += int(raw_count or 0)
        except (TypeError, ValueError):
            continue
    if total:
        return total
    return 0


def _trace_no_candidate_source(item, source_inventory_report):
    entries = _inventory_entries_for_residual_item(source_inventory_report, item)
    other_role_entries = [
        entry
        for entry in source_inventory_report.get("items", []) or []
        if (
            (
                _text(entry.get("document_id")) == _text(item.get("document_id"))
                and _hashes_match(entry.get("file_hash"), item.get("file_hash"))
            )
            or _hashes_match(entry.get("file_hash"), item.get("file_hash"))
        )
        and _text(entry.get("field")) != _text(item.get("field"))
    ] if source_inventory_report else []
    generated_count = _inventory_candidate_count_for_residual_item(
        source_inventory_report,
        item,
    )
    if any(entry.get("safety_status") == "unsafe" for entry in entries):
        reason = "component_from_payment_or_instruction"
    elif any(entry.get("role") not in {"pickup", "delivery"} for entry in entries):
        reason = "component_candidate_generated_but_role_missing"
    elif any(entry.get("source_group") == "shadow_selected_stop" for entry in entries) and not generated_count:
        reason = "selected_stop_comes_from_assembler_without_component_sources"
    elif any(entry.get("provenance_status") == "missing_page_line" for entry in entries):
        reason = "component_candidate_generated_but_page_line_missing"
    elif any(entry.get("provenance_status") == "missing_source" for entry in entries):
        reason = "component_candidate_generated_but_source_metadata_missing"
    elif entries:
        reason = "evaluator_only_missing_candidate_source"
    elif other_role_entries:
        reason = "component_from_wrong_role"
    elif generated_count:
        reason = "component_candidate_generated_but_not_in_inventory"
    else:
        reason = "true_no_source"
    return {
        "document_id": item.get("document_id", ""),
        "file_hash": item.get("file_hash", ""),
        "file_name": item.get("file_name", ""),
        "field": item.get("field", ""),
        "root_cause": reason,
        "inventory_entries_for_field": len(entries),
        "other_role_entries_for_document": len(other_role_entries),
        "candidate_count_for_field": generated_count,
    }


def build_no_candidate_source_trace_summary(residual_items, source_inventory_report):
    cases = [
        _trace_no_candidate_source(item, source_inventory_report)
        for item in residual_items or []
    ]
    reason_counts = _counter(cases, "root_cause")
    recoverable = {
        "component_candidate_generated_but_not_in_inventory",
        "evaluator_only_missing_candidate_source",
        "review_packet_lookup_bug",
    }
    generation_gap = {"component_candidate_never_generated", "true_no_source"}
    provenance_loss = {
        "component_candidate_generated_but_deduped_without_provenance",
        "component_candidate_generated_but_role_missing",
        "component_candidate_generated_but_page_line_missing",
        "component_candidate_generated_but_source_metadata_missing",
        "selected_stop_comes_from_assembler_without_component_sources",
        "selected_stop_summary_lost_component_sources",
    }
    unsafe = {"component_from_wrong_role", "component_from_payment_or_instruction"}
    return {
        "issues_checked": len(cases),
        "reason_counts": reason_counts,
        "recoverable_inventory_omission": sum(
            1 for case in cases if case["root_cause"] in recoverable
        ),
        "true_generation_gap": sum(
            1 for case in cases if case["root_cause"] in generation_gap
        ),
        "dedupe_or_provenance_loss": sum(
            1 for case in cases if case["root_cause"] in provenance_loss
        ),
        "wrong_role_or_unsafe_source": sum(
            1 for case in cases if case["root_cause"] in unsafe
        ),
        "unknown": reason_counts.get("unknown", 0),
        "cases": cases,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _best_available_source(item):
    for prefix in ["selected", "best_candidate", "draft"]:
        hint = item.get(f"{prefix}_source_hint", {}) or {}
        source = _text(hint.get("parser_name")) or _text(hint.get("source"))
        if source:
            return source
    return "source_not_available"


def _candidate_issue_type(item):
    selected = item.get("selected_stop_component_summary", {}) or {}
    dispatch = item.get("best_dispatch_usable_candidate_summary", {}) or {}
    draft = item.get("draft_stop_summary", {}) or {}
    selected_components = item.get("selected_components", {}) or {}
    dispatch_components = item.get("best_candidate_components", {}) or {}
    draft_components = item.get("draft_components", {}) or {}
    issues = _row_issues(selected) | _row_issues(dispatch) | _row_issues(draft)
    issue_text = " ".join(sorted(issues)).lower()
    source_text = " ".join(
        _text((item.get(f"{prefix}_source_hint", {}) or {}).get("parser_name"))
        + " "
        + _text((item.get(f"{prefix}_source_hint", {}) or {}).get("source"))
        + " "
        + _text((item.get(f"{prefix}_source_hint", {}) or {}).get("pairing_method"))
        for prefix in ["selected", "best_candidate", "draft"]
    ).lower()
    selected_presence = _component_presence(selected_components, selected)
    dispatch_presence = _component_presence(dispatch_components, dispatch)
    draft_presence = _component_presence(draft_components, draft)
    any_presence = {
        key: selected_presence[key] or dispatch_presence[key] or draft_presence[key]
        for key in ["location", "date", "time"]
    }
    if "wrong_city" in issue_text or "wrong_state" in issue_text:
        return "selected_wrong_city_state"
    if "wrong_facility" in issue_text:
        return "selected_wrong_facility"
    if "wrong_time" in issue_text or "wrong_appointment" in issue_text:
        return "selected_wrong_time"
    if "wrong_location" in issue_text or "wrong_address" in issue_text:
        return "selected_wrong_location"
    if "ocr_stop_table_reconstructor" in source_text and "unsafe_wrong" in {
        _text(dispatch.get("dispatch_usability_tier")),
        _text(draft.get("dispatch_usability_tier")),
        _text(selected.get("dispatch_usability_tier")),
    }:
        return "OCR_column_candidate_wrong_alignment"
    selected_status = _text(selected.get("raw_status") or selected.get("source_status"))
    if selected_presence["location"] and not selected_presence["date"] and not selected_presence["time"]:
        return "selected_location_only_partial"
    if selected_presence["date"] and not selected_presence["location"] and not selected_presence["time"]:
        return "selected_date_only_partial"
    if selected_presence["time"] and not selected_presence["location"] and not selected_presence["date"]:
        return "selected_time_only_partial"
    if selected_presence["location"] and not (selected_presence["date"] or selected_presence["time"]):
        return "selected_missing_date_time"
    if (selected_presence["date"] or selected_presence["time"]) and not selected_presence["location"]:
        return "selected_missing_location_components"
    if dispatch.get("dispatch_usability_tier") == "unsafe_wrong" or draft.get("dispatch_usability_tier") == "unsafe_wrong":
        return "candidate_has_components_but_wrong_against_gold"
    if any_presence["location"] or any_presence["date"] or any_presence["time"]:
        if selected_status in {
            "extractor_missing",
            "source_not_available",
            "selected_partial_not_comparable",
            "unsupported_unparsed_location",
        }:
            return "best_candidate_exists_not_selected"
        return "selected_abstained_candidate_counted_wrong"
    return "no_viable_candidate"


def _recommended_fix_type(issue_type, item):
    source = _best_available_source(item).lower()
    if issue_type in {
        "selected_location_only_partial",
        "selected_date_only_partial",
        "selected_time_only_partial",
        "selected_missing_location_components",
        "selected_missing_date_time",
        "best_candidate_exists_not_selected",
    }:
        return "candidate_fusion"
    if issue_type in {
        "OCR_column_candidate_wrong_alignment",
        "OCR_column_candidate_missing_city_state",
    } or "ocr" in source:
        return "OCR_geometry"
    if issue_type in {
        "selected_wrong_time",
        "selected_wrong_location",
        "selected_wrong_facility",
        "selected_wrong_city_state",
        "candidate_has_components_but_wrong_against_gold",
        "selected_abstained_candidate_counted_wrong",
    }:
        return "stop_ranking"
    if issue_type == "no_viable_candidate":
        return "leave_review_required"
    if "layout" in source or "table" in source:
        return "native_layout_table"
    return "unknown"


def _source_inventory_presence(entries):
    safe_entries = [
        entry for entry in entries or [] if entry.get("safety_status") != "unsafe"
    ]
    components = {entry.get("component") for entry in safe_entries}
    sources = sorted(
        {
            _text(entry.get("source")) or "unknown"
            for entry in safe_entries
            if _text(entry.get("source")) or entry.get("source") == "unknown"
        }
    )
    has_location = bool(
        components.intersection({"facility", "address", "city_state_zip", "raw_location"})
    )
    has_date = "date" in components
    has_time = bool(components.intersection({"time", "appointment_window"}))
    return {
        "has_location": has_location,
        "has_date": has_date,
        "has_time": has_time,
        "sources": sources,
        "component_counts": _counter(safe_entries, "component"),
        "unsafe_count": len(entries or []) - len(safe_entries),
    }


def _location_components(entries):
    return [
        entry
        for entry in entries or []
        if entry.get("component") in {"facility", "address", "city_state_zip", "raw_location"}
    ]


def _date_components(entries):
    return [entry for entry in entries or [] if entry.get("component") == "date"]


def _time_components(entries):
    return [
        entry
        for entry in entries or []
        if entry.get("component") in {"time", "appointment_window"}
    ]


def _entry_has_proximity(entry):
    return bool(
        entry.get("page_line_status") == "available"
        or entry.get("bbox")
        or entry.get("source_lineage")
        or entry.get("merged_provenance")
    )


def _entry_has_row_or_block_boundary(entry):
    metadata = entry.get("metadata_summary") if isinstance(entry.get("metadata_summary"), dict) else {}
    if entry.get("bbox"):
        return True
    if entry.get("component_sources") or entry.get("source_lineage") or entry.get("merged_provenance"):
        return True
    if metadata.get("assembled_from_column_geometry"):
        return True
    if metadata.get("has_clear_horizontal_boundary") or metadata.get("row_boundary_confidence"):
        return True
    if metadata.get("component_bboxes_available") or metadata.get("geometry_available"):
        return True
    return False


def _source_trust_metadata(entry):
    metadata = entry.get("metadata_summary") if isinstance(entry.get("metadata_summary"), dict) else {}
    source = _text(entry.get("source")).lower()
    parser = _text(entry.get("parser_name")).lower()
    generator = _text(entry.get("generator_name")).lower()
    source_group = _text(entry.get("source_group")).lower()
    if _entry_is_instruction_or_payment(entry):
        return {
            "source_trust_tier": "unsafe",
            "trust_reason": "payment_instruction_footer_source",
            "eligible_for_disambiguation": False,
            "eligible_for_review_fusion": False,
            "exclusion_reason": "payment_instruction_footer_source",
        }
    if _entry_is_reference_or_contact(entry):
        return {
            "source_trust_tier": "unsafe",
            "trust_reason": "reference_contact_only_source",
            "eligible_for_disambiguation": False,
            "eligible_for_review_fusion": False,
            "exclusion_reason": "reference_contact_only_source",
        }
    if entry.get("role") not in {"pickup", "delivery"}:
        return {
            "source_trust_tier": "unsafe",
            "trust_reason": "role_not_linked",
            "eligible_for_disambiguation": False,
            "eligible_for_review_fusion": False,
            "exclusion_reason": "role_not_linked",
        }
    row_geometry = bool(
        entry.get("source") == "ocr_geometry_column"
        or "ocr_stop_table_reconstructor" in parser
        or metadata.get("assembled_from_column_geometry")
    )
    native_row = bool(
        entry.get("source") in {"native_layout", "pdfplumber_table"}
        or "table" in parser
        or "layout" in parser
        or metadata.get("table_cell_candidate")
    )
    explicit_block = bool(
        "role_block" in parser
        or "role_block" in generator
        or metadata.get("has_clear_role_anchor")
        or metadata.get("has_clear_horizontal_boundary")
        or metadata.get("component_sources")
    )
    if (row_geometry or native_row or explicit_block) and _entry_has_proximity(entry):
        return {
            "source_trust_tier": "trusted_row_level",
            "trust_reason": "bounded_row_or_role_block",
            "eligible_for_disambiguation": True,
            "eligible_for_review_fusion": True,
            "exclusion_reason": "",
        }
    if entry.get("page_line_status") == "available" and entry.get("component_sources_available"):
        return {
            "source_trust_tier": "trusted_component_level",
            "trust_reason": "same_role_component_with_lineage",
            "eligible_for_disambiguation": True,
            "eligible_for_review_fusion": False,
            "exclusion_reason": "",
        }
    if entry.get("page_line_status") == "available" and source not in {"legacy_fallback", ""}:
        return {
            "source_trust_tier": "trusted_component_level",
            "trust_reason": "same_role_component_with_page_line",
            "eligible_for_disambiguation": True,
            "eligible_for_review_fusion": False,
            "exclusion_reason": "",
        }
    if source == "legacy_fallback" or "legacy" in parser or "legacy" in source_group:
        return {
            "source_trust_tier": "weak_diagnostic_only",
            "trust_reason": "legacy_fallback_without_row_boundary",
            "eligible_for_disambiguation": False,
            "eligible_for_review_fusion": False,
            "exclusion_reason": "legacy_fallback_without_row_boundary",
        }
    if entry.get("source") == "stop_evidence_assembler" and not _entry_has_row_or_block_boundary(entry):
        return {
            "source_trust_tier": "weak_diagnostic_only",
            "trust_reason": "aggregate_without_component_proximity",
            "eligible_for_disambiguation": False,
            "eligible_for_review_fusion": False,
            "exclusion_reason": "aggregate_without_component_proximity",
        }
    return {
        "source_trust_tier": "weak_diagnostic_only",
        "trust_reason": "unbounded_component_source",
        "eligible_for_disambiguation": False,
        "eligible_for_review_fusion": False,
        "exclusion_reason": "unbounded_component_source",
    }


def _apply_source_trust_metadata(entry):
    trust = _source_trust_metadata(entry)
    for key, value in trust.items():
        entry[key] = value
    return entry


def _fusion_safety_for_entries(entries):
    entries = entries or []
    if not entries:
        return "fusion_not_possible", ["no_proximity_evidence"]
    if any(entry.get("safety_status") == "unsafe" for entry in entries):
        return "fusion_unsafe", ["unsafe_source_payment_instruction"]
    if any(entry.get("role") not in {"pickup", "delivery"} for entry in entries):
        return "fusion_unsafe", ["source_not_linked_to_role"]
    locations = _location_components(entries)
    dates = _date_components(entries)
    times = _time_components(entries)
    if not locations or not (dates or times):
        return "fusion_not_possible", ["missing_page_line_or_geometry"]
    if len({entry.get("value_local_only") for entry in locations if _text(entry.get("value_local_only"))}) > 1:
        return "fusion_risky", ["multiple_locations"]
    if len({entry.get("value_local_only") for entry in dates if _text(entry.get("value_local_only"))}) > 1:
        return "fusion_risky", ["multiple_dates"]
    if len({entry.get("value_local_only") for entry in times if _text(entry.get("value_local_only"))}) > 1:
        return "fusion_risky", ["multiple_times"]
    candidate_entries = locations + dates + times
    if any(entry.get("page_line_status") == "dropped_by_pipeline" for entry in candidate_entries):
        return "fusion_risky", ["dedupe_lost_provenance"]
    if any(entry.get("page_line_status") == "unavailable_from_source" for entry in candidate_entries):
        return "fusion_risky", ["unavailable_from_source"]
    if not all(_entry_has_proximity(entry) for entry in candidate_entries):
        return "fusion_risky", ["no_proximity_evidence"]
    pages = {
        _text(entry.get("page"))
        for entry in candidate_entries
        if _text(entry.get("page"))
    }
    if len(pages) > 1:
        return "fusion_risky", ["no_proximity_evidence"]
    return "fusion_safe", []


def _fusion_safety_model_summary(items):
    groups = {}
    for item in items or []:
        if item.get("role") not in {"pickup", "delivery"}:
            continue
        key = (
            _text(item.get("document_id")),
            _text(item.get("file_hash")),
            _text(item.get("field")),
        )
        groups.setdefault(key, []).append(item)
    cases = []
    for key, entries in groups.items():
        status, reasons = _fusion_safety_for_entries(entries)
        cases.append(
            {
                "document_id": key[0],
                "file_hash": key[1],
                "field": key[2],
                "fusion_safety": status,
                "blocked_reasons": reasons,
                "component_counts": _counter(entries, "component"),
                "source_counts": _counter(entries, "source"),
            }
        )
    return {
        "fusion_safe": sum(1 for case in cases if case["fusion_safety"] == "fusion_safe"),
        "fusion_risky": sum(1 for case in cases if case["fusion_safety"] == "fusion_risky"),
        "fusion_unsafe": sum(1 for case in cases if case["fusion_safety"] == "fusion_unsafe"),
        "fusion_not_possible": sum(1 for case in cases if case["fusion_safety"] == "fusion_not_possible"),
        "blocked_reason_counts": _counter(cases, "blocked_reasons"),
        "cases": cases,
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def _normalize_location_text(value):
    value = _text(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _entry_line_number(entry):
    try:
        return int(float(entry.get("line_index")))
    except (TypeError, ValueError):
        return None


def _bbox_top(entry):
    bbox = entry.get("bbox")
    if not isinstance(bbox, dict):
        return None
    for key in ["top", "y", "y0"]:
        try:
            return float(bbox.get(key))
        except (TypeError, ValueError):
            continue
    return None


def _same_location_proximity(left, right):
    if _text(left.get("candidate_id")) and _text(left.get("candidate_id")) == _text(right.get("candidate_id")):
        return True
    if _text(left.get("page")) and _text(left.get("page")) != _text(right.get("page")):
        return False
    left_line = _entry_line_number(left)
    right_line = _entry_line_number(right)
    if left_line is not None and right_line is not None:
        return abs(left_line - right_line) <= 4
    left_top = _bbox_top(left)
    right_top = _bbox_top(right)
    if left_top is not None and right_top is not None:
        return abs(left_top - right_top) <= 90.0
    return False


def _entry_location_text(entry):
    return _normalize_location_text(entry.get("value_local_only"))


def _location_texts_related(left_text, right_text):
    if not left_text or not right_text:
        return False
    if left_text == right_text:
        return True
    shorter, longer = (left_text, right_text) if len(left_text) <= len(right_text) else (right_text, left_text)
    return len(shorter) >= 5 and shorter in longer


def _entry_is_reference_or_contact(entry):
    metadata = entry.get("metadata_summary") if isinstance(entry.get("metadata_summary"), dict) else {}
    haystack = " ".join(
        [
            _text(entry.get("parser_name")),
            _text(entry.get("generator_name")),
            _text(entry.get("source_group")),
            _text(metadata.get("section_context")),
            _text(metadata.get("document_region")),
            _text(metadata.get("table_context_role")),
            _text(metadata.get("raw_field")),
            _text(entry.get("unsafe_reason")),
        ]
    ).lower()
    return any(token in haystack for token in ["reference", "contact", "phone", "email"])


def _entry_is_instruction_or_payment(entry):
    metadata = entry.get("metadata_summary") if isinstance(entry.get("metadata_summary"), dict) else {}
    haystack = " ".join(
        [
            _text(entry.get("unsafe_reason")),
            _text(metadata.get("section_context")),
            _text(metadata.get("document_region")),
            _text(metadata.get("stop_column_warnings")),
            _text(metadata.get("stop_geometry_warnings")),
            _text(metadata.get("alignment_warnings")),
        ]
    ).lower()
    return entry.get("safety_status") == "unsafe" or any(
        token in haystack for token in ["payment", "instruction", "terms", "footer"]
    )


def _locations_should_cluster(entry, cluster_entries):
    if not cluster_entries:
        return True
    if entry.get("role") not in {"pickup", "delivery"}:
        return False
    for member in cluster_entries:
        if member.get("role") != entry.get("role"):
            return False
        if _text(member.get("stop_index")) and _text(entry.get("stop_index")) and _text(member.get("stop_index")) != _text(entry.get("stop_index")):
            continue
        entry_text = _entry_location_text(entry)
        member_text = _entry_location_text(member)
        if _location_texts_related(entry_text, member_text):
            return True
        complementary = {
            entry.get("component"),
            member.get("component"),
        }.issubset({"facility", "address", "city_state_zip", "raw_location"})
        if complementary and _same_location_proximity(entry, member):
            return True
    return False


def _cluster_location_entries(location_entries):
    clusters = []
    sorted_entries = sorted(
        location_entries or [],
        key=lambda entry: (
            _text(entry.get("role")),
            _text(entry.get("stop_index")),
            _text(entry.get("page")),
            _entry_line_number(entry) if _entry_line_number(entry) is not None else 999999,
            _bbox_top(entry) if _bbox_top(entry) is not None else 999999.0,
            _text(entry.get("candidate_id")),
        ),
    )
    for entry in sorted_entries:
        for cluster in clusters:
            if _locations_should_cluster(entry, cluster["entries"]):
                cluster["entries"].append(entry)
                break
        else:
            clusters.append({"entries": [entry]})
    result = []
    for index, cluster in enumerate(clusters, start=1):
        entries = cluster["entries"]
        components = {entry.get("component") for entry in entries}
        values = {
            _entry_location_text(entry)
            for entry in entries
            if _entry_location_text(entry)
        }
        roles = {entry.get("role") for entry in entries}
        sources = sorted({_text(entry.get("source")) or "unknown" for entry in entries})
        status = "single_location_cluster"
        blocked_reason = None
        if any(_entry_is_instruction_or_payment(entry) or _entry_is_reference_or_contact(entry) for entry in entries):
            status = "unsafe_cluster"
            blocked_reason = "unsafe_source"
        elif len(roles - {"pickup", "delivery"}) > 0 or len({role for role in roles if role in {"pickup", "delivery"}}) > 1:
            status = "wrong_role_cluster"
            blocked_reason = "wrong_role"
        elif len(values) <= 1 and len(entries) > 1:
            status = "duplicate_cluster"
        elif components.intersection({"facility", "address", "city_state_zip"}) and len(components) > 1:
            status = "facility_address_city_cluster"
        elif len([entry for entry in entries if entry.get("component") in {"address", "raw_location"}]) > 1:
            status = "split_address_cluster"
        result.append(
            {
                "cluster_id": f"loc-cluster-{index}",
                "role": next(iter(roles), ""),
                "stop_index": entries[0].get("stop_index", 1),
                "source_types": sources,
                "component_types": sorted(component for component in components if component),
                "has_facility": "facility" in components,
                "has_address": "address" in components,
                "has_city_state_zip": "city_state_zip" in components,
                "page_line_available": any(entry.get("page_line_status") == "available" for entry in entries),
                "bbox_available": any(bool(entry.get("bbox")) for entry in entries),
                "cluster_confidence": 0.0 if status in {"unsafe_cluster", "wrong_role_cluster"} else (0.95 if status == "duplicate_cluster" else 0.85),
                "cluster_status": status,
                "blocked_reason": blocked_reason,
                "entries": entries,
                "normalized_value_count": len(values),
            }
        )
    return result


def _location_disambiguation_status(clusters, entries):
    if not entries:
        return "insufficient_geometry", 0.0
    if any(cluster["cluster_status"] == "unsafe_cluster" for cluster in clusters):
        return "unsafe_location_source", 0.0
    safe_clusters = [
        cluster for cluster in clusters if cluster["cluster_status"] not in {"unsafe_cluster", "wrong_role_cluster"}
    ]
    if len(safe_clusters) == 1:
        status = safe_clusters[0]["cluster_status"]
        if status == "single_location_cluster":
            return "clear_single_location", 1.0
        if status == "duplicate_cluster":
            return "duplicate_locations_collapsed", 0.95
        return "clear_location_cluster", 0.85
    if len(safe_clusters) > 1:
        return "ambiguous_multiple_locations", 0.35
    if clusters:
        return "unsafe_location_source", 0.0
    return "unknown", 0.0


def _diagnostic_cluster_representatives(entries, clusters):
    representatives = []
    represented_ids = set()
    for cluster in clusters:
        if cluster["cluster_status"] in {"unsafe_cluster", "wrong_role_cluster"}:
            representatives.extend(cluster["entries"])
            continue
        representative = sorted(
            cluster["entries"],
            key=lambda entry: (
                0 if entry.get("component") == "city_state_zip" else 1,
                0 if entry.get("page_line_status") == "available" else 1,
                _text(entry.get("candidate_id")),
            ),
        )[0]
        representatives.append(representative)
        represented_ids.update(id(entry) for entry in cluster["entries"])
    return [
        entry
        for entry in entries or []
        if entry.get("component") not in {"facility", "address", "city_state_zip", "raw_location"}
    ] + representatives


def _multiple_location_root_cause(entries, clusters):
    location_entries = _location_components(entries)
    if any(_entry_is_instruction_or_payment(entry) for entry in location_entries):
        return "instruction_or_payment_leakage"
    if any(_entry_is_reference_or_contact(entry) for entry in location_entries):
        return "reference_contact_leakage"
    if any(entry.get("role") not in {"pickup", "delivery"} for entry in location_entries):
        return "wrong_role_candidates"
    if len({entry.get("stop_index") for entry in location_entries if _text(entry.get("stop_index"))}) > 1:
        return "multiple_stops_same_role"
    safe_clusters = [
        cluster for cluster in clusters if cluster["cluster_status"] not in {"unsafe_cluster", "wrong_role_cluster"}
    ]
    if len(safe_clusters) == 1:
        status = safe_clusters[0]["cluster_status"]
        if status == "duplicate_cluster":
            return "duplicate_fragments"
        if status == "facility_address_city_cluster":
            return "facility_address_city_split"
        if status == "split_address_cluster":
            return "OCR_geometry_split"
    if any(_text(entry.get("source")) == "legacy_fallback" for entry in location_entries):
        return "legacy_fallback_noise"
    if any("ocr" in _text(entry.get("source")).lower() for entry in location_entries):
        return "OCR_geometry_split"
    if all(entry.get("component") == "raw_location" for entry in location_entries):
        return "duplicate_fragments"
    if any("table" in _text(entry.get("parser_name")).lower() or "row" in _text(entry.get("parser_name")).lower() for entry in location_entries):
        return "table_row_ambiguity"
    return "table_row_ambiguity"


def _legacy_fallback_noise_reason(entry, entries):
    metadata = entry.get("metadata_summary") if isinstance(entry.get("metadata_summary"), dict) else {}
    if _entry_is_instruction_or_payment(entry):
        return "instruction_or_payment_text"
    if _entry_is_reference_or_contact(entry):
        return "reference_or_contact_text"
    if entry.get("role") not in {"pickup", "delivery"}:
        return "missing_role"
    if not _text(entry.get("stop_index")):
        return "missing_stop_index"
    entry_text = _entry_location_text(entry)
    better_sources = [
        candidate
        for candidate in _location_components(entries)
        if candidate is not entry and _text(candidate.get("source")) != "legacy_fallback"
    ]
    for candidate in better_sources:
        if _location_texts_related(entry_text, _entry_location_text(candidate)):
            source = _text(candidate.get("source"))
            if source == "ocr_geometry_column":
                return "duplicate_of_ocr_geometry_candidate"
            if source in {"native_layout", "pdfplumber_table"}:
                return "duplicate_of_native_layout_candidate"
            return "duplicate_of_structured_candidate"
    if entry.get("page_line_status") == "unavailable_from_source":
        if metadata.get("selected_output_only") or entry.get("source_group") == "shadow_selected_stop":
            return "selected_output_only_no_evidence"
        return "useful_but_unbounded_location"
    if entry.get("page_line_status") in {"dropped_by_pipeline", "missing"}:
        return "missing_page_line"
    if entry.get("component") in {"facility", "address", "city_state_zip"}:
        return "facility_address_city_fragment"
    if metadata.get("stale_final_row_value"):
        return "stale_final_row_value"
    return "useful_but_unbounded_location"


def _legacy_fallback_stop_noise_report(cases, groups):
    records = []
    for case in cases or []:
        if case.get("root_cause") != "legacy_fallback_noise":
            continue
        key = (
            _text(case.get("document_id")),
            _text(case.get("file_hash")),
            _text(case.get("field")),
        )
        entries = groups.get(key, []) or []
        for entry in _location_components(entries):
            if _text(entry.get("source")) != "legacy_fallback":
                continue
            reason = _legacy_fallback_noise_reason(entry, entries)
            records.append(
                {
                    "document_id": key[0],
                    "file_hash": key[1],
                    "file_name": case.get("file_name", ""),
                    "field": key[2],
                    "role": entry.get("role", ""),
                    "candidate_id": entry.get("candidate_id", ""),
                    "reason": reason,
                    "source_trust_tier": entry.get("source_trust_tier", ""),
                    "exclusion_reason": entry.get("exclusion_reason", ""),
                    "value_local_only": entry.get("value_local_only", ""),
                }
            )
    reason_counts = _counter(records, "reason")
    duplicate_count = sum(
        count
        for reason, count in reason_counts.items()
        if reason.startswith("duplicate_of_")
    )
    missing_role_or_boundary = sum(
        reason_counts.get(reason, 0)
        for reason in [
            "missing_role",
            "missing_stop_index",
            "missing_page_line",
            "source_unavailable",
            "selected_output_only_no_evidence",
        ]
    )
    unsafe_or_wrong_role = sum(
        reason_counts.get(reason, 0)
        for reason in ["wrong_role", "reference_or_contact_text", "instruction_or_payment_text"]
    )
    useful_unbounded = reason_counts.get("useful_but_unbounded_location", 0)
    return {
        "legacy_fallback_location_candidates": len(records),
        "noise_cases": len([case for case in cases or [] if case.get("root_cause") == "legacy_fallback_noise"]),
        "duplicate_of_better_source": duplicate_count,
        "missing_role_or_boundary": missing_role_or_boundary,
        "unsafe_or_wrong_role": unsafe_or_wrong_role,
        "useful_but_unbounded": useful_unbounded,
        "unknown": reason_counts.get("unknown", 0),
        "reason_counts": reason_counts,
        "items": records,
    }


def _location_candidate_record(entry, include_private_values):
    return {
        "candidate_id": _text(entry.get("candidate_id")),
        "component_type": _text(entry.get("component_type") or entry.get("component")),
        "source": _text(entry.get("source")),
        "parser_name": _text(entry.get("parser_name")),
        "generator_name": _text(entry.get("generator_name")),
        "page": entry.get("page"),
        "line_index": entry.get("line_index"),
        "bbox": entry.get("bbox"),
        "stop_index": entry.get("stop_index"),
        "role": _text(entry.get("role")),
        "section_context": _text((entry.get("metadata_summary") or {}).get("section_context")),
        "safety_status": _text(entry.get("safety_status")),
        "unsafe_reason": entry.get("unsafe_reason"),
        "is_duplicate_or_fragment": False,
        "is_reference_or_contact_text": _entry_is_reference_or_contact(entry),
        "is_instruction_or_payment_text": _entry_is_instruction_or_payment(entry),
        "is_gold_matching_local_only": False,
        "source_trust_tier": _text(entry.get("source_trust_tier")),
        "trust_reason": _text(entry.get("trust_reason")),
        "eligible_for_disambiguation": bool(entry.get("eligible_for_disambiguation")),
        "eligible_for_review_fusion": bool(entry.get("eligible_for_review_fusion")),
        "exclusion_reason": _text(entry.get("exclusion_reason")),
        "value_local_only": entry.get("value_local_only") if include_private_values else "",
    }


def _date_time_text(entry):
    value = _text(entry.get("value_local_only")).lower()
    value = re.sub(r"\b(fcfs|appt|appointment|between|from|to|time|date)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _date_time_values(entries):
    return {
        _date_time_text(entry)
        for entry in _date_components(entries) + _time_components(entries)
        if _date_time_text(entry)
    }


def _date_time_conflict_reason(entries):
    date_time = _date_components(entries) + _time_components(entries)
    if not date_time:
        return "same_row_date_time_unproven"
    if any(_entry_is_instruction_or_payment(entry) for entry in date_time):
        haystack = " ".join(
            _text(entry.get("unsafe_reason")) + " " + _text((entry.get("metadata_summary") or {}).get("section_context"))
            for entry in date_time
        ).lower()
        if "payment" in haystack or "terms" in haystack:
            return "payment_or_terms_date_time"
        if "footer" in haystack or "signature" in haystack:
            return "page_footer_signature_date"
        return "instructions_date_time_leakage"
    roles = {entry.get("role") for entry in date_time if entry.get("role")}
    if len(roles.intersection({"pickup", "delivery"})) > 1:
        return "pickup_and_delivery_dates_mixed"
    stop_indexes = {_text(entry.get("stop_index")) for entry in date_time if _text(entry.get("stop_index"))}
    if len(stop_indexes) > 1:
        return "multiple_stops_same_role"
    values = sorted(_date_time_values(entries))
    if len(values) <= 1:
        components = {entry.get("component") for entry in date_time}
        if components.intersection({"time", "appointment_window"}) and len(date_time) > 1:
            return "appointment_window_split_start_end"
        return "duplicate_time_window_fragments"
    for left in values:
        for right in values:
            if left != right and _location_texts_related(left, right):
                return "appointment_window_split_start_end"
    if any(entry.get("page_line_status") == "unavailable_from_source" for entry in date_time):
        return "missing_role_boundary"
    if any("ocr" in _text(entry.get("source")).lower() for entry in date_time):
        return "OCR_line_order_noise"
    return "same_row_date_time_unproven"


def _date_time_cluster_conflict_report(row_records, groups):
    records = []
    for row in row_records or []:
        reasons = row.get("blocked_reasons", []) or []
        if "conflicting_date_time_clusters" not in reasons:
            continue
        key = (
            _text(row.get("document_id")),
            _text(row.get("file_hash")),
            _text(row.get("field")),
        )
        entries = groups.get(key, []) or []
        reason = _date_time_conflict_reason(entries)
        records.append(
            {
                "document_id": key[0],
                "file_hash": key[1],
                "field": key[2],
                "role": row.get("role", ""),
                "reason": reason,
                "date_time_candidate_count": len(_date_components(entries) + _time_components(entries)),
                "source_counts": _counter(_date_components(entries) + _time_components(entries), "source"),
                "values_local_only": sorted(_date_time_values(entries)),
            }
        )
    reason_counts = _counter(records, "reason")
    wrong_section = sum(
        reason_counts.get(reason, 0)
        for reason in [
            "instructions_date_time_leakage",
            "payment_or_terms_date_time",
            "page_footer_signature_date",
        ]
    )
    return {
        "conflict_cases": len(records),
        "duplicate_or_split_window": reason_counts.get("duplicate_time_window_fragments", 0)
        + reason_counts.get("appointment_window_split_start_end", 0),
        "wrong_section_leakage": wrong_section,
        "role_mixing": reason_counts.get("pickup_and_delivery_dates_mixed", 0),
        "row_boundary_missing": reason_counts.get("same_row_date_time_unproven", 0)
        + reason_counts.get("missing_role_boundary", 0),
        "unknown": reason_counts.get("unknown", 0),
        "reason_counts": reason_counts,
        "items": records,
    }


def _row_block_type_for_entries(entries):
    parts = []
    for entry in entries or []:
        parts.extend(
            [
                _text(entry.get("source")),
                _text(entry.get("parser_name")),
                _text(entry.get("generator_name")),
                _text((entry.get("metadata_summary") or {}).get("section_context")),
                _text((entry.get("metadata_summary") or {}).get("pairing_method")),
            ]
        )
    haystack = " ".join(parts).lower()
    if "tql" in haystack or "compact" in haystack:
        return "tql_compact_row"
    if "express" in haystack or "pickup 1" in haystack or "drop 2" in haystack:
        return "express_pickup_drop_table"
    if "pu" in haystack or " so " in f" {haystack} " or "ocr_stop_table_reconstructor" in haystack:
        return "pu_so_role_row"
    if any(token in haystack for token in ["shipper", "consignee", "fello", "landstar", "spi"]):
        return "shipper_consignee_role_block"
    if "native_layout" in haystack or "pdfplumber_table" in haystack or "route" in haystack:
        return "route_block"
    return "unknown"


def _row_block_proof_diagnostic(entries, clusters):
    base = _row_block_disambiguation_for_case(entries, clusters)
    row_block_type = _row_block_type_for_entries(entries)
    locations = _location_components(entries)
    date_time = _date_components(entries) + _time_components(entries)
    trusted_locations = [entry for entry in locations if entry.get("eligible_for_disambiguation")]
    trusted_date_time = [entry for entry in date_time if entry.get("eligible_for_disambiguation")]
    blocker = ",".join(base.get("blocked_reasons", []) or [])
    proof_status = "not_proven"
    if base["same_row_or_block_proven"]:
        proof_status = "proven"
        blocker = ""
    elif any(reason in base.get("blocked_reasons", []) for reason in ["payment_instruction_overlap", "role_boundary_unclear"]):
        proof_status = "blocked"
    elif trusted_locations and trusted_date_time:
        if any(_same_location_proximity(location, component) for location in trusted_locations for component in trusted_date_time):
            proof_status = "probable"
            blocker = ""
        elif row_block_type != "unknown" and all(_entry_has_proximity(entry) for entry in trusted_locations + trusted_date_time):
            proof_status = "probable"
            blocker = ""
    if proof_status == "not_proven" and not blocker:
        blocker = "no_bbox_or_line_geometry"
    return {
        **base,
        "row_block_type": row_block_type,
        "proof_status": proof_status,
        "blocker_reason": blocker,
        "location_present": bool(locations),
        "date_time_present": bool(date_time),
    }


def _row_block_disambiguation_for_case(entries, clusters):
    locations = _location_components(entries)
    date_time = _date_components(entries) + _time_components(entries)
    reasons = []
    source_counts = _counter(entries, "source")
    if any(_entry_is_instruction_or_payment(entry) for entry in entries):
        reasons.append("payment_instruction_overlap")
    if any(entry.get("role") not in {"pickup", "delivery"} for entry in entries):
        reasons.append("role_boundary_unclear")
    if len([cluster for cluster in clusters if cluster["cluster_status"] not in {"unsafe_cluster", "wrong_role_cluster"}]) > 1:
        reasons.append("conflicting_location_clusters")
    if len({_text(entry.get("value_local_only")) for entry in date_time if _text(entry.get("value_local_only"))}) > 1:
        reasons.append("conflicting_date_time_clusters")
    if len({entry.get("stop_index") for entry in locations if _text(entry.get("stop_index"))}) > 1:
        reasons.append("multiple_stops_same_role")
    if any(entry.get("page_line_status") == "unavailable_from_source" for entry in locations + date_time):
        reasons.append("source_unavailable")
    if not all(_entry_has_proximity(entry) for entry in locations + date_time):
        reasons.append("no_bbox_or_line_geometry")
    same_row_or_block = False
    if not reasons and locations and date_time:
        for location in locations:
            if any(_same_location_proximity(location, component) for component in date_time):
                same_row_or_block = True
                break
        if not same_row_or_block:
            reasons.append("section_boundary_unclear")
    if not reasons and same_row_or_block:
        reasons = []
    elif not reasons:
        reasons.append("unknown")
    return {
        "same_row_or_block_proven": same_row_or_block,
        "blocked_reasons": sorted(set(reasons)),
        "source_counts": source_counts,
    }


def build_stop_location_disambiguation_report(source_inventory_report, include_private_values=False):
    items = (source_inventory_report or {}).get("items", []) or []
    cases = []
    cluster_records = []
    row_records = []
    after_cases = []
    trusted_cases = []
    trusted_safe_opportunities = []
    groups = {}
    for item in items:
        if item.get("role") not in {"pickup", "delivery"}:
            continue
        _apply_source_trust_metadata(item)
        key = (
            _text(item.get("document_id")),
            _text(item.get("file_hash")),
            _text(item.get("field")),
        )
        groups.setdefault(key, []).append(item)
    for key, entries in groups.items():
        before_status, before_reasons = _fusion_safety_for_entries(entries)
        trusted_entries = [
            entry for entry in entries if entry.get("eligible_for_disambiguation")
        ]
        trusted_locations = _location_components(trusted_entries)
        trusted_clusters = _cluster_location_entries(trusted_locations)
        trusted_clustered_entries = _diagnostic_cluster_representatives(
            trusted_entries,
            trusted_clusters,
        )
        trusted_status, trusted_reasons = _fusion_safety_for_entries(trusted_clustered_entries)
        trusted_status_label, _trusted_score = _location_disambiguation_status(
            trusted_clusters,
            trusted_locations,
        )
        trusted_row_block = _row_block_proof_diagnostic(trusted_entries, trusted_clusters)
        trusted_cases.append(
            {
                "document_id": key[0],
                "file_hash": key[1],
                "field": key[2],
                "fusion_safety": trusted_status,
                "blocked_reasons": trusted_reasons,
                "multiple_locations": "multiple_locations" in trusted_reasons,
                "location_disambiguation_status": trusted_status_label,
                "same_row_or_block_proven": trusted_row_block["same_row_or_block_proven"],
                "row_block_proof_status": trusted_row_block["proof_status"],
                "row_block_type": trusted_row_block["row_block_type"],
            }
        )
        if (
            trusted_status == "fusion_safe"
            and trusted_row_block["proof_status"] in {"proven", "probable"}
        ):
            trusted_safe_opportunities.append(
                {
                    "document_id": key[0],
                    "file_hash": key[1],
                    "file_name": _text(entries[0].get("file_name")) if entries else "",
                    "field": key[2],
                    "role": trusted_entries[0].get("role", "") if trusted_entries else "",
                    "source_type": ",".join(sorted({_text(entry.get("source")) for entry in trusted_entries if _text(entry.get("source"))})),
                    "row_block_type": trusted_row_block["row_block_type"],
                    "location_components": sorted({_text(entry.get("component")) for entry in _location_components(trusted_entries)}),
                    "date_time_components": sorted({_text(entry.get("component")) for entry in _date_components(trusted_entries) + _time_components(trusted_entries)}),
                    "proof_status": trusted_row_block["proof_status"],
                    "recommended_next_step": "eligible_for_review_only_fusion_next_branch",
                    "values_local_only": [
                        entry.get("value_local_only")
                        for entry in trusted_entries
                        if include_private_values
                    ],
                }
            )
        if "multiple_locations" not in before_reasons:
            after_cases.append(
                {
                    "document_id": key[0],
                    "file_hash": key[1],
                    "field": key[2],
                    "before_fusion_safety": before_status,
                    "before_blocked_reasons": before_reasons,
                    "after_fusion_safety": before_status,
                    "after_blocked_reasons": before_reasons,
                    "location_disambiguation_status": "",
                }
            )
            continue
        locations = _location_components(entries)
        clusters = _cluster_location_entries(locations)
        status, score = _location_disambiguation_status(clusters, locations)
        clustered_entries = _diagnostic_cluster_representatives(entries, clusters)
        after_status, after_reasons = _fusion_safety_for_entries(clustered_entries)
        root_cause = _multiple_location_root_cause(entries, clusters)
        location_records = []
        duplicate_ids = set()
        for cluster in clusters:
            if cluster["cluster_status"] in {"duplicate_cluster", "split_address_cluster"}:
                duplicate_ids.update(id(entry) for entry in cluster["entries"])
        for entry in locations:
            record = _location_candidate_record(entry, include_private_values)
            record["is_duplicate_or_fragment"] = id(entry) in duplicate_ids
            location_records.append(record)
        case = {
            "file_name": _text(entries[0].get("file_name")),
            "document_id": key[0],
            "file_hash": key[1],
            "role": entries[0].get("role"),
            "field": key[2],
            "candidate_location_count": len(locations),
            "location_candidates": location_records,
            "root_cause": root_cause,
            "location_disambiguation_score": score,
            "location_disambiguation_status": status,
            "cluster_count": len(clusters),
        }
        cases.append(case)
        for cluster in clusters:
            cluster_records.append(
                {
                    key: value
                    for key, value in cluster.items()
                    if key != "entries"
                }
                | {
                    "document_id": key[0],
                    "file_hash": key[1],
                    "field": key[2],
                    "entry_count": len(cluster["entries"]),
                    "candidate_ids": [
                        _text(entry.get("candidate_id")) for entry in cluster["entries"]
                    ],
                    "values_local_only": [
                        entry.get("value_local_only") for entry in cluster["entries"]
                    ]
                    if include_private_values
                    else [],
                }
            )
        row_block = _row_block_disambiguation_for_case(entries, clusters)
        row_block_proof = _row_block_proof_diagnostic(entries, clusters)
        row_records.append(
            {
                "document_id": key[0],
                "file_hash": key[1],
                "field": key[2],
                "role": entries[0].get("role"),
                "same_row_or_block_proven": row_block["same_row_or_block_proven"],
                "blocked_reasons": row_block["blocked_reasons"],
                "source_counts": row_block["source_counts"],
                "row_block_type": row_block_proof["row_block_type"],
                "proof_status": row_block_proof["proof_status"],
                "blocker_reason": row_block_proof["blocker_reason"],
                "location_present": row_block_proof["location_present"],
                "date_time_present": row_block_proof["date_time_present"],
            }
        )
        after_cases.append(
            {
                "document_id": key[0],
                "file_hash": key[1],
                "field": key[2],
                "before_fusion_safety": before_status,
                "before_blocked_reasons": before_reasons,
                "after_fusion_safety": after_status,
                "after_blocked_reasons": after_reasons,
                "location_disambiguation_status": status,
            }
        )
    after_counts = _counter(after_cases, "after_fusion_safety")
    before_counts = _counter(after_cases, "before_fusion_safety")
    row_source_counts = Counter()
    for row in row_records:
        row_source_counts.update(row.get("source_counts", {}) or {})
    row_summary = {
        "opportunities_checked": len(row_records),
        "same_row_or_block_proven": sum(1 for row in row_records if row["same_row_or_block_proven"]),
        "same_row_or_block_not_proven": sum(1 for row in row_records if not row["same_row_or_block_proven"]),
        "blocked_reason_counts": _counter(row_records, "blocked_reasons"),
        "source_counts": dict(row_source_counts.most_common()),
        "proof_status_counts": _counter(row_records, "proof_status"),
        "row_block_type_counts": _counter(row_records, "row_block_type"),
    }
    source_trust_tier_counts = _counter(items, "source_trust_tier")
    excluded_items = [
        item
        for item in items
        if item.get("role") in {"pickup", "delivery"}
        and not item.get("eligible_for_disambiguation")
    ]
    trusted_counts = _counter(trusted_cases, "fusion_safety")
    trusted_summary = {
        "all_sources": {
            "multiple_locations": len(cases),
            "ambiguous_multiple_locations": sum(
                1 for case in cases if case.get("location_disambiguation_status") == "ambiguous_multiple_locations"
            ),
            "clear_location_cluster": sum(
                1 for case in cases if case.get("location_disambiguation_status") == "clear_location_cluster"
            ),
            "same_row_or_block_proven": row_summary["same_row_or_block_proven"],
            "fusion_safe": after_counts.get("fusion_safe", 0),
            "fusion_risky": after_counts.get("fusion_risky", 0),
            "fusion_unsafe": after_counts.get("fusion_unsafe", 0),
            "fusion_not_possible": after_counts.get("fusion_not_possible", 0),
        },
        "trusted_sources_only": {
            "multiple_locations": sum(1 for case in trusted_cases if case.get("multiple_locations")),
            "ambiguous_multiple_locations": sum(
                1 for case in trusted_cases if case.get("location_disambiguation_status") == "ambiguous_multiple_locations"
            ),
            "clear_location_cluster": sum(
                1 for case in trusted_cases if case.get("location_disambiguation_status") == "clear_location_cluster"
            ),
            "same_row_or_block_proven": sum(
                1 for case in trusted_cases if case.get("same_row_or_block_proven")
            ),
            "fusion_safe": trusted_counts.get("fusion_safe", 0),
            "fusion_risky": trusted_counts.get("fusion_risky", 0),
            "fusion_unsafe": trusted_counts.get("fusion_unsafe", 0),
            "fusion_not_possible": trusted_counts.get("fusion_not_possible", 0),
        },
        "excluded_source_counts": _counter(excluded_items, "source"),
        "excluded_reason_counts": _counter(excluded_items, "exclusion_reason"),
    }
    legacy_noise_report = _legacy_fallback_stop_noise_report(cases, groups)
    datetime_conflict_report = _date_time_cluster_conflict_report(row_records, groups)
    return {
        "schema_version": "ratecon_stop_location_disambiguation_v1",
        "multiple_location_items": cases,
        "location_clusters": cluster_records,
        "row_block_disambiguation": row_records,
        "trusted_source_disambiguation_cases": trusted_cases,
        "trusted_safe_opportunities": trusted_safe_opportunities,
        "multiple_location_root_cause_counts": _counter(cases, "root_cause"),
        "location_cluster_counts": _counter(cluster_records, "cluster_status"),
        "location_disambiguation_score_counts": _counter(cases, "location_disambiguation_status"),
        "stop_row_block_disambiguation_summary": row_summary,
        "fusion_safety_before_disambiguation": before_counts,
        "fusion_safety_after_disambiguation": after_counts,
        "fusion_safety_after_disambiguation_cases": after_cases,
        "legacy_fallback_stop_noise_summary": {
            key: value for key, value in legacy_noise_report.items() if key != "items"
        },
        "legacy_fallback_stop_noise_items": legacy_noise_report.get("items", []),
        "source_trust_tier_counts": source_trust_tier_counts,
        "trusted_source_disambiguation_summary": trusted_summary,
        "date_time_cluster_conflict_summary": {
            key: value for key, value in datetime_conflict_report.items() if key != "items"
        },
        "date_time_cluster_conflict_items": datetime_conflict_report.get("items", []),
        "safe_opportunity_count": len(trusted_safe_opportunities),
        "private_values_printed": bool(include_private_values),
        "raw_text_printed": False,
        "local_only": True,
    }


def _fusion_diagnostic(item, issue_type, source_inventory_entries=None):
    selected = item.get("selected_stop_component_summary", {}) or {}
    dispatch = item.get("best_dispatch_usable_candidate_summary", {}) or {}
    draft = item.get("draft_stop_summary", {}) or {}
    selected_presence = _component_presence(item.get("selected_components", {}) or {}, selected)
    dispatch_presence = _component_presence(item.get("best_candidate_components", {}) or {}, dispatch)
    draft_presence = _component_presence(item.get("draft_components", {}) or {}, draft)
    sources = {
        "selected": selected_presence,
        "best_candidate": dispatch_presence,
        "draft": draft_presence,
    }
    has_location = any(presence["location"] for presence in sources.values())
    has_date = any(presence["date"] for presence in sources.values())
    has_time = any(presence["time"] for presence in sources.values())
    inventory_presence = _source_inventory_presence(source_inventory_entries or [])
    has_location = has_location or inventory_presence["has_location"]
    has_date = has_date or inventory_presence["has_date"]
    has_time = has_time or inventory_presence["has_time"]
    issues = _row_issues(selected) | _row_issues(dispatch) | _row_issues(draft)
    blocked_reasons = []
    if any(issue.startswith("wrong_role") for issue in issues):
        blocked_reasons.append("component_from_wrong_role")
    if any("payment" in issue for issue in issues):
        blocked_reasons.append("component_from_payment_or_instruction")
    if any("instruction" in issue for issue in issues):
        blocked_reasons.append("component_from_payment_or_instruction")
    if any("reference" in issue for issue in issues):
        blocked_reasons.append("component_from_reference_text")
    if "wrong_time" in " ".join(issues) or "wrong_location" in " ".join(issues):
        blocked_reasons.append("component_from_wrong_role")
    if _best_available_source(item) == "source_not_available" and not source_inventory_entries:
        blocked_reasons.append("no_candidate_source")
    if inventory_presence["unsafe_count"]:
        blocked_reasons.append("component_from_payment_or_instruction")
    if "ocr" in _best_available_source(item).lower() and issue_type in {
        "OCR_column_candidate_wrong_alignment",
        "candidate_has_components_but_wrong_against_gold",
    }:
        blocked_reasons.append("OCR_noise")
    if has_location and (has_date or has_time) and not blocked_reasons:
        fusion_possible = True
    else:
        fusion_possible = False
    if has_location and (has_date or has_time) and not fusion_possible and not blocked_reasons:
        blocked_reasons.append("no_line_or_geometry_proximity")
    if has_location and not (has_date or has_time) and not blocked_reasons:
        blocked_reasons.append("no_date_time_candidate_source")
    if (has_date or has_time) and not has_location and not blocked_reasons:
        blocked_reasons.append("no_location_candidate_source")
    if not (has_location or has_date or has_time) and not blocked_reasons:
        blocked_reasons.append("no_candidate_source")
    fusion_safety, safety_reasons = _fusion_safety_for_entries(source_inventory_entries or [])
    if fusion_safety != "fusion_safe":
        blocked_reasons.extend(safety_reasons)
    return {
        "fusion_possible": fusion_safety == "fusion_safe",
        "fusion_safety": fusion_safety,
        "same_role_location_date_available": bool(has_location and has_date),
        "same_role_location_time_available": bool(has_location and has_time),
        "same_role_date_time_available": bool(has_date and has_time),
        "blocked_reasons": sorted(set(blocked_reasons)),
        "source_inventory_components": inventory_presence["component_counts"],
        "source_inventory_sources": inventory_presence["sources"],
    }


def _residual_item_record(item, source_inventory_report=None):
    issue_type = _candidate_issue_type(item)
    inventory_entries = _inventory_entries_for_residual_item(source_inventory_report, item)
    fusion = _fusion_diagnostic(item, issue_type, inventory_entries)
    selected_source = _best_available_source(item)
    if selected_source == "source_not_available" and fusion["source_inventory_sources"]:
        selected_source = "inventory:" + ",".join(fusion["source_inventory_sources"])
    return {
        "document_id": item.get("document_id", ""),
        "file_hash": item.get("file_hash", ""),
        "file_name": item.get("file_name", ""),
        "field": item.get("field", ""),
        "selected_status": (item.get("selected_stop_component_summary", {}) or {}).get("raw_status", ""),
        "selected_usability_tier": (item.get("selected_stop_component_summary", {}) or {}).get(
            "dispatch_usability_tier",
            "",
        ),
        "selected_candidate_source": selected_source,
        "selected_candidate_components": _prediction_component_payload(item, "selected"),
        "gold_components": _prediction_component_payload(item, "gold"),
        "best_structured_candidate": _prediction_component_payload(item, "best_candidate"),
        "best_ocr_column_candidate": (
            _prediction_component_payload(item, "best_candidate")
            if "ocr" in _best_available_source(item).lower()
            else {}
        ),
        "best_native_layout_candidate": (
            _prediction_component_payload(item, "best_candidate")
            if "layout" in _best_available_source(item).lower()
            else {}
        ),
        "candidate_issue_type": issue_type,
        "recommended_fix_type": _recommended_fix_type(issue_type, item),
        "fusion_possible": fusion["fusion_possible"],
        "fusion_safety": fusion["fusion_safety"],
        "same_role_location_date_available": fusion["same_role_location_date_available"],
        "same_role_location_time_available": fusion["same_role_location_time_available"],
        "same_role_date_time_available": fusion["same_role_date_time_available"],
        "blocked_reasons": fusion["blocked_reasons"],
        "source_inventory_match_count": len(inventory_entries),
        "source_inventory_components": fusion["source_inventory_components"],
        "source_inventory_sources": fusion["source_inventory_sources"],
    }


def _counter(items, key):
    counts = {}
    for item in items:
        value = item.get(key)
        if isinstance(value, list):
            values = value or [""]
        else:
            values = [value]
        for entry in values:
            entry = _text(entry) or "none"
            counts[entry] = counts.get(entry, 0) + 1
    return dict(sorted(counts.items()))


def build_residual_extraction_report(packet, source_inventory_report=None):
    residual_items = [
        _residual_item_record(item, source_inventory_report=source_inventory_report)
        for item in packet.get("items", []) or []
        if "extraction_candidate_issue" in (item.get("categories", []) or [])
    ]
    fusion_possible = [item for item in residual_items if item.get("fusion_possible")]
    fusion_summary = {
        "issues_checked": len(residual_items),
        "fusion_possible": len(fusion_possible),
        "fusion_not_possible": len(residual_items) - len(fusion_possible),
        "same_role_location_date_available": sum(
            1 for item in residual_items if item.get("same_role_location_date_available")
        ),
        "same_role_location_time_available": sum(
            1 for item in residual_items if item.get("same_role_location_time_available")
        ),
        "same_role_date_time_available": sum(
            1 for item in residual_items if item.get("same_role_date_time_available")
        ),
        "best_source_counts": _counter(residual_items, "selected_candidate_source"),
        "blocked_reason_counts": _counter(residual_items, "blocked_reasons"),
        "fusion_safety_counts": _counter(residual_items, "fusion_safety"),
    }
    by_field = {}
    for field in [FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS]:
        field_items = [item for item in residual_items if item.get("field") == field]
        issue_counts = _counter(field_items, "candidate_issue_type")
        if issue_counts.get("selected_location_only_partial") or issue_counts.get("selected_missing_date_time"):
            decision = "needs_component_fusion"
        elif any("OCR" in key for key in issue_counts):
            decision = "needs_ocr_geometry_work"
        elif issue_counts.get("no_viable_candidate"):
            decision = "keep_manual_review"
        else:
            decision = "keep_manual_review"
        by_field["pickup" if field == FIELD_PICKUP_STOPS else "delivery"] = decision
    return {
        "schema_version": "ratecon_stop_residual_extraction_report_v1",
        "exclusive_category_counts": packet.get("exclusive_category_counts", {}),
        "residual_item_count": len(residual_items),
        "candidate_issue_type_counts": _counter(residual_items, "candidate_issue_type"),
        "recommended_fix_type_counts": _counter(residual_items, "recommended_fix_type"),
        "stop_component_fusion_opportunity_summary": fusion_summary,
        "no_candidate_source_trace_summary": build_no_candidate_source_trace_summary(
            residual_items,
            source_inventory_report,
        ),
        "stop_residual_decision": by_field,
        "items": residual_items,
        "private_values_printed": bool(packet.get("private_values_printed")),
        "raw_text_printed": False,
        "local_only": True,
    }


def build_stop_gold_review_packet(
    gold_labels,
    audit_records,
    evaluation=None,
    include_private_values_local_only=False,
):
    evaluation = evaluation or evaluate_ratecon_against_gold(gold_labels, audit_records)
    gold_lookup = _gold_by_doc_field(gold_labels)
    audit_lookup = _audit_by_doc_field(audit_records)
    selected_side_by_side = _selected_stop_side_by_side_items(
        evaluation,
        audit_lookup,
        gold_lookup,
        include_private_values_local_only,
    )
    review_items = []
    for key, rows in sorted(_comparison_rows_by_doc_field(evaluation).items()):
        selected = rows.get(SYSTEM_SHADOW, {})
        dispatch = rows.get(SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP, {})
        draft = rows.get(SYSTEM_SHADOW_STOP_REVIEW_DRAFT, {})
        statuses = {
            _text(row.get("status"))
            for row in [selected, dispatch, draft]
            if isinstance(row, dict) and row
        }
        tiers = {
            _text(row.get("stop_usability_tier"))
            for row in [selected, dispatch, draft]
            if isinstance(row, dict) and row
        }
        gold_info = gold_lookup.get(key, {})
        if (
            not statuses.intersection(
            {
                "partial_match",
                "wrong",
                "extractor_missing",
                "shadow_component_not_serialized",
                "source_not_available",
                "unsupported_unparsed_location",
                "selected_partial_not_comparable",
                "selected_partial_missing_required_components",
            }
            )
            and not tiers.intersection(
                {
                    "unsafe_wrong",
                    "useful_partial",
                    "useful_partial_location_only",
                    "unsupported_unparsed_location",
                    "selected_partial_not_comparable",
                    "selected_partial_missing_required_components",
                }
            )
            and not _true_gold_review_needed(gold_info)
            and not _known_absent_reason(gold_info)
        ):
            continue
        reason = _reason_for_case(selected, dispatch, draft, gold_info)
        secondary_reasons = _secondary_reasons_for_case(
            selected,
            dispatch,
            draft,
            gold_info,
        )
        categories = _item_categories(
            selected,
            dispatch,
            draft,
            gold_info,
            reason,
            secondary_reasons,
        )
        record = _record_for_key(audit_lookup, key)
        selected_prediction = _private_prediction(record, SYSTEM_SHADOW, key[2])
        dispatch_prediction = _private_prediction(
            record,
            SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP,
            key[2],
        )
        draft_prediction = _private_prediction(
            record,
            SYSTEM_SHADOW_STOP_REVIEW_DRAFT,
            key[2],
        )
        review_items.append(
            {
                "document_id": _text(key[0]),
                "file_hash": _text(key[1]),
                "file_name": _text(gold_info.get("file_name")),
                "field": _text(key[2]),
                "primary_category": _primary_category(categories),
                "categories": categories,
                "current_gold_completeness_status": gold_info.get("completeness", []),
                "gold_components": _gold_component_values(
                    gold_info,
                    include_private_values_local_only,
                ),
                "selected_stop_component_summary": _safe_row_summary(selected),
                "selected_components": _stop_component_values_from_prediction(
                    selected_prediction,
                    include_private_values_local_only,
                ),
                "selected_source_hint": _source_hint_from_prediction(selected_prediction),
                "best_dispatch_usable_candidate_summary": _safe_row_summary(dispatch),
                "best_candidate_components": _stop_component_values_from_prediction(
                    dispatch_prediction,
                    include_private_values_local_only,
                ),
                "best_candidate_source_hint": _source_hint_from_prediction(
                    dispatch_prediction,
                ),
                "draft_stop_summary": _safe_row_summary(draft),
                "draft_components": _stop_component_values_from_prediction(
                    draft_prediction,
                    include_private_values_local_only,
                ),
                "draft_source_hint": _source_hint_from_prediction(draft_prediction),
                "missing_gold_components": _missing_gold_components(gold_info),
                "suspect_reason": reason,
                "secondary_reasons": secondary_reasons,
                "recommendation": _recommendation_for_reason(reason),
            }
        )
    reason_counts = {}
    secondary_reason_counts = {}
    category_counts = {category: 0 for category in STOP_REVIEW_CATEGORIES}
    for item in review_items:
        reason = item["suspect_reason"]
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        for secondary_reason in item.get("secondary_reasons", []) or []:
            secondary_reason_counts[secondary_reason] = (
                secondary_reason_counts.get(secondary_reason, 0) + 1
            )
        for category in item.get("categories", []) or []:
            category_counts[category] = category_counts.get(category, 0) + 1
    return {
        "schema_version": "ratecon_stop_gold_review_packet_v3_known_absent",
        "review_item_count": len(review_items),
        "reason_counts": reason_counts,
        "secondary_reason_counts": secondary_reason_counts,
        "category_counts": category_counts,
        "exclusive_category_counts": _exclusive_category_counts(review_items),
        "stop_gold_completeness_summary": build_stop_gold_completeness_summary(
            gold_labels,
        ),
        "selected_stop_serialization_gap_summary": evaluation.get(
            "selected_stop_serialization_gap_summary",
            {},
        ),
        "remaining_sidecar_component_gap_summary": evaluation.get(
            "remaining_sidecar_component_gap_summary",
            {},
        ),
        "selected_stop_side_by_side_items": selected_side_by_side,
        "items": review_items,
        "known_absent_summary": _known_absent_summary(review_items),
        "gold_labels_modified": False,
        "private_values_printed": bool(include_private_values_local_only),
        "local_only": True,
    }


def build_patch_template(packet):
    patches = []
    for item in packet.get("items", []) or []:
        if "true_gold_review_needed" not in (item.get("categories", []) or []):
            continue
        patches.append(
            {
                "document_id": item.get("document_id", ""),
                "file_hash": item.get("file_hash", ""),
                "file_name": item.get("file_name", ""),
                "field": item.get("field", ""),
                "stop_index": 1,
                "review_reason": item.get("suspect_reason", ""),
                "secondary_reasons": item.get("secondary_reasons", []),
                "proposed_gold": {
                    component: None for component in STOP_GOLD_COMPLETENESS_COMPONENTS
                },
                "reviewer_notes": "",
            }
        )
    return {
        "schema_version": "ratecon_stop_gold_patch_template_v1",
        "instructions": (
            "Dry-run by default with scripts/apply_ratecon_stop_gold_review_patch.py. "
            "Fill proposed_gold manually; this template is not populated from shadow candidates."
        ),
        "patches": patches,
        "auto_filled_from_shadow_candidates": False,
        "gold_labels_modified": False,
        "local_only": True,
    }


def write_packet(packet, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "stop_gold_review_summary.md"
    items_json_path = output_dir / "stop_gold_review_items.json"
    items_csv_path = output_dir / "stop_gold_review_items.csv"
    patch_template_path = output_dir / "stop_gold_patch_template.json"
    code_issues_path = output_dir / "stop_code_issues.csv"
    manual_review_path = output_dir / "stop_manual_review_items.csv"
    known_absent_path = output_dir / "stop_known_absent_items.csv"
    selected_gaps_csv_path = output_dir / "selected_stop_serialization_gaps.csv"
    selected_gaps_json_path = output_dir / "selected_stop_serialization_gaps.json"
    selected_side_by_side_path = output_dir / "selected_stop_component_side_by_side.csv"
    items_json_path.write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Stop Gold Review",
        "",
        f"Review items: {packet.get('review_item_count', 0)}",
        f"Category counts: {json.dumps(packet.get('category_counts', {}), sort_keys=True)}",
        "Exclusive category counts: "
        + json.dumps(packet.get("exclusive_category_counts", {}), sort_keys=True),
        f"Reason counts: {json.dumps(packet.get('reason_counts', {}), sort_keys=True)}",
        f"Secondary reason counts: {json.dumps(packet.get('secondary_reason_counts', {}), sort_keys=True)}",
        f"Known absent summary: {json.dumps(packet.get('known_absent_summary', {}), sort_keys=True)}",
        f"Patch template rows: {len(build_patch_template(packet).get('patches', []))}",
        "Selected stop serialization gap summary: "
        + json.dumps(
            packet.get("selected_stop_serialization_gap_summary", {}) or {},
            sort_keys=True,
        ),
        "Remaining sidecar component gap summary: "
        + json.dumps(
            packet.get("remaining_sidecar_component_gap_summary", {}) or {},
            sort_keys=True,
        ),
        "",
        "## Stop Gold Completeness",
        "",
        json.dumps(
            packet.get("stop_gold_completeness_summary", {}),
            indent=2,
            sort_keys=True,
        ),
        "",
        "## Items",
        "",
    ]
    for item in packet.get("items", []) or []:
        lines.append(
            f"- {item.get('file_name') or item.get('document_id')} "
            f"{item.get('field')}: {item.get('primary_category')} / {item.get('suspect_reason')} "
            f"-> {item.get('recommendation')}"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    fieldnames = [
        "document_id",
        "file_hash",
        "file_name",
        "field",
        "primary_category",
        "categories",
        "suspect_reason",
        "recommendation",
        "secondary_reasons",
        "missing_gold_components",
        "selected_raw_status",
        "selected_dispatch_usability_tier",
        "selected_candidate_has_dispatch_components",
        "selected_gold_dispatch_usable_match",
        "selected_serialization_gap_classification",
        "dispatch_raw_status",
        "dispatch_dispatch_usability_tier",
        "dispatch_candidate_has_dispatch_components",
        "dispatch_gold_dispatch_usable_match",
        "draft_raw_status",
        "draft_dispatch_usability_tier",
        "draft_candidate_has_dispatch_components",
        "draft_gold_dispatch_usable_match",
    ]

    def item_row(item):
        selected = item.get("selected_stop_component_summary", {}) or {}
        dispatch = item.get("best_dispatch_usable_candidate_summary", {}) or {}
        draft = item.get("draft_stop_summary", {}) or {}
        row = {
            "document_id": item.get("document_id", ""),
            "file_hash": item.get("file_hash", ""),
            "file_name": item.get("file_name", ""),
            "field": item.get("field", ""),
            "primary_category": item.get("primary_category", ""),
            "categories": ",".join(item.get("categories", []) or []),
            "suspect_reason": item.get("suspect_reason", ""),
            "recommendation": item.get("recommendation", ""),
            "secondary_reasons": ",".join(
                item.get("secondary_reasons", []) or []
            ),
            "missing_gold_components": ",".join(
                item.get("missing_gold_components", []) or []
            ),
            "selected_raw_status": selected.get("raw_status", ""),
            "selected_dispatch_usability_tier": selected.get(
                "dispatch_usability_tier",
                "",
            ),
            "selected_candidate_has_dispatch_components": selected.get(
                "candidate_has_dispatch_components",
                "",
            ),
            "selected_gold_dispatch_usable_match": selected.get(
                "gold_dispatch_usable_match",
                "",
            ),
            "selected_serialization_gap_classification": selected.get(
                "serialization_gap_classification",
                "",
            ),
            "dispatch_raw_status": dispatch.get("raw_status", ""),
            "dispatch_dispatch_usability_tier": dispatch.get(
                "dispatch_usability_tier",
                "",
            ),
            "dispatch_candidate_has_dispatch_components": dispatch.get(
                "candidate_has_dispatch_components",
                "",
            ),
            "dispatch_gold_dispatch_usable_match": dispatch.get(
                "gold_dispatch_usable_match",
                "",
            ),
            "draft_raw_status": draft.get("raw_status", ""),
            "draft_dispatch_usability_tier": draft.get(
                "dispatch_usability_tier",
                "",
            ),
            "draft_candidate_has_dispatch_components": draft.get(
                "candidate_has_dispatch_components",
                "",
            ),
            "draft_gold_dispatch_usable_match": draft.get(
                "gold_dispatch_usable_match",
                "",
            ),
        }
        for prefix in ["gold", "selected", "best_candidate", "draft"]:
            values = item.get(f"{prefix}_components", {}) or {}
            for component in STOP_GOLD_COMPLETENESS_COMPONENTS:
                key = f"{prefix}_{component}"
                row[key] = values.get(component, "")
            if prefix != "gold":
                for component in LOCAL_ONLY_STOP_COMPONENTS:
                    key = f"{prefix}_{component}"
                    row[key] = values.get(component, "")
        for prefix in ["selected", "best_candidate", "draft"]:
            hint = item.get(f"{prefix}_source_hint", {}) or {}
            for key in ["source", "parser_name", "pairing_method", "page"]:
                row[f"{prefix}_{key}"] = hint.get(key, "")
        return row

    private_fieldnames = list(fieldnames)
    for prefix in ["gold", "selected", "best_candidate", "draft"]:
        for component in STOP_GOLD_COMPLETENESS_COMPONENTS:
            private_fieldnames.append(f"{prefix}_{component}")
    for prefix in ["selected", "best_candidate", "draft"]:
        for component in LOCAL_ONLY_STOP_COMPONENTS:
            private_fieldnames.append(f"{prefix}_{component}")
    for prefix in ["selected", "best_candidate", "draft"]:
        for key in ["source", "parser_name", "pairing_method", "page"]:
            private_fieldnames.append(f"{prefix}_{key}")

    def write_rows(path, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=private_fieldnames)
            writer.writeheader()
            for item in rows:
                writer.writerow(item_row(item))

    write_rows(items_csv_path, packet.get("items", []) or [])
    write_rows(
        code_issues_path,
        [
            item
            for item in packet.get("items", []) or []
            if "code_or_evaluator_issue" in (item.get("categories", []) or [])
        ],
    )
    write_rows(
        manual_review_path,
        [
            item
            for item in packet.get("items", []) or []
            if "true_gold_review_needed" in (item.get("categories", []) or [])
        ],
    )
    write_rows(
        known_absent_path,
        [
            item
            for item in packet.get("items", []) or []
            if item.get("suspect_reason") in KNOWN_ABSENT_REASONS
            or set(item.get("secondary_reasons", []) or []).intersection(KNOWN_ABSENT_REASONS)
        ],
    )
    side_by_side_fieldnames = [
        "document_id",
        "file_hash",
        "file_name",
        "field",
        "stop_index",
        "selected_source",
        "selected_parser_name",
        "selected_pairing_method",
        "raw_status",
        "dispatch_usability_tier",
        "serialization_gap_reason",
        "fix_status",
    ]
    for prefix in ["gold", "selected"]:
        for component in STOP_GOLD_COMPLETENESS_COMPONENTS:
            side_by_side_fieldnames.append(f"{prefix}_{component}")
    for component in LOCAL_ONLY_STOP_COMPONENTS:
        side_by_side_fieldnames.append(f"selected_{component}")

    def side_by_side_row(item):
        row = {
            key: item.get(key, "")
            for key in [
                "document_id",
                "file_hash",
                "file_name",
                "field",
                "stop_index",
                "selected_source",
                "selected_parser_name",
                "selected_pairing_method",
                "raw_status",
                "dispatch_usability_tier",
                "serialization_gap_reason",
                "fix_status",
            ]
        }
        for prefix in ["gold", "selected"]:
            values = item.get(f"{prefix}_components", {}) or {}
            for component in STOP_GOLD_COMPLETENESS_COMPONENTS:
                row[f"{prefix}_{component}"] = values.get(component, "")
            if prefix == "selected":
                for component in LOCAL_ONLY_STOP_COMPONENTS:
                    row[f"{prefix}_{component}"] = values.get(component, "")
        return row

    selected_side_by_side_items = packet.get("selected_stop_side_by_side_items", []) or []
    with selected_side_by_side_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=side_by_side_fieldnames)
        writer.writeheader()
        for item in selected_side_by_side_items:
            writer.writerow(side_by_side_row(item))
    selected_gap_items = [
        item
        for item in selected_side_by_side_items
        if item.get("fix_status")
        in {"needs_private_eval_serialization", "true_missing", "unsupported_selected_partial"}
    ]
    selected_gaps_json_path.write_text(
        json.dumps(
            {
                "selected_stop_serialization_gap_summary": packet.get(
                    "selected_stop_serialization_gap_summary",
                    {},
                ),
                "items": selected_gap_items,
                "private_values_printed": bool(packet.get("private_values_printed")),
                "raw_text_printed": False,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    with selected_gaps_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=side_by_side_fieldnames)
        writer.writeheader()
        for item in selected_gap_items:
            writer.writerow(side_by_side_row(item))
    patch_template_path.write_text(
        json.dumps(build_patch_template(packet), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "summary_md": str(summary_path),
        "items_json": str(items_json_path),
        "items_csv": str(items_csv_path),
        "code_issues_csv": str(code_issues_path),
        "manual_review_items_csv": str(manual_review_path),
        "known_absent_items_csv": str(known_absent_path),
        "patch_template_json": str(patch_template_path),
        "selected_stop_serialization_gaps_csv": str(selected_gaps_csv_path),
        "selected_stop_serialization_gaps_json": str(selected_gaps_json_path),
        "selected_stop_component_side_by_side_csv": str(selected_side_by_side_path),
    }


def write_residual_extraction_report(report, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "stop_residual_extraction_summary.md"
    items_csv_path = output_dir / "stop_residual_extraction_items.csv"
    items_json_path = output_dir / "stop_residual_extraction_items.json"
    items = report.get("items", []) or []
    items_json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary_lines = [
        "# Stop Residual Extraction Forensics",
        "",
        f"Residual extraction/candidate items: {report.get('residual_item_count', 0)}",
        "Exclusive category counts: "
        + json.dumps(report.get("exclusive_category_counts", {}), sort_keys=True),
        "Candidate issue type counts: "
        + json.dumps(report.get("candidate_issue_type_counts", {}), sort_keys=True),
        "Recommended fix type counts: "
        + json.dumps(report.get("recommended_fix_type_counts", {}), sort_keys=True),
        "Fusion opportunity summary: "
        + json.dumps(
            report.get("stop_component_fusion_opportunity_summary", {}),
            sort_keys=True,
        ),
        "No candidate source trace summary: "
        + json.dumps(report.get("no_candidate_source_trace_summary", {}), sort_keys=True),
        "Stop residual decision: "
        + json.dumps(report.get("stop_residual_decision", {}), sort_keys=True),
        "",
        "Private values are local-only and must not be committed.",
        "",
        "## Items",
        "",
    ]
    for item in items:
        summary_lines.append(
            f"- {item.get('file_name') or item.get('document_id')} "
            f"{item.get('field')}: {item.get('candidate_issue_type')} "
            f"-> {item.get('recommended_fix_type')}"
        )
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    fieldnames = [
        "document_id",
        "file_hash",
        "file_name",
        "field",
        "selected_status",
        "selected_usability_tier",
        "selected_candidate_source",
        "selected_candidate_components",
        "gold_components",
        "best_structured_candidate",
        "best_ocr_column_candidate",
        "best_native_layout_candidate",
        "candidate_issue_type",
        "recommended_fix_type",
        "fusion_possible",
        "fusion_safety",
        "same_role_location_date_available",
        "same_role_location_time_available",
        "same_role_date_time_available",
        "blocked_reasons",
        "source_inventory_match_count",
        "source_inventory_components",
        "source_inventory_sources",
    ]
    with items_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            row = dict(item)
            for key in [
                "selected_candidate_components",
                "gold_components",
                "best_structured_candidate",
                "best_ocr_column_candidate",
                "best_native_layout_candidate",
                "blocked_reasons",
                "source_inventory_components",
                "source_inventory_sources",
            ]:
                row[key] = json.dumps(row.get(key, [] if key == "blocked_reasons" else {}), sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    return {
        "summary_md": str(summary_path),
        "items_csv": str(items_csv_path),
        "items_json": str(items_json_path),
    }


def write_stop_source_inventory_report(report, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "stop_source_inventory_summary.md"
    items_csv_path = output_dir / "stop_source_inventory_items.csv"
    items_json_path = output_dir / "stop_source_inventory_items.json"
    by_document_path = output_dir / "stop_source_inventory_by_document.json"
    provenance_gap_path = output_dir / "stop_provenance_gap_report.csv"
    dedupe_lineage_path = output_dir / "stop_dedupe_lineage_report.csv"
    component_lineage_path = output_dir / "stop_component_source_lineage_report.csv"
    items = report.get("items", []) or []
    matrix = report.get("stop_component_availability_matrix", {}) or {}
    items_json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    by_document_path.write_text(
        json.dumps(matrix, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary_lines = [
        "# Stop Component Source Inventory",
        "",
        "Source inventory summary: "
        + json.dumps(report.get("source_inventory_summary", {}), sort_keys=True),
        "Source inventory V2 summary: "
        + json.dumps(report.get("source_inventory_v2_summary", {}), sort_keys=True),
        "Source inventory V3 summary: "
        + json.dumps(report.get("source_inventory_v3_summary", {}), sort_keys=True),
        "Provenance loss root cause by module: "
        + json.dumps(report.get("provenance_loss_root_cause_by_module", {}), sort_keys=True),
        "Component availability corpus summary: "
        + json.dumps(
            (
                report.get("source_inventory_summary", {})
                .get("component_availability_corpus_summary", {})
            ),
            sort_keys=True,
        ),
        "Dedupe/provenance loss summary: "
        + json.dumps(
            report.get("stop_dedupe_provenance_loss_summary", {}),
            sort_keys=True,
        ),
        "Fusion safety model summary: "
        + json.dumps(
            {
                key: value
                for key, value in (report.get("stop_fusion_safety_model_summary", {}) or {}).items()
                if key != "cases"
            },
            sort_keys=True,
        ),
        "",
        "Private values are local-only and must not be committed.",
        "",
        "## Documents",
        "",
    ]
    for doc in matrix.values():
        summary_lines.append(
            f"- {doc.get('file_name') or doc.get('document_id')}: "
            f"pickup={json.dumps(doc.get('pickup', {}), sort_keys=True)} "
            f"delivery={json.dumps(doc.get('delivery', {}), sort_keys=True)}"
        )
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    fieldnames = [
        "file_name",
        "document_id",
        "file_hash",
        "field",
        "role",
        "component",
        "component_type",
        "value_local_only",
        "source",
        "parser_name",
        "generator_name",
        "source_group",
        "page",
        "line_index",
        "bbox",
        "stop_index",
        "candidate_id",
        "synthetic_candidate_id",
        "page_line_status",
        "source_lineage",
        "component_sources",
        "component_sources_available",
        "dedupe_lineage",
        "merged_provenance",
        "provenance_status",
        "safety_status",
        "unsafe_reason",
    ]
    with items_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            row = dict(item)
            row["bbox"] = json.dumps(row.get("bbox"), sort_keys=True)
            row["source_lineage"] = json.dumps(row.get("source_lineage") or [], sort_keys=True)
            row["component_sources"] = json.dumps(row.get("component_sources") or [], sort_keys=True)
            row["dedupe_lineage"] = json.dumps(row.get("dedupe_lineage") or [], sort_keys=True)
            row["merged_provenance"] = json.dumps(row.get("merged_provenance") or [], sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    gap_rows = [
        item
        for item in items
        if item.get("provenance_status")
        not in {"complete", "page_line_unavailable_from_source"}
    ]
    with provenance_gap_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in gap_rows:
            row = dict(item)
            row["bbox"] = json.dumps(row.get("bbox"), sort_keys=True)
            row["source_lineage"] = json.dumps(row.get("source_lineage") or [], sort_keys=True)
            row["component_sources"] = json.dumps(row.get("component_sources") or [], sort_keys=True)
            row["dedupe_lineage"] = json.dumps(row.get("dedupe_lineage") or [], sort_keys=True)
            row["merged_provenance"] = json.dumps(row.get("merged_provenance") or [], sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    lineage_rows = [
        item for item in items if item.get("dedupe_lineage") or item.get("merged_provenance")
    ]
    with dedupe_lineage_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in lineage_rows:
            row = dict(item)
            row["bbox"] = json.dumps(row.get("bbox"), sort_keys=True)
            row["source_lineage"] = json.dumps(row.get("source_lineage") or [], sort_keys=True)
            row["component_sources"] = json.dumps(row.get("component_sources") or [], sort_keys=True)
            row["dedupe_lineage"] = json.dumps(row.get("dedupe_lineage") or [], sort_keys=True)
            row["merged_provenance"] = json.dumps(row.get("merged_provenance") or [], sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    component_lineage_rows = [
        item for item in items if item.get("component_sources") or item.get("component_sources_available")
    ]
    with component_lineage_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in component_lineage_rows:
            row = dict(item)
            row["bbox"] = json.dumps(row.get("bbox"), sort_keys=True)
            row["source_lineage"] = json.dumps(row.get("source_lineage") or [], sort_keys=True)
            row["component_sources"] = json.dumps(row.get("component_sources") or [], sort_keys=True)
            row["dedupe_lineage"] = json.dumps(row.get("dedupe_lineage") or [], sort_keys=True)
            row["merged_provenance"] = json.dumps(row.get("merged_provenance") or [], sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    return {
        "summary_md": str(summary_path),
        "items_csv": str(items_csv_path),
        "items_json": str(items_json_path),
        "by_document_json": str(by_document_path),
        "provenance_gap_csv": str(provenance_gap_path),
        "dedupe_lineage_csv": str(dedupe_lineage_path),
        "component_source_lineage_csv": str(component_lineage_path),
    }


def write_stop_location_disambiguation_report(report, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "stop_location_disambiguation_summary.md"
    trusted_summary_path = output_dir / "stop_trusted_disambiguation_summary.md"
    multiple_items_path = output_dir / "stop_multiple_location_items.csv"
    trusted_items_path = output_dir / "stop_trusted_disambiguation_items.csv"
    safe_opportunities_path = output_dir / "stop_trusted_safe_opportunities.csv"
    excluded_legacy_path = output_dir / "stop_excluded_legacy_fallback_noise.csv"
    datetime_conflicts_path = output_dir / "stop_datetime_conflicts.csv"
    clusters_path = output_dir / "stop_location_clusters.json"
    row_block_path = output_dir / "stop_row_block_disambiguation.csv"
    fusion_after_path = output_dir / "stop_fusion_safety_after_disambiguation.json"
    summary_lines = [
        "# Stop Location Disambiguation Diagnostics",
        "",
        "Multiple-location root causes: "
        + json.dumps(report.get("multiple_location_root_cause_counts", {}), sort_keys=True),
        "Location cluster counts: "
        + json.dumps(report.get("location_cluster_counts", {}), sort_keys=True),
        "Disambiguation score counts: "
        + json.dumps(report.get("location_disambiguation_score_counts", {}), sort_keys=True),
        "Row/block disambiguation summary: "
        + json.dumps(report.get("stop_row_block_disambiguation_summary", {}), sort_keys=True),
        "Fusion safety before disambiguation: "
        + json.dumps(report.get("fusion_safety_before_disambiguation", {}), sort_keys=True),
        "Fusion safety after disambiguation: "
        + json.dumps(report.get("fusion_safety_after_disambiguation", {}), sort_keys=True),
        "Legacy fallback noise: "
        + json.dumps(report.get("legacy_fallback_stop_noise_summary", {}), sort_keys=True),
        "Source trust tiers: "
        + json.dumps(report.get("source_trust_tier_counts", {}), sort_keys=True),
        "Trusted-source disambiguation: "
        + json.dumps(report.get("trusted_source_disambiguation_summary", {}), sort_keys=True),
        "Date/time conflict summary: "
        + json.dumps(report.get("date_time_cluster_conflict_summary", {}), sort_keys=True),
        f"Trusted safe opportunity count: {report.get('safe_opportunity_count', 0)}",
        "",
        "This report is diagnostic-only. It must not change selected output or enable fusion.",
        "Private values are local-only and must not be committed.",
        "",
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    trusted_summary_lines = [
        "# Trusted Source Stop Disambiguation Diagnostics",
        "",
        "Legacy fallback noise summary: "
        + json.dumps(report.get("legacy_fallback_stop_noise_summary", {}), sort_keys=True),
        "Source trust tier counts: "
        + json.dumps(report.get("source_trust_tier_counts", {}), sort_keys=True),
        "All sources vs trusted sources only: "
        + json.dumps(report.get("trusted_source_disambiguation_summary", {}), sort_keys=True),
        "Date/time conflict summary: "
        + json.dumps(report.get("date_time_cluster_conflict_summary", {}), sort_keys=True),
        "Narrow row/block proof summary: "
        + json.dumps(report.get("stop_row_block_disambiguation_summary", {}), sort_keys=True),
        f"Safe opportunities: {report.get('safe_opportunity_count', 0)}",
        "",
        "This report is diagnostic-only. Fused stops are not emitted by this packet.",
        "",
    ]
    trusted_summary_path.write_text("\n".join(trusted_summary_lines) + "\n", encoding="utf-8")
    clusters_path.write_text(
        json.dumps(report.get("location_clusters", []), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    fusion_after_path.write_text(
        json.dumps(
            {
                "before": report.get("fusion_safety_before_disambiguation", {}),
                "after": report.get("fusion_safety_after_disambiguation", {}),
                "cases": report.get("fusion_safety_after_disambiguation_cases", []),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    item_fieldnames = [
        "document_id",
        "file_hash",
        "file_name",
        "field",
        "role",
        "candidate_location_count",
        "root_cause",
        "location_disambiguation_status",
        "location_disambiguation_score",
        "cluster_count",
        "location_candidates",
    ]
    with multiple_items_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=item_fieldnames)
        writer.writeheader()
        for item in report.get("multiple_location_items", []) or []:
            row = dict(item)
            row["location_candidates"] = json.dumps(
                row.get("location_candidates", []),
                sort_keys=True,
            )
            writer.writerow({key: row.get(key, "") for key in item_fieldnames})
    row_fieldnames = [
        "document_id",
        "file_hash",
        "field",
        "role",
        "same_row_or_block_proven",
        "blocked_reasons",
        "source_counts",
        "row_block_type",
        "proof_status",
        "blocker_reason",
        "location_present",
        "date_time_present",
    ]
    with row_block_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=row_fieldnames)
        writer.writeheader()
        for item in report.get("row_block_disambiguation", []) or []:
            row = dict(item)
            row["blocked_reasons"] = json.dumps(row.get("blocked_reasons", []), sort_keys=True)
            row["source_counts"] = json.dumps(row.get("source_counts", {}), sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in row_fieldnames})
    trusted_fieldnames = [
        "document_id",
        "file_hash",
        "field",
        "fusion_safety",
        "blocked_reasons",
        "multiple_locations",
        "location_disambiguation_status",
        "same_row_or_block_proven",
        "row_block_proof_status",
        "row_block_type",
    ]
    with trusted_items_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=trusted_fieldnames)
        writer.writeheader()
        for item in report.get("trusted_source_disambiguation_cases", []) or []:
            row = dict(item)
            row["blocked_reasons"] = json.dumps(row.get("blocked_reasons", []), sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in trusted_fieldnames})
    safe_fieldnames = [
        "document_id",
        "file_hash",
        "file_name",
        "field",
        "role",
        "source_type",
        "row_block_type",
        "location_components",
        "date_time_components",
        "proof_status",
        "recommended_next_step",
        "values_local_only",
    ]
    with safe_opportunities_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=safe_fieldnames)
        writer.writeheader()
        for item in report.get("trusted_safe_opportunities", []) or []:
            row = dict(item)
            row["location_components"] = json.dumps(row.get("location_components", []), sort_keys=True)
            row["date_time_components"] = json.dumps(row.get("date_time_components", []), sort_keys=True)
            row["values_local_only"] = json.dumps(row.get("values_local_only", []), sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in safe_fieldnames})
    legacy_fieldnames = [
        "document_id",
        "file_hash",
        "file_name",
        "field",
        "role",
        "candidate_id",
        "reason",
        "source_trust_tier",
        "exclusion_reason",
        "value_local_only",
    ]
    with excluded_legacy_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=legacy_fieldnames)
        writer.writeheader()
        for item in report.get("legacy_fallback_stop_noise_items", []) or []:
            writer.writerow({key: item.get(key, "") for key in legacy_fieldnames})
    datetime_fieldnames = [
        "document_id",
        "file_hash",
        "field",
        "role",
        "reason",
        "date_time_candidate_count",
        "source_counts",
        "values_local_only",
    ]
    with datetime_conflicts_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=datetime_fieldnames)
        writer.writeheader()
        for item in report.get("date_time_cluster_conflict_items", []) or []:
            row = dict(item)
            row["source_counts"] = json.dumps(row.get("source_counts", {}), sort_keys=True)
            row["values_local_only"] = json.dumps(row.get("values_local_only", []), sort_keys=True)
            writer.writerow({key: row.get(key, "") for key in datetime_fieldnames})
    return {
        "summary_md": str(summary_path),
        "trusted_summary_md": str(trusted_summary_path),
        "multiple_location_items_csv": str(multiple_items_path),
        "trusted_disambiguation_items_csv": str(trusted_items_path),
        "trusted_safe_opportunities_csv": str(safe_opportunities_path),
        "excluded_legacy_fallback_noise_csv": str(excluded_legacy_path),
        "datetime_conflicts_csv": str(datetime_conflicts_path),
        "location_clusters_json": str(clusters_path),
        "row_block_disambiguation_csv": str(row_block_path),
        "fusion_safety_after_disambiguation_json": str(fusion_after_path),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-dir", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--eval-dir")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--residual-output-dir")
    parser.add_argument("--source-inventory-output-dir")
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    if not _is_under_local_outputs(output_dir) and not args.confirm_private_local_run:
        raise SystemExit(
            "Refusing to write stop review packet outside .local_outputs without "
            "--confirm-private-local-run"
        )
    residual_output_dir = Path(args.residual_output_dir) if args.residual_output_dir else None
    if (
        residual_output_dir
        and not _is_under_local_outputs(residual_output_dir)
        and not args.confirm_private_local_run
    ):
        raise SystemExit(
            "Refusing to write residual stop extraction report outside .local_outputs "
            "without --confirm-private-local-run"
        )
    source_inventory_output_dir = (
        Path(args.source_inventory_output_dir)
        if args.source_inventory_output_dir
        else None
    )
    if (
        source_inventory_output_dir
        and not _is_under_local_outputs(source_inventory_output_dir)
        and not args.confirm_private_local_run
    ):
        raise SystemExit(
            "Refusing to write stop source inventory outside .local_outputs "
            "without --confirm-private-local-run"
        )
    gold_labels = load_gold_labels(args.gold_dir)
    audit_records = _read_jsonl(Path(args.audit))
    evaluation = _evaluation_from_dir(args.eval_dir)
    packet = build_stop_gold_review_packet(
        gold_labels,
        audit_records,
        evaluation=evaluation,
        include_private_values_local_only=args.include_private_values_local_only,
    )
    paths = write_packet(packet, output_dir)
    source_inventory_report = build_stop_source_inventory_report(
        packet,
        audit_records,
        include_private_values=args.include_private_values_local_only,
    )
    location_disambiguation_report = build_stop_location_disambiguation_report(
        source_inventory_report,
        include_private_values=args.include_private_values_local_only,
    )
    location_disambiguation_paths = write_stop_location_disambiguation_report(
        location_disambiguation_report,
        output_dir,
    )
    source_inventory_paths = {}
    if source_inventory_output_dir:
        source_inventory_paths = write_stop_source_inventory_report(
            source_inventory_report,
            source_inventory_output_dir,
        )
    residual_paths = {}
    residual_report = build_residual_extraction_report(
        packet,
        source_inventory_report=source_inventory_report,
    )
    if residual_output_dir:
        residual_paths = write_residual_extraction_report(residual_report, residual_output_dir)
    print(
        json.dumps(
            {
                "output_paths": paths,
                "residual_output_paths": residual_paths,
                "source_inventory_output_paths": source_inventory_paths,
                "location_disambiguation_output_paths": location_disambiguation_paths,
                "review_item_count": packet["review_item_count"],
                "reason_counts": packet["reason_counts"],
                "secondary_reason_counts": packet["secondary_reason_counts"],
                "category_counts": packet["category_counts"],
                "exclusive_category_counts": packet["exclusive_category_counts"],
                "known_absent_summary": packet.get("known_absent_summary", {}),
                "residual_extraction_summary": {
                    "residual_item_count": residual_report.get("residual_item_count", 0),
                    "candidate_issue_type_counts": residual_report.get(
                        "candidate_issue_type_counts",
                        {},
                    ),
                    "recommended_fix_type_counts": residual_report.get(
                        "recommended_fix_type_counts",
                        {},
                    ),
                    "stop_component_fusion_opportunity_summary": residual_report.get(
                        "stop_component_fusion_opportunity_summary",
                        {},
                    ),
                    "no_candidate_source_trace_summary": residual_report.get(
                        "no_candidate_source_trace_summary",
                        {},
                    ),
                    "stop_residual_decision": residual_report.get(
                        "stop_residual_decision",
                        {},
                    ),
                },
                "source_inventory_summary": source_inventory_report.get(
                    "source_inventory_summary",
                    {},
                ),
                "source_inventory_v2_summary": source_inventory_report.get(
                    "source_inventory_v2_summary",
                    {},
                ),
                "source_inventory_v3_summary": source_inventory_report.get(
                    "source_inventory_v3_summary",
                    {},
                ),
                "stop_dedupe_provenance_loss_summary": source_inventory_report.get(
                    "stop_dedupe_provenance_loss_summary",
                    {},
                ),
                "provenance_loss_root_cause_by_module": source_inventory_report.get(
                    "provenance_loss_root_cause_by_module",
                    {},
                ),
                "stop_fusion_safety_model_summary": {
                    key: value
                    for key, value in (
                        source_inventory_report.get(
                            "stop_fusion_safety_model_summary",
                            {},
                        )
                        or {}
                    ).items()
                    if key != "cases"
                },
                "stop_location_disambiguation_summary": {
                    "multiple_location_root_cause_counts": location_disambiguation_report.get(
                        "multiple_location_root_cause_counts",
                        {},
                    ),
                    "location_cluster_counts": location_disambiguation_report.get(
                        "location_cluster_counts",
                        {},
                    ),
                    "location_disambiguation_score_counts": location_disambiguation_report.get(
                        "location_disambiguation_score_counts",
                        {},
                    ),
                    "stop_row_block_disambiguation_summary": location_disambiguation_report.get(
                        "stop_row_block_disambiguation_summary",
                        {},
                    ),
                    "fusion_safety_before_disambiguation": location_disambiguation_report.get(
                        "fusion_safety_before_disambiguation",
                        {},
                    ),
                    "fusion_safety_after_disambiguation": location_disambiguation_report.get(
                        "fusion_safety_after_disambiguation",
                        {},
                    ),
                    "legacy_fallback_stop_noise_summary": location_disambiguation_report.get(
                        "legacy_fallback_stop_noise_summary",
                        {},
                    ),
                    "source_trust_tier_counts": location_disambiguation_report.get(
                        "source_trust_tier_counts",
                        {},
                    ),
                    "trusted_source_disambiguation_summary": location_disambiguation_report.get(
                        "trusted_source_disambiguation_summary",
                        {},
                    ),
                    "date_time_cluster_conflict_summary": location_disambiguation_report.get(
                        "date_time_cluster_conflict_summary",
                        {},
                    ),
                    "safe_opportunity_count": location_disambiguation_report.get(
                        "safe_opportunity_count",
                        0,
                    ),
                },
                "patch_template_row_count": len(
                    build_patch_template(packet).get("patches", [])
                ),
                "selected_stop_serialization_gap_summary": packet.get(
                    "selected_stop_serialization_gap_summary",
                    {},
                ),
                "remaining_sidecar_component_gap_summary": packet.get(
                    "remaining_sidecar_component_gap_summary",
                    {},
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
