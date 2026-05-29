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


def append_test_row(settings):
    if not settings["spreadsheet_id"]:
        print("GOOGLE_SPREADSHEET_ID is missing.")
        return False

    import gspread
    from google.oauth2.service_account import Credentials

    credentials = Credentials.from_service_account_file(
        settings["credentials_file"],
        scopes=SCOPES,
    )
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(settings["spreadsheet_id"])
    worksheet = spreadsheet.worksheet(settings["sheet_name"])

    test_row = [
        "TEST",
        "AI Dispatch Team",
        "Google Sheets connection works",
    ]

    worksheet.append_row(test_row)

    print("Row added successfully.")
    return True


def main():
    settings = load_settings()
    return append_test_row(settings)


if __name__ == "__main__":
    main()
