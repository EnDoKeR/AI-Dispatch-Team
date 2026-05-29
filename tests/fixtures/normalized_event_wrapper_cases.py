from app.market_intelligence.case_event_types import (
    EVENT_GROUP_LOAD_BOARD_SIMULATION,
    EVENT_GROUP_LOAD_LEVEL,
    EVENT_GROUP_SEARCH_REPORTING,
    EVENT_GROUP_UNKNOWN,
)


NORMALIZED_EVENT_WRAPPER_CASES = [
    {
        "scenario_id": "ai_decision_created_current_style",
        "event": {
            "event_id": "EVT-AI-001",
            "event_type": "AI_DECISION_CREATED",
            "case_id": "CASE-AI-001",
            "timestamp_utc": "2026-05-29T10:00:00Z",
            "source": "synthetic_decision",
            "load_id": "LOAD-AI-001",
            "reference_id": "SYN-AI-001",
            "driver_name": "Synthetic Driver",
            "payload": {
                "decision": "MATCH",
                "category": "LOAD OPPORTUNITY",
            },
        },
        "expected_event_type": "AI_DECISION_CREATED",
        "expected_event_group": EVENT_GROUP_LOAD_LEVEL,
        "expected_warnings": [],
    },
    {
        "scenario_id": "telegram_alert_sent_current_style",
        "event": {
            "event_id": "EVT-TG-001",
            "event_type": "TELEGRAM_ALERT_SENT",
            "case_id": "CASE-TG-001",
            "timestamp_utc": "2026-05-29T10:05:00Z",
            "source": "synthetic_outbox",
            "reference_id": "SYN-TG-001",
            "payload": {
                "message_type": "LOAD_OPPORTUNITY",
                "telegram_message_id": "777",
            },
        },
        "expected_event_type": "TELEGRAM_ALERT_SENT",
        "expected_event_group": EVENT_GROUP_LOAD_LEVEL,
        "expected_warnings": [],
    },
    {
        "scenario_id": "dispatcher_feedback_added_current_style",
        "event": {
            "event_id": "EVT-FB-001",
            "event_type": "DISPATCHER_FEEDBACK_ADDED",
            "case_id": "CASE-FB-001",
            "timestamp_utc": "2026-05-29T10:10:00Z",
            "source": "synthetic_feedback",
            "driver_name": "Synthetic Driver",
            "payload": {
                "dispatcher_feedback": "calling",
                "dispatcher_note": "Synthetic dispatcher note.",
            },
        },
        "expected_event_type": "DISPATCHER_FEEDBACK_ADDED",
        "expected_event_group": EVENT_GROUP_LOAD_LEVEL,
        "expected_warnings": [],
    },
    {
        "scenario_id": "ratecon_received_current_style",
        "event": {
            "event_id": "EVT-RC-001",
            "event_type": "RATECON_RECEIVED",
            "case_id": "CASE-RC-001",
            "timestamp_utc": "2026-05-29T10:20:00Z",
            "source": "synthetic_document",
            "reference_id": "SYN-RC-001",
            "payload": {
                "document_path": "synthetic/not-real-ratecon.pdf",
                "dispatcher_note": "Synthetic RateCon received.",
            },
        },
        "expected_event_type": "RATECON_RECEIVED",
        "expected_event_group": EVENT_GROUP_LOAD_LEVEL,
        "expected_warnings": [],
    },
    {
        "scenario_id": "simulation_load_appeared_current_style",
        "event": {
            "event_id": "EVT-SIM-001",
            "event_type": "LOAD_APPEARED",
            "case_id": "CASE-SIM-001",
            "timestamp_utc": "2026-05-29T10:30:00Z",
            "source": "synthetic_simulation",
            "load_id": "SIM-LOAD-001",
            "reference_id": "SYN-SIM-001",
            "payload": {
                "load": {
                    "pickup": "Austin, TX",
                    "delivery": "Tulsa, OK",
                    "rate": 2400,
                },
            },
        },
        "expected_event_type": "LOAD_APPEARED",
        "expected_event_group": EVENT_GROUP_LOAD_BOARD_SIMULATION,
        "expected_warnings": [],
    },
    {
        "scenario_id": "market_snapshot_sent_reporting_like",
        "event": {
            "event_id": "EVT-MKT-001",
            "event_type": "MARKET_SNAPSHOT_SENT",
            "case_id": "",
            "timestamp_utc": "2026-05-29T10:40:00Z",
            "source": "synthetic_market_report",
            "driver_name": "Synthetic Driver",
            "payload": {
                "market_activity": "WEAK",
                "driver_fit": "WATCH",
            },
        },
        "expected_event_type": "MARKET_SNAPSHOT_SENT",
        "expected_event_group": EVENT_GROUP_SEARCH_REPORTING,
        "expected_warnings": ["missing_case_id"],
    },
    {
        "scenario_id": "missing_case_id",
        "event": {
            "event_id": "EVT-MISSING-001",
            "event_type": "TELEGRAM_ALERT_SENT",
            "timestamp_utc": "2026-05-29T10:50:00Z",
            "source": "synthetic_outbox",
            "reference_id": "SYN-MISSING-001",
            "payload": {
                "message_type": "REVIEW_ONCE",
            },
        },
        "expected_event_type": "TELEGRAM_ALERT_SENT",
        "expected_event_group": EVENT_GROUP_LOAD_LEVEL,
        "expected_warnings": ["missing_case_id"],
    },
    {
        "scenario_id": "unknown_event_type",
        "event": {
            "event_id": "EVT-UNKNOWN-001",
            "event_type": "FUTURE_CUSTOM_EVENT",
            "case_id": "CASE-UNKNOWN-001",
            "timestamp_utc": "2026-05-29T11:00:00Z",
            "source": "synthetic_future",
            "payload": {
                "note": "Synthetic future event.",
            },
        },
        "expected_event_type": "FUTURE_CUSTOM_EVENT",
        "expected_event_group": EVENT_GROUP_UNKNOWN,
        "expected_warnings": ["unknown_event_type"],
    },
]
