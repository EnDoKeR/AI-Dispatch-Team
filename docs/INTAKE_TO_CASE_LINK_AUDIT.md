# Intake-to-Case Link Audit

This document audits the current intake and DispatchCase boundary before any link behavior is implemented.

This is audit/design only. It does not change runtime behavior, create DispatchCases from IntakeRecords, link IntakeRecords to DispatchCases, write DispatchCase events, change `case_event_builder.py`, parse PDFs/OCR, read real RateCons, or add integrations.

## Current State

### What Is an IntakeRecord Today?

An IntakeRecord is a normalized JSON-ready evidence record produced by the intake foundation.

Current source modules:

```text
app/market_intelligence/intake/record.py
app/market_intelligence/intake/parser_contract.py
app/market_intelligence/intake/repository.py
app/market_intelligence/intake/status.py
app/market_intelligence/intake/summary.py
```

Core fields:

```text
intake_id
source_type
source_file_name
received_at_utc
broker_name
broker_mc
rate
pickup_location
pickup_date
pickup_time
delivery_location
delivery_date
delivery_time
commodity
weight
reference_id
equipment
special_requirements
missing_fields
needs_check_fields
field_confidence
linked_dispatch_case_id
```

Current behavior:

- builds normalized records from dict/object input;
- normalizes parser output into the same record shape;
- calculates `missing_fields`;
- calculates `needs_check_fields`;
- stores optional local dry-run records in `data/intake_records.json`;
- can summarize/report records manually;
- keeps `ready_for_dispatch_case_linking = False` in dry-run summaries.

Current non-behavior:

- no DispatchCase creation;
- no DispatchCase linking;
- no event writes;
- no parser-driven dispatch decisions;
- no PDF/OCR/Gmail/Telegram upload/Google Sheets integration.

### What Is a DispatchCase Today?

A DispatchCase is the current load-level operational case/timeline record.

Current source modules:

```text
app/market_intelligence/dispatch_case.py
app/market_intelligence/case_factory.py
app/market_intelligence/case_matcher.py
app/market_intelligence/case_update_applier.py
app/market_intelligence/case_event_builder.py
```

Current DispatchCase creation/update inputs:

- decision records;
- successful eligible Telegram outbox records: `LOAD_OPPORTUNITY`, `REVIEW_ONCE`;
- feedback records;
- feedback records with `document_path`, which create `RATECON_RECEIVED`;
- matching `LOAD_APPEARED` simulation events.

Current excluded/reporting-only inputs:

- `MARKET_SNAPSHOT`;
- `SEARCH_HEALTH_CHECK`;
- reload-watch dry-runs;
- intake records;
- DecisionResult previews;
- normalized wrapper reports.

Current case fields overlap with intake records in practical load identity and document evidence areas:

```text
case_id
driver_name
load_id
reference_id
pickup
delivery
rate
weight
commodity
broker_name
broker_mc
telegram_alerts
dispatcher_feedback
ratecons
events_count
```

## Field Overlap

Direct overlap:

| IntakeRecord field | DispatchCase field |
| --- | --- |
| `reference_id` | `reference_id` |
| `pickup_location` | `pickup` |
| `delivery_location` | `delivery` |
| `rate` | `rate` |
| `weight` | `weight` |
| `commodity` | `commodity` |
| `broker_name` | `broker_name` |
| `broker_mc` | `broker_mc` |
| `equipment` | `posted_trailer_type` or driver/equipment context later |
| `source_file_name` | future document evidence only |

Potential future overlap:

- `pickup_date` and `delivery_date` may map to future appointment/timeline fields, but DispatchCase does not currently have dedicated pickup/delivery date fields.
- `special_requirements` may become document evidence or DecisionEngine signals, but should not directly update case status.
- `field_confidence` may affect link confidence, but it is not currently part of DispatchCase.
- `linked_dispatch_case_id` exists on IntakeRecord but is not used by runtime today.

## Missing For Safe Linking

Current gaps before safe linking:

1. no IntakeCaseLinkCandidate structure;
2. no match scoring policy;
3. no confidence threshold policy;
4. no human approval workflow for link/create;
5. no dedicated intake link event types beyond general intake/document taxonomy;
6. no tests for duplicate intake records;
7. no tests for mismatched broker/reference/lane conflicts;
8. no policy for multi-stop RateCons;
9. no policy for low-confidence parser fields;
10. no policy for whether an IntakeRecord can create a case when no load alert exists.

## What Must Not Trigger Case Creation Automatically

The following should not automatically create a load-level DispatchCase:

- a parser output alone;
- an IntakeRecord with missing mandatory fields;
- an IntakeRecord with low confidence critical fields;
- a RateCon/source document without approved matching policy;
- a source file name or private file path alone;
- special requirements text alone;
- broker name alone;
- pickup/delivery lane alone;
- any record with `reference_id` missing or suspicious;
- any dry-run scenario output.

## Evidence To Preserve

Future linking should preserve evidence without overwriting current case facts blindly.

Important evidence:

- `intake_id`;
- source type and source file name;
- received timestamp;
- parsed/imported fields;
- missing fields;
- needs-check fields;
- field confidence;
- special requirements;
- parser/manual source indicator;
- match reasons;
- mismatch reasons;
- approval record later;
- linked case ID only after approval/policy.

## What Should Remain Review-only

Review-only until a future implementation block:

- incomplete intake records;
- conflicting reference IDs;
- conflicting broker name/MC;
- low confidence rate/date/lane fields;
- multi-stop-like records;
- records with missing pickup/delivery dates;
- records where equipment is ambiguous;
- records with special requirements affecting driver compatibility;
- any proposed case creation from intake.

## Future Tests Needed Before Implementation

Before any code links intake records to cases, add focused tests for:

1. IntakeRecord with exact reference ID matches existing case candidate;
2. IntakeRecord with load ID/reference conflict remains review-only;
3. missing mandatory fields prevent auto-link;
4. low confidence critical fields require review;
5. broker MC mismatch blocks auto-link;
6. pickup/delivery mismatch creates mismatch reason;
7. duplicate intake IDs do not create duplicate case links;
8. `linked_dispatch_case_id` is not set without explicit approval;
9. no DispatchCase event is written during dry-run candidate generation;
10. future link candidate output is JSON-serializable;
11. no parser/Telegram/Gmail/Google Sheets/PDF/OCR dependencies in link logic.

## Current Conclusion

IntakeRecord is structured evidence. DispatchCase is load-level operational state and timeline.

Current foundation is strong enough to design a link candidate layer, but not to link or create cases yet. The next design step should define conservative link/create/keep-unlinked policy before any helper or runtime behavior is implemented.
