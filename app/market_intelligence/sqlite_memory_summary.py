from app.market_intelligence.sqlite_memory_connection import (
    SQLITE_DB_FILE,
    connect_db,
)


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
