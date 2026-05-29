from app.market_intelligence.sqlite_memory_connection import (
    SQLITE_DB_FILE,
    connect_db,
)
from app.market_intelligence.sqlite_memory_io import (
    json_text,
    load_jsonl,
)
from app.market_intelligence.sqlite_memory_schema import (
    clear_tables,
    create_tables,
)
from app.market_intelligence.sqlite_memory_repository import (
    insert_case,
    insert_case_children,
    insert_event,
)


def rebuild_sqlite_memory(cases_file, events_file, db_path=SQLITE_DB_FILE):
    cases = load_jsonl(cases_file)
    events = load_jsonl(events_file)

    connection = connect_db(db_path)

    create_tables(connection)
    clear_tables(connection)

    for case in cases:
        insert_case(connection, case)
        insert_case_children(connection, case)

    for event in events:
        insert_event(connection, event)

    connection.commit()
    connection.close()

    return {
        "cases_loaded": len(cases),
        "events_loaded": len(events),
        "db_path": str(db_path),
    }


def get_table_count(connection, table_name):
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
    row = cursor.fetchone()

    return row["count"]


def print_sqlite_summary(db_path=SQLITE_DB_FILE):
    connection = connect_db(db_path)

    print("")
    print("SQLite Dispatch Memory Summary")
    print("------------------------------")
    print(f"Database: {db_path}")
    print(f"dispatch_cases: {get_table_count(connection, 'dispatch_cases')}")
    print(f"dispatch_events: {get_table_count(connection, 'dispatch_events')}")
    print(f"dispatcher_feedback: {get_table_count(connection, 'dispatcher_feedback')}")
    print(f"telegram_alerts: {get_table_count(connection, 'telegram_alerts')}")
    print(f"ratecons: {get_table_count(connection, 'ratecons')}")

    connection.close()
