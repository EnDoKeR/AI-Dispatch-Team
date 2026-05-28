from pathlib import Path

from app.load_intake.parser import parse_ratecon
from app.load_intake.sheet_writer import append_load

RATECON_FOLDER = "data/ratecons"
TRACK_FILE = "data/imported_loads.txt"


def get_imported():
    try:
        with open(TRACK_FILE, "r") as file:
            return set(file.read().splitlines())
    except:
        return set()


def save_imported(file_name):
    with open(TRACK_FILE, "a") as file:
        file.write(file_name + "\n")


def import_all_ratecons():
    imported_files = get_imported()
    folder = Path(RATECON_FOLDER)

    imported = 0
    skipped = 0

    for pdf in folder.glob("*.pdf"):
        if pdf.name in imported_files:
            print(f"SKIPPED: {pdf.name}")
            skipped += 1
            continue

        print(f"\nIMPORTING: {pdf.name}")

        load = parse_ratecon(str(pdf))
        append_load(load)

        save_imported(pdf.name)
        imported += 1

    print("\n===== SUMMARY =====")
    print(f"Imported: {imported}")
    print(f"Skipped: {skipped}")
