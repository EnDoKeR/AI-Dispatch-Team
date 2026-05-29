from app.market_intelligence.sqlite_memory_connection import (
    SQLITE_DB_FILE,
    connect_db,
)
from app.market_intelligence.sqlite_memory_io import load_jsonl
from app.market_intelligence.sqlite_memory_repository import (
    insert_case,
    insert_case_children,
    insert_event,
)
from app.market_intelligence.sqlite_memory_schema import (
    clear_tables,
    create_tables,
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
