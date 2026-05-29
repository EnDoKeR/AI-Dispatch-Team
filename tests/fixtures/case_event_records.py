SYNTHETIC_CASE_EVENT_RECORDS = [
    {
        "case_id": "CASE-SYN-1",
        "event_type": "AI_DECISION_CREATED",
        "timestamp_utc": "2026-05-29T10:00:00Z",
        "source": "synthetic_decision",
        "payload": {
            "decision": "MATCH",
            "category": "LOAD OPPORTUNITY",
            "reference_id": "SYN-EVENT-REF-1",
        },
    },
    {
        "case_id": "CASE-SYN-1",
        "event_type": "TELEGRAM_ALERT_SENT",
        "timestamp_utc": "2026-05-29T10:01:00Z",
        "source": "synthetic_outbox",
        "payload": {
            "message_type": "LOAD_OPPORTUNITY",
            "reference_id": "SYN-EVENT-REF-1",
        },
    },
    {
        "case_id": "CASE-SYN-1",
        "event_type": "DISPATCHER_FEEDBACK_ADDED",
        "timestamp_utc": "2026-05-29T10:04:00Z",
        "source": "synthetic_feedback",
        "payload": {
            "feedback": "CALLING",
            "note": "Synthetic dispatcher note.",
        },
    },
    {
        "case_id": "CASE-SYN-1",
        "event_type": "RATECON_RECEIVED",
        "timestamp_utc": "2026-05-29T10:20:00Z",
        "source": "synthetic_document",
        "payload": {
            "document_path": "synthetic/private/not-real.pdf",
        },
    },
    {
        "case_id": "",
        "event_type": "MARKET_SNAPSHOT_SENT",
        "timestamp_utc": "2026-05-29T10:30:00Z",
        "source": "synthetic_reporting",
        "payload": {
            "driver_name": "Synthetic Driver",
            "market_activity": "NORMAL_MARKET",
        },
    },
    {
        "case_id": "CASE-SYN-WATCH-1",
        "event_type": "RELOAD_WATCH_STARTED",
        "timestamp_utc": "2026-05-29T10:40:00Z",
        "source": "synthetic_reload_watch",
        "payload": {
            "watch_id": "WATCH-SYN-1",
            "parent_reference_id": "SYN-EVENT-REF-1",
        },
    },
    {
        "case_id": "CASE-SYN-UNKNOWN-1",
        "event_type": "UNCLASSIFIED_SYNTHETIC_EVENT",
        "timestamp_utc": "2026-05-29T10:45:00Z",
        "source": "synthetic_unknown",
        "payload": {
            "note": "Used to verify unknown event reporting.",
        },
    },
]
