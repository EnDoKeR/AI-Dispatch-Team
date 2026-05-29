# Telegram Outbox Metadata Audit

Date: 2026-05-29

Scope:

- audit only
- no runtime behavior changes
- no Telegram sending changes
- no formatter changes
- no DispatchCase changes
- no outbox JSONL schema changes
- no reload-watch live wiring
- no scheduler, buttons, DAT/API, Google Maps, or RateCon work

## Current flow

Current send path:

```text
telegram_notifier.py
  -> formatter builds Telegram text
  -> telegram_sender.send_telegram_message(text, reply_markup=None)
  -> Telegram API call
  -> telegram_outbox_logger.log_outgoing_telegram_message(text, success, response, error)
  -> data/telegram_outbox.jsonl
  -> scripts/build_dispatch_cases.py
  -> dispatch_case.build_cases_and_events(...)
  -> DispatchCase timeline / SQLite memory / replay reports
```

`telegram_outbox_logger.py` is the only production caller that writes the outbox JSONL file.

`telegram_sender.py` calls the logger on:

- missing bot token
- missing chat id
- transport exception
- successful send
- Telegram API error

`telegram_notifier.py` currently calls `send_telegram_message(...)` from these paths:

- market summary
- top opportunities
- review-once loads
- search health check
- reload-chain candidates

## Current outbox record shape

Outbox records currently include:

```text
timestamp_utc
message_type
category
driver_name
pickup
delivery
rate
broker
broker_mc
reference_id
send_success
telegram_message_id
error_text
text
```

These fields are used later by DispatchCase, case events, SQLite memory, and replay/report scripts.

## Current parser behavior

The logger can already accept optional `metadata`.

If metadata is present for a field, the logger prefers metadata.

If metadata is missing, the logger falls back to parsing Telegram text.

This compatibility behavior is protected by `tests/test_telegram_outbox_logger.py`.

Current text parsing extracts:

- `message_type` from header keywords such as `MARKET SNAPSHOT`, `LOAD OPPORTUNITY`, `REVIEW ONCE`, `SEARCH HEALTH CHECK`, and `RELOAD`
- `category` from the first line
- `driver_name` from the first line and current mojibake dash separator
- `pickup` / `delivery` from the current mojibake arrow separator
- `rate` from the first `Rate:` line
- `broker` from the first `Broker:` line
- `broker_mc` from the first `MC:` line
- `reference_id` from the first `Reference ID:` line

## Fragile fields

The most fragile fields are:

- `driver_name`, because it depends on the current first-line separator
- `category`, because review-once parsing depends on first-line text shape
- `pickup` / `delivery`, because lane parsing depends on a rendered arrow separator
- `rate`, because reload-chain messages contain multiple `Rate:` lines and the parser takes the first one
- `broker`, `broker_mc`, and `reference_id`, because chain messages contain first-load and reload-load broker blocks
- `message_type`, because any formatter header text change can change inference

Formatter encoding/mojibake cleanup is therefore risky until structured metadata is passed by live send paths.

## DispatchCase dependency

`dispatch_case.py` currently consumes successful outbox records only.

It creates or updates cases only for these outbox message types:

```text
LOAD_OPPORTUNITY
REVIEW_ONCE
```

`MARKET_SNAPSHOT` is logged for outbox/reporting, but it is excluded from load-level DispatchCase creation and matching until a search-level entity exists.

`SEARCH_HEALTH_CHECK` is logged for outbox/reporting, but it is excluded from load-level DispatchCase creation and matching until a search-level entity exists.

`RELOAD_CHAIN` is currently logged but not used to create DispatchCases.

Outbox matching depends on:

- `driver_name`
- `reference_id`
- `pickup`
- `delivery`
- `broker_mc`

Case event payloads preserve:

- `message_type`
- `category`
- `telegram_message_id`
- `pickup`
- `delivery`
- `rate`
- `broker`
- `broker_mc`
- `reference_id`

Any future metadata path must preserve these existing keys and meanings.

## Compatibility risks

Adding metadata is safe only if the current keys remain stable.

Risks to avoid:

- removing text parser fallback too early
- changing Telegram formatter text and outbox parsing in the same mini-block
- changing outbox JSONL field names before DispatchCase/SQLite/replay are ready
- treating reload-chain metadata as DispatchCase input before a separate design exists
- changing sender call signatures without preserving existing callers and tests
- silently changing field types that reports assume are strings

## Safest future path

Recommended path:

1. Keep `telegram_outbox_logger.py` text parser fallback.
2. Add optional `metadata=None` to `send_telegram_message(...)`. Completed.
3. Pass `metadata` through every logger call in `telegram_sender.py`, including failure paths. Completed.
4. Keep current `reply_markup` behavior unchanged.
5. Add sender tests proving metadata is forwarded on success and failures. Completed.
6. Add small metadata builder helpers outside formatter modules, one message family at a time. Load opportunity helper completed.
7. Wire metadata first for top opportunity alerts. Completed.
8. Add review-once metadata helper. Completed.
9. Wire review-once metadata. Completed.
10. Audit market summary metadata shape before wiring. Completed.
11. Add market summary metadata helper. Completed.
12. Audit DispatchCase `MARKET_SNAPSHOT` policy. Completed.
13. Exclude `MARKET_SNAPSHOT` from load-level DispatchCase handling. Completed.
14. Wire market summary metadata. Completed.
15. Audit DispatchCase `SEARCH_HEALTH_CHECK` policy. Completed.
16. Exclude `SEARCH_HEALTH_CHECK` from load-level DispatchCase handling. Completed.
17. Add search health metadata helper. Completed.
18. Wire search health metadata. Completed.
19. Wire reload-chain only in a separate future block.
20. Keep reload-chain DispatchCase role separate until it has an accepted design.
21. Keep old text parser tests until every live path passes metadata and historical records remain readable.

Suggested future call shape:

```python
send_telegram_message(
    message,
    reply_markup=...,
    metadata={
        "message_type": "LOAD_OPPORTUNITY",
        "category": "LOAD OPPORTUNITY",
        "driver_name": search_request.driver_name,
        "pickup": load.pickup,
        "delivery": load.delivery,
        "rate": load.rate,
        "broker": load.broker_name,
        "broker_mc": load.broker_mc,
        "reference_id": load.reference_id,
    },
)
```

Formatter responsibility should remain text only.

Notifier or a focused metadata helper should own metadata construction.

Current helper status:

```text
telegram_load_metadata.py
```

`build_load_opportunity_metadata(...)` builds structured metadata for normal load opportunity alerts only.

It is wired into `send_top_opportunities_to_telegram(...)` only.

`build_review_once_metadata(...)` builds structured metadata for review-once alerts.

It is wired into `send_review_once_to_telegram(...)`.

Reload-chain is the only current Telegram alert family still relying on text parsing for live sender metadata.

```text
telegram_summary_metadata.py
```

`build_market_summary_metadata(...)` builds structured metadata for market snapshot alerts.

It is wired into `send_market_summary_to_telegram(...)`.

```text
telegram_search_health_metadata.py
```

`build_search_health_metadata(...)` builds structured metadata for search health alerts.

It is wired into `send_search_health_check_to_telegram(...)`.

## Market summary metadata audit

Current market summary send path:

```text
send_market_summary_to_telegram(...)
  -> market_summary_key(...)
  -> format_market_summary_message(...)
  -> send_telegram_message(message)
  -> log_outgoing_telegram_message(...)
```

Market summary metadata is wired through `send_market_summary_to_telegram(...)`.

`telegram_outbox_logger.py` currently infers `MARKET_SNAPSHOT` from the message header and parses:

- `driver_name` from the first line
- `category` as `MARKET SNAPSHOT`
- `pickup` and `delivery` from the first rendered lane line, usually the best clean match if present
- `rate` from the first `Rate:` line, usually the best clean match if present
- `broker`, `broker_mc`, and `reference_id` as empty unless the summary text happens to include matching fields

Original DispatchCase risk:

- `dispatch_case.py` previously included `MARKET_SNAPSHOT` in successful outbox records that could create or update DispatchCases.
- `outbox_matches_case(...)` could match a market summary to an existing load case if parsed lane fields matched driver, pickup, and delivery.
- If no existing case matched, `build_case_from_outbox(...)` could create an outbox-only case from the market summary record.
- There is no dedicated driver/search-level market snapshot case model yet.

This meant wiring structured market summary metadata could change DispatchCase behavior even if Telegram text was unchanged. The accepted policy now keeps `MARKET_SNAPSHOT` outbox/reporting-only until a search-level entity exists.

Recommended market summary core metadata shape:

```python
{
    "message_type": "MARKET_SNAPSHOT",
    "category": "MARKET SNAPSHOT",
    "driver_name": "...",
    "pickup": "",
    "delivery": "",
    "rate": "",
    "broker": "",
    "broker_mc": "",
    "reference_id": "",
}
```

Recommended market summary context fields for future use:

```python
{
    "search_area": "...",
    "current_location": "...",
    "available_time": "...",
    "equipment": "...",
    "target_direction": "...",
    "market_activity": "...",
    "driver_fit": "...",
    "action_status": "...",
    "best_bucket": "...",
    "good_loads": 0,
    "qualified_loads": 0,
    "clean_match_count": 0,
    "review_once_count": 0,
    "blocked_count": 0,
}
```

Compatibility recommendation:

- Keep existing outbox core keys stable.
- For market summaries, keep load-specific core keys intentionally empty unless the project explicitly chooses to connect the summary to a specific best-load case.
- Extra context fields should be considered future-context metadata until outbox reports, SQLite memory, and search-level handling are ready to preserve or consume them.
- `MARKET_SNAPSHOT` metadata is wired, and DispatchCase now excludes it from load-level case matching/creation.

Policy decision:

```text
docs/DISPATCH_CASE_MARKET_SNAPSHOT_POLICY.md
```

Implemented current policy: `MARKET_SNAPSHOT` is outbox/reporting-only in DispatchCase flow until a search-level entity exists.

It does not create or attach to load-level DispatchCases through parsed best-load lane fields.

## Do not change yet

Do not change yet:

- Telegram message text
- Telegram sender behavior
- outbox JSONL schema
- DispatchCase outbox matching
- SQLite schema
- reload-chain DispatchCase behavior
- reload-watch live wiring
- mojibake/encoding in formatter text

## Recommended next mini-block

Recommended next mini-block:

```text
Compileall warning cleanup
```

Scope should be limited to:

- remove or update stale `test_sheet_connection.py` command references only
- keep runtime behavior unchanged
- keep old text parser fallback and outbox schema stable
- keep `LOAD_OPPORTUNITY`, `REVIEW_ONCE`, `MARKET_SNAPSHOT`, and `SEARCH_HEALTH_CHECK` metadata tests green
- avoid reload-chain metadata, reload-watch live wiring, scheduler, buttons, DAT/API, Google Maps, and RateCon expansion

Do not wire reload-chain or reload-watch metadata in the same block.
