"""Create/apply local-only RateCon gold-rate adjudication recommendations."""

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.document_ai.ratecon_gold_labels import (  # noqa: E402
    FIELD_TOTAL_CARRIER_RATE,
    LABEL_SKIPPED,
    evaluate_ratecon_against_gold,
    load_gold_labels,
    normalize_money,
    read_json,
    read_jsonl,
    write_json,
    _audit_by_key,
    _find_record,
    _gold_scalar_value,
    _private_eval_values,
    _rate_inventory,
    _rate_inventory_context,
    _text,
)
from app.document_ai.ratecon_shadow_audit import RATECON_SHADOW_AUDIT_JSONL  # noqa: E402


DEFAULT_GOLD_DIR = Path(".local_outputs") / "private_ratecon_gold_labels"
DEFAULT_AUDIT = Path(".local_outputs") / "private_ratecon_measurement" / RATECON_SHADOW_AUDIT_JSONL
DEFAULT_OUTPUT_DIR = Path(".local_outputs") / "private_ratecon_gold_adjudication"

SAFE_TOTAL_CONTEXTS = {
    "total_carrier_pay",
    "total_rate",
    "total_cost",
    "estimated_rate_to_truck",
    "agreed_rate_total",
}


def _normalize_local_output_dir(output_dir, allow_custom_output_dir=False):
    path = Path(output_dir)
    if (
        not allow_custom_output_dir
        and (not path.parts or (path.parts[0] != ".local_outputs" and ".local_outputs" not in path.parts))
    ):
        raise ValueError(
            "gold adjudication output must be under .local_outputs unless "
            "--allow-custom-output-dir is used"
        )
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_private_gold_dir(gold_dir, confirm_private_local_run=False):
    path = Path(gold_dir)
    if path.parts and path.parts[0] == ".local_outputs":
        return path
    if ".local_outputs" in path.parts:
        return path
    if confirm_private_local_run:
        return path
    raise ValueError(
        "apply mode only writes gold labels under .local_outputs unless "
        "--confirm-private-local-run is passed"
    )


def _money_equal(left, right):
    return bool(normalize_money(left) and normalize_money(left) == normalize_money(right))


def _prediction_value(record, field_name):
    payload = _private_eval_values(record)
    selected = (payload.get("shadow_selected", {}) or {}).get(field_name, {})
    if isinstance(selected, dict):
        return selected.get("value")
    return selected


def _context_bucket():
    return {
        "present": False,
        "nonblank": False,
        "matches_gold": False,
        "matches_shadow": False,
        "values": [],
    }


def _context_group(context):
    if context == "total_carrier_pay":
        return "total_carrier_pay"
    if context == "carrier_freight_pay":
        return "carrier_freight_pay"
    if context in {"linehaul", "linehaul_total", "line_item_rate"}:
        return "linehaul"
    if context in {"total_rate", "total_cost", "agreed_rate_total"}:
        return "grand_total"
    if context == "estimated_rate_to_truck":
        return "estimated_rate_to_truck"
    return ""


def _candidate_values_summary(record, gold_value, selected_value):
    summary = {
        "total_carrier_pay": _context_bucket(),
        "carrier_freight_pay": _context_bucket(),
        "linehaul": _context_bucket(),
        "grand_total": _context_bucket(),
        "estimated_rate_to_truck": _context_bucket(),
    }
    for item in _rate_inventory(record):
        if not isinstance(item, dict):
            continue
        group = _context_group(_rate_inventory_context(item))
        if not group:
            continue
        value = item.get("value")
        bucket = summary[group]
        bucket["present"] = True
        if normalize_money(value):
            bucket["nonblank"] = True
            if value not in bucket["values"]:
                bucket["values"].append(value)
        if _money_equal(value, gold_value):
            bucket["matches_gold"] = True
        if _money_equal(value, selected_value):
            bucket["matches_shadow"] = True
    return summary


def _first_value(summary, *groups):
    for group in groups:
        values = ((summary.get(group) or {}).get("values") or [])
        if values:
            return values[0]
    return ""


def _recommend_gold_value(case, summary, current_gold, selected_value):
    diagnosis = _text(case.get("diagnosis"))
    selected = case.get("selected_rate", {}) or {}
    selected_context = _text(selected.get("money_context"))
    total_pay = summary["total_carrier_pay"]
    carrier_freight = summary["carrier_freight_pay"]
    linehaul = summary["linehaul"]
    grand_total = summary["grand_total"]
    estimated = summary["estimated_rate_to_truck"]

    if (
        selected_context == "total_carrier_pay"
        and total_pay["nonblank"]
        and carrier_freight["matches_gold"]
        and not total_pay["matches_gold"]
    ):
        return {
            "recommended_gold_value": _first_value(summary, "total_carrier_pay"),
            "recommendation_reason": "nonblank_total_carrier_pay_over_carrier_freight_pay",
            "confidence": "high",
            "needs_manual_review": False,
        }
    if (
        diagnosis == "selected_grand_total_but_gold_uses_linehaul"
        and linehaul["matches_gold"]
        and (grand_total["nonblank"] or estimated["nonblank"] or total_pay["nonblank"])
    ):
        return {
            "recommended_gold_value": _first_value(
                summary,
                "grand_total",
                "estimated_rate_to_truck",
                "total_carrier_pay",
            )
            or selected_value,
            "recommendation_reason": "full_total_over_linehaul_component",
            "confidence": "high",
            "needs_manual_review": False,
        }
    if (
        not total_pay["nonblank"]
        and carrier_freight["nonblank"]
        and carrier_freight["matches_gold"]
    ):
        return {
            "recommended_gold_value": current_gold,
            "recommendation_reason": "blank_total_carrier_pay_valid_carrier_freight_fallback",
            "confidence": "high",
            "needs_manual_review": False,
        }
    if selected_context in SAFE_TOTAL_CONTEXTS and selected_value and not _money_equal(selected_value, current_gold):
        confidence = "medium" if diagnosis == "selected_safe_total_but_gold_differs" else "high"
        return {
            "recommended_gold_value": selected_value,
            "recommendation_reason": "safe_total_candidate_differs_from_gold",
            "confidence": confidence,
            "needs_manual_review": confidence != "high",
        }
    return {
        "recommended_gold_value": current_gold,
        "recommendation_reason": "ambiguous_or_unknown_rate_definition",
        "confidence": "low",
        "needs_manual_review": True,
    }


def _gold_labels_by_document(gold_labels):
    labels = {}
    for label in gold_labels:
        if _text(label.get("label_status")) == LABEL_SKIPPED:
            continue
        document_id = _text(label.get("document_id"))
        if document_id:
            labels[document_id] = label
    return labels


def _build_review_case(case, gold_labels_by_document, audit_index):
    document_id = _text(case.get("document_id"))
    label = gold_labels_by_document.get(document_id, {}) or {}
    gold = label.get("gold", {}) if isinstance(label, dict) else {}
    gold_field = gold.get(FIELD_TOTAL_CARRIER_RATE, {})
    current_gold = _gold_scalar_value(gold_field)
    record = _find_record(label, audit_index)
    selected_value = _prediction_value(record, FIELD_TOTAL_CARRIER_RATE)
    summary = _candidate_values_summary(record, current_gold, selected_value)
    recommendation = _recommend_gold_value(case, summary, current_gold, selected_value)
    return {
        "file_name": _text(label.get("file_name") or case.get("file_name")),
        "document_id": document_id,
        "current_gold_total_carrier_rate": current_gold,
        "selected_shadow_rate": selected_value,
        "candidate_values_summary": summary,
        "diagnosis": _text(case.get("diagnosis")),
        **recommendation,
    }


def build_adjudication_review(gold_labels, audit_records):
    audit_index = _audit_by_key(audit_records)
    evaluation = evaluate_ratecon_against_gold(gold_labels, audit_records)
    labels_by_document = _gold_labels_by_document(gold_labels)
    cases = [
        _build_review_case(case, labels_by_document, audit_index)
        for case in (evaluation.get("residual_wrong_rate_forensics", {}) or {}).get("cases", [])
    ]
    high = [case for case in cases if case.get("confidence") == "high"]
    medium = [case for case in cases if case.get("confidence") == "medium"]
    low = [case for case in cases if case.get("confidence") == "low"]
    return {
        "schema_version": "ratecon_gold_rate_adjudication_v1",
        "cases": cases,
        "case_count": len(cases),
        "high_confidence_recommendation_count": len(high),
        "medium_confidence_recommendation_count": len(medium),
        "low_confidence_recommendation_count": len(low),
        "manual_review_count": sum(1 for case in cases if case.get("needs_manual_review")),
        "recommendation_reason_counts": {
            reason: sum(1 for case in cases if case.get("recommendation_reason") == reason)
            for reason in sorted({case.get("recommendation_reason") for case in cases})
        },
        "private_values_included": True,
        "raw_text_included": False,
        "gold_files_modified": False,
    }


def _review_markdown(review):
    lines = [
        "# RateCon Gold Rate Adjudication Review",
        "",
        f"case_count: {review.get('case_count', 0)}",
        f"high_confidence_recommendation_count: {review.get('high_confidence_recommendation_count', 0)}",
        f"manual_review_count: {review.get('manual_review_count', 0)}",
        "",
        "| file | diagnosis | recommendation_reason | confidence | needs_manual_review |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in review.get("cases", []) or []:
        lines.append(
            "| {file} | {diagnosis} | {reason} | {confidence} | {review} |".format(
                file=case.get("file_name", ""),
                diagnosis=case.get("diagnosis", ""),
                reason=case.get("recommendation_reason", ""),
                confidence=case.get("confidence", ""),
                review=case.get("needs_manual_review", True),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _gold_label_files(gold_dir):
    path = Path(gold_dir)
    return sorted(path.glob("*.json")) if path.exists() else []


def _payload_template(payload):
    if isinstance(payload, dict) and isinstance(payload.get("gold_label_template"), dict):
        return payload["gold_label_template"]
    return payload


def apply_high_confidence_recommendations(gold_dir, review, confirm_private_local_run=False):
    gold_dir = _safe_private_gold_dir(
        gold_dir,
        confirm_private_local_run=confirm_private_local_run,
    )
    by_file = {
        case.get("file_name"): case
        for case in review.get("cases", []) or []
        if case.get("confidence") == "high"
        and not case.get("needs_manual_review")
        and case.get("recommended_gold_value") not in [None, ""]
        and not _money_equal(case.get("recommended_gold_value"), case.get("current_gold_total_carrier_rate"))
    }
    changes = []
    for path in _gold_label_files(gold_dir):
        payload = read_json(path)
        updated = deepcopy(payload)
        label = _payload_template(updated)
        file_name = _text(label.get("file_name")) or path.name.replace(".gold.json", ".pdf")
        case = by_file.get(file_name)
        if not case:
            continue
        gold = label.setdefault("gold", {})
        rate = gold.setdefault(FIELD_TOTAL_CARRIER_RATE, {})
        old_value = rate.get("value")
        new_value = case.get("recommended_gold_value")
        if _money_equal(old_value, new_value):
            continue
        rate["value"] = new_value
        rate["uncertain"] = False
        note = _text(rate.get("notes"))
        addendum = f"gold_rate_adjudication: {case.get('recommendation_reason')}"
        rate["notes"] = f"{note}; {addendum}" if note else addendum
        path.write_text(json.dumps(updated, indent=2, sort_keys=True), encoding="utf-8")
        changes.append(
            {
                "file_name": file_name,
                "gold_label_file": path.name,
                "old_value": old_value,
                "new_value": new_value,
                "recommendation_reason": case.get("recommendation_reason"),
            }
        )
    return changes


def write_adjudication_outputs(review, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    review_json = output_dir / "rate_gold_adjudication_review.json"
    review_md = output_dir / "rate_gold_adjudication_review.md"
    patch_json = output_dir / "rate_gold_adjudication_patch.json"
    write_json(review_json, review)
    review_md.write_text(_review_markdown(review), encoding="utf-8")
    patch = {
        "schema_version": "ratecon_gold_rate_adjudication_patch_v1",
        "high_confidence_cases": [
            case
            for case in review.get("cases", []) or []
            if case.get("confidence") == "high" and not case.get("needs_manual_review")
        ],
        "private_values_included": True,
    }
    write_json(patch_json, patch)
    return {
        "review_json": review_json.name,
        "review_md": review_md.name,
        "patch_json": patch_json.name,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create/apply local private RateCon gold-rate adjudication recommendations."
    )
    parser.add_argument("--gold-dir", default=str(DEFAULT_GOLD_DIR))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--allow-custom-output-dir", action="store_true")
    return parser


def run_adjudication(
    gold_dir=DEFAULT_GOLD_DIR,
    audit=DEFAULT_AUDIT,
    output_dir=DEFAULT_OUTPUT_DIR,
    apply=False,
    confirm_private_local_run=False,
    allow_custom_output_dir=False,
):
    output_dir = _normalize_local_output_dir(
        output_dir,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    gold_labels = load_gold_labels(gold_dir)
    audit_records = read_jsonl(audit)
    review = build_adjudication_review(gold_labels, audit_records)
    files = write_adjudication_outputs(review, output_dir)
    changes = []
    if apply:
        changes = apply_high_confidence_recommendations(
            gold_dir,
            review,
            confirm_private_local_run=confirm_private_local_run,
        )
        write_json(
            output_dir / "applied_gold_rate_changes.json",
            {
                "schema_version": "ratecon_gold_rate_adjudication_applied_v1",
                "changes": changes,
                "change_count": len(changes),
                "private_values_included": True,
            },
        )
        review["gold_files_modified"] = bool(changes)
    return {
        "files": files,
        "case_count": review.get("case_count", 0),
        "high_confidence_recommendation_count": review.get(
            "high_confidence_recommendation_count",
            0,
        ),
        "manual_review_count": review.get("manual_review_count", 0),
        "applied_change_count": len(changes),
        "applied_files": [change["gold_label_file"] for change in changes],
        "private_values_printed": False,
        "raw_text_printed": False,
    }


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = run_adjudication(
        gold_dir=args.gold_dir,
        audit=args.audit,
        output_dir=args.output_dir,
        apply=args.apply,
        confirm_private_local_run=args.confirm_private_local_run,
        allow_custom_output_dir=args.allow_custom_output_dir,
    )
    print("ratecon_gold_rate_adjudication_written: " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
