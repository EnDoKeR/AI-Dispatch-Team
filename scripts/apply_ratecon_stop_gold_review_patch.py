"""Dry-run or apply a local-only stop gold review patch.

Patch files are reviewer-authored. The workflow never derives gold values from
shadow candidates and only writes under .local_outputs unless explicitly
confirmed.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
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
    read_json,
)


def _text(value) -> str:
    return str(value or "").strip()


def _is_under_local_outputs(path: Path) -> bool:
    resolved = path.resolve()
    local_outputs = (REPO_ROOT / ".local_outputs").resolve()
    return resolved == local_outputs or local_outputs in resolved.parents


def _require_safe_path(path: Path, description: str, confirm_private_local_run=False):
    if _is_under_local_outputs(path) or confirm_private_local_run:
        return path
    raise SystemExit(
        f"Refusing to use {description} outside .local_outputs without "
        "--confirm-private-local-run"
    )


def _gold_label_files(gold_dir: Path):
    return sorted(gold_dir.glob("*.json")) if gold_dir.exists() else []


def _payload_template(payload):
    if isinstance(payload, dict) and isinstance(payload.get("gold_label_template"), dict):
        return payload["gold_label_template"]
    return payload


def _label_matches(label, patch):
    document_id = _text(patch.get("document_id"))
    file_hash = _text(patch.get("file_hash"))
    file_name = _text(patch.get("file_name"))
    if document_id and _text(label.get("document_id")) != document_id:
        return False
    if file_hash and _text(label.get("file_hash")) != file_hash:
        return False
    if file_name and _text(label.get("file_name")) != file_name:
        return False
    return bool(document_id or file_hash or file_name)


def _proposed_values(patch):
    proposed = patch.get("proposed_gold", {})
    if not isinstance(proposed, dict):
        return {}
    return {
        component: proposed.get(component)
        for component in STOP_GOLD_COMPLETENESS_COMPONENTS
        if proposed.get(component) not in [None, ""]
    }


def _ensure_stop_slot(label, field_name, stop_index):
    gold = label.setdefault("gold", {})
    stops = gold.setdefault(field_name, [])
    if not isinstance(stops, list):
        raise ValueError(f"gold.{field_name} must be a list")
    while len(stops) < stop_index:
        stops.append({"stop_index": len(stops) + 1})
    if not isinstance(stops[stop_index - 1], dict):
        stops[stop_index - 1] = {"stop_index": stop_index}
    return stops[stop_index - 1]


def plan_stop_gold_patch(gold_dir: Path, patch_payload):
    patches = patch_payload.get("patches", []) if isinstance(patch_payload, dict) else []
    planned = []
    skipped = []
    files = [(path, read_json(path)) for path in _gold_label_files(gold_dir)]
    for patch in patches:
        if not isinstance(patch, dict):
            skipped.append({"reason": "invalid_patch_entry"})
            continue
        field_name = _text(patch.get("field"))
        if field_name not in {FIELD_PICKUP_STOPS, FIELD_DELIVERY_STOPS}:
            skipped.append({"reason": "invalid_stop_field", "field": field_name})
            continue
        values = _proposed_values(patch)
        if not values:
            skipped.append(
                {
                    "reason": "empty_proposed_gold",
                    "document_id": _text(patch.get("document_id")),
                    "file_name": _text(patch.get("file_name")),
                    "field": field_name,
                }
            )
            continue
        matches = []
        for path, payload in files:
            label = _payload_template(payload)
            if isinstance(label, dict) and _label_matches(label, patch):
                matches.append((path, payload, label))
        if len(matches) != 1:
            skipped.append(
                {
                    "reason": "label_match_not_unique",
                    "match_count": len(matches),
                    "document_id": _text(patch.get("document_id")),
                    "file_name": _text(patch.get("file_name")),
                    "field": field_name,
                }
            )
            continue
        stop_index = int(patch.get("stop_index") or 1)
        path, payload, label = matches[0]
        current = deepcopy(_ensure_stop_slot(label, field_name, stop_index))
        planned.append(
            {
                "gold_label_file": str(path),
                "document_id": _text(label.get("document_id")),
                "file_name": _text(label.get("file_name")),
                "field": field_name,
                "stop_index": stop_index,
                "updates": values,
                "current_keys": sorted(
                    key
                    for key in STOP_GOLD_COMPLETENESS_COMPONENTS
                    if _text(current.get(key))
                ),
                "reviewer_notes": _text(patch.get("reviewer_notes")),
            }
        )
    return planned, skipped


def apply_stop_gold_patch(gold_dir: Path, patch_payload):
    planned, skipped = plan_stop_gold_patch(gold_dir, patch_payload)
    by_file = {}
    for change in planned:
        by_file.setdefault(change["gold_label_file"], []).append(change)
    modified_files = []
    for file_name, changes in by_file.items():
        path = Path(file_name)
        payload = read_json(path)
        label = _payload_template(payload)
        for change in changes:
            stop = _ensure_stop_slot(
                label,
                change["field"],
                int(change["stop_index"]),
            )
            for component, value in change["updates"].items():
                stop[component] = value
            note = _text(stop.get("notes"))
            addendum = "stop_gold_review_patch: reviewer supplied value"
            stop["notes"] = f"{note}; {addendum}" if note else addendum
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        modified_files.append(str(path))
    return planned, skipped, modified_files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-dir", required=True)
    parser.add_argument("--patch", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-private-local-run", action="store_true")
    args = parser.parse_args(argv)
    gold_dir = _require_safe_path(
        Path(args.gold_dir),
        "gold dir",
        confirm_private_local_run=args.confirm_private_local_run,
    )
    patch_path = _require_safe_path(
        Path(args.patch),
        "patch file",
        confirm_private_local_run=args.confirm_private_local_run,
    )
    patch_payload = read_json(patch_path)
    if args.apply:
        planned, skipped, modified_files = apply_stop_gold_patch(gold_dir, patch_payload)
    else:
        planned, skipped = plan_stop_gold_patch(gold_dir, patch_payload)
        modified_files = []
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry_run",
                "planned_change_count": len(planned),
                "skipped_count": len(skipped),
                "modified_files": modified_files,
                "gold_labels_modified": bool(args.apply and modified_files),
                "auto_filled_from_shadow_candidates": False,
                "planned_changes": planned,
                "skipped": skipped,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
