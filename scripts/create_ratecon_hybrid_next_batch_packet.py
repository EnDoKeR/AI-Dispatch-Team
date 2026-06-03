"""Create a local-only next-batch manual packet for RateCon hybrid results.

The packet generator consumes a local next-batch plan CSV plus local audit/gold
metadata and writes blank manual-fill hybrid result templates. It does not call
AI models, cloud services, OCR, local model runtimes, or PDF readers.
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


DEFAULT_OUTPUT_DIR = Path(".local_outputs/private_ratecon_hybrid_next_batch_packet")
DEFAULT_TEMPLATE_SOURCE = "plan"
TEMPLATE_SOURCES = {"audit", "gold", "plan"}
CHECKLIST_FIELDNAMES = [
    "document_id",
    "file_name",
    "suggested_pattern",
    "difficulty",
    "reason_selected",
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
INDEX_FIELDNAMES = [
    "document_id",
    "file_name",
    "file_hash_prefix",
    "suggested_pattern",
    "difficulty",
    "reason_selected",
    "document_type_expected",
    "template_file",
    "stops_review_required",
    "stop_auto_accept",
    "private_values_included",
]
COMMON_MISTAKES = (
    "do not use payment terms as stop data; "
    "do not use contact phone as address; "
    "do not use BOL/POD-only date as rate-con stop date unless it is actually the rate-con stop; "
    "do not auto-accept stops; "
    "include page/evidence for every filled value; "
    "preserve uncertainty instead of guessing"
)


class HybridNextBatchPacketError(ValueError):
    """Raised when next-batch packet generation would be unsafe or invalid."""


def _repo_relative(path: Path) -> Path:
    return (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    resolved = _repo_relative(path)
    if not resolved.exists():
        raise HybridNextBatchPacketError(f"Next-batch plan does not exist: {path}")
    with resolved.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def _index_by_keys(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in keys:
            value = _text(row.get(key))
            if value and value not in index:
                index[value] = row
    return index


def _gold_index(labels: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _index_by_keys(labels, ("document_id", "file_name", "file_hash"))


def _audit_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _index_by_keys(records, ("document_id", "file_name", "file_hash", "file_hash_prefix"))


def _match_metadata(plan_row: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for key in ("document_id", "file_name", "file_hash", "file_hash_prefix"):
        value = _text(plan_row.get(key))
        if value and value in index:
            return index[value]
    return {}


def _safe_file_name(document_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in document_id)
    return f"{safe or 'RATECON_NEXT_BATCH'}.hybrid_result.json"


def _gold_document_type(label: dict[str, Any]) -> str:
    gold = label.get("gold", {}) if isinstance(label, dict) else {}
    return _text(gold.get("document_type")) if isinstance(gold, dict) else ""


def _document_type_from_plan(row: dict[str, Any]) -> str:
    explicit = _text(row.get("document_type_expected") or row.get("document_type"))
    if explicit:
        return explicit
    combined = " ".join(
        _text(row.get(key)).lower()
        for key in ("suggested_pattern", "difficulty", "reason_selected", "expected_fields_to_fill", "notes_for_reviewer")
    )
    if any(token in combined for token in ("non-rc", "non_rc", "bol/pod", "bol_pod", "bol pod")):
        return "bol_pod"
    return "unknown"


def _document_type_expected(row: dict[str, Any], audit: dict[str, Any], gold: dict[str, Any], template_source: str) -> str:
    values = {
        "plan": _document_type_from_plan(row),
        "audit": _text(audit.get("document_type")),
        "gold": _gold_document_type(gold),
    }
    preferred = values.get(template_source) or ""
    if preferred:
        return preferred
    for key in ("plan", "gold", "audit"):
        if values[key]:
            return values[key]
    return "unknown"


def _file_name(row: dict[str, Any], audit: dict[str, Any], gold: dict[str, Any], template_source: str) -> str:
    values = {
        "plan": _text(row.get("file_name")),
        "audit": _text(audit.get("file_name")),
        "gold": _text(gold.get("file_name")),
    }
    preferred = values.get(template_source) or ""
    if preferred:
        return preferred
    for key in ("plan", "audit", "gold"):
        if values[key]:
            return values[key]
    return ""


def _file_hash_prefix(row: dict[str, Any], audit: dict[str, Any], gold: dict[str, Any], template_source: str) -> str:
    values = {
        "plan": _text(row.get("file_hash_prefix") or row.get("file_hash"))[:16],
        "audit": _text(audit.get("file_hash_prefix") or audit.get("file_hash"))[:16],
        "gold": _text(gold.get("file_hash"))[:16],
    }
    preferred = values.get(template_source) or ""
    if preferred:
        return preferred
    for key in ("plan", "audit", "gold"):
        if values[key]:
            return values[key]
    return ""


def _is_likely_rate_confirmation(document_type_expected: str) -> bool:
    return document_type_expected in {"", "unknown", "rate_confirmation"}


def _template_document_type(document_type_expected: str) -> str:
    if document_type_expected == "bol_pod":
        return "bol_pod"
    return "unknown"


def _manual_next_batch_template(row: dict[str, Any]) -> dict[str, Any]:
    is_rate_confirmation = _is_likely_rate_confirmation(row.get("document_type_expected") or "")
    template = {
        "schema_version": HYBRID_SCHEMA_VERSION,
        "document_id": row["document_id"],
        "file_name_or_label": row.get("file_name") or row["document_id"],
        "document_type": _template_document_type(row.get("document_type_expected") or "unknown"),
        "model_provider": "manual",
        "model_name": "manual_next_batch_v1",
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
        "review_reasons": ["manual_next_batch_unfilled", "phase_1_no_auto_accept"],
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


def _selected_rows(
    plan_rows: list[dict[str, Any]],
    *,
    audit_records: list[dict[str, Any]],
    gold_labels: list[dict[str, Any]],
    max_docs: int,
    document_ids: list[str] | None,
    template_source: str,
) -> list[dict[str, Any]]:
    if max_docs < 1:
        raise HybridNextBatchPacketError("--max-docs must be at least 1.")
    if template_source not in TEMPLATE_SOURCES:
        raise HybridNextBatchPacketError("--template-source must be audit, gold, or plan.")
    audit_by_key = _audit_index(audit_records)
    gold_by_key = _gold_index(gold_labels)
    wanted = set(document_ids or [])
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in plan_rows:
        document_id = _text(raw.get("document_id"))
        if not document_id:
            continue
        if wanted and document_id not in wanted:
            continue
        if document_id in seen:
            continue
        audit = _match_metadata(raw, audit_by_key)
        gold = _match_metadata(raw, gold_by_key)
        file_name = _file_name(raw, audit, gold, template_source)
        row = {
            "document_id": document_id,
            "file_name": file_name,
            "file_hash_prefix": _file_hash_prefix(raw, audit, gold, template_source),
            "suggested_pattern": _text(raw.get("suggested_pattern")) or "unclassified",
            "difficulty": _text(raw.get("difficulty")) or "unknown",
            "reason_selected": _text(raw.get("reason_selected")) or "expand representative manual pilot coverage",
            "document_type_expected": _document_type_expected(raw, audit, gold, template_source) or "unknown",
            "expected_fields_to_fill": _text(raw.get("expected_fields_to_fill")),
            "notes_for_reviewer": _text(raw.get("notes_for_reviewer")),
        }
        rows.append(row)
        seen.add(document_id)
        if len(rows) >= max_docs:
            break
    return rows


def _document_index_rows(rows: list[dict[str, Any]], *, private_values: bool) -> list[dict[str, Any]]:
    index_rows: list[dict[str, Any]] = []
    for row in rows:
        template_file = f"templates/{_safe_file_name(row['document_id'])}"
        index_rows.append(
            {
                "document_id": row["document_id"],
                "file_name": row.get("file_name") or "",
                "file_hash_prefix": row.get("file_hash_prefix") or "",
                "suggested_pattern": row.get("suggested_pattern") or "unclassified",
                "difficulty": row.get("difficulty") or "unknown",
                "reason_selected": row.get("reason_selected") or "",
                "document_type_expected": row.get("document_type_expected") or "unknown",
                "template_file": template_file,
                "stops_review_required": True,
                "stop_auto_accept": False,
                "private_values_included": bool(private_values),
            }
        )
    return index_rows


def _checklist_rows(row: dict[str, Any]) -> list[dict[str, str]]:
    base = {
        "document_id": row["document_id"],
        "file_name": row.get("file_name") or "",
        "suggested_pattern": row.get("suggested_pattern") or "unclassified",
        "difficulty": row.get("difficulty") or "unknown",
        "reason_selected": row.get("reason_selected") or "",
        "document_type_expected": row.get("document_type_expected") or "unknown",
        "completion_status": "not_started",
    }
    rows = [
        {
            **base,
            "field_group": "document",
            "field_name": "document_type",
            "stop_role": "",
            "stop_index": "",
            "what_to_fill": "document type",
            "evidence_required": "yes",
            "instructions": "Choose rate_confirmation, bol_pod, or unknown before filling any other fields.",
            "common_mistakes": "do not score BOL/POD as a failed rate confirmation; preserve uncertainty instead of guessing",
        },
        {
            **base,
            "field_group": "critical",
            "field_name": "load_number",
            "stop_role": "",
            "stop_index": "",
            "what_to_fill": "load number",
            "evidence_required": "yes",
            "instructions": "Fill the rate-con load identifier exactly as shown; leave null if not present.",
            "common_mistakes": "do not use PO, BOL, PRO, or reference numbers unless they are the load number; include page/evidence for every filled value",
        },
        {
            **base,
            "field_group": "critical",
            "field_name": "total_carrier_rate",
            "stop_role": "",
            "stop_index": "",
            "what_to_fill": "total carrier rate",
            "evidence_required": "yes",
            "instructions": "Fill carrier pay only; leave null if the document is not a rate confirmation.",
            "common_mistakes": "do not use payment terms as stop data; include page/evidence for every filled value",
        },
    ]
    if row.get("document_type_expected") == "bol_pod":
        return rows
    stop_components = [
        ("facility", "facility", "Fill facility if visible; otherwise leave null."),
        ("address", "address", "Fill street address if visible; otherwise leave null."),
        ("city", "city", "Fill city if visible; otherwise leave null."),
        ("state", "state", "Fill state if visible; otherwise leave null."),
        ("zip", "zip", "Fill ZIP/postal code if visible; otherwise leave null."),
        ("date", "date", "Fill the pickup/delivery date if visible; preserve uncertainty in notes/review."),
        ("time", "time", "Fill explicit time if visible; otherwise leave null."),
        ("appointment_window", "time/window", "Fill appointment window if visible; preserve weird windows instead of guessing."),
    ]
    for role in ("pickup", "delivery"):
        for field_name, label, instructions in stop_components:
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
                    "common_mistakes": COMMON_MISTAKES,
                }
            )
        for field_name, label in (("evidence_page", "evidence page"), ("evidence_source", "evidence source")):
            rows.append(
                {
                    **base,
                    "field_group": f"{role}_stops",
                    "field_name": field_name,
                    "stop_role": role,
                    "stop_index": "1",
                    "what_to_fill": f"{role} {label}",
                    "evidence_required": "yes",
                    "instructions": "Record page/source evidence for every filled stop value.",
                    "common_mistakes": COMMON_MISTAKES,
                }
            )
    return rows


def _readme() -> str:
    return """# RateCon Hybrid Next-Batch Manual Packet

This local-only packet contains blank manual-fill hybrid result templates for
the next manual pilot batch. It made no AI, cloud, OCR, model, or PDF processing
calls.

Start with `next_batch_document_index.csv`, then use `next_batch_checklist.csv`
while editing files under `templates/`.

Every filled value needs evidence. Every stop stays
`requires_human_review=true` and `auto_accept=false`.
"""


def _how_to_fill() -> str:
    return """# How To Fill Next-Batch Hybrid Templates

1. Open `next_batch_document_index.csv` and pick a document.
2. Open the matching file under `templates/`.
3. Set `document_type` first: `rate_confirmation`, `bol_pod`, or `unknown`.
4. Fill `load_number.value` and `total_carrier_rate.value` only when visible.
5. Fill pickup and delivery stop components only when visible.
6. Add evidence rows to `evidence`, then reference those evidence IDs from the
   field or stop.
7. Keep every stop `requires_human_review=true`.
8. Keep every stop `auto_accept=false`.

Leave unavailable components as `null`. Preserve uncertainty instead of
guessing.
"""


def _benchmark_doc(output_dir: Path) -> str:
    output = output_dir.as_posix()
    return f"""# How To Run The Next-Batch Benchmark

PowerShell `^` version:

```powershell
python scripts/run_ratecon_hybrid_benchmark.py ^
  --hybrid-results-dir {output}/templates ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_next_batch_benchmark ^
  --confirm-private-local-run ^
  --allow-unfilled-manual-templates ^
  --write-review-packets
```

PowerShell array version:

```powershell
$benchmarkArgs = @(
  "--hybrid-results-dir", "{output}/templates",
  "--gold-dir", ".local_outputs/private_ratecon_gold_labels",
  "--audit", ".local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl",
  "--output-dir", ".local_outputs/private_ratecon_hybrid_next_batch_benchmark",
  "--confirm-private-local-run",
  "--allow-unfilled-manual-templates",
  "--write-review-packets"
)
python scripts/run_ratecon_hybrid_benchmark.py @benchmarkArgs
```

Generated benchmark outputs stay under `.local_outputs/` and must not be
committed.
"""


def _zip_doc() -> str:
    return """# How To Zip Templates For Manual Review

Zip only the index, checklist, and blank/fillable JSON templates:

```powershell
Compress-Archive `
  ".local_outputs\\private_ratecon_hybrid_next_batch_packet\\next_batch_document_index.csv", `
  ".local_outputs\\private_ratecon_hybrid_next_batch_packet\\next_batch_checklist.csv", `
  ".local_outputs\\private_ratecon_hybrid_next_batch_packet\\templates\\*.hybrid_result.json" `
  -DestinationPath ".local_outputs\\hybrid_next_batch_templates_for_chatgpt.zip" `
  -Force
```

Do not zip PDFs unless explicitly requested. Do not commit the zip. Upload the
zip only for manual filling/review.
"""


def create_next_batch_packet(
    *,
    next_batch_plan: Path,
    audit: Path,
    gold_dir: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    max_docs: int = 10,
    document_ids: list[str] | None = None,
    include_private_values_local_only: bool = False,
    write_empty_templates: bool = True,
    write_checklist: bool = True,
    write_zip_instructions: bool = True,
    template_source: str = DEFAULT_TEMPLATE_SOURCE,
) -> dict[str, Any]:
    if not is_under_local_outputs(output_dir, REPO_ROOT):
        raise HybridNextBatchPacketError("Output directory must be under .local_outputs.")
    resolved_output = _repo_relative(output_dir)
    templates_dir = resolved_output / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    plan_rows = _read_csv(next_batch_plan)
    audit_records = _read_audit_records(audit)
    labels = load_gold_labels(_repo_relative(gold_dir)) if _repo_relative(gold_dir).exists() else []
    selected = _selected_rows(
        plan_rows,
        audit_records=audit_records,
        gold_labels=labels,
        max_docs=max_docs,
        document_ids=document_ids,
        template_source=template_source,
    )

    index_rows = _document_index_rows(selected, private_values=include_private_values_local_only)
    checklist_rows: list[dict[str, Any]] = []
    if write_empty_templates:
        for row in selected:
            _write_json(templates_dir / _safe_file_name(row["document_id"]), _manual_next_batch_template(row))
    if write_checklist:
        for row in selected:
            checklist_rows.extend(_checklist_rows(row))
        _write_csv(resolved_output / "next_batch_checklist.csv", checklist_rows, CHECKLIST_FIELDNAMES)

    _write_csv(resolved_output / "next_batch_document_index.csv", index_rows, INDEX_FIELDNAMES)
    (resolved_output / "next_batch_readme.md").write_text(_readme(), encoding="utf-8")
    (resolved_output / "how_to_fill_templates.md").write_text(_how_to_fill(), encoding="utf-8")
    (resolved_output / "how_to_run_benchmark.md").write_text(_benchmark_doc(output_dir), encoding="utf-8")
    if write_zip_instructions:
        (resolved_output / "how_to_zip_for_review.md").write_text(_zip_doc(), encoding="utf-8")

    pattern_counts = Counter(row["suggested_pattern"] for row in selected)
    summary = {
        "schema_version": "ratecon_hybrid_next_batch_packet_summary_v1",
        "output_dir": str(output_dir),
        "template_source": template_source,
        "plan_row_count": len(plan_rows),
        "audit_records_seen": len(audit_records),
        "gold_labels_seen": len(labels),
        "selected_document_count": len(selected),
        "template_count": len(selected) if write_empty_templates else 0,
        "checklist_row_count": len(checklist_rows) if write_checklist else 0,
        "index_row_count": len(index_rows),
        "document_pattern_counts": dict(pattern_counts),
        "external_api_calls_attempted": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "ai_model_invocation_attempted": False,
        "gold_labels_modified": False,
        "filled_hybrid_templates_modified": False,
        "private_values_included": bool(include_private_values_local_only),
    }
    _write_json(resolved_output / "next_batch_summary.json", summary)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a local-only RateCon hybrid next-batch manual packet.")
    parser.add_argument("--next-batch-plan", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--max-docs", type=int, default=10)
    parser.add_argument("--document-id", action="append", default=[])
    parser.add_argument("--include-private-values-local-only", action="store_true")
    parser.add_argument("--write-empty-templates", action="store_true")
    parser.add_argument("--write-checklist", action="store_true")
    parser.add_argument("--write-zip-instructions", action="store_true")
    parser.add_argument("--template-source", choices=sorted(TEMPLATE_SOURCES), default=DEFAULT_TEMPLATE_SOURCE)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_private_local_run:
        parser.error("--confirm-private-local-run is required for local next-batch packet generation")
    summary = create_next_batch_packet(
        next_batch_plan=args.next_batch_plan,
        audit=args.audit,
        gold_dir=args.gold_dir,
        output_dir=args.output_dir,
        max_docs=args.max_docs,
        document_ids=args.document_id or None,
        include_private_values_local_only=args.include_private_values_local_only,
        write_empty_templates=True,
        write_checklist=True,
        write_zip_instructions=True,
        template_source=args.template_source,
    )
    print("RateCon hybrid next-batch packet summary")
    print(f"output_dir: {summary['output_dir']}")
    print(f"selected_document_count: {summary['selected_document_count']}")
    print(f"template_count: {summary['template_count']}")
    print(f"checklist_row_count: {summary['checklist_row_count']}")
    print("external_api_calls_attempted: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("ai_model_invocation_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
