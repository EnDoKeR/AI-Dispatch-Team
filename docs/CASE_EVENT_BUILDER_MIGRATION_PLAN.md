# Case Event Builder Migration Plan

This document defines a safe migration strategy for `case_event_builder.py`.

This is a plan only. It does not change runtime behavior, replace event builders, write new events, or wire DecisionResult into DispatchCase.

## Current Runtime Source

The current runtime source for DispatchCase event payloads is:

```text
app/market_intelligence/case_event_builder.py
```

It builds event dictionaries through:

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

This envelope is the current compatibility contract. It must remain stable until an explicit accepted migration block changes it with focused tests.

## Existing Foundations

The newer timeline foundation already exists:

- `case_event_types.py`: stable event type taxonomy and group lookup.
- `case_event_payload.py`: JSON-ready base payload helper for future normalized views.
- `case_event_report.py`: read-only report helper for event lists.
- `case_event_builder_report.py`: read-only shape report helper for current builder outputs.
- `decision_engine/timeline_preview.py`: report-only future `AI_DECISION_CREATED` preview with nested DecisionResult.

These helpers are not runtime sources today.

## Migration Goals

Future migration should:

1. preserve all current runtime event fields;
2. keep current event type names stable;
3. expose a normalized/base-payload-compatible view for reporting first;
4. avoid changing DispatchCase build/match/update behavior;
5. avoid writing DecisionResult into runtime events until a separate wiring block is accepted;
6. keep reports able to compare old envelope and normalized view;
7. keep current tests and compatibility reports green at every step.

## Strategy A: Keep Current Builder And Add Optional Normalized Payload

Description:

- Keep current `case_event_builder.py` output as the runtime event.
- Add optional normalized payload data alongside existing fields later, such as:

```python
{
    "event_id": "...",
    "case_id": "...",
    "event_type": "AI_DECISION_CREATED",
    "timestamp_utc": "...",
    "driver_name": "...",
    "load_id": "...",
    "reference_id": "...",
    "source": "decision_logger",
    "payload": {...},
    "normalized_payload": {
        "event_type": "AI_DECISION_CREATED",
        "event_group": "load_level",
        "case_id": "...",
        "timestamp_utc": "...",
        "source": "decision_logger",
        "details": {...},
        "related_ids": {...},
    },
}
```

Pros:

- low disruption;
- current consumers still read old fields;
- reports can compare old and normalized views.

Cons:

- increases event size;
- creates two representations of similar facts;
- requires clear ownership rules for which representation is authoritative.

Current recommendation:

- Useful later, but not the first implementation step.

## Strategy B: Wrapper Around Builder Output

Description:

- Leave `case_event_builder.py` unchanged.
- Add a separate wrapper/helper that accepts an existing event dict and returns a normalized report view.
- Runtime continues using old event dicts.
- Reports can consume:

```python
{
    "legacy_payload": {...},
    "normalized_payload": {...},
}
```

Pros:

- safest first implementation;
- no runtime event shape change;
- easy to test against current synthetic/current-style event samples;
- aligns with the accepted dry-run/report-first approach.

Cons:

- normalized view is not yet stored on runtime events;
- downstream tools must explicitly call the wrapper.

Current recommendation:

- Preferred first implementation target after this plan.

## Strategy C: Gradually Migrate Individual Event Types

Description:

- Pick one event type, such as `AI_DECISION_CREATED`, and add normalized data or wrapper support first.
- Repeat for `TELEGRAM_ALERT_SENT`, `DISPATCHER_FEEDBACK_ADDED`, `RATECON_RECEIVED`, and simulation events.

Pros:

- reduces blast radius;
- allows one event type to be validated before expanding.

Cons:

- can create uneven behavior if some event types are migrated and others are not;
- requires careful docs and tests for each event type.

Current recommendation:

- Good later strategy after the wrapper shape is accepted.

## Strategy D: Replace Builder Entirely

Description:

- Rewrite `case_event_builder.py` to use `case_event_payload.py` as the primary runtime source.

Pros:

- one normalized event shape.

Cons:

- high regression risk;
- likely breaks current event consumers;
- may change event IDs, payload keys, dedupe behavior, and reporting assumptions;
- not necessary for current foundation phase.

Current recommendation:

- Reject for now.

## Recommended Migration Path

Recommended sequence:

1. Keep `case_event_builder.py` unchanged.
2. Add a report-only normalized wrapper around existing event dicts.
3. Add tests comparing:
   - current event envelope,
   - normalized/base payload view,
   - taxonomy group,
   - JSON serializability.
4. Use wrapper output in reports only.
5. Add a DecisionResult timeline preview comparison only in dry-run/report mode.
6. Later, design an explicit runtime wiring block if normalized payloads should be stored.
7. Only much later consider per-event migration or stored normalized payloads.

## What Must Not Change Yet

Do not change:

- `case_event_builder.py` runtime output;
- `event_logger.build_dispatch_event(...)`;
- `dispatch_case.build_cases_and_events(...)`;
- DispatchCase case creation/matching/update behavior;
- event type strings;
- event ID generation;
- dedupe key behavior;
- Telegram sender/notifier/formatter behavior;
- MarketLoad decision behavior;
- load selection;
- market snapshot behavior.

## Required Tests Before Any Code Migration

Before any wrapper/helper implementation:

- current builder output shape is preserved;
- all current builder event types are known in taxonomy;
- current builder payloads remain JSON-serializable;
- normalized wrapper does not mutate input events;
- wrapper output is JSON-serializable;
- wrapper handles unknown event types safely;
- wrapper keeps legacy payload intact;
- reports can read wrapper output;
- no runtime writer imports are introduced;
- full unittest discovery remains green.

## Event Builder Migration Safety Rules

Future event builder migration must follow these rules:

1. Never remove existing event fields without compatibility tests.
2. Never rename `event_type` values without a taxonomy update and migration note.
3. Any normalized payload must coexist with old fields before it replaces anything.
4. Runtime event builders must not import Telegram sender/notifier modules.
5. Runtime event builders must not call external APIs.
6. DecisionResult can only be embedded after a report-only preview and an explicit wiring block.
7. Search/reporting events must not become load-level events accidentally.
8. `MARKET_SNAPSHOT` and `SEARCH_HEALTH_CHECK` remain reporting-only until a SearchSession entity exists.
9. Reload-watch remains dry-run/manual until a separate accepted wiring block.
10. Builder migration must include focused tests, old-shape preservation tests, normalized-view tests, full unittest discovery, and docs updates.

Minimum test coverage for any builder migration:

- existing runtime event envelope keys remain present;
- existing payload field names remain present;
- `event_type` is known in `case_event_types.py`;
- event group is correct;
- normalized view is JSON-serializable;
- legacy event is JSON-serializable;
- input event is not mutated;
- DispatchCase builder tests remain green;
- reporting-only outbox policy remains protected.

## Normalized Event Wrapper Design

Future helper name candidate:

```text
app/market_intelligence/case_event_normalizer.py
```

Potential function:

```python
normalize_case_event_for_report(event)
```

This should be report-only at first.

### Proposed Return Shape

Recommended shape:

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

Answer to design question 1:

The wrapper should return both `legacy_payload` and `normalized_payload`.

Reason:

- reports can compare old and normalized shapes;
- runtime event consumers can keep using the old envelope;
- future migrations can prove compatibility before storing normalized data.

### Normalized Details

Answer to design question 2:

`normalized_payload["details"]` should copy current event `payload` data first.

For example:

```python
"details": {
    "legacy_event_payload": event.get("payload", {}),
}
```

Later event-specific mappers can add structured fields, but the first wrapper should avoid reinterpreting payload semantics.

### Related IDs

The normalized view should move current identity fields into `related_ids`:

```python
"related_ids": {
    "event_id": event.get("event_id", ""),
    "load_id": event.get("load_id", ""),
    "reference_id": event.get("reference_id", ""),
    "driver_name": event.get("driver_name", ""),
}
```

This preserves identity context without removing old top-level fields.

### Missing Fields

Answer to design question 3:

Missing `case_id`, `timestamp_utc`, or `source` should become safe defaults and warnings, not exceptions.

Suggested warnings:

- `missing_case_id`
- `missing_timestamp_utc`
- `missing_source`

The wrapper should not invent a case ID.

### Unknown Event Types

Answer to design question 4:

Unknown event types should normalize to uppercase/underscore text, use `event_group = "unknown"`, and add a warning:

```text
unknown_event_type
```

Unknown event types should remain reportable and JSON-serializable.

### Report First

Answer to design question 5:

The wrapper should be used by reports first, not runtime.

Allowed first consumers:

- synthetic fixture reports
- compatibility CLI
- future DecisionResult timeline preview comparisons

Not allowed first consumers:

- `dispatch_case.build_cases_and_events(...)`
- `case_event_builder.py`
- event_logger writes
- Telegram paths

### Required Tests Before Implementation

Answer to design question 6:

Before implementation, add tests for:

1. `legacy_payload` equals a copy of the original event;
2. `normalized_payload` contains `event_type`, `event_group`, `case_id`, `timestamp_utc`, `source`, `details`, and `related_ids`;
3. event type normalizes through taxonomy;
4. unknown event types are safe;
5. missing case/timestamp/source produce warnings;
6. input event is not mutated;
7. output is JSON-serializable;
8. current builder event samples normalize successfully;
9. no imports from Telegram sender/notifier, DispatchCase runtime builder, event logger writes, storage, or external APIs.

### Non-goals

The wrapper should not:

- write events;
- call `build_cases_and_events(...)`;
- call `case_event_builder.py`;
- change event IDs;
- decide event ownership;
- add DecisionResult to runtime events;
- create cases;
- read or write JSONL/SQLite.

## DecisionResult Event Wiring Prerequisites

DecisionResult must not be written into real case events until all prerequisites below are true.

Prerequisites:

1. Normalized event wrapper is implemented and accepted in report-only mode.
2. Old event shape preservation tests exist and are stable.
3. DecisionResult adapter coverage is accepted.
4. DecisionEngine comparison report is stable.
5. DecisionResult timeline preview is stable.
6. DispatchCase ownership policy confirms `AI_DECISION_CREATED` is load-level.
7. DecisionResult payload size is acceptable for event storage and reports.
8. Event reports can read both old runtime event shape and normalized wrapper output.
9. No Telegram sender/notifier/formatter dependency is introduced.
10. An explicit wiring mini-block is approved.

DecisionResult writes must not originate from:

- parser helpers;
- intake record helpers;
- Telegram formatters;
- Telegram sender/notifier modules;
- market summary or search health reporting-only paths;
- reload-watch dry-run/manual paths;
- reload-chain metadata or formatter paths.

First wiring policy:

- Prefer dry-run/report-only comparison first.
- If runtime wiring is later accepted, start with `AI_DECISION_CREATED` only.
- Preserve current flat fields: `decision`, `category`, `score`, `reasons`, `pickup`, `delivery`, and `rate`.
- Add nested DecisionResult only as additive data.
- Do not remove or rename existing event fields.
- Keep DispatchCase case creation/matching/update behavior unchanged unless explicitly in scope.
- Add focused old-shape and new-shape tests in the same mini-block.

Explicitly not allowed without separate accepted design:

- writing DecisionResult from a parser;
- writing DecisionResult from a Telegram formatter;
- writing DecisionResult from `MARKET_SNAPSHOT` or `SEARCH_HEALTH_CHECK`;
- attaching DecisionResult to search/session-level records before SearchSession exists;
- writing DecisionResult for reload-chain or reload-watch before ownership policy is accepted.

## Current Recommendation

Next safe implementation target:

```text
normalized event wrapper helper, report-only
```

This should accept existing event dicts and return a normalized report view while leaving runtime event builders untouched.

## Migration Plan Closeout

Completed planning:

- current builder runtime contract documented
- migration strategies evaluated
- full replacement rejected for now
- wrapper-first strategy selected
- migration safety rules documented
- normalized wrapper return shape proposed
- DecisionResult event wiring prerequisites documented

Recommended next implementation target:

```text
normalized event wrapper helper, report-only
```

Suggested first helper:

```text
app/market_intelligence/case_event_normalizer.py
```

Suggested first tests:

```text
tests/test_case_event_normalizer.py
```

Initial scope:

- accept existing event dict
- return `legacy_payload`
- return `normalized_payload`
- attach `event_group`
- move identity fields into `related_ids`
- place current `payload` under normalized `details`
- add warnings for missing case ID, timestamp, source, or unknown event type
- avoid mutation
- stay JSON-serializable
- stay report-only

Still not allowed:

- no runtime event writing
- no DispatchCase build/match/update changes
- no replacement of `case_event_builder.py`
- no DecisionResult event writes
- no Telegram behavior changes
- no storage reads/writes
