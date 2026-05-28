import json
import sqlite3
from pathlib import Path


SQLITE_DB_FILE = Path("data/dispatch_memory.db")


def connect_db(db_path=SQLITE_DB_FILE):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    return connection


def load_jsonl(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        return []

    records = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def json_text(value):
    return json.dumps(value, ensure_ascii=False)


def create_tables(connection):
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dispatch_cases (
            case_id TEXT PRIMARY KEY,
            created_at_utc TEXT,
            updated_at_utc TEXT,
            status TEXT,
            final_outcome TEXT,

            driver_name TEXT,
            driver_location TEXT,
            driver_equipment TEXT,

            load_id TEXT,
            reference_id TEXT,
            pickup TEXT,
            delivery TEXT,
            rate TEXT,
            loaded_miles REAL,
            empty_miles REAL,
            total_miles REAL,
            total_rpm REAL,
            weight REAL,
            posted_trailer_type TEXT,
            commodity TEXT,

            broker_name TEXT,
            broker_mc TEXT,
            broker_contact TEXT,
            broker_status TEXT,
            credit_score TEXT,
            days_to_pay TEXT,

            ai_decision TEXT,
            ai_category TEXT,
            ai_score REAL,
            ai_priority TEXT,
            ai_suggested_action TEXT,
            ai_reasons_json TEXT,

            telegram_alert_count INTEGER,
            dispatcher_feedback_count INTEGER,
            ratecon_count INTEGER,
            events_count INTEGER,

            raw_json TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dispatch_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT,
            event_type TEXT,
            timestamp_utc TEXT,
            driver_name TEXT,
            load_id TEXT,
            reference_id TEXT,
            source TEXT,
            payload_json TEXT,
            raw_json TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dispatcher_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            timestamp_utc TEXT,
            feedback TEXT,
            note TEXT,
            source TEXT,
            raw_json TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS telegram_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            timestamp_utc TEXT,
            message_type TEXT,
            category TEXT,
            telegram_message_id TEXT,
            send_success INTEGER,
            source TEXT,
            raw_json TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ratecons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            timestamp_utc TEXT,
            document_path TEXT,
            note TEXT,
            source TEXT,
            raw_json TEXT
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cases_driver ON dispatch_cases(driver_name)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cases_status ON dispatch_cases(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cases_reference ON dispatch_cases(reference_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cases_broker_mc ON dispatch_cases(broker_mc)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_case ON dispatch_events(case_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_type ON dispatch_events(event_type)"
    )

    connection.commit()


def clear_tables(connection):
    cursor = connection.cursor()

    cursor.execute("DELETE FROM ratecons")
    cursor.execute("DELETE FROM telegram_alerts")
    cursor.execute("DELETE FROM dispatcher_feedback")
    cursor.execute("DELETE FROM dispatch_events")
    cursor.execute("DELETE FROM dispatch_cases")

    connection.commit()


def insert_case(connection, case):
    cursor = connection.cursor()

    ai_decision = case.get("ai_decision", {}) or {}

    cursor.execute(
        """
        INSERT OR REPLACE INTO dispatch_cases (
            case_id,
            created_at_utc,
            updated_at_utc,
            status,
            final_outcome,

            driver_name,
            driver_location,
            driver_equipment,

            load_id,
            reference_id,
            pickup,
            delivery,
            rate,
            loaded_miles,
            empty_miles,
            total_miles,
            total_rpm,
            weight,
            posted_trailer_type,
            commodity,

            broker_name,
            broker_mc,
            broker_contact,
            broker_status,
            credit_score,
            days_to_pay,

            ai_decision,
            ai_category,
            ai_score,
            ai_priority,
            ai_suggested_action,
            ai_reasons_json,

            telegram_alert_count,
            dispatcher_feedback_count,
            ratecon_count,
            events_count,

            raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case.get("case_id", ""),
            case.get("created_at_utc", ""),
            case.get("updated_at_utc", ""),
            case.get("status", ""),
            case.get("final_outcome", ""),

            case.get("driver_name", ""),
            case.get("driver_location", ""),
            case.get("driver_equipment", ""),

            case.get("load_id", ""),
            case.get("reference_id", ""),
            case.get("pickup", ""),
            case.get("delivery", ""),
            str(case.get("rate", "")),
            case.get("loaded_miles", 0),
            case.get("empty_miles", 0),
            case.get("total_miles", 0),
            case.get("total_rpm", 0),
            case.get("weight", 0),
            case.get("posted_trailer_type", ""),
            case.get("commodity", ""),

            case.get("broker_name", ""),
            case.get("broker_mc", ""),
            case.get("broker_contact", ""),
            case.get("broker_status", ""),
            case.get("credit_score", ""),
            case.get("days_to_pay", ""),

            ai_decision.get("decision", ""),
            ai_decision.get("category", ""),
            ai_decision.get("score", 0),
            ai_decision.get("priority", ""),
            ai_decision.get("suggested_action", ""),
            json_text(ai_decision.get("reasons", [])),

            len(case.get("telegram_alerts", [])),
            len(case.get("dispatcher_feedback", [])),
            len(case.get("ratecons", [])),
            case.get("events_count", 0),

            json_text(case),
        ),
    )


def insert_event(connection, event):
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO dispatch_events (
            event_id,
            case_id,
            event_type,
            timestamp_utc,
            driver_name,
            load_id,
            reference_id,
            source,
            payload_json,
            raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.get("event_id", ""),
            event.get("case_id", ""),
            event.get("event_type", ""),
            event.get("timestamp_utc", ""),
            event.get("driver_name", ""),
            event.get("load_id", ""),
            event.get("reference_id", ""),
            event.get("source", ""),
            json_text(event.get("payload", {})),
            json_text(event),
        ),
    )


def insert_case_children(connection, case):
    cursor = connection.cursor()
    case_id = case.get("case_id", "")

    for feedback in case.get("dispatcher_feedback", []):
        cursor.execute(
            """
            INSERT INTO dispatcher_feedback (
                case_id,
                timestamp_utc,
                feedback,
                note,
                source,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                feedback.get("timestamp_utc", ""),
                feedback.get("feedback", ""),
                feedback.get("note", ""),
                feedback.get("source", ""),
                json_text(feedback),
            ),
        )

    for alert in case.get("telegram_alerts", []):
        cursor.execute(
            """
            INSERT INTO telegram_alerts (
                case_id,
                timestamp_utc,
                message_type,
                category,
                telegram_message_id,
                send_success,
                source,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                alert.get("timestamp_utc", ""),
                alert.get("message_type", ""),
                alert.get("category", ""),
                str(alert.get("telegram_message_id", "")),
                1 if alert.get("send_success", False) else 0,
                alert.get("source", ""),
                json_text(alert),
            ),
        )

    for ratecon in case.get("ratecons", []):
        cursor.execute(
            """
            INSERT INTO ratecons (
                case_id,
                timestamp_utc,
                document_path,
                note,
                source,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                ratecon.get("timestamp_utc", ""),
                ratecon.get("document_path", ""),
                ratecon.get("note", ""),
                ratecon.get("source", ""),
                json_text(ratecon),
            ),
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
