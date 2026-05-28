import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CREDS_FILE = "data/credentials/google_credentials.json"
SPREADSHEET_ID = "10b3JvejGgRFz2nVtmVbea-DWIryi9rQHeYBqxftycug"
SHEET_NAME = "Sheet1"


def append_load(load):
    row = [
        "TEST-RATECON",
        load.booked_at,
        load.source,
        load.why_booked,
        load.why_note,
        load.next_plan,
        load.next_note,
        load.outcome,
        load.outcome_note,
        load.broker,
        load.pickup,
        load.pickup_date,
        load.delivery,
        load.delivery_date,
        load.load_no,
        load.carrier,
        load.trailer_type,
        load.commodity,
        load.total_weight,
        load.final_rate,
        load.loaded_miles,
        load.rpm,
        load.zone,
        load.zone_score,
        load.broker_score,
        load.broker_status,
        load.book,
        load.rpm_score,
        load.final_score,
        load.final_decision,
        load.reload_score,
        load.reload_status,
        load.adjusted_score,
        load.adjusted_decision,
        "TRUE",
        "Imported through Load object",
    ]

    row = [str(value) for value in row]

    credentials = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=SCOPES,
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(SHEET_NAME)

    worksheet.insert_row(row, 2)

    print("Load written to Google Sheet вњ…")
