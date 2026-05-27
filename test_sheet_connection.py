import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDS_FILE = "data/credentials/google_credentials.json"

SPREADSHEET_ID = "10b3JvejGgRFz2nVtmVbea-DWIryi9rQHeYBqxftycug"
SHEET_NAME = "Sheet1"

credentials = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)

spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet(SHEET_NAME)

test_row = [
    "TEST",
    "AI Dispatch Team",
    "Google Sheets connection works",
]

worksheet.append_row(test_row)

print("Row added successfully ✅")