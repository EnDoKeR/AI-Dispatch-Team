"""Run local-only redacted RateCon template pattern collection."""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.private_measurement_inputs import (
    PrivateMeasurementInputError,
    build_safe_aliases,
    discover_private_pdfs,
)
from app.document_ai.private_template_drafts import write_private_template_draft_skeletons
from app.document_ai.private_template_pattern_collector import (
    collect_redacted_template_patterns_from_pdf,
)
from app.document_ai.private_template_pattern_families import (
    group_redacted_patterns_into_template_families,
)


DEFAULT_PATTERN_OUTPUT_DIR = Path(".local_outputs/private_ratecon_measurement/template_patterns")

SAFETY_BANNER = (
    "PRIVATE LOCAL TEMPLATE PATTERN COLLECTION - raw text is not printed or saved; "
    "private values are redacted; outputs are local-only and ignored"
)


def _write_pattern_json(summaries, families, output_dir):
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "local_only": True,
        "private_values_redacted": True,
        "raw_text_saved": False,
        "summaries": summaries,
        "families": families,
    }
    path = directory / "redacted_template_patterns.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_family_md(families, output_dir):
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "template_family_candidates.md"
    lines = [
        "# Redacted Template Family Candidates",
        "",
        "Local-only ignored report. Contains aliases and redacted markers only.",
        "",
    ]
    for family in families:
        lines.extend(
            [
                f"## {family.get('family_alias', '')}",
                "",
                f"- aliases: {', '.join(family.get('aliases', [])) or 'none'}",
                f"- confidence_bucket: {family.get('confidence_bucket', '')}",
                f"- common_redacted_markers: {family.get('common_redacted_markers', [])}",
                f"- likely_rate_labels_redacted: {family.get('likely_rate_labels_redacted', [])}",
                f"- likely_stop_labels_redacted: {family.get('likely_stop_labels_redacted', [])}",
                f"- likely_reference_labels_redacted: {family.get('likely_reference_labels_redacted', [])}",
                f"- warnings: {family.get('warnings', [])}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _safe_file_labels(paths):
    return [Path(path).name for path in paths or []]


def build_private_template_pattern_collection_report(
    input_dir,
    output_dir=DEFAULT_PATTERN_OUTPUT_DIR,
    alias_prefix="RATECON",
    limit=0,
    include_ocr_needed_aliases=False,
    write_pattern_json=False,
    write_family_md=False,
    write_template_drafts=False,
):
    pdfs = discover_private_pdfs(input_dir)
    if limit and int(limit) > 0:
        pdfs = pdfs[: int(limit)]

    aliases = build_safe_aliases(pdfs, prefix=alias_prefix)
    summaries = []
    for path in pdfs:
        summary = collect_redacted_template_patterns_from_pdf(path, aliases[path])
        if include_ocr_needed_aliases or "OCR_NEEDED" not in summary.get("warning_codes", []):
            summaries.append(summary)

    families = group_redacted_patterns_into_template_families(summaries)
    output_paths = []
    if write_pattern_json:
        output_paths.append(_write_pattern_json(summaries, families, output_dir))
    if write_family_md:
        output_paths.append(_write_family_md(families, output_dir))
    if write_template_drafts:
        output_paths.extend(write_private_template_draft_skeletons(families))

    return {
        "documents_scanned": len(pdfs),
        "pattern_summaries": summaries,
        "families": families,
        "text_pattern_summary_count": len(
            [summary for summary in summaries if "OCR_NEEDED" not in summary.get("warning_codes", [])]
        ),
        "ocr_needed_count": len(
            [summary for summary in summaries if "OCR_NEEDED" in summary.get("warning_codes", [])]
        ),
        "output_files": _safe_file_labels(output_paths),
        "raw_text_printed": False,
        "raw_text_saved": False,
        "private_values_redacted": True,
    }


def format_pattern_collection_report(report):
    lines = [
        SAFETY_BANNER,
        f"documents_scanned: {report.get('documents_scanned', 0)}",
        f"text_pattern_summaries: {report.get('text_pattern_summary_count', 0)}",
        f"ocr_needed_summaries: {report.get('ocr_needed_count', 0)}",
        f"template_families: {len(report.get('families', []))}",
    ]
    for family in report.get("families", []):
        lines.extend(
            [
                "",
                family.get("family_alias", ""),
                f"  aliases: {family.get('aliases', [])}",
                f"  confidence_bucket: {family.get('confidence_bucket', '')}",
                f"  common_redacted_markers: {family.get('common_redacted_markers', [])}",
                f"  warnings: {family.get('warnings', [])}",
            ]
        )
    if report.get("output_files"):
        lines.append("")
        lines.append(f"safe_outputs_written: {report.get('output_files', [])}")
    lines.append("")
    lines.append("SAFE TO SHARE: family IDs, aliases, counts, statuses, field names, blocker categories.")
    lines.append("DO NOT SHARE: raw text, filenames, broker names, MCs, rates, addresses, references, local paths.")
    return lines


def _print_expected_error(reason):
    print("Private RateCon template pattern collection could not start.", file=sys.stderr)
    print(f"Reason: {reason}.", file=sys.stderr)
    print("Replace the example path with a real local folder containing RateCon PDFs.", file=sys.stderr)
    print("Tip: start with --limit 3 for the first safe run.", file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Collect redacted local-only RateCon template patterns. Requires explicit "
            "confirmation and never prints raw text or private values."
        )
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_PATTERN_OUTPUT_DIR))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--alias-prefix", default="RATECON")
    parser.add_argument("--write-pattern-json", action="store_true")
    parser.add_argument("--write-family-md", action="store_true")
    parser.add_argument("--write-template-drafts", action="store_true")
    parser.add_argument("--use-existing-safe-measurement", action="store_true")
    parser.add_argument("--include-ocr-needed-aliases", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.confirm_private_local_run:
        print("Refusing to run: pass --confirm-private-local-run for local private pattern collection.")
        return 2

    try:
        report = build_private_template_pattern_collection_report(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            alias_prefix=args.alias_prefix,
            limit=args.limit,
            include_ocr_needed_aliases=args.include_ocr_needed_aliases,
            write_pattern_json=False if args.dry_run else args.write_pattern_json,
            write_family_md=False if args.dry_run else args.write_family_md,
            write_template_drafts=False if args.dry_run else args.write_template_drafts,
        )
    except (PrivateMeasurementInputError, FileNotFoundError) as exc:
        _print_expected_error(str(exc))
        return 2

    for line in format_pattern_collection_report(report):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
