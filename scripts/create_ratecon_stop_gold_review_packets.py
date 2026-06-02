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


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_stop_gold_review")


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
        "usability_tier": _text(row.get("stop_usability_tier")),
        "source_status": _text(row.get("source_status")),
        "source": _text(row.get("source")),
        "parser_name": _text(row.get("parser_name")),
        "pairing_method": _text(row.get("pairing_method")),
        "confidence": row.get("confidence"),
        "dispatch_usable": bool(row.get("dispatch_usable")),
        "has_location": bool(row.get("has_location")),
        "has_date": bool(row.get("has_date")),
        "has_time": bool(row.get("has_time")),
        "stop_selection_policy": _text(row.get("stop_selection_policy")),
        "stop_abstention_reason": _text(row.get("stop_abstention_reason")),
        "issues": list(row.get("issues") or []),
    }


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
        return "evaluator_serialized_gap"
    if dispatch.get("status") == "partial_match" and dispatch.get("stop_usability_tier") == "unsafe_wrong":
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
        reasons.append("evaluator_serialized_gap")
    if dispatch.get("status") == "partial_match" and dispatch.get("stop_usability_tier") == "unsafe_wrong":
        reasons.append("candidate_partial_match_but_unsafe_by_usability")
    if dispatch.get("predicted") and missing:
        reasons.append("dispatch_candidate_compared_against_incomplete_gold")
    if draft.get("predicted"):
        reasons.append("candidate_is_review_draft_only")
    return sorted(set(reasons))


def _recommendation_for_reason(reason):
    if reason == "evaluator_serialized_gap":
        return "evaluator_bug_suspected"
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


def build_stop_gold_review_packet(gold_labels, audit_records):
    evaluation = evaluate_ratecon_against_gold(gold_labels, audit_records)
    gold_lookup = _gold_by_doc_field(gold_labels)
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
        if not statuses.intersection(
            {
                "partial_match",
                "wrong",
                "extractor_missing",
                "shadow_component_not_serialized",
                "source_not_available",
            }
        ) and not tiers.intersection({"unsafe_wrong", "useful_partial"}):
            continue
        gold_info = gold_lookup.get(key, {})
        reason = _reason_for_case(selected, dispatch, draft, gold_info)
        secondary_reasons = _secondary_reasons_for_case(
            selected,
            dispatch,
            draft,
            gold_info,
        )
        review_items.append(
            {
                "document_id": _text(key[0]),
                "file_hash": _text(key[1]),
                "file_name": _text(gold_info.get("file_name")),
                "field": _text(key[2]),
                "current_gold_completeness_status": gold_info.get("completeness", []),
                "selected_stop_component_summary": _safe_row_summary(selected),
                "best_dispatch_usable_candidate_summary": _safe_row_summary(dispatch),
                "draft_stop_summary": _safe_row_summary(draft),
                "missing_gold_components": _missing_gold_components(gold_info),
                "suspect_reason": reason,
                "secondary_reasons": secondary_reasons,
                "recommendation": _recommendation_for_reason(reason),
            }
        )
    reason_counts = {}
    secondary_reason_counts = {}
    for item in review_items:
        reason = item["suspect_reason"]
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        for secondary_reason in item.get("secondary_reasons", []) or []:
            secondary_reason_counts[secondary_reason] = (
                secondary_reason_counts.get(secondary_reason, 0) + 1
            )
    return {
        "schema_version": "ratecon_stop_gold_review_packet_v2",
        "review_item_count": len(review_items),
        "reason_counts": reason_counts,
        "secondary_reason_counts": secondary_reason_counts,
        "stop_gold_completeness_summary": build_stop_gold_completeness_summary(
            gold_labels,
        ),
        "items": review_items,
        "gold_labels_modified": False,
        "private_values_printed": True,
        "local_only": True,
    }


def build_patch_template(packet):
    patches = []
    for item in packet.get("items", []) or []:
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
    items_json_path.write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Stop Gold Review",
        "",
        f"Review items: {packet.get('review_item_count', 0)}",
        f"Reason counts: {json.dumps(packet.get('reason_counts', {}), sort_keys=True)}",
        f"Secondary reason counts: {json.dumps(packet.get('secondary_reason_counts', {}), sort_keys=True)}",
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
            f"{item.get('field')}: {item.get('suspect_reason')} "
            f"-> {item.get('recommendation')}"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with items_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "document_id",
                "file_hash",
                "file_name",
                "field",
                "suspect_reason",
                "recommendation",
                "secondary_reasons",
                "missing_gold_components",
                "selected_raw_status",
                "selected_usability_tier",
                "dispatch_raw_status",
                "dispatch_usability_tier",
                "draft_raw_status",
                "draft_usability_tier",
            ],
        )
        writer.writeheader()
        for item in packet.get("items", []) or []:
            selected = item.get("selected_stop_component_summary", {}) or {}
            dispatch = item.get("best_dispatch_usable_candidate_summary", {}) or {}
            draft = item.get("draft_stop_summary", {}) or {}
            writer.writerow(
                {
                    "document_id": item.get("document_id", ""),
                    "file_hash": item.get("file_hash", ""),
                    "file_name": item.get("file_name", ""),
                    "field": item.get("field", ""),
                    "suspect_reason": item.get("suspect_reason", ""),
                    "recommendation": item.get("recommendation", ""),
                    "secondary_reasons": ",".join(
                        item.get("secondary_reasons", []) or []
                    ),
                    "missing_gold_components": ",".join(
                        item.get("missing_gold_components", []) or []
                    ),
                    "selected_raw_status": selected.get("raw_status", ""),
                    "selected_usability_tier": selected.get("usability_tier", ""),
                    "dispatch_raw_status": dispatch.get("raw_status", ""),
                    "dispatch_usability_tier": dispatch.get("usability_tier", ""),
                    "draft_raw_status": draft.get("raw_status", ""),
                    "draft_usability_tier": draft.get("usability_tier", ""),
                }
            )
    patch_template_path.write_text(
        json.dumps(build_patch_template(packet), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "summary_md": str(summary_path),
        "items_json": str(items_json_path),
        "items_csv": str(items_csv_path),
        "patch_template_json": str(patch_template_path),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-dir", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--confirm-private-local-run", action="store_true")
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    if not _is_under_local_outputs(output_dir) and not args.confirm_private_local_run:
        raise SystemExit(
            "Refusing to write stop review packet outside .local_outputs without "
            "--confirm-private-local-run"
        )
    gold_labels = load_gold_labels(args.gold_dir)
    audit_records = _read_jsonl(Path(args.audit))
    packet = build_stop_gold_review_packet(gold_labels, audit_records)
    paths = write_packet(packet, output_dir)
    print(
        json.dumps(
            {
                "output_paths": paths,
                "review_item_count": packet["review_item_count"],
                "reason_counts": packet["reason_counts"],
                "secondary_reason_counts": packet["secondary_reason_counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
