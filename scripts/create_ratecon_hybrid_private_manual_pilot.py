"""Create a local-only private manual pilot packet for RateCon hybrid results.

The generator reads local audit/gold metadata, selects a small representative
document set, and writes blank manual-fill templates plus a checklist. It does
not call AI models, cloud services, OCR, local model runtimes, or PDF readers.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.ratecon_gold_labels import load_gold_labels  # noqa: E402
from app.document_ai.ratecon_hybrid_contract import (  # noqa: E402
    HYBRID_SCHEMA_VERSION,
    build_stop_template,
    is_under_local_outputs,
)


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_manual_pilot")
PATTERN_PRIORITY = (
    "compact_table_row",
    "pickup_drop_block",
    "pu_so_row",
    "structured_shipper_consignee_block",
    "city_level_or_non_rc",
)
CHECKLIST_FIELDNAMES = [
    "document_id",
    "file_name",
    "document_pattern",
    "document_type_expected",
    "field_group",
    "field_name",
    "stop_role",
    "stop_index",
    "what_to_fill",
    "evidence_required",
    "instructions",
    "common_mistakes",
    "completion_status",
]


class HybridManualPilotError(ValueError):
    """Raised when pilot packet generation would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_file_name(document_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in document_id)
    return f"{safe or 'RATECON_MANUAL_PILOT'}.hybrid_result.json"


def _read_audit_records(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    resolved = _repo_relative(path)
    if not resolved.exists():
        return []
    records: list[dict[str, Any]] = []
    with resolved.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _audit_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for record in records:
        for key in ("document_id", "file_name", "file_hash", "file_hash_prefix"):
            value = _text(record.get(key))
            if value and value not in index:
                index[value] = record
    return index


def _match_audit(label: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for key in ("document_id", "file_name", "file_hash"):
        value = _text(label.get(key))
        if value and value in index:
            return index[value]
    file_hash = _text(label.get("file_hash"))
    if file_hash:
        for candidate, record in index.items():
            if file_hash.startswith(candidate) or candidate.startswith(file_hash):
                return record
    return {}


def _combined_metadata_text(record: dict[str, Any], label: dict[str, Any]) -> str:
    parts: list[str] = []
    for source in (record, label):
        for key in (
            "document_id",
            "file_name",
            "document_pattern",
            "pattern",
            "layout_pattern",
            "template_family",
            "scenario",
        ):
            value = source.get(key) if isinstance(source, dict) else ""
            if isinstance(value, str):
                parts.append(value.lower())
    gold = label.get("gold", {}) if isinstance(label, dict) else {}
    if isinstance(gold, dict):
        parts.append(_text(gold.get("document_type")).lower())
    return " ".join(parts)


def infer_document_pattern(record: dict[str, Any], label: dict[str, Any]) -> str:
    """Infer a pilot grouping from safe metadata, not document text."""

    explicit = _text(record.get("document_pattern") or record.get("pattern") or record.get("template_family"))
    if explicit:
        return explicit
    text = _combined_metadata_text(record, label)
    if "perfect" in text:
        return "sanitized_perfect_rate_confirmation"
    if "missing_evidence" in text or "missing evidence" in text:
        return "sanitized_missing_evidence"
    if "unsafe" in text or "wrong_stop" in text:
        return "sanitized_unsafe_wrong_stop"
    if "auto_accept" in text or "auto accept" in text:
        return "sanitized_auto_accept_violation"
    if "partial" in text:
        return "sanitized_optional_partial_stop"
    if "bol_pod" in text or "bol pod" in text or "non_rc" in text or "non rc" in text:
        return "city_level_or_non_rc"
    if "compact" in text or "location / date / time" in text:
        return "compact_table_row"
    if "pickup/drop" in text or "pickup drop" in text or "drop block" in text:
        return "pickup_drop_block"
    if "pu/so" in text or "pu so" in text:
        return "pu_so_row"
    if "shipper" in text or "consignee" in text:
        return "structured_shipper_consignee_block"
    if "city-level" in text or "city level" in text or "verbal" in text:
        return "city_level_or_non_rc"
    return "unclassified"


def _document_type_expected(label: dict[str, Any]) -> str:
    gold = label.get("gold", {}) if isinstance(label, dict) else {}
    return _text(gold.get("document_type")) if isinstance(gold, dict) else "unknown"


def _candidate_rows(audit_records: list[dict[str, Any]], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audit_by_key = _audit_index(audit_records)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, label in enumerate(labels, start=1):
        audit = _match_audit(label, audit_by_key)
        document_id = _text(label.get("document_id")) or _text(audit.get("document_id")) or f"RATECON_PILOT_{index:03d}"
        file_name = _text(label.get("file_name")) or _text(audit.get("file_name"))
        row = {
            "document_id": document_id,
            "file_name": file_name,
            "file_hash_prefix": (_text(label.get("file_hash")) or _text(audit.get("file_hash")) or "")[:16],
            "document_type_expected": _document_type_expected(label) or "unknown",
            "document_pattern": infer_document_pattern(audit, label),
        }
        rows.append(row)
        seen.add(document_id)
    for index, audit in enumerate(audit_records, start=1):
        document_id = _text(audit.get("document_id")) or f"RATECON_PILOT_AUDIT_{index:03d}"
        if document_id in seen:
            continue
        rows.append(
            {
                "document_id": document_id,
                "file_name": _text(audit.get("file_name")),
                "file_hash_prefix": _text(audit.get("file_hash_prefix") or audit.get("file_hash"))[:16],
                "document_type_expected": _text(audit.get("document_type")) or "unknown",
                "document_pattern": infer_document_pattern(audit, {}),
            }
        )
    return rows


def _priority(pattern: str) -> int:
    if pattern in PATTERN_PRIORITY:
        return PATTERN_PRIORITY.index(pattern)
    if pattern.startswith("sanitized_"):
        return len(PATTERN_PRIORITY)
    if pattern == "unclassified":
        return len(PATTERN_PRIORITY) + 2
    return len(PATTERN_PRIORITY) + 1


def select_pilot_documents(
    rows: list[dict[str, Any]],
    *,
    max_docs: int = 5,
    document_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    if document_ids:
        wanted = set(document_ids)
        return [row for row in rows if row["document_id"] in wanted][:max_docs]
    by_pattern: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(rows, key=lambda item: (_priority(item["document_pattern"]), item["document_id"])):
        by_pattern.setdefault(row["document_pattern"], []).append(row)
    selected: list[dict[str, Any]] = []
    for pattern in sorted(by_pattern, key=_priority):
        if len(selected) >= max_docs:
            break
        selected.append(by_pattern[pattern][0])
    selected_ids = {row["document_id"] for row in selected}
    for row in sorted(rows, key=lambda item: (_priority(item["document_pattern"]), item["document_id"])):
        if len(selected) >= max_docs:
            break
        if row["document_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["document_id"])
    return selected


def _manual_template(row: dict[str, Any]) -> dict[str, Any]:
    is_rate_confirmation = row.get("document_type_expected") in {"", "unknown", "rate_confirmation"}
    template = {
        "schema_version": HYBRID_SCHEMA_VERSION,
        "document_id": row["document_id"],
        "file_name_or_label": row.get("file_name") or row["document_id"],
        "document_type": "unknown",
        "model_provider": "manual",
        "model_name": "manual_pilot_v1",
        "private_local_only": True,
        "fields": {
            "load_number": {
                "value": None,
                "confidence": 0.0,
                "requires_human_review": True,
                "evidence_ids": [],
            },
            "total_carrier_rate": {
                "value": None,
                "currency": "USD",
                "confidence": 0.0,
                "requires_human_review": True,
                "evidence_ids": [],
            },
            "pickup_stops": [build_stop_template("pickup", 1)] if is_rate_confirmation else [],
            "delivery_stops": [build_stop_template("delivery", 1)] if is_rate_confirmation else [],
        },
        "evidence": [],
        "confidence": {
            "overall": 0.0,
            "load_number": 0.0,
            "total_carrier_rate": 0.0,
            "pickup_stops": 0.0,
            "delivery_stops": 0.0,
        },
        "requires_human_review": True,
        "review_reasons": ["manual_pilot_unfilled", "phase_1_no_auto_accept"],
        "validator_results": {
            "document_classification_gate": {"status": "not_evaluated"},
            "critical_field_gate": {"status": "not_evaluated"},
            "stop_consistency_gate": {"status": "review_required"},
            "evidence_gate": {"status": "not_evaluated"},
            "confidence_review_gate": {"status": "review_required"},
            "no_auto_accept_gate": {"status": "passed"},
        },
    }
    if row.get("file_hash_prefix"):
        template["file_hash_prefix"] = row["file_hash_prefix"]
    return template


def _checklist_rows(row: dict[str, Any]) -> list[dict[str, str]]:
    base = {
        "document_id": row["document_id"],
        "file_name": row.get("file_name") or "",
        "document_pattern": row.get("document_pattern") or "unclassified",
        "document_type_expected": row.get("document_type_expected") or "unknown",
        "completion_status": "not_started",
    }
    common = "include page/evidence for every filled value; do not auto-accept stops"
    rows = [
        {
            **base,
            "field_group": "document",
            "field_name": "document_type",
            "stop_role": "",
            "stop_index": "",
            "what_to_fill": "document type",
            "evidence_required": "yes",
            "instructions": "Choose rate_confirmation, bol_pod, or unknown.",
            "common_mistakes": "do not score BOL/POD as a failed rate confirmation",
        },
        {
            **base,
            "field_group": "critical",
            "field_name": "load_number",
            "stop_role": "",
            "stop_index": "",
            "what_to_fill": "load number",
            "evidence_required": "yes",
            "instructions": "Fill the load identifier exactly as shown in the document.",
            "common_mistakes": "do not use PO, BOL, PRO, or reference numbers unless they are the load number",
        },
        {
            **base,
            "field_group": "critical",
            "field_name": "total_carrier_rate",
            "stop_role": "",
            "stop_index": "",
            "what_to_fill": "total carrier rate",
            "evidence_required": "yes",
            "instructions": "Fill the carrier-pay amount, not charges, accessorial notes, or payment terms.",
            "common_mistakes": "do not use payment terms as stop data",
        },
    ]
    if row.get("document_type_expected") == "bol_pod":
        return rows
    stop_fields = [
        ("facility", "facility", "fill facility if visible; otherwise leave null", "do not use contact phone as address"),
        ("address", "address", "fill street address if visible; otherwise leave null", "do not use contact phone as address"),
        ("city_state", "city/state", "fill city and state when visible", "do not use reference/contact-only rows as stop location"),
        ("date", "date", "fill pickup or delivery date when visible", "do not use BOL/POD date unless it is the rate-con stop date"),
        ("time_window", "time/window", "fill time or appointment window when visible", "do not use payment or instruction dates/times"),
    ]
    for role in ("pickup", "delivery"):
        for field_name, label, instructions, mistakes in stop_fields:
            rows.append(
                {
                    **base,
                    "field_group": f"{role}_stops",
                    "field_name": field_name,
                    "stop_role": role,
                    "stop_index": "1",
                    "what_to_fill": f"{role} {label}",
                    "evidence_required": "yes",
                    "instructions": instructions,
                    "common_mistakes": f"{mistakes}; {common}",
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def create_private_manual_pilot(
    *,
    audit: Path,
    gold_dir: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    max_docs: int = 5,
    include_private_values_local_only: bool = False,
    pilot_profile: str = "representative_v1",
    document_ids: list[str] | None = None,
    write_empty_templates: bool = True,
    write_review_checklist: bool = True,
) -> dict[str, Any]:
    if pilot_profile != "representative_v1":
        raise HybridManualPilotError("Only pilot-profile representative_v1 is supported.")
    if max_docs < 1:
        raise HybridManualPilotError("--max-docs must be at least 1.")
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise HybridManualPilotError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    templates_dir = resolved_output / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    audit_records = _read_audit_records(audit)
    labels = load_gold_labels(_repo_relative(gold_dir))
    candidates = _candidate_rows(audit_records, labels)
    selected = select_pilot_documents(candidates, max_docs=max_docs, document_ids=document_ids)

    index_rows: list[dict[str, Any]] = []
    checklist_rows: list[dict[str, Any]] = []
    for row in selected:
        template_file = _safe_file_name(row["document_id"])
        if write_empty_templates:
            _write_json(templates_dir / template_file, _manual_template(row))
        index_rows.append(
            {
                "document_id": row["document_id"],
                "file_name": row.get("file_name") or "",
                "document_pattern": row["document_pattern"],
                "document_type_expected": row["document_type_expected"],
                "template_file": f"templates/{template_file}",
                "stops_review_required": True,
                "stop_auto_accept": False,
                "private_values_included": bool(include_private_values_local_only),
            }
        )
        if write_review_checklist:
            checklist_rows.extend(_checklist_rows(row))

    if write_review_checklist:
        _write_csv(resolved_output / "manual_pilot_checklist.csv", checklist_rows, CHECKLIST_FIELDNAMES)
    _write_csv(
        resolved_output / "manual_pilot_document_index.csv",
        index_rows,
        [
            "document_id",
            "file_name",
            "document_pattern",
            "document_type_expected",
            "template_file",
            "stops_review_required",
            "stop_auto_accept",
            "private_values_included",
        ],
    )
    readme = """# RateCon Hybrid Manual Pilot Packet

This local-only packet is for manually filling review-first hybrid extraction
templates. No AI, cloud service, OCR, local model, or PDF processing was used to
create it.

Start with `manual_pilot_checklist.csv`, then edit files under `templates/`.
Every filled value needs evidence, every stop remains `requires_human_review=true`,
and every stop must keep `auto_accept=false`.
"""
    (resolved_output / "manual_pilot_readme.md").write_text(readme, encoding="utf-8")
    benchmark_doc = f"""# How To Run The Manual Pilot Benchmark

After manually filling templates, run:

```powershell
python scripts/run_ratecon_hybrid_benchmark.py ^
  --hybrid-results-dir {output_dir.as_posix()}/templates ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_manual_pilot_benchmark ^
  --confirm-private-local-run ^
  --allow-unfilled-manual-templates ^
  --write-review-packets
```

Generated benchmark outputs stay under `.local_outputs/` and must not be
committed.
"""
    (resolved_output / "how_to_run_benchmark.md").write_text(benchmark_doc, encoding="utf-8")

    pattern_counts = Counter(row["document_pattern"] for row in selected)
    summary = {
        "schema_version": "ratecon_hybrid_manual_pilot_summary_v1",
        "output_dir": str(output_dir),
        "pilot_profile": pilot_profile,
        "audit_records_seen": len(audit_records),
        "gold_labels_seen": len(labels),
        "candidate_document_count": len(candidates),
        "selected_document_count": len(selected),
        "template_count": len(index_rows) if write_empty_templates else 0,
        "checklist_row_count": len(checklist_rows) if write_review_checklist else 0,
        "document_pattern_counts": dict(pattern_counts),
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
        "private_values_included": bool(include_private_values_local_only),
    }
    _write_json(resolved_output / "manual_pilot_summary.json", summary)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a local-only RateCon hybrid private manual pilot packet.")
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--max-docs", type=int, default=5)
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--pilot-profile", default="representative_v1")
    parser.add_argument("--document-id", action="append", default=[])
    parser.add_argument("--write-empty-templates", action="store_true")
    parser.add_argument("--write-review-checklist", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local private manual pilot generation")
    summary = create_private_manual_pilot(
        audit=args.audit,
        gold_dir=args.gold_dir,
        output_dir=args.output_dir,
        max_docs=args.max_docs,
        include_private_values_local_only=args.include_private_values_local_only,
        pilot_profile=args.pilot_profile,
        document_ids=args.document_id or None,
        write_empty_templates=True,
        write_review_checklist=True,
    )
    print("RateCon hybrid private manual pilot summary")
    print(f"output_dir: {summary['output_dir']}")
    print(f"selected_document_count: {summary['selected_document_count']}")
    print(f"template_count: {summary['template_count']}")
    print(f"checklist_row_count: {summary['checklist_row_count']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
