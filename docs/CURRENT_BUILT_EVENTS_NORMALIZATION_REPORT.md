# Current Built-events Normalization Report

This document defines a report-only dry-run flow for inspecting current-style built event samples through the normalized event wrapper and event report layer.

This is design/audit only. It does not change runtime behavior, read runtime JSONL event files, write events, modify `case_event_builder.py`, or validate dispatch business correctness.

## Purpose

The report should show how event dictionaries shaped like current `case_event_builder.py` output normalize through:

```text
legacy event sample
-> normalized wrapper output
-> event report summary
```

This helps verify shape compatibility and warning visibility before any event builder migration is considered.

## Input

Input must be synthetic/current-style event samples only.

Expected shape:

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

The samples may include intentionally incomplete records to verify warnings, such as missing case ID, missing timestamp/source, or unknown event type.

Not allowed:

- runtime JSONL reads;
- DispatchCase runtime storage reads;
- live Telegram/outbox data;
- real broker/customer/driver data;
- real RateCon documents or paths.

## Step 1: Legacy Event Sample

Each sample should preserve the current flat runtime-style envelope. The report should not change the legacy event itself.

Event families to cover:

- `AI_DECISION_CREATED`
- `TELEGRAM_ALERT_SENT`
- `DISPATCHER_FEEDBACK_ADDED`
- `RATECON_RECEIVED`
- load-board simulation events such as `LOAD_APPEARED` and `LOAD_REMOVED`
- warning cases with missing identity/timestamp/source
- unknown event type

## Step 2: Normalized Wrapper Output

Each current-style sample should pass through:

```text
normalize_case_event(...)
```

The wrapper should return:

```python
{
    "legacy_payload": {...},
    "normalized_payload": {
        "event_type": "...",
        "event_group": "...",
        "case_id": "...",
        "timestamp_utc": "...",
        "source": "...",
        "details": {...},
        "related_ids": {...},
    },
    "warnings": [],
}
```

Warnings should make compatibility gaps visible without failing the report.

Expected warnings:

- `missing_case_id`
- `missing_timestamp_utc`
- `missing_source`
- `unknown_event_type`

## Step 3: Event Report Summary

The normalized wrapper records should be summarized through the event report layer that already supports both legacy and wrapper input.

Summary should include:

```python
{
    "total_events": 0,
    "known_event_count": 0,
    "unknown_event_count": 0,
    "warnings_count": 0,
    "warnings_by_type": {},
    "counts_by_event_type": {},
    "counts_by_event_group": {},
    "normalized_events": [],
}
```

## What This Proves

This report proves:

- current-style event samples can be wrapped without mutation;
- event type taxonomy covers expected current event families;
- unknown event types remain visible;
- missing identity/timestamp/source warnings are visible;
- wrapper records can be summarized by report helpers;
- output remains JSON-serializable.

## What This Does Not Prove

This report does not prove:

- dispatch decisions are correct;
- event payload business content is complete;
- `case_event_builder.py` should be changed;
- runtime events should store normalized payloads;
- DecisionResult should be written to real case events;
- DispatchCase timeline ownership should change.

## Non-goals

Do not:

- read runtime JSONL files;
- write events;
- call `case_event_builder.py` in runtime paths;
- change DispatchCase build/match/update behavior;
- change Telegram behavior;
- wire DecisionResult into events;
- call DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, replay, or missed-opportunity code;
- touch reload-chain metadata.

## Required Tests Before Implementation

Focused tests should cover:

1. fixture import;
2. every fixture normalizes;
3. expected event groups match;
4. expected warnings match;
5. fixture set is JSON-serializable;
6. report handles all fixtures;
7. known/unknown counts are correct;
8. warning summaries are correct;
9. event type and group counts are correct;
10. report output is JSON-serializable;
11. inputs are not mutated;
12. no forbidden imports.
