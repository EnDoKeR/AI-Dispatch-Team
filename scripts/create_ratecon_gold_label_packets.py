"""Create local RateCon gold-label packets from shadow audit diagnostics."""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.document_ai.private_measurement_outputs import DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR  # noqa: E402
from app.document_ai.ratecon_gold_labels import (  # noqa: E402
    PacketBuildOptions,
    build_gold_label_packet,
    read_json,
    read_jsonl,
    write_json,
)
from app.document_ai.ratecon_shadow_audit import (  # noqa: E402
    RATECON_SHADOW_AUDIT_JSONL,
    RATECON_SHADOW_AUDIT_SUMMARY_JSON,
)


DEFAULT_GOLD_PACKET_DIR = Path(".local_outputs") / "private_ratecon_gold_packets"


def _normalize_local_output_dir(output_dir, allow_custom_output_dir=False):
    path = Path(output_dir)
    if not allow_custom_output_dir and (not path.parts or path.parts[0] != ".local_outputs"):
        raise ValueError("gold-label packet output must be under .local_outputs unless --allow-custom-output-dir is used")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slug(value):
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())
    return text.strip("_") or "document"


def _score_record(record):
    failure = record.get("failure_attribution", {}) if isinstance(record, dict) else {}
    codes = set(failure.get("codes", []) or [])
    candidate_summary = record.get("candidate_summary", {}) or {}
    resolver = candidate_summary.get("resolver_selection_summary", {}) or {}
    fields = resolver.get("fields", {}) if isinstance(resolver, dict) else {}
    score = 0
    if not (record.get("shadow", {}) or {}).get("success", True):
        score += 1000
    if "MISSING_LOAD_NUMBER_CANDIDATE" in codes or "REVIEW_GATE_LOAD_MISSING" in codes:
        score += 200
    if "REVIEW_GATE_RATE_MISSING" in codes or "CONFLICTING_TOTAL_RATE_CANDIDATES" in codes:
        score += 150
    if "REVIEW_GATE_STOP_MISSING" in codes or "REVIEW_GATE_STOP_PRESENT_PARTIAL" in codes:
        score += 125
    score += len(codes)
    for details in fields.values():
        score += int((details or {}).get("high_quality_not_selected_count") or 0)
    return score


def _packet_markdown(packet):
    fields = ["load_number", "total_carrier_rate", "broker_name", "carrier_name", "pickup_stops", "delivery_stops"]
    lines = [
        "# RateCon Gold Label Packet",
        "",
        f"document_id: {packet.get('document_id', '')}",
        f"file_hash: {packet.get('file_hash', '')}",
        f"private_values_included: {packet.get('private_values_included', False)}",
        f"private_evidence_included: {packet.get('private_evidence_included', False)}",
        "",
        "## Field Status",
        "",
        "| field | legacy_present | shadow_confidence | shadow_needs_review | shadow_reasons |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    legacy = packet.get("legacy_values", {}) or {}
    shadow = packet.get("shadow_values", {}) or {}
    for field_name in fields:
        legacy_present = (legacy.get(field_name, {}) or {}).get("present", False)
        shadow_field = shadow.get(field_name, {}) or {}
        lines.append(
            "| {field} | {legacy_present} | {confidence} | {needs_review} | {reasons} |".format(
                field=field_name,
                legacy_present=legacy_present,
                confidence=shadow_field.get("confidence", ""),
                needs_review=shadow_field.get("needs_review", False),
                reasons=", ".join(shadow_field.get("review_reasons", []) or []),
            )
        )
    lines.extend(
        [
            "",
            "## Instructions",
            "",
            "Fill `gold_label_template` in the JSON packet or copy it into the gold-label directory.",
            "Do not commit completed private labels or generated packet outputs.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser():
    default_root = DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR
    parser = argparse.ArgumentParser(
        description="Create local private RateCon gold-label packet templates."
    )
    parser.add_argument(
        "--audit",
        default=str(default_root / RATECON_SHADOW_AUDIT_JSONL),
        help="Path to ratecon_shadow_document_pipeline_audit.jsonl.",
    )
    parser.add_argument(
        "--summary",
        default=str(default_root / RATECON_SHADOW_AUDIT_SUMMARY_JSON),
        help="Path to ratecon_shadow_document_pipeline_summary.json.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_GOLD_PACKET_DIR),
        help="Local output directory for generated gold-label packets.",
    )
    parser.add_argument("--top-n", type=int, default=18)
    parser.add_argument("--include-private-values", action="store_true")
    parser.add_argument("--include-private-evidence", action="store_true")
    parser.add_argument("--write-markdown", action="store_true")
    parser.add_argument("--allow-custom-output-dir", action="store_true")
    return parser


def create_packets(
    audit_path,
    summary_path,
    output_dir,
    top_n=18,
    include_private_values=False,
    include_private_evidence=False,
    write_markdown=False,
    allow_custom_output_dir=False,
):
    output_dir = _normalize_local_output_dir(
        output_dir,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    records = read_jsonl(audit_path)
    summary = read_json(summary_path) if Path(summary_path).exists() else {}
    selected = sorted(records, key=_score_record, reverse=True)
    if top_n and top_n > 0:
        selected = selected[:top_n]
    options = PacketBuildOptions(
        include_private_values=include_private_values,
        include_private_evidence=include_private_evidence,
    )
    packet_files = []
    markdown_files = []
    for index, record in enumerate(selected, start=1):
        packet = build_gold_label_packet(record, summary=summary, options=options)
        name = f"{index:03d}_{_slug(packet.get('document_id'))}_gold_label_packet.json"
        packet_path = output_dir / name
        write_json(packet_path, packet)
        packet_files.append(packet_path.name)
        if write_markdown:
            md_path = output_dir / name.replace(".json", ".md")
            md_path.write_text(_packet_markdown(packet), encoding="utf-8")
            markdown_files.append(md_path.name)
    manifest = {
        "schema_version": "ratecon_gold_label_packet_manifest_v1",
        "packet_count": len(packet_files),
        "packet_files": packet_files,
        "markdown_files": markdown_files,
        "include_private_values": bool(include_private_values),
        "include_private_evidence": bool(include_private_evidence),
        "raw_text_included": False,
        "source_audit_basename": Path(audit_path).name,
        "source_summary_basename": Path(summary_path).name,
    }
    manifest_path = output_dir / "ratecon_gold_label_packet_manifest.json"
    write_json(manifest_path, manifest)
    return {
        "packet_count": len(packet_files),
        "manifest": manifest_path.name,
        "packet_files": packet_files,
        "markdown_files": markdown_files,
        "private_values_included": bool(include_private_values),
        "private_evidence_included": bool(include_private_evidence),
        "raw_text_included": False,
    }


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = create_packets(
        audit_path=args.audit,
        summary_path=args.summary,
        output_dir=args.output_dir,
        top_n=args.top_n,
        include_private_values=args.include_private_values,
        include_private_evidence=args.include_private_evidence,
        write_markdown=args.write_markdown,
        allow_custom_output_dir=args.allow_custom_output_dir,
    )
    print(
        "ratecon_gold_label_packets_written: "
        + json.dumps(
            {
                "packet_count": result["packet_count"],
                "manifest": result["manifest"],
                "private_values_included": result["private_values_included"],
                "private_evidence_included": result["private_evidence_included"],
                "raw_text_included": result["raw_text_included"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
