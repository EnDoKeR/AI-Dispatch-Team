# DispatchCase SEARCH_HEALTH_CHECK Policy

Date: 2026-05-29

Scope:

- audit/design only
- no runtime behavior changes
- no Telegram formatter/sender/notifier changes
- no outbox JSONL schema changes
- no DispatchCase code changes in this block
- no reload-watch live wiring
- no scheduler, buttons, DAT/API, Google Maps, or RateCon work

## Current Behavior

Successful Telegram outbox records are processed by:

```text
dispatch_case.build_cases_and_events(...)
```

Current case-eligible outbox message types are:

```text
LOAD_OPPORTUNITY
REVIEW_ONCE
SEARCH_HEALTH_CHECK
```

For every successful eligible outbox record, DispatchCase currently:

1. Tries to match an existing case with `outbox_matches_case(...)`.
2. If no case matches, creates a new case with `build_case_from_outbox(...)`.
3. Applies the outbox alert to the case with `apply_outbox_to_case(...)`.
4. Emits a `TELEGRAM_ALERT_SENT` event.

This means `SEARCH_HEALTH_CHECK` is currently treated as a load-level outbox candidate even though it describes a driver/search condition, not one load.

## Current Search Health Outbox Shape

`telegram_search_health_formatter.py` formats a search health message with:

- driver name
- current location
- monitored minutes
- current filters
- review/top counts
- common blockers
- possible adjustments
- recommendation

It does not intentionally describe a single load.

`telegram_outbox_logger.py` currently infers `SEARCH_HEALTH_CHECK` from text and can parse:

- `message_type`
- `category`
- `driver_name`

It usually cannot parse meaningful load-specific fields:

```text
pickup
delivery
rate
broker
broker_mc
reference_id
```

## Can SEARCH_HEALTH_CHECK Attach To A Load Case?

With the current formatter text, accidental load-case matching is unlikely because search health messages do not include a rendered load lane or valid reference ID.

However, the message is still case-eligible, so future metadata or text changes could accidentally provide load-like fields and attach to a load case.

## Can SEARCH_HEALTH_CHECK Create A Generic Load-Shaped Case?

Yes.

If a successful `SEARCH_HEALTH_CHECK` outbox record has no matching existing case, `build_case_from_outbox(...)` can create a load-shaped case using only driver-level information.

Because `build_case_id(...)` falls back to driver + broker MC when there is no load ID or reference ID, multiple search health checks for the same driver with empty broker MC can collapse into the same generic load-shaped case.

That is not ideal because a search health check is not a load opportunity.

## Recommended Policy

Recommended current policy:

```text
SEARCH_HEALTH_CHECK should be outbox/reporting-only in DispatchCase flow until a search-level entity exists.
```

Practical meaning:

- `SEARCH_HEALTH_CHECK` should still be written to `telegram_outbox.jsonl`.
- `SEARCH_HEALTH_CHECK` should remain available for outbox reports, replay, and SQLite/reporting work.
- `SEARCH_HEALTH_CHECK` should not create a load-level DispatchCase.
- `SEARCH_HEALTH_CHECK` should not attach to a load-level DispatchCase through future metadata or accidental parsed fields.
- `SEARCH_HEALTH_CHECK` should not create a generic outbox-only case with empty load identity.

Future policy after a search-level model exists:

```text
SEARCH_HEALTH_CHECK can become a driver/search-level event attached to DispatchSearchSession.
```

Possible future entity:

```text
DispatchSearchSession
```

Possible future event:

```text
SEARCH_HEALTH_CHECK_SENT
```

That future model should be separate from load-level DispatchCase.

## Recommended Metadata Shape

Future search health metadata should keep existing outbox core keys stable:

```python
{
    "message_type": "SEARCH_HEALTH_CHECK",
    "category": "SEARCH HEALTH CHECK",
    "driver_name": "...",
    "pickup": "",
    "delivery": "",
    "rate": "",
    "broker": "",
    "broker_mc": "",
    "reference_id": "",
}
```

Recommended context fields for future use:

```python
{
    "search_area": "...",
    "current_location": "...",
    "available_time": "...",
    "equipment": "...",
    "target_direction": "...",
    "monitored_minutes": 30,
    "total_loads": 0,
    "top_opportunities": 0,
    "review_once_count": 0,
    "common_blocker_count": 0,
    "health_status": "",
    "action_status": "",
}
```

These context fields should be treated as future metadata until outbox reports, SQLite memory, and a search/session model are ready to preserve or consume them.

## Tests Needed Before Behavior Change

Before changing DispatchCase behavior, add focused tests covering:

1. A successful `SEARCH_HEALTH_CHECK` with no decision records does not create a load case.
2. A successful `SEARCH_HEALTH_CHECK` with accidental load-like fields does not attach to an existing load case.
3. A successful `SEARCH_HEALTH_CHECK` with empty metadata fields does not create a generic outbox-only case.
4. `LOAD_OPPORTUNITY` still creates or updates load-level DispatchCases.
5. `REVIEW_ONCE` still creates or updates load-level DispatchCases.
6. `MARKET_SNAPSHOT` remains excluded from load-level DispatchCase flow.
7. Failed outbox records are still ignored.
8. Existing `TELEGRAM_ALERT_SENT` behavior for load-level alerts remains unchanged.

## Do Not Change Yet

Do not change yet:

- Telegram message text
- search health formatter
- Telegram sender/notifier behavior
- outbox JSONL schema
- outbox logger fallback parser
- search health metadata helper or wiring
- reload-chain DispatchCase policy
- reload-watch live wiring
- SQLite schema

## Recommended Next Mini-Block

Recommended next mini-block:

```text
DispatchCase SEARCH_HEALTH_CHECK load-case exclusion
```

Scope should be:

- test-first
- exclude `SEARCH_HEALTH_CHECK` from load-level DispatchCase creation/matching
- preserve `LOAD_OPPORTUNITY` and `REVIEW_ONCE`
- preserve `MARKET_SNAPSHOT` exclusion
- do not wire search health metadata in the same block
- do not change Telegram/outbox schema

After that behavior is protected, search health metadata helper and wiring can be handled in separate mini-blocks.
