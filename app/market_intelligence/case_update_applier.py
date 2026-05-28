from app.market_intelligence.case_status_engine import (
    apply_status_update_to_case,
    status_update_from_feedback,
)


def apply_feedback_to_case(case_record, feedback_record):
    feedback_type = feedback_record.get("dispatcher_feedback", "")
    document_path = feedback_record.get("document_path", "")

    case_record["updated_at_utc"] = feedback_record.get(
        "timestamp_utc",
        case_record.get("updated_at_utc", ""),
    )

    feedback_item = {
        "timestamp_utc": feedback_record.get("timestamp_utc", ""),
        "feedback": feedback_type,
        "note": feedback_record.get("dispatcher_note", ""),
        "source": feedback_record.get("source", ""),
    }

    case_record["dispatcher_feedback"].append(feedback_item)

    if document_path:
        case_record["ratecons"].append(
            {
                "timestamp_utc": feedback_record.get("timestamp_utc", ""),
                "document_path": document_path,
                "note": feedback_record.get("dispatcher_note", ""),
                "source": feedback_record.get("source", ""),
            }
        )

    status_update = status_update_from_feedback(feedback_type)

    return apply_status_update_to_case(
        case_record=case_record,
        status_update=status_update,
    )


def apply_outbox_to_case(case_record, outbox_record):
    case_record["updated_at_utc"] = outbox_record.get(
        "timestamp_utc",
        case_record.get("updated_at_utc", ""),
    )

    alert_item = {
        "timestamp_utc": outbox_record.get("timestamp_utc", ""),
        "message_type": outbox_record.get("message_type", ""),
        "category": outbox_record.get("category", ""),
        "telegram_message_id": outbox_record.get("telegram_message_id", ""),
        "send_success": outbox_record.get("send_success", False),
        "source": "telegram_outbox",
    }

    case_record["telegram_alerts"].append(alert_item)

    return case_record
