import re
import gspread
from pypdf import PdfReader
from google.oauth2.service_account import Credentials

PDF_PATH = r"data/ratecons/test_ratecon.pdf"
CREDS_FILE = "data/credentials/google_credentials.json"

SPREADSHEET_ID = "10b3JvejGgRFz2nVtmVbea-DWIryi9rQHeYBqxftycug"
SHEET_NAME = "Sheet1"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def read_pdf_text(pdf_path):
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


text = read_pdf_text(PDF_PATH)

load = {
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

row = [
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
    "", "", "", "", "", "", "", "", "", "",
    load["mc"],
]

credentials = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)

spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet(SHEET_NAME)

worksheet.append_row(row)

print("Rate confirmation imported successfully вњ…")
print(load)
