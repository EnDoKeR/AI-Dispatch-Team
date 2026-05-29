import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_intelligence.intake.pdf_text_extraction import extract_pdf_text_local


DEFAULT_PRIVATE_RATECON_DIR = Path("data/private_ratecons/originals")
DEFAULT_LIMIT = 3
DRY_RUN_WARNING = (
    "DRY RUN ONLY - private PDF extraction inventory, no raw text printed or saved"
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


def _safe_result(label, extraction):
    return {
        "label": label,
        "extraction_status": extraction.get("extraction_status", ""),
        "extractor_name": extraction.get("extractor_name", ""),
        "page_count": extraction.get("page_count", 0),
        "char_count": extraction.get("char_count", 0),
        "warnings": list(extraction.get("warnings", [])),
        "private_text_saved": False,
    }


def build_private_pdf_extraction_inventory(
    directory=DEFAULT_PRIVATE_RATECON_DIR,
    limit=DEFAULT_LIMIT,
    extractor=extract_pdf_text_local,
):
    pdf_files = list_private_pdf_files(directory)
    safe_limit = _safe_limit(limit)
    results = []

    for index, path in enumerate(pdf_files[:safe_limit], start=1):
        extraction = extractor(path)
        results.append(_safe_result(f"RATECON_{index:03d}", extraction))

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


def format_warning_list(warnings):
    if not warnings:
        return "none"
    return ", ".join(str(warning) for warning in warnings)


def format_private_pdf_extraction_inventory(report):
    lines = [
        "PRIVATE RATECON PDF EXTRACTION INVENTORY",
        DRY_RUN_WARNING,
        f"Directory: {report['directory']}",
        f"Total PDF files: {report['total_pdf_files']}",
        f"Processed PDF files: {report['processed_count']}",
        f"Limit: {report['limit']}",
        "Results:",
    ]

    for item in report["results"]:
        lines.append(
            "- {label}: status={status}; extractor={extractor}; pages={pages}; chars={chars}; warnings={warnings}".format(
                label=item["label"],
                status=item["extraction_status"],
                extractor=item["extractor_name"] or "none",
                pages=item["page_count"],
                chars=item["char_count"],
                warnings=format_warning_list(item["warnings"]),
            )
        )

    if not report["results"]:
        lines.append("- none")

    lines.append("")
    lines.append("No raw extracted text is printed or saved.")
    lines.append("Do not commit private PDFs, extracted text, or local dry-run outputs.")

    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Local-only private RateCon PDF extraction inventory."
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
        help="Print safe JSON metadata without raw extracted text.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = build_private_pdf_extraction_inventory(
        directory=args.directory,
        limit=args.limit,
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_private_pdf_extraction_inventory(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
