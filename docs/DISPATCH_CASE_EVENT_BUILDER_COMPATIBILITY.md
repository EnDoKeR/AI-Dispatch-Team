# DispatchCase Event Builder Compatibility Audit

This audit compares current `case_event_builder.py` runtime event payloads with the newer Event Timeline foundation helpers:

- `case_event_types.py`
- `case_event_payload.py`
- `case_event_report.py`

It does not change runtime behavior, replace builders, write new events, or wire DecisionResult into DispatchCase.

## Current Runtime Builder

Current runtime case events are built by:

```text
app/market_intelligence/case_event_builder.py
```

Those builders call:

```text
app/market_intelligence/event_logger.py::build_dispatch_event(...)
```

Current runtime event envelope:

```python
{
    "event_id": "...",
    "case_id": "...",
    "event_type": "...",
    "timestamp_utc": "...",
    "driver_name": "...",
    "load_id": "...",
    "reference_id": "...",
    "source": "...",
    "payload": {...},
}
```

This shape must remain stable until an explicit migration is accepted.

## Event Types Emitted Today

`case_event_builder.py` currently emits or can emit:

| Builder | Event Type | Current Runtime Use | Taxonomy Group |
| --- | --- | --- | --- |
| `build_ai_decision_created_event(...)` | `AI_DECISION_CREATED` | decision records create load-level case events | `load_level` |
| `build_telegram_alert_sent_event(...)` | `TELEGRAM_ALERT_SENT` | load-level Telegram outbox records create alert events | `load_level` |
| `build_dispatcher_feedback_added_event(...)` | `DISPATCHER_FEEDBACK_ADDED` | dispatcher feedback creates feedback events | `load_level` |
| `build_ratecon_received_event(...)` | `RATECON_RECEIVED` | feedback with document path creates RateCon event | `load_level` |
| `build_load_board_simulation_event(...)` | `LOAD_APPEARED` | currently attached by DispatchCase builder when matching simulation event appears | `load_board_simulation` |
| `build_load_board_simulation_event(...)` | `LOAD_UPDATED` | builder supports payload shape, not currently attached by `build_cases_and_events(...)` | `load_board_simulation` |
| `build_load_board_simulation_event(...)` | `LOAD_REMOVED` | builder supports payload shape, not currently attached by `build_cases_and_events(...)` | `load_board_simulation` |

All current builder-emitted event types are known in `case_event_types.py`.

## Current Payload Fields

### `AI_DECISION_CREATED`

Source:

```text
decision_logger
```

Payload fields:

- `decision`
- `category`
- `score`
- `reasons`
- `pickup`
- `delivery`
- `rate`

Compatibility note:

- This is the current load-level AI decision event.
- A future nested `DecisionResult` may be added only after a separate behavior-change block.
- Existing flat fields must remain stable.

### `TELEGRAM_ALERT_SENT`

Source:

```text
telegram_outbox
```

Payload fields:

- `message_type`
- `category`
- `telegram_message_id`
- `pickup`
- `delivery`
- `rate`
- `broker`
- `broker_mc`
- `reference_id`

Compatibility note:

- This remains load-level only for eligible outbox types.
- `MARKET_SNAPSHOT` and `SEARCH_HEALTH_CHECK` are excluded from load-level DispatchCase outbox handling.

### `DISPATCHER_FEEDBACK_ADDED`

Source:

```text
dispatcher_feedback` or provided feedback source
```

Payload fields:

- `feedback`
- `note`
- `document_path`

Compatibility note:

- This is load-level feedback.
- It may coexist with a separate `RATECON_RECEIVED` event when `document_path` is present.

### `RATECON_RECEIVED`

Source:

```text
telegram_document` or provided feedback source
```

Payload fields:

- `document_path`
- `note`

Compatibility note:

- This is currently the only RateCon/document event emitted by runtime DispatchCase flow.
- It does not parse the RateCon and does not create an intake record.

### `LOAD_APPEARED`

Source:

```text
load_board_simulation
```

Payload fields:

- `simulation_step`
- `event_time`
- `simulation_load_id`
- `pickup`
- `delivery`
- `rate`
- `broker`
- `broker_mc`
- `reference_id`

Compatibility note:

- `dispatch_case.build_cases_and_events(...)` currently attaches simulation events only when `event_type == "LOAD_APPEARED"` and it matches an existing case.

### `LOAD_UPDATED`

Source:

```text
load_board_simulation
```

Payload fields:

- `simulation_step`
- `event_time`
- `simulation_load_id`
- `updates`

Compatibility note:

- Builder supports this payload shape.
- Runtime DispatchCase flow does not currently attach it.

### `LOAD_REMOVED`

Source:

```text
load_board_simulation
```

Payload fields:

- `simulation_step`
- `event_time`
- `simulation_load_id`
- `reason`

Compatibility note:

- Builder supports this payload shape.
- Runtime DispatchCase flow does not currently attach it.

## Comparison With Base Payload Helper

The new base helper returns:

```python
{
    "event_type": "...",
    "event_group": "...",
    "case_id": "...",
    "timestamp_utc": "...",
    "source": "...",
    "details": {...},
    "related_ids": {...},
}
```

Current builder events already provide compatible core fields:

- `event_type`
- `case_id`
- `timestamp_utc`
- `source`

Current builder events also provide runtime-specific fields:

- `event_id`
- `driver_name`
- `load_id`
- `reference_id`
- `payload`

Base payload fields not present in current builder output:

- `event_group`
- `details`
- `related_ids`

Current builder fields not present in the base payload helper:

- `event_id`
- `driver_name`
- `load_id`
- `reference_id`
- `payload`

Compatibility policy:

- Do not replace `payload` with `details` yet.
- Do not remove `event_id`, `driver_name`, `load_id`, or `reference_id`.
- Future wrappers may add `event_group` or a nested base payload view, but only after tests protect current shape.

## What Must Remain Stable

These current behaviors should not change in a compatibility block:

- event type strings
- event source values
- event envelope keys
- payload field names
- event ID generation
- dedupe key behavior in `dedupe_dispatch_events(...)`
- `LOAD_OPPORTUNITY` and `REVIEW_ONCE` outbox case eligibility
- `MARKET_SNAPSHOT` and `SEARCH_HEALTH_CHECK` exclusion from load-level cases
- simulation runtime behavior that attaches only `LOAD_APPEARED`

## What Should Not Be Changed Yet

Do not yet:

- replace `case_event_builder.py`
- route builders through `case_event_payload.py`
- write `DecisionResult` into `AI_DECISION_CREATED`
- add new runtime event types
- add intake-to-case linking
- add reload-chain case events
- add reload-watch live case events
- read/write new storage
- alter Telegram, market snapshot, or load selection behavior

## Tests Needed Before Migration

Before any migration, add tests that prove:

1. all builder-emitted event types are known in `case_event_types.py`
2. builder outputs normalize through the event taxonomy
3. current load-level events map to `load_level`
4. simulation events map to `load_board_simulation`
5. current event payloads remain JSON-serializable
6. current event envelope keys remain stable
7. missing base payload fields are reported, not treated as runtime errors
8. `dedupe_dispatch_events(...)` behavior remains unchanged
9. `MARKET_SNAPSHOT` and `SEARCH_HEALTH_CHECK` stay reporting-only in DispatchCase flow
10. future `DecisionResult` timeline previews remain report-only until explicitly wired

## Recommended Next Step

Add focused compatibility tests and a read-only payload shape report helper.

Do not migrate event builders yet.
