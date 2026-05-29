import os


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_CREDS_FILE = "data/credentials/google_credentials.json"
DEFAULT_SHEET_NAME = "Sheet1"


def load_settings():
    return {
        "credentials_file": os.environ.get(
            "GOOGLE_CREDENTIALS_FILE",
            DEFAULT_CREDS_FILE,
        ),
        "spreadsheet_id": os.environ.get("GOOGLE_SPREADSHEET_ID", ""),
        "sheet_name": os.environ.get("GOOGLE_SHEET_NAME", DEFAULT_SHEET_NAME),
    }


def append_load(load, settings=None):
    settings = settings or load_settings()

    if not settings["spreadsheet_id"]:
        print("GOOGLE_SPREADSHEET_ID is missing.")
        return False

    import gspread
    from google.oauth2.service_account import Credentials

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
        settings["credentials_file"],
        scopes=SCOPES,
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(settings["spreadsheet_id"])
    worksheet = spreadsheet.worksheet(settings["sheet_name"])

    worksheet.insert_row(row, 2)

    print("Load written to Google Sheet.")
    return True
