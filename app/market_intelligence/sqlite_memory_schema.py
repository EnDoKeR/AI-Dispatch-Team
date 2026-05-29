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
