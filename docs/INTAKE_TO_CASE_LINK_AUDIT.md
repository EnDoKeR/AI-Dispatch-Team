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

## Link Policy Proposal

This section defines a future conservative policy. It is not implemented.

### Core Policy

Parser/intake must not automatically create DispatchCases.

An IntakeRecord may later produce a link candidate only. The candidate may recommend:

- link to an existing case;
- create a case for review;
- keep unlinked;
- require manual review.

Any actual link/create behavior must wait for a separate accepted implementation block and focused tests.

### When Should IntakeRecord Link To An Existing Case?

Future link candidate generation may recommend linking to an existing DispatchCase when enough identity evidence agrees.

Strong evidence:

- exact `reference_id` match to an existing case;
- exact `load_id` match if a load ID is available later;
- broker MC agrees when present on both sides;
- pickup and delivery agree;
- rate agrees or is within an explicitly accepted tolerance;
- pickup/delivery dates do not conflict;
- no critical missing fields;
- no low-confidence critical fields.

Recommended conservative link requirement:

```text
reference_id or load_id
+ pickup/delivery
+ broker/broker_mc when available
+ no critical conflict
+ human approval before persisted link
```

### When Should IntakeRecord Create A New Case?

Future case creation from intake should be rare and approval-gated.

Recommended policy:

- IntakeRecord can recommend `CREATE_CASE_REVIEW`;
- it must not create the case automatically;
- human approval is required;
- record must have enough core identity and load facts.

Minimum facts before create-review recommendation:

- `reference_id`;
- `broker_name` or `broker_mc`;
- pickup location;
- delivery location;
- pickup date;
- delivery date;
- rate;
- equipment.

Even with all fields present, a new case should remain review-first until the user accepts an explicit case creation workflow.

### When Should IntakeRecord Stay Unlinked?

Keep unlinked when:

- no reference ID or load ID exists;
- broker identity is missing or conflicting;
- pickup/delivery are missing;
- pickup/delivery dates are missing;
- parser confidence for critical identity/lane fields is low;
- multiple stops make lane identity ambiguous;
- the record appears duplicate but the target case is unclear;
- the record came from dry-run/sample data;
- source document is private and has not been reviewed;
- any mismatch indicates the record may belong to a different load.

### Required Fields For Safe Link/Create

Recommended safe-link fields:

```text
reference_id or load_id
broker_mc when available
broker_name when broker_mc is missing
pickup_location
delivery_location
pickup_date
delivery_date
rate when available
```

Recommended safe-create fields:

```text
reference_id
broker_name or broker_mc
rate
pickup_location
delivery_location
pickup_date
delivery_date
equipment
```

Weight and commodity are mandatory for dispatch review in the intake record model. Missing weight or commodity should not silently block candidate generation, but should prevent automatic case creation and keep the candidate in review.

### Missing Fields And Needs-check Fields

Policy:

- any `missing_fields` value should prevent auto-link and auto-create;
- missing identity fields should strongly push `KEEP_UNLINKED` or `NEEDS_REVIEW`;
- missing dispatch fields can still allow a candidate if identity is strong, but approval is required;
- `needs_check_fields` should force `NEEDS_REVIEW`;
- candidate output should preserve the exact missing/needs-check field names.

### Low-confidence Parser Fields

Policy:

- low confidence identity fields should prevent auto-link;
- low confidence lane fields should force review;
- low confidence rate/date/equipment fields should force review;
- high confidence fields may support evidence, but should not by themselves approve a link.

Critical confidence fields:

```text
reference_id
broker_mc
broker_name
pickup_location
delivery_location
pickup_date
delivery_date
rate
equipment
```

### Duplicate And Reference Matching

Reference matching should be conservative.

Recommended future duplicate/link rules:

1. exact normalized `reference_id` match is strongest;
2. exact `load_id` match is strongest if available;
3. if `reference_id` is `"NO ID"`, blank, or missing, do not auto-link;
4. if multiple cases share the same reference, require manual review;
5. if reference matches but lane/broker conflicts, require manual review;
6. if no reference exists, lane + broker + date can produce only a review candidate.

### Driver, Broker, And Lane Matching

Driver matching:

- IntakeRecord does not currently include `driver_name`.
- Driver should not be required for intake evidence unless the source explicitly includes it later.
- Do not infer driver from Telegram chat or file source.

Broker matching:

- broker MC is stronger than broker name;
- broker name alone is weak evidence;
- broker name conflict with broker MC match should require review;
- broker MC conflict should block auto-link.

Lane matching:

- pickup and delivery should normalize before comparison later;
- date agreement should matter once case/date fields exist;
- multi-stop records should require review.

### Manual Approval

Manual approval is required before:

- setting `linked_dispatch_case_id`;
- creating a new DispatchCase from intake;
- writing `INTAKE_LINK_APPROVED`;
- writing `CASE_CREATED_FROM_INTAKE`;
- changing any existing case field from intake evidence.

Dry-run reports may show recommendations, but must not mutate intake records or cases.

### Policy Summary

Recommended future actions:

| Situation | Recommended action |
| --- | --- |
| exact reference/load match, no conflicts | `LINK_EXISTING` candidate, approval required |
| strong identity but missing dispatch fields | `NEEDS_REVIEW` |
| complete record but no matching case | `CREATE_CASE_REVIEW`, approval required |
| missing identity | `KEEP_UNLINKED` or `NEEDS_REVIEW` |
| low confidence critical fields | `NEEDS_REVIEW` |
| broker/lane/reference conflict | `KEEP_UNLINKED` or `NEEDS_REVIEW` |

No action in this table is runtime behavior today.
