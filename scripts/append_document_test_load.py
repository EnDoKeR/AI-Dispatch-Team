import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDS_FILE = "data/credentials/google_credentials.json"

SPREADSHEET_ID = "10b3JvejGgRFz2nVtmVbea-DWIryi9rQHeYBqxftycug"
SHEET_NAME = "Sheet1"

test_load = {
    "truck": "TEST-001",
    "broker": "Test Broker",
    "pickup_city": "Chicago",
    "pickup_state": "IL",
    "pickup_date": "05/23/2026",
    "delivery_city": "Dallas",
    "delivery_state": "TX",
    "delivery_date": "05/25/2026",
    "load_no": "TEST123",
    "empty_miles": 50,
    "loaded_miles": 925,
    "rate": 3000,
    "factoring": "TRUE",
    "notes": "Test load from Python",
    "mc": "123456",
}

row = [
    test_load["truck"],
    test_load["broker"],
    f'{test_load["pickup_city"]}, {test_load["pickup_state"]}',
    test_load["pickup_date"],
    f'{test_load["delivery_city"]}, {test_load["delivery_state"]}',
    test_load["delivery_date"],
    test_load["load_no"],
    test_load["empty_miles"],
    test_load["loaded_miles"],
    test_load["rate"],
    test_load["factoring"],
    test_load["notes"],
    "", "", "", "", "", "", "", "", "", "",
    test_load["mc"],
]

credentials = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)

spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet(SHEET_NAME)

worksheet.append_row(row)

print("Test load added successfully ✅")