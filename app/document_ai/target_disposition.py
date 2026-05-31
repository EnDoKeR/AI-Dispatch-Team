"""Safe local target disposition registry.

The registry records which local hardening targets are active, completed, or
deferred. It stores target names, statuses, counts, and safe notes only.
"""

import json
from pathlib import Path

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)


TARGET_DISPOSITION_STATUS_ACTIVE = "active"
TARGET_DISPOSITION_STATUS_COMPLETED = "completed"
TARGET_DISPOSITION_STATUS_DEFERRED_UNTIL_REVIEW = "deferred_until_review"
TARGET_DISPOSITION_STATUS_NO_SHARED_CODE_ROOT_CAUSE = "no_shared_code_root_cause"
TARGET_DISPOSITION_STATUS_BLOCKED_BY_OCR = "blocked_by_ocr"
TARGET_DISPOSITION_STATUS_BLOCKED_BY_MISSING_CREDENTIAL = (
    "blocked_by_missing_credential"
)
TARGET_DISPOSITION_STATUS_NEEDS_HUMAN_REVIEW = "needs_human_review"

TARGET_DISPOSITION_STATUSES = {
    TARGET_DISPOSITION_STATUS_ACTIVE,
    TARGET_DISPOSITION_STATUS_COMPLETED,
    TARGET_DISPOSITION_STATUS_DEFERRED_UNTIL_REVIEW,
    TARGET_DISPOSITION_STATUS_NO_SHARED_CODE_ROOT_CAUSE,
    TARGET_DISPOSITION_STATUS_BLOCKED_BY_OCR,
    TARGET_DISPOSITION_STATUS_BLOCKED_BY_MISSING_CREDENTIAL,
    TARGET_DISPOSITION_STATUS_NEEDS_HUMAN_REVIEW,
}

NON_SELECTABLE_STATUSES = {
    TARGET_DISPOSITION_STATUS_COMPLETED,
    TARGET_DISPOSITION_STATUS_DEFERRED_UNTIL_REVIEW,
    TARGET_DISPOSITION_STATUS_NO_SHARED_CODE_ROOT_CAUSE,
    TARGET_DISPOSITION_STATUS_BLOCKED_BY_OCR,
    TARGET_DISPOSITION_STATUS_BLOCKED_BY_MISSING_CREDENTIAL,
    TARGET_DISPOSITION_STATUS_NEEDS_HUMAN_REVIEW,
}

DEFERRED_STATUSES = {
    TARGET_DISPOSITION_STATUS_DEFERRED_UNTIL_REVIEW,
    TARGET_DISPOSITION_STATUS_NO_SHARED_CODE_ROOT_CAUSE,
    TARGET_DISPOSITION_STATUS_BLOCKED_BY_OCR,
    TARGET_DISPOSITION_STATUS_BLOCKED_BY_MISSING_CREDENTIAL,
    TARGET_DISPOSITION_STATUS_NEEDS_HUMAN_REVIEW,
}

TARGET_DISPOSITION_REGISTRY_VERSION = "target_disposition_registry_v1"
TARGET_DISPOSITION_REGISTRY_JSON = "target_disposition_registry.json"


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def normalize_target_disposition_status(value):
    token = _token(value)
    return (
        token
        if token in TARGET_DISPOSITION_STATUSES
        else TARGET_DISPOSITION_STATUS_ACTIVE
    )


def _safe_counts(counts):
    if not isinstance(counts, dict):
        return {}
    safe = {}
    for key, value in counts.items():
        try:
            safe[_token(key)] = int(value or 0)
        except (TypeError, ValueError):
            continue
    return dict(sorted(safe.items()))


def build_target_disposition_record(
    target_name="",
    status=TARGET_DISPOSITION_STATUS_ACTIVE,
    reason="",
    supporting_counts=None,
    created_at="",
    updated_at="",
    warning_codes=None,
    notes_safe="",
):
    return {
        "target_name": _token(target_name),
        "status": normalize_target_disposition_status(status),
        "reason": _text(reason),
        "supporting_counts": _safe_counts(supporting_counts),
        "created_at": _text(created_at),
        "updated_at": _text(updated_at),
        "warning_codes": [
            _token(code) for code in warning_codes or [] if _token(code)
        ],
        "notes_safe": _text(notes_safe),
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }


def build_target_disposition_registry(records=None):
    normalized_records = [
        build_target_disposition_record(
            target_name=record.get("target_name", ""),
            status=record.get("status", TARGET_DISPOSITION_STATUS_ACTIVE),
            reason=record.get("reason", ""),
            supporting_counts=record.get("supporting_counts", {}),
            created_at=record.get("created_at", ""),
            updated_at=record.get("updated_at", ""),
            warning_codes=record.get("warning_codes", []),
            notes_safe=record.get("notes_safe", ""),
        )
        for record in records or []
        if isinstance(record, dict)
    ]
    return {
        "registry_version": TARGET_DISPOSITION_REGISTRY_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
        "records": normalized_records,
    }


def _records_by_target(registry):
    return {
        record.get("target_name", ""): record
        for record in (registry or {}).get("records", []) or []
        if record.get("target_name")
    }


def mark_target_deferred(
    registry,
    target_name,
    status=TARGET_DISPOSITION_STATUS_DEFERRED_UNTIL_REVIEW,
    reason="",
    supporting_counts=None,
    warning_codes=None,
    notes_safe="",
    updated_at="",
):
    existing = _records_by_target(build_target_disposition_registry(
        (registry or {}).get("records", [])
    ))
    target = _token(target_name)
    prior = existing.get(target, {})
    record = build_target_disposition_record(
        target_name=target,
        status=status,
        reason=reason,
        supporting_counts=supporting_counts,
        created_at=prior.get("created_at", ""),
        updated_at=updated_at,
        warning_codes=warning_codes,
        notes_safe=notes_safe,
    )
    existing[target] = record
    return build_target_disposition_registry(existing.values())


def is_target_selectable(
    target_name,
    registry=None,
    allow_deferred_targets=False,
    allow_completed_targets=False,
):
    record = _records_by_target(registry or {}).get(_token(target_name))
    if not record:
        return True
    status = normalize_target_disposition_status(record.get("status"))
    if status == TARGET_DISPOSITION_STATUS_ACTIVE:
        return True
    if status == TARGET_DISPOSITION_STATUS_COMPLETED:
        return bool(allow_completed_targets)
    if status in DEFERRED_STATUSES:
        return bool(allow_deferred_targets)
    return status not in NON_SELECTABLE_STATUSES


def skipped_targets_for_registry(registry, allow_deferred_targets=False):
    skipped = []
    for record in (registry or {}).get("records", []) or []:
        target = record.get("target_name", "")
        if target and not is_target_selectable(
            target,
            registry,
            allow_deferred_targets=allow_deferred_targets,
        ):
            skipped.append(target)
    return sorted(set(skipped))


def apply_target_dispositions_to_selection(
    selection,
    registry,
    allow_deferred_targets=False,
    fallback_target="human_review_required",
):
    selected = _token((selection or {}).get("selected_target"))
    result = dict(selection or {})
    skipped = skipped_targets_for_registry(
        registry,
        allow_deferred_targets=allow_deferred_targets,
    )
    result["skipped_deferred_targets"] = skipped
    if selected and not is_target_selectable(
        selected,
        registry,
        allow_deferred_targets=allow_deferred_targets,
    ):
        result["previous_selected_target"] = selected
        result["selected_target"] = fallback_target
        result["next_selectable_target"] = fallback_target
        result["confidence"] = "low"
        result.setdefault("warning_codes", [])
        if "selected_target_deferred" not in result["warning_codes"]:
            result["warning_codes"].append("selected_target_deferred")
    else:
        result["next_selectable_target"] = selected or fallback_target
    result["private_values_included"] = False
    result["raw_text_included"] = False
    return result


def load_target_dispositions(input_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR):
    path = Path(input_dir) / TARGET_DISPOSITION_REGISTRY_JSON
    if not path.exists():
        return build_target_disposition_registry()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return build_target_disposition_registry(payload.get("records", []))


def save_target_dispositions(
    registry,
    output_dir=DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    allow_custom_output_dir=False,
):
    output_root = _normalize_output_dir(
        output_dir,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    payload = build_target_disposition_registry(
        (registry or {}).get("records", [])
    )
    output_path = output_root / TARGET_DISPOSITION_REGISTRY_JSON
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "json": output_path.name,
        "private_values_printed": False,
        "raw_text_printed": False,
        "money_values_printed": False,
    }
