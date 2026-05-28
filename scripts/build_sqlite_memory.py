import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.sqlite_memory import (
    SQLITE_DB_FILE,
    print_sqlite_summary,
    rebuild_sqlite_memory,
)


DISPATCH_CASES_FILE = Path("data/dispatch_cases.jsonl")
DISPATCH_EVENTS_FILE = Path("data/dispatch_events.jsonl")


def main():
    if not DISPATCH_CASES_FILE.exists():
        print(f"Missing file: {DISPATCH_CASES_FILE}")
        print("Run first:")
        print("py scripts/build_dispatch_cases.py")
        return

    if not DISPATCH_EVENTS_FILE.exists():
        print(f"Missing file: {DISPATCH_EVENTS_FILE}")
        print("Run first:")
        print("py scripts/build_dispatch_cases.py")
        return

    result = rebuild_sqlite_memory(
        cases_file=DISPATCH_CASES_FILE,
        events_file=DISPATCH_EVENTS_FILE,
        db_path=SQLITE_DB_FILE,
    )

    print("SQLite dispatch memory rebuilt.")
    print(f"Cases loaded: {result['cases_loaded']}")
    print(f"Events loaded: {result['events_loaded']}")
    print(f"Saved to: {result['db_path']}")

    print_sqlite_summary(SQLITE_DB_FILE)


if __name__ == "__main__":
    main()
