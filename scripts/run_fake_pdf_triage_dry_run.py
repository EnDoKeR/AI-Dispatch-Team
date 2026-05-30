"""Run fake/anonymized PDF triage dry-run summaries."""

import argparse
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.document_ai.pdf_triage import triage_pdf  # noqa: E402
from tests.fixtures.document_ai.pdf_triage.fake_pdf_factory import (  # noqa: E402
    write_fake_empty_text_pdf,
    write_fake_invalid_pdf,
    write_fake_text_pdf,
)


DRY_RUN_WARNING = "DRY RUN ONLY - fake PDF triage, no private documents processed"


def create_generated_fixture_dir(directory):
    write_fake_text_pdf(directory)
    write_fake_empty_text_pdf(directory)
    write_fake_invalid_pdf(directory)
    return Path(directory)


def safe_summary(path, triage_result):
    return {
        "file_name": Path(path).name,
        "page_count": triage_result.get("page_count", 0),
        "char_count": triage_result.get("char_count", 0),
        "chars_per_page": triage_result.get("chars_per_page", 0),
        "has_text_layer": triage_result.get("has_text_layer", False),
        "likely_image_based": triage_result.get("likely_image_based", False),
        "mixed_pdf": triage_result.get("mixed_pdf", False),
        "recommended_route": triage_result.get("recommended_route", ""),
        "warnings": triage_result.get("warnings", []),
    }


def pdf_files(input_dir):
    path = Path(input_dir)

    if not path.exists() or not path.is_dir():
        return []

    return sorted(path.glob("*.pdf"))


def build_fake_pdf_triage_report(input_dir=None):
    if input_dir:
        fixture_dir = Path(input_dir)
        temp_dir = None
    else:
        temp_dir = tempfile.TemporaryDirectory()
        fixture_dir = create_generated_fixture_dir(temp_dir.name)

    try:
        summaries = [
            safe_summary(path, triage_pdf(path, document_id=f"FAKE-DOC-{index:03d}"))
            for index, path in enumerate(pdf_files(fixture_dir), start=1)
        ]

        return {
            "fixture_dir": str(fixture_dir),
            "total_files": len(summaries),
            "summaries": summaries,
            "dry_run_only": True,
            "private_documents_processed": False,
        }
    finally:
        if temp_dir:
            temp_dir.cleanup()


def print_report(report):
    print("FAKE PDF TRIAGE DRY RUN")
    print(f"total_files: {report['total_files']}")

    for item in report["summaries"]:
        print("")
        print(item["file_name"])
        print(f"  page_count: {item['page_count']}")
        print(f"  char_count: {item['char_count']}")
        print(f"  chars_per_page: {item['chars_per_page']}")
        print(f"  has_text_layer: {item['has_text_layer']}")
        print(f"  likely_image_based: {item['likely_image_based']}")
        print(f"  mixed_pdf: {item['mixed_pdf']}")
        print(f"  recommended_route: {item['recommended_route']}")
        print(f"  warnings: {', '.join(item['warnings']) if item['warnings'] else 'none'}")

    print("")
    print(DRY_RUN_WARNING)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run fake PDF triage dry-run.")
    parser.add_argument(
        "--input-dir",
        default="",
        help="Optional fake fixture directory. Defaults to generated temp fixtures.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path for safe summary JSON output.",
    )
    args = parser.parse_args(argv)

    report = build_fake_pdf_triage_report(input_dir=args.input_dir or None)
    print_report(report)

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return report


if __name__ == "__main__":
    main()
