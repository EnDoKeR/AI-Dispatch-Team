"""Deprecated RateCon-to-Google-Sheets prototype.

This script predates the current document AI candidate/template/resolver flow.
It is intentionally blocked by default because it reads a PDF, extracts fields
with direct regexes, and can write to Google Sheets. It is not an official
RateCon extraction path and must not be used for production extraction.
"""

import argparse
import re


PDF_PATH = r"data/ratecons/test_ratecon.pdf"
CREDS_FILE = "data/credentials/google_credentials.json"

SPREADSHEET_ID = "10b3JvejGgRFz2nVtmVbea-DWIryi9rQHeYBqxftycug"
SHEET_NAME = "Sheet1"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

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
            full_text += text + "\n"

    return full_text


def extract(pattern, text):
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def build_legacy_load_from_text(text):
    return {
        "truck": "TEST-RATECON",
        "broker": extract(r"TRUCKLOAD RATE CONFIRMATION\s*(.*?)\s*440", text),
        "pickup_city_state": extract(
            r"Shipper Information:.*?Address:.*?\n([A-Za-z\s]+,\s*[A-Z]{2}\s*[0-9]{5})",
            text,
        ),
        "pickup_date": extract(r"Pick Up\s*Time:\s*([0-9\/]+)", text),
        "delivery_city_state": extract(
            r"Consignee Information:.*?Address:.*?\n([A-Za-z\s]+,\s*[A-Z]{2}\s*[0-9]{5})",
            text,
        ),
        "delivery_date": extract(r"Delivery\s*Time:\s*([0-9\/]+)", text),
        "load_no": extract(r"Load #:\s*([0-9]+)", text),
        "empty_miles": "",
        "loaded_miles": "",
        "rate": extract(r"TOTAL:\s*USD\s*\$([0-9,\.]+)", text),
        "factoring": "TRUE",
        "notes": "Imported from rate confirmation PDF",
        "mc": "",
    }


def build_legacy_sheet_row(load):
    return [
        load["truck"],
        load["broker"],
        load["pickup_city_state"],
        load["pickup_date"],
        load["delivery_city_state"],
        load["delivery_date"],
        load["load_no"],
        load["empty_miles"],
        load["loaded_miles"],
        load["rate"],
        load["factoring"],
        load["notes"],
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        load["mc"],
    ]


def append_legacy_sheet_row(row, creds_file, spreadsheet_id, sheet_name):
    import gspread
    from google.oauth2.service_account import Credentials

    credentials = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    worksheet.append_row(row)


def run_legacy_import(
    pdf_path=PDF_PATH,
    creds_file=CREDS_FILE,
    spreadsheet_id=SPREADSHEET_ID,
    sheet_name=SHEET_NAME,
):
    text = read_pdf_text(pdf_path)
    load = build_legacy_load_from_text(text)
    row = build_legacy_sheet_row(load)
    append_legacy_sheet_row(row, creds_file, spreadsheet_id, sheet_name)
    return {
        "row_written": True,
        "extracted_values_printed": False,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Deprecated legacy RateCon PDF to Google Sheets prototype."
    )
    parser.add_argument("--pdf-path", default=PDF_PATH)
    parser.add_argument("--creds-file", default=CREDS_FILE)
    parser.add_argument("--spreadsheet-id", default=SPREADSHEET_ID)
    parser.add_argument("--sheet-name", default=SHEET_NAME)
    parser.add_argument(
        "--allow-legacy-google-sheet-write",
        action="store_true",
        help=(
            "Explicitly allow the deprecated Google Sheets write. "
            "This is not the official RateCon extraction path."
        ),
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    print(DEPRECATION_MESSAGE)

    if not args.allow_legacy_google_sheet_write:
        print("No PDF was read and no Google Sheet was written.")
        print("Use fake candidate/template/resolver tooling for extraction development.")
        return 2

    result = run_legacy_import(
        pdf_path=args.pdf_path,
        creds_file=args.creds_file,
        spreadsheet_id=args.spreadsheet_id,
        sheet_name=args.sheet_name,
    )
    print("Legacy Google Sheets write completed. Extracted values were not printed.")
    return 0 if result["row_written"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
