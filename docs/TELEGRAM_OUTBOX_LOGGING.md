# Telegram Outbox Logging

Telegram outbox records are part of the DispatchCase memory trail.

They connect:

```text
Telegram message -> outbox JSONL record -> DispatchCase timeline -> SQLite memory
```

---

## Current State

Current logger:

```text
app/market_intelligence/telegram_outbox_logger.py
```

Current storage:

```text
data/telegram_outbox.jsonl
```

The logger currently extracts structured fields from Telegram message text:

```text
message_type
category
driver_name
pickup
delivery
rate
broker
broker_mc
reference_id
telegram_message_id
send_success
error_text
text
```

This is useful, but fragile.

If Telegram message text changes, outbox parsing can change too. That can affect DispatchCase matching, event timelines, SQLite memory, broker memory reports, and replay.

---

## Current Protection

Text parsing behavior is protected by:

```text
tests/test_telegram_outbox_logger.py
```

The tests cover:

- message type inference
- current load opportunity parsing
- review-once category parsing
- lane extraction
- Telegram response message id extraction
- JSONL outbox write shape

These tests intentionally preserve current mojibake separator behavior until controlled encoding cleanup is done.

---

## Future Direction

The safer future shape is:

```text
formatter -> text only
sender/logger -> structured metadata
```

Future call shape may look like:

```text
log_outgoing_telegram_message(
    text=message,
    success=True,
    telegram_response=response,
    metadata={
        "message_type": "LOAD_OPPORTUNITY",
        "driver_name": "Alex",
        "pickup": "Dallas, TX",
        "delivery": "Houston, TX",
        "rate": 2200,
        "broker": "Test Broker",
        "broker_mc": "123456",
        "reference_id": "REF-123",
    },
)
```

If metadata exists, logger should prefer metadata.

If metadata is missing, logger should fall back to text parsing for backward compatibility.

---

## Do Not Do Yet

- Do not change Telegram message text and outbox parsing in the same untested move.
- Do not remove text parsing until all send paths pass metadata.
- Do not clean mojibake globally before formatter and outbox parser tests are ready.
- Do not let Telegram formatting decide whether a load is good.

---

## Safe Next Steps

1. Add optional metadata support to `log_outgoing_telegram_message()`.
2. Keep existing text parser fallback.
3. Update one sender path at a time to pass metadata.
4. Keep DispatchCase matching tests green after each sender path.
5. Clean message encoding one formatter family at a time after metadata is stable.
