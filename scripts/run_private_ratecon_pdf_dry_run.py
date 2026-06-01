import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.intake.ratecon_pdf_dry_run import (  # noqa: E402
    run_ratecon_pdf_dry_run,
)


DEFAULT_PRIVATE_RATECON_DIR = Path("data/private_ratecons/originals")
DEFAULT_LIMIT = 1
DRY_RUN_WARNING = (
    "DRY RUN ONLY - private PDFs processed locally; no text saved, no cases linked or created"
)


def list_private_pdf_files(directory=DEFAULT_PRIVATE_RATECON_DIR):
    root = Path(directory)

    if not root.exists():
        return []

    return sorted(
        [
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        ],
        key=lambda path: path.name.lower(),
    )


def _safe_limit(limit):
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(value, 0)


def _low_confidence_fields(dry_run_result):
    if not dry_run_result:
        return []

    parser_output = dry_run_result.get("parser_output", {})
    field_confidence = parser_output.get("field_confidence", {})

    if not isinstance(field_confidence, dict):
        return []

    return sorted(
        field_name
        for field_name, confidence in field_confidence.items()
        if str(confidence or "").strip().upper() == "LOW"
    )


def _safe_summary(label, result):
    dry_run_result = result.get("dry_run_result") or {}
    intake_summary = dry_run_result.get("intake_summary", {})
    core_summary = dry_run_result.get("ratecon_core_summary", {})
    link_candidate = dry_run_result.get("link_candidate") or {}
    extraction_metadata = result.get("extraction_metadata", {})
    shadow_record = result.get("ratecon_shadow_audit_record") or {}
    shadow = shadow_record.get("shadow", {}) or {}
    failure = shadow_record.get("failure_attribution", {}) or {}

    return {
        "label": label,
        "extraction_status": result.get("extraction_status", ""),
        "char_count": extraction_metadata.get("char_count", 0),
        "page_count": extraction_metadata.get("page_count", 0),
        "intake_status": dry_run_result.get("status", ""),
        "core_fields_present": bool(core_summary.get("core_fields_present", False)),
        "missing_core_fields": list(core_summary.get("missing_core_fields", [])),
        "optional_missing_fields": list(
            core_summary.get("optional_missing_fields", [])
        ),
        "deferred_fields": list(core_summary.get("deferred_fields", [])),
        "miles_status": str(core_summary.get("miles_status", "")),
        "miles_source": str(core_summary.get("miles_source", "")),
        "missing_fields": list(intake_summary.get("missing_fields", [])),
        "needs_check_fields": list(intake_summary.get("needs_check_fields", [])),
        "low_confidence_fields": _low_confidence_fields(dry_run_result),
        "link_candidate_action": link_candidate.get("recommended_action", ""),
        "result_category": result.get("status", ""),
        "warnings": list(result.get("warnings", [])),
        "ratecon_shadow_enabled": bool(result.get("ratecon_shadow_enabled", False)),
        "shadow_success": bool(shadow.get("success", False)),
        "shadow_needs_review": bool(shadow.get("needs_review", False)),
        "shadow_failure_primary_layer": failure.get("primary_suspected_layer", ""),
        "shadow_failure_codes": list(failure.get("codes", [])),
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }


def build_private_pdf_dry_run_report(
    directory=DEFAULT_PRIVATE_RATECON_DIR,
    limit=DEFAULT_LIMIT,
    runner=run_ratecon_pdf_dry_run,
    ratecon_shadow_document_pipeline=False,
    include_document_ai_debug=False,
    strict_ratecon_shadow_document_pipeline=False,
):
    pdf_files = list_private_pdf_files(directory)
    safe_limit = _safe_limit(limit)
    results = []

    for index, path in enumerate(pdf_files[:safe_limit], start=1):
        label = f"RATECON_{index:03d}"
        runner_kwargs = {"anonymized_label": label}
        if ratecon_shadow_document_pipeline:
            runner_kwargs.update(
                {
                    "ratecon_shadow_document_pipeline": True,
                    "include_document_ai_debug": include_document_ai_debug,
                    "strict_ratecon_shadow_document_pipeline": (
                        strict_ratecon_shadow_document_pipeline
                    ),
                }
            )
        dry_run = runner(path, **runner_kwargs)
        results.append(_safe_summary(label, dry_run))

    return {
        "directory": str(Path(directory)),
        "total_pdf_files": len(pdf_files),
        "processed_count": len(results),
        "limit": safe_limit,
        "results": results,
        "privacy_warning": DRY_RUN_WARNING,
        "raw_text_printed": False,
        "private_text_saved": False,
        "cases_created": False,
        "events_written": False,
    }


def format_list(values):
    if not values:
        return "none"
    return ", ".join(str(value) for value in values)


def format_private_pdf_dry_run_report(report):
    lines = [
        "PRIVATE RATECON PDF DRY-RUN REPORT",
        DRY_RUN_WARNING,
        f"Directory: {report['directory']}",
        f"Total PDF files: {report['total_pdf_files']}",
        f"Processed PDF files: {report['processed_count']}",
        f"Limit: {report['limit']}",
        "Results:",
    ]

    for item in report["results"]:
        lines.extend(
            [
                f"- {item['label']}:",
                f"  extraction_status: {item['extraction_status']}",
                f"  char_count: {item['char_count']}",
                f"  page_count: {item['page_count']}",
                f"  intake_status: {item['intake_status'] or 'none'}",
                f"  core_fields_present: {item['core_fields_present']}",
                f"  missing_core_fields: {format_list(item['missing_core_fields'])}",
                f"  optional_missing_fields: {format_list(item['optional_missing_fields'])}",
                f"  deferred_fields: {format_list(item['deferred_fields'])}",
                f"  miles_status: {item['miles_status'] or 'none'}",
                f"  miles_source: {item['miles_source'] or 'none'}",
                f"  missing_fields: {format_list(item['missing_fields'])}",
                f"  needs_check_fields: {format_list(item['needs_check_fields'])}",
                f"  low_confidence_fields: {format_list(item['low_confidence_fields'])}",
                f"  link_candidate_action: {item['link_candidate_action'] or 'none'}",
                f"  result_category: {item['result_category'] or 'none'}",
                f"  warnings: {format_list(item['warnings'])}",
                f"  ratecon_shadow_enabled: {item.get('ratecon_shadow_enabled', False)}",
                f"  shadow_success: {item.get('shadow_success', False)}",
                f"  shadow_needs_review: {item.get('shadow_needs_review', False)}",
                f"  shadow_failure_primary_layer: {item.get('shadow_failure_primary_layer') or 'none'}",
                f"  shadow_failure_codes: {format_list(item.get('shadow_failure_codes', []))}",
            ]
        )

    if not report["results"]:
        lines.append("- none")

    lines.append("")
    lines.append("No raw extracted text is printed or saved.")
    lines.append("Do not commit private PDFs, extracted text, or local dry-run outputs.")

    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Local-only private RateCon PDF dry-run with safe summaries."
    )
    parser.add_argument(
        "--directory",
        default=str(DEFAULT_PRIVATE_RATECON_DIR),
        help="Local private RateCon originals folder.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of private PDFs to process.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print safe JSON summary without raw extracted text.",
    )
    parser.add_argument("--ratecon-shadow-document-pipeline", action="store_true")
    parser.add_argument("--include-document-ai-debug", action="store_true")
    parser.add_argument("--strict-ratecon-shadow-document-pipeline", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = build_private_pdf_dry_run_report(
        directory=args.directory,
        limit=args.limit,
        ratecon_shadow_document_pipeline=args.ratecon_shadow_document_pipeline,
        include_document_ai_debug=args.include_document_ai_debug,
        strict_ratecon_shadow_document_pipeline=args.strict_ratecon_shadow_document_pipeline,
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_private_pdf_dry_run_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
