# Case Event Report Wrapper Support

This audit defines how read-only event reports should support normalized wrapper output while preserving existing legacy event dict behavior.

This is report-layer work only. It must not change DispatchCase runtime behavior, event writing, `case_event_builder.py`, Telegram behavior, MarketLoad behavior, or DecisionResult wiring.

## Current Input Shapes

The project now has two event-shaped records that reports may need to read.

### Legacy Event Dict

Legacy event dicts are the current runtime/report input shape:

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

`case_event_builder.py` and existing synthetic fixtures use this shape. It must remain backward-compatible.

### Normalized Wrapper Record

The normalized wrapper helper returns:

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

This shape is report-only. It does not write events, replace the legacy envelope, or change runtime event behavior.

## Should `case_event_report.py` Accept Both?

Yes.

Reason:

- legacy dicts remain the runtime source and existing report input;
- wrapper records are the accepted migration bridge;
- reports should be able to summarize both shapes without requiring callers to unwrap records manually;
- this lets future reports compare current and normalized event views before runtime migration.

## Normalization Policy

For legacy event dicts, report behavior should remain unchanged:

- normalize `event_type` through the event taxonomy;
- derive `event_group` from taxonomy;
- count by event type, group, and case ID;
- build timelines and latest event per case ID;
- report unknown event types safely.

For wrapper records, reports should prefer `normalized_payload` for:

- `event_type`
- `event_group`
- `case_id`
- `timestamp_utc`
- `source`

The report should keep enough wrapper context to remain inspectable. The normalized event in the timeline may include:

- normalized payload fields;
- `legacy_payload`;
- `warnings`;
- normalized `details`;
- normalized `related_ids`.

## Warning Policy

Wrapper warnings should be summarized by the report.

Recommended additions:

```python
{
    "warnings_count": 0,
    "warnings_by_type": {},
}
```

Legacy event dicts normally have no wrapper warnings. If a legacy dict already includes a `warnings` list, reporting may count it only if that field is explicitly part of a wrapper-like record. The first implementation should avoid reinterpreting arbitrary legacy payload fields as wrapper warnings.

## Event Group Policy

Wrapper records should use `normalized_payload["event_group"]` when present because the wrapper already mapped the event through the taxonomy.

If the wrapper event group is missing, the report should safely derive it from `event_type`.

Unknown event types should remain reportable as:

```text
event_group = "unknown"
```

and should appear in `unknown_event_types`.

## Backward Compatibility Requirements

The existing legacy report contract must remain stable:

- existing legacy event lists still produce the same counts;
- `timeline_by_case_id` still groups by normalized case ID;
- `latest_event_by_case_id` still uses timestamp ordering;
- unknown legacy event types are still reported once by normalized name;
- output remains JSON-serializable;
- input records are not mutated.

The report helper must remain read-only and must not import runtime writers or adapters.

## Required Tests Before Implementation

Add focused tests that prove:

1. legacy event report behavior still works;
2. wrapper output records are accepted;
3. mixed legacy + wrapper input is accepted;
4. wrapper warnings are counted;
5. normalized payload event group is used;
6. unknown wrapper event types are reported safely;
7. output remains JSON-serializable;
8. inputs are not mutated;
9. no forbidden imports are introduced.

## Not In Scope

Do not:

- change `case_event_builder.py`;
- write or migrate runtime events;
- read runtime JSONL files;
- wire DecisionResult into events;
- change DispatchCase build/match/update behavior;
- change Telegram behavior;
- change MarketLoad behavior;
- introduce DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, or replay/missed-opportunity behavior.
