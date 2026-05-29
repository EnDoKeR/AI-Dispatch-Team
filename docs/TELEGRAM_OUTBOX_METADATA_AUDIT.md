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
MARKET_SNAPSHOT
SEARCH_HEALTH_CHECK
```

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
9. Wire review-once, market summary/search health, and reload-chain only in separate future blocks.
10. Keep reload-chain DispatchCase role separate until it has an accepted design.
11. Keep old text parser tests until every live path passes metadata and historical records remain readable.

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

It is not wired into `telegram_notifier.py` yet.

Other `telegram_notifier.py` message families are not wired yet.

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
Telegram review-once metadata wiring
```

Scope should be limited to:

- review-once sender path only
- `telegram_notifier.py`
- focused notifier tests around review-once metadata
- possibly a small docs note

Do not wire market summary, search health, reload-chain, or reload-watch metadata in the same block.
