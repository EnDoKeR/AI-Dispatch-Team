from app.market_intelligence.sqlite_memory_io import json_text


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
