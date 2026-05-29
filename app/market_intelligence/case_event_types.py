EVENT_GROUP_LOAD_LEVEL = "load_level"
EVENT_GROUP_SEARCH_REPORTING = "search_reporting"
EVENT_GROUP_RELOAD_WATCH = "reload_watch"
EVENT_GROUP_INTAKE_DOCUMENT = "intake_document"
EVENT_GROUP_ACCOUNTING_FACTORING = "accounting_factoring"
EVENT_GROUP_LOAD_BOARD_SIMULATION = "load_board_simulation"
EVENT_GROUP_UNKNOWN = "unknown"


AI_DECISION_CREATED = "AI_DECISION_CREATED"
TELEGRAM_ALERT_SENT = "TELEGRAM_ALERT_SENT"
DISPATCHER_FEEDBACK_ADDED = "DISPATCHER_FEEDBACK_ADDED"
RATECON_RECEIVED = "RATECON_RECEIVED"
RATECON_PARSED = "RATECON_PARSED"
DRIVER_DISPATCHED = "DRIVER_DISPATCHED"
PICKUP_ARRIVED = "PICKUP_ARRIVED"
PICKUP_DEPARTED = "PICKUP_DEPARTED"
DELIVERY_ARRIVED = "DELIVERY_ARRIVED"
DELIVERY_DEPARTED = "DELIVERY_DEPARTED"
POD_RECEIVED = "POD_RECEIVED"
BOL_RECEIVED = "BOL_RECEIVED"

MARKET_SNAPSHOT_SENT = "MARKET_SNAPSHOT_SENT"
SEARCH_HEALTH_CHECK_SENT = "SEARCH_HEALTH_CHECK_SENT"
NO_CLEAN_MATCHES_FOUND = "NO_CLEAN_MATCHES_FOUND"

RELOAD_WATCH_STARTED = "RELOAD_WATCH_STARTED"
RELOAD_WATCH_STATUS_DUE = "RELOAD_WATCH_STATUS_DUE"
PARENT_LOAD_UPDATED = "PARENT_LOAD_UPDATED"
CLEAN_EXIT_FOUND = "CLEAN_EXIT_FOUND"
STRONG_CHAIN_FOUND = "STRONG_CHAIN_FOUND"

INTAKE_RECORD_CREATED = "INTAKE_RECORD_CREATED"
INTAKE_MISSING_FIELDS = "INTAKE_MISSING_FIELDS"
DOCUMENT_RECEIVED = "DOCUMENT_RECEIVED"
DOCUMENT_LINKED = "DOCUMENT_LINKED"

FACTORING_PACKET_READY = "FACTORING_PACKET_READY"
SENT_TO_FACTORING = "SENT_TO_FACTORING"
PAID = "PAID"
ACCOUNTING_ISSUE_OPENED = "ACCOUNTING_ISSUE_OPENED"
ACCOUNTING_ISSUE_CLOSED = "ACCOUNTING_ISSUE_CLOSED"

LOAD_APPEARED = "LOAD_APPEARED"
LOAD_UPDATED = "LOAD_UPDATED"
LOAD_REMOVED = "LOAD_REMOVED"


EVENT_TYPES_BY_GROUP = {
    EVENT_GROUP_LOAD_LEVEL: (
        AI_DECISION_CREATED,
        TELEGRAM_ALERT_SENT,
        DISPATCHER_FEEDBACK_ADDED,
        RATECON_RECEIVED,
        RATECON_PARSED,
        DRIVER_DISPATCHED,
        PICKUP_ARRIVED,
        PICKUP_DEPARTED,
        DELIVERY_ARRIVED,
        DELIVERY_DEPARTED,
        POD_RECEIVED,
        BOL_RECEIVED,
    ),
    EVENT_GROUP_SEARCH_REPORTING: (
        MARKET_SNAPSHOT_SENT,
        SEARCH_HEALTH_CHECK_SENT,
        NO_CLEAN_MATCHES_FOUND,
    ),
    EVENT_GROUP_RELOAD_WATCH: (
        RELOAD_WATCH_STARTED,
        RELOAD_WATCH_STATUS_DUE,
        PARENT_LOAD_UPDATED,
        CLEAN_EXIT_FOUND,
        STRONG_CHAIN_FOUND,
    ),
    EVENT_GROUP_INTAKE_DOCUMENT: (
        INTAKE_RECORD_CREATED,
        INTAKE_MISSING_FIELDS,
        DOCUMENT_RECEIVED,
        DOCUMENT_LINKED,
    ),
    EVENT_GROUP_ACCOUNTING_FACTORING: (
        FACTORING_PACKET_READY,
        SENT_TO_FACTORING,
        PAID,
        ACCOUNTING_ISSUE_OPENED,
        ACCOUNTING_ISSUE_CLOSED,
    ),
    EVENT_GROUP_LOAD_BOARD_SIMULATION: (
        LOAD_APPEARED,
        LOAD_UPDATED,
        LOAD_REMOVED,
    ),
}

EVENT_GROUP_BY_TYPE = {
    event_type: group
    for group, event_types in EVENT_TYPES_BY_GROUP.items()
    for event_type in event_types
}

ALL_EVENT_TYPES = tuple(EVENT_GROUP_BY_TYPE.keys())


def normalize_event_type(event_type):
    text = str(event_type or "").strip().upper()

    for old, new in [
        ("-", "_"),
        (" ", "_"),
        ("/", "_"),
    ]:
        text = text.replace(old, new)

    while "__" in text:
        text = text.replace("__", "_")

    return text.strip("_")


def is_known_event_type(event_type):
    return normalize_event_type(event_type) in EVENT_GROUP_BY_TYPE


def event_type_group(event_type):
    return EVENT_GROUP_BY_TYPE.get(
        normalize_event_type(event_type),
        EVENT_GROUP_UNKNOWN,
    )


def event_types_by_group(group):
    normalized_group = str(group or "").strip().lower()

    return list(EVENT_TYPES_BY_GROUP.get(normalized_group, ()))


def event_type_metadata(event_type):
    normalized = normalize_event_type(event_type)

    return {
        "event_type": normalized,
        "event_group": event_type_group(normalized),
        "known": is_known_event_type(normalized),
    }
