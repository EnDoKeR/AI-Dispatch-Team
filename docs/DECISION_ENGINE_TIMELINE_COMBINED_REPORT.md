# DecisionEngine Timeline Combined Report

This document defines a report-only bridge between existing load decision fields, the read-only DecisionResult adapter, future timeline preview payloads, and normalized event wrapper/report views.

This is design/audit only. It does not change runtime behavior, evaluate decision correctness, write events, modify DispatchCase, replace `case_event_builder.py`, or wire DecisionResult into case events.

## Purpose

The combined report should show whether the existing read-only pieces line up before any runtime event wiring exists.

For synthetic/fake load-like objects, it should show:

1. current load decision fields;
2. normalized DecisionResult from the read-only adapter;
3. future `AI_DECISION_CREATED` timeline preview payload;
4. normalized wrapper/report view over that preview payload.

## Input

Input should be synthetic or fake load-like objects only.

Accepted examples:

- dictionaries shaped like current load records;
- lightweight objects or `SimpleNamespace` values in tests;
- synthetic fixtures under `tests/fixtures/`.

Not allowed:

- live load board data;
- DispatchCase runtime records;
- Telegram outbox runtime data;
- JSONL/runtime event files;
- calls to `MarketLoad.apply_search_request(...)`.

## Stage 1: Original Load Decision Fields

The report should capture current load decision fields without recalculating them.

Suggested fields:

```python
{
    "load_id": "...",
    "reference_id": "...",
    "original_decision": "...",
    "original_category": "...",
}
```

These are descriptive fields only. The report does not decide if the load was correctly classified.

## Stage 2: DecisionResult From Read-only Adapter

Use:

```text
decision_result_from_market_load(...)
```

The adapter reads existing load fields and builds a JSON-ready DecisionResult. It must not call external services, mutate the load, write DispatchCase records, or call Telegram.

The combined report should include the full DecisionResult so future report tools can inspect:

- decision;
- category;
- risk flags;
- missing fields;
- needs-check fields;
- review/block reasons;
- source signals;
- linked load/reference IDs.

## Stage 3: Timeline Preview Payload

Use:

```text
build_decision_result_timeline_preview(...)
```

This should build a future-looking `AI_DECISION_CREATED` payload with:

- `preview_only = True`;
- `runtime_wired = False`;
- nested DecisionResult under `details.decision_result`.

The preview payload is not written anywhere.

## Stage 4: Normalized Wrapper / Report View

The timeline preview payload can be passed through:

```text
normalize_case_event(...)
```

This returns:

```python
{
    "legacy_payload": {...},
    "normalized_payload": {...},
    "warnings": [],
}
```

The wrapper view lets report helpers understand the future payload shape without changing runtime event writers.

## Output Report Shape

Suggested report item:

```python
{
    "load_id": "...",
    "reference_id": "...",
    "original_decision": "...",
    "original_category": "...",
    "decision_result": {...},
    "timeline_preview_payload": {...},
    "normalized_event_view": {...},
    "warnings": [],
}
```

Suggested report summary:

```python
{
    "dry_run": True,
    "total": 0,
    "decisions_by_type": {},
    "risk_flag_summary": {},
    "warning_count": 0,
    "preview_event_count": 0,
    "items": [],
}
```

## What This Proves

The combined report can prove:

- current load decision fields can be read without recalculation;
- the read-only adapter can represent current fields as DecisionResult;
- DecisionResult can fit inside a future timeline preview payload;
- the preview payload can be wrapped into the normalized event view;
- event report support can handle wrapper-style records;
- all of this can stay JSON-serializable and synthetic-only.

## What This Does Not Prove

The combined report does not prove:

- the original load decision is correct;
- the DecisionEngine should replace current logic;
- runtime DispatchCase events should be changed;
- DecisionResult should be stored on real events now;
- Telegram, DispatchCase, MarketLoad, market snapshot, or load selection behavior should change.

## Non-goals

Do not:

- write events;
- read runtime case/event storage;
- change `case_event_builder.py`;
- change DispatchCase build/match/update behavior;
- call `MarketLoad.apply_search_request(...)`;
- send Telegram;
- call DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, replay, or missed-opportunity code;
- touch reload-chain metadata.

## Required Tests Before Implementation

Focused tests should cover:

1. clean match report item;
2. review-once report item;
3. block report item;
4. timeline preview payload included;
5. normalized event wrapper view included;
6. summary counts decisions and risk flags;
7. JSON serializability;
8. input immutability;
9. no forbidden imports.
