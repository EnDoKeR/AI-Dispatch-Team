"""Deprecated local RateCon PDF regex reader.

This script predates the current document AI candidate/template/resolver flow.
It is intentionally blocked by default because it reads a PDF, extracts fields
with direct regexes, and prints extracted values. It is not an official RateCon
extraction path.
"""

import argparse
import re


PDF_PATH = r"data/ratecons/test_ratecon.pdf"
DEPRECATION_MESSAGE = (
    "DEPRECATED LEGACY PROTOTYPE - do not use for production RateCon extraction. "
    "Use the document_ai candidate/template/resolver flow instead."
)


def read_pdf_text(pdf_path):
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    full_text = ""

    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text

    return full_text


def extract(pattern, full_text):
    match = re.search(pattern, full_text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return ""


def build_legacy_load_from_text(full_text):
    return {
        "broker": extract(r"TRUCKLOAD RATE CONFIRMATION\s*(.*?)\s*440", full_text),
        "load_no": extract(r"Load #:\s*([0-9]+)", full_text),
        "pickup_date": extract(r"Pick Up\s*Time:\s*([0-9\/]+)", full_text),
        "delivery_date": extract(r"Delivery\s*Time:\s*([0-9\/]+)", full_text),
        "rate": extract(r"Rate:\s*USD\s*\$([0-9,\.]+)", full_text),
        "total": extract(r"TOTAL:\s*USD\s*\$([0-9,\.]+)", full_text),
        "pickup_city_state": extract(
            r"Shipper Information:.*?Address:.*?\n([A-Za-z\s]+,\s*[A-Z]{2}\s*[0-9]{5})",
            full_text,
        ),
        "delivery_city_state": extract(
            r"Consignee Information:.*?Address:.*?\n([A-Za-z\s]+,\s*[A-Z]{2}\s*[0-9]{5})",
            full_text,
        ),
    }


def print_legacy_load(load):
    print("\n===== LEGACY PARSED LOAD =====\n")

    for key, value in load.items():
        print(f"{key}: {value}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Deprecated legacy RateCon PDF regex reader."
    )
    parser.add_argument("--pdf-path", default=PDF_PATH)
    parser.add_argument(
        "--allow-legacy-value-print",
        action="store_true",
        help=(
            "Explicitly allow deprecated local value printing. "
            "Do not use with private documents in shared reports."
        ),
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    print(DEPRECATION_MESSAGE)

    if not args.allow_legacy_value_print:
        print("No PDF was read and no extracted values were printed.")
        print("Use fake candidate/template/resolver tooling for extraction development.")
        return 2

    full_text = read_pdf_text(args.pdf_path)
    print_legacy_load(build_legacy_load_from_text(full_text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
