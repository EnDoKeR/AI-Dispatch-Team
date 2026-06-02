"""Create local-only stop gold review packets from RateCon gold evaluation.

This script writes private review artifacts under .local_outputs by default.
It does not modify gold labels.
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
    SYSTEM_SHADOW,
    SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP,
    SYSTEM_SHADOW_STOP_REVIEW_DRAFT,
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
        "facility": bool(_text(stop.get("facility"))),
        "address": bool(_text(stop.get("address"))),
        "city": bool(_text(stop.get("city"))),
        "state": bool(_text(stop.get("state"))),
        "zip": bool(_text(stop.get("zip"))),
        "date": bool(_text(stop.get("date"))),
        "time": bool(_text(stop.get("time")) or _text(stop.get("appointment_window"))),
    }
    missing = [key for key, present in components.items() if not present]
    return {
        "components_present": components,
        "missing_components": missing,
        "complete_dispatch_components": bool(
            (components["city"] or components["address"] or components["facility"])
            and components["date"]
        ),
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
    return {
        "system": _text(row.get("system")),
        "status": _text(row.get("status")),
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


def _reason_for_case(selected, dispatch, draft, gold_info):
    completeness = gold_info.get("completeness", []) if isinstance(gold_info, dict) else []
    missing = set()
    for item in completeness:
        missing.update(item.get("missing_components", []) or [])
    if selected and selected.get("source_status") == "shadow_component_not_serialized":
        return "evaluator_serialized_gap"
    if dispatch and dispatch.get("status") in {"correct_exact", "correct_normalized", "partial_match"}:
        return "selected_has_dispatch_components_but_gold_incomplete" if missing else "manual_review_needed"
    if "date" in missing:
        return "gold_missing_date"
    if "time" in missing:
        return "gold_missing_time"
    if "city" in missing or "state" in missing:
        return "gold_missing_city_state"
    if draft:
        return "candidate_is_review_draft_only"
    return "manual_review_needed"


def build_stop_gold_review_packet(gold_labels, audit_records):
    evaluation = evaluate_ratecon_against_gold(gold_labels, audit_records)
    gold_lookup = _gold_by_doc_field(gold_labels)
    by_key = {}
    for row in evaluation.get("comparison_rows", []) or []:
        if row.get("field") not in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
            continue
        key = (row.get("document_id"), row.get("file_hash"), row.get("field"))
        by_key.setdefault(key, {})[row.get("system")] = row
    review_items = []
    for key, rows in sorted(by_key.items()):
        selected = rows.get(SYSTEM_SHADOW, {})
        dispatch = rows.get(SYSTEM_SHADOW_BEST_DISPATCH_USABLE_STOP, {})
        draft = rows.get(SYSTEM_SHADOW_STOP_REVIEW_DRAFT, {})
        statuses = {
            _text(row.get("status"))
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
        ):
            continue
        gold_info = gold_lookup.get(key, {})
        reason = _reason_for_case(selected, dispatch, draft, gold_info)
        recommendation = (
            "candidate_is_review_draft_only"
            if draft and draft.get("predicted")
            else "manually_review_gold"
        )
        if reason == "evaluator_serialized_gap":
            recommendation = "evaluator_bug_suspected"
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
                "missing_gold_components": sorted(
                    {
                        component
                        for item in gold_info.get("completeness", []) or []
                        for component in item.get("missing_components", []) or []
                    }
                ),
                "suspect_reason": reason,
                "recommendation": recommendation,
            }
        )
    reason_counts = {}
    for item in review_items:
        reason = item["suspect_reason"]
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "schema_version": "ratecon_stop_gold_review_packet_v1",
        "review_item_count": len(review_items),
        "reason_counts": reason_counts,
        "items": review_items,
        "gold_labels_modified": False,
        "private_values_printed": True,
        "local_only": True,
    }


def write_packet(packet, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "stop_gold_review.json"
    md_path = output_dir / "stop_gold_review.md"
    csv_path = output_dir / "stop_gold_review.csv"
    json_path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Stop Gold Review",
        "",
        f"Review items: {packet.get('review_item_count', 0)}",
        f"Reason counts: {json.dumps(packet.get('reason_counts', {}), sort_keys=True)}",
        "",
    ]
    for item in packet.get("items", []) or []:
        lines.append(
            f"- {item.get('file_name') or item.get('document_id')} "
            f"{item.get('field')}: {item.get('suspect_reason')} "
            f"-> {item.get('recommendation')}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "document_id",
                "file_hash",
                "file_name",
                "field",
                "suspect_reason",
                "recommendation",
            ],
        )
        writer.writeheader()
        for item in packet.get("items", []) or []:
            writer.writerow({key: item.get(key, "") for key in writer.fieldnames})
    return {"json": str(json_path), "md": str(md_path), "csv": str(csv_path)}


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
    print(json.dumps({"output_paths": paths, "review_item_count": packet["review_item_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
