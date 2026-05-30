# Event Timeline Contract

The Event Timeline is the audit trail for dispatch workflow state changes. It
must remain append-only in runtime implementations, while helpers in this
foundation layer stay pure and report-only until a dedicated wiring block is
approved.

## Event Shape

Timeline events use this contract:

- `event_id`
- `case_id`
- `event_type`
- `event_group`
- `known_event_type`
- `created_at`
- `actor_type`
- `actor_id`
- `payload`
- `evidence_refs`
- `source`
- `idempotency_key`
- `schema_version`

`payload` must be JSON-ready and must not contain raw private RateCon text.
`evidence_refs` should point to redacted evidence records or local-only artifact
metadata, not document snippets.

## Append Points

Future event append points are:

- load source: `LOAD_SEEN`
- document intake: `RATE_CON_RECEIVED`
- PDF triage: `PDF_TRIAGED`
- text extraction: `TEXT_EXTRACTED`
- OCR routing: `OCR_FALLBACK_NEEDED`
- RateCon parsing: `RATE_CON_PARSED`
- RateCon review gate: `RATE_CON_REVIEW_REQUIRED`
- field correction: `FIELD_CORRECTED`
- case creation: `CASE_CREATED`
- AI evaluation: `AI_EVALUATED`
- dispatcher approval/rejection: `DISPATCHER_APPROVED`, `DISPATCHER_REJECTED`
- document linking: `DOCUMENT_LINKED`
- missing document detection: `MISSING_DOCUMENT_DETECTED`
- factoring readiness: `FACTORING_PACKET_READY`

These names are taxonomy foundations only. Adding the constants does not write
events, replace `case_event_builder.py`, or change DispatchCase behavior.

## Idempotency

Runtime appenders should reject duplicate events when an `idempotency_key`
already exists for the same timeline. Report helpers may model this by returning
an unchanged list when a duplicate key is detected.

## Ordering

Reports should sort by `created_at`, then `event_id`, when presenting timeline
history. Storage order can remain append order, but presentation should be
stable and deterministic.

## Unknown Types

Unknown event types must remain safe:

- normalize the provided name;
- mark `known_event_type` false;
- group as `unknown`;
- do not crash reports.

Unknown types should not be written by runtime flows without a taxonomy update
and migration note.

## Current Boundary

This contract does not implement OCR, document storage, case creation, event
writing, Telegram sending, or accounting/factoring behavior. It prepares the
shape future wiring must use once those implementation blocks are explicitly
approved.
