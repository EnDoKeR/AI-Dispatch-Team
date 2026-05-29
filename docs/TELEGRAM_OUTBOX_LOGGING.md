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

The logger can now accept optional structured metadata and fall back to
Telegram message text parsing when metadata is missing.

Outbox records include:

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

Text parsing is useful, but fragile.

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
- optional metadata override behavior
- text parser fallback when metadata is partial

These tests intentionally preserve current mojibake separator behavior until controlled encoding cleanup is done.

---

## Metadata Path

The safer shape is:

```text
formatter -> text only
sender/logger -> structured metadata
```

Current supported call shape:

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

Current sender status:

```text
telegram_sender.send_telegram_message(..., metadata=None)
```

The sender can now pass metadata through to the outbox logger on success and failure paths.

Only the top-opportunity `LOAD_OPPORTUNITY` notifier path is wired so far. Other live send paths still rely on text parsing unless a caller explicitly passes metadata.

Current load metadata helper:

```text
telegram_load_metadata.py
```

This helper builds metadata for normal load opportunity and review-once alerts. Normal load opportunity metadata is wired into the top-opportunity `LOAD_OPPORTUNITY` sender path, and review-once metadata is wired into the review-once sender path.

Market summary, search health, and reload-chain sender paths still use text parsing fallback.

---

## Do Not Do Yet

- Do not change Telegram message text and outbox parsing in the same untested move.
- Do not remove text parsing until all send paths pass metadata.
- Do not clean mojibake globally before formatter and outbox parser tests are ready.
- Do not let Telegram formatting decide whether a load is good.

---

## Safe Next Steps

1. Keep existing text parser fallback.
2. Add market summary metadata helper only; do not wire it until DispatchCase `MARKET_SNAPSHOT` policy is decided.
3. Keep DispatchCase matching tests green after each sender path.
4. Clean message encoding one formatter family at a time after metadata is stable.

See also:

```text
docs/TELEGRAM_OUTBOX_METADATA_AUDIT.md
```
