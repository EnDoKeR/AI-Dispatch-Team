from pypdf import PdfReader
import re

PDF_PATH = r"data/ratecons/test_ratecon.pdf"

reader = PdfReader(PDF_PATH)

full_text = ""

for page in reader.pages:
    text = page.extract_text()

    if text:
        full_text += text


def extract(pattern):
    match = re.search(pattern, full_text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return ""


load = {
    "broker": extract(r"TRUCKLOAD RATE CONFIRMATION\s*(.*?)\s*440"),
    "load_no": extract(r"Load #:\s*([0-9]+)"),
    "pickup_date": extract(r"Pick Up\s*Time:\s*([0-9\/]+)"),
    "delivery_date": extract(r"Delivery\s*Time:\s*([0-9\/]+)"),
    "rate": extract(r"Rate:\s*USD\s*\$([0-9,\.]+)"),
    "total": extract(r"TOTAL:\s*USD\s*\$([0-9,\.]+)"),
    "pickup_city_state": extract(
    r"Shipper Information:.*?Address:.*?\n([A-Za-z\s]+,\s*[A-Z]{2}\s*[0-9]{5})"
),

    "delivery_city_state": extract(
    r"Consignee Information:.*?Address:.*?\n([A-Za-z\s]+,\s*[A-Z]{2}\s*[0-9]{5})"
),
}

print("\n===== PARSED LOAD =====\n")

for key, value in load.items():
    print(f"{key}: {value}")
