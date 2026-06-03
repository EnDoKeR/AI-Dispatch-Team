"""Create local-only stop gold review packets from RateCon gold evaluation.

The output is private review material and must stay under .local_outputs.
This script does not modify gold labels.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
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

LOCAL_ONLY_STOP_COMPONENTS = (
    "raw_location_text_local_only",
    "unparsed_location_text_local_only",
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
    if draft.get("predicted"):
        reasons.append("candidate_is_review_draft_only")
    return sorted(set(reasons))


def _true_gold_review_needed(gold_info):
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
    return "manual_review_needed"


def _comparison_rows_by_doc_field(evaluation):
    by_key = {}
    for row in evaluation.get("comparison_rows", []) or []:
        if row.get("field") not in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
            continue
        key = (row.get("document_id"), row.get("file_hash"), row.get("field"))
        by_key.setdefault(key, {})[row.get("system")] = row
    return by_key


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
        "schema_version": "ratecon_stop_gold_review_packet_v2",
        "review_item_count": len(review_items),
        "reason_counts": reason_counts,
        "secondary_reason_counts": secondary_reason_counts,
        "category_counts": category_counts,
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
        f"Reason counts: {json.dumps(packet.get('reason_counts', {}), sort_keys=True)}",
        f"Secondary reason counts: {json.dumps(packet.get('secondary_reason_counts', {}), sort_keys=True)}",
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
        "patch_template_json": str(patch_template_path),
        "selected_stop_serialization_gaps_csv": str(selected_gaps_csv_path),
        "selected_stop_serialization_gaps_json": str(selected_gaps_json_path),
        "selected_stop_component_side_by_side_csv": str(selected_side_by_side_path),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-dir", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--eval-dir")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    if not _is_under_local_outputs(output_dir) and not args.confirm_private_local_run:
        raise SystemExit(
            "Refusing to write stop review packet outside .local_outputs without "
            "--confirm-private-local-run"
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
    print(
        json.dumps(
            {
                "output_paths": paths,
                "review_item_count": packet["review_item_count"],
                "reason_counts": packet["reason_counts"],
                "secondary_reason_counts": packet["secondary_reason_counts"],
                "category_counts": packet["category_counts"],
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
