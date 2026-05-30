import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.intake.pdf_text_extraction import (  # noqa: E402
    TEXT_EXTRACTED,
    extract_pdf_text_local,
)
from app.market_intelligence.intake.ratecon_layout_diagnostics import (  # noqa: E402
    detect_ratecon_layout_shapes,
)
from app.market_intelligence.intake.ratecon_parser_coverage import (  # noqa: E402
    build_ratecon_parser_coverage_report,
)


DEFAULT_PRIVATE_RATECON_DIR = Path("data/private_ratecons/originals")
DEFAULT_LIMIT = 1
DRY_RUN_WARNING = (
    "DRY RUN ONLY - redacted layout diagnostics, no raw text printed or saved"
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


def _empty_coverage():
    return {
        "signal_counts": {},
        "suspected_parser_gap_fields": [],
        "warnings": [],
    }


def _empty_shapes():
    return {
        "shape_counts_by_category": {},
        "shapes_by_category": {},
        "warnings": [],
    }


def _safe_summary(label, extraction, coverage, layout):
    return {
        "label": label,
        "extraction_status": extraction.get("extraction_status", ""),
        "char_count": extraction.get("char_count", 0),
        "page_count": extraction.get("page_count", 0),
        "signal_counts": dict(coverage.get("signal_counts", {})),
        "shape_counts_by_category": dict(
            layout.get("shape_counts_by_category", {})
        ),
        "shapes_by_category": dict(layout.get("shapes_by_category", {})),
        "suspected_parser_gap_fields": list(
            coverage.get("suspected_parser_gap_fields", [])
        ),
        "warnings": list(extraction.get("warnings", []))
        + list(coverage.get("warnings", []))
        + list(layout.get("warnings", [])),
        "raw_text_printed": False,
        "private_text_saved": False,
    }


def build_private_ratecon_layout_diagnostics_report(
    directory=DEFAULT_PRIVATE_RATECON_DIR,
    limit=DEFAULT_LIMIT,
    extractor=extract_pdf_text_local,
):
    pdf_files = list_private_pdf_files(directory)
    safe_limit = _safe_limit(limit)
    results = []

    for index, path in enumerate(pdf_files[:safe_limit], start=1):
        label = f"RATECON_{index:03d}"
        extraction = extractor(path)

        if extraction.get("extraction_status") == TEXT_EXTRACTED:
            text = extraction.get("text", "")
            coverage = build_ratecon_parser_coverage_report(text)
            layout = detect_ratecon_layout_shapes(text)
        else:
            coverage = _empty_coverage()
            layout = _empty_shapes()

        results.append(_safe_summary(label, extraction, coverage, layout))

    return {
        "directory": str(Path(directory)),
        "total_pdf_files": len(pdf_files),
        "processed_count": len(results),
        "limit": safe_limit,
        "results": results,
        "privacy_warning": DRY_RUN_WARNING,
        "raw_text_printed": False,
        "private_text_saved": False,
    }


def _format_count_map(values):
    if not values:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(values.items()))


def _format_list(values):
    if not values:
        return "none"
    return ", ".join(str(value) for value in values)


def _format_shapes(shapes_by_category):
    if not shapes_by_category:
        return ["  sanitized_shapes: none"]

    lines = ["  sanitized_shapes:"]

    for category, shapes in sorted(shapes_by_category.items()):
        shape_text = "; ".join(
            f"{shape['shape']} ({shape['position_group']})"
            for shape in shapes
        )
        lines.append(f"    {category}: {shape_text}")

    return lines


def format_private_ratecon_layout_diagnostics_report(report):
    lines = [
        "PRIVATE RATECON REDACTED LAYOUT DIAGNOSTICS",
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
                f"  signal_counts: {_format_count_map(item['signal_counts'])}",
                f"  shape_counts_by_category: {_format_count_map(item['shape_counts_by_category'])}",
                f"  suspected_parser_gap_fields: {_format_list(item['suspected_parser_gap_fields'])}",
                f"  warnings: {_format_list(item['warnings'])}",
            ]
        )
        lines.extend(_format_shapes(item["shapes_by_category"]))

    if not report["results"]:
        lines.append("- none")

    lines.append("")
    lines.append("No raw extracted text is printed or saved.")
    lines.append("Share only placeholders, counts, categories, and generic warnings.")

    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Local-only redacted RateCon layout-shape diagnostics."
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
        help="Maximum number of private PDFs to inspect.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print safe JSON diagnostics without raw extracted text.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = build_private_ratecon_layout_diagnostics_report(
        directory=args.directory,
        limit=args.limit,
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_private_ratecon_layout_diagnostics_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
