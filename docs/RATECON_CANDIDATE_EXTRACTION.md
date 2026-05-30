# RateCon Candidate Extraction

This document describes the fake/anonymized candidate-based RateCon extraction layer.
It does not implement OCR, Vision AI, private PDF parsing, DispatchCase creation,
Telegram output, Google Sheets, DAT/API, or event writes. Broker-template
matching and scoring now live in the separate fake/anonymized layer documented
in `docs/RATECON_BROKER_TEMPLATES.md`.

## Why This Layer Exists

PDF triage answers whether a document has usable text. Candidate extraction answers
what field-like values appear in that text.

The project should not keep growing a single parser where one regex immediately
becomes final truth. Regex is now only one candidate source. Candidate extraction
collects possible values, confidence, reasons, and evidence location. A separate
resolver decides whether one value is safe enough to populate a draft intake field.

## Current Flow

```text
fake/anonymized text artifact
-> FieldCandidate records
-> CandidateExtractionResult
-> optional broker template matching / template-aware scoring
-> FieldResolution records
-> RateConFieldResolutionResult
-> RateConfirmationIntake draft
-> validation / review gating
```

This flow is deterministic, dependency-free, and tested only with fake/anonymized
fixtures.

## Contracts

### FieldCandidate

FieldCandidate is an extraction-layer evidence record. Multiple candidates for one
field are expected.

Core fields:

- `field_name`
- `raw_value`
- `normalized_value`
- `confidence`
- `confidence_reasons`
- `page_number`
- `line_number`
- `label`
- `context_before`
- `context_after`
- `source`
- `evidence_ref`
- `warnings`
- `candidate_id`
- `value_type`

Candidate confidence is not final dispatch confidence. A high-confidence extraction
candidate can still require review if another high-confidence candidate conflicts
with it.

### FieldResolution

FieldResolution is the resolver output for one field.

Statuses:

- `resolved`
- `missing`
- `needs_review`
- `conflict`
- `low_confidence`

Rules:

- conflict is explicit;
- low confidence is explicit;
- missing critical fields remain missing;
- rejected candidates are preserved;
- no DispatchCase is created;
- no dispatch recommendation is emitted.

### RateConfirmationIntake Draft

The intake draft is built only from resolved fields. Missing, low-confidence, and
conflicting fields remain visible through `missing_fields` and
`needs_check_fields`.

The draft builder can also preserve typed references, special requirements,
accessorial terms, resolver warning context, and template metadata. It does not
create DispatchCases, write events, call Telegram, or invent values.

## Candidate Families

Implemented fake/anonymized candidate families:

- money/rate candidates, including accessorial separation;
- broker identity and broker MC candidates;
- load number and typed reference candidates;
- pickup/delivery location, date, and time candidates;
- equipment, commodity, weight, special requirement, and accessorial-term candidates.

## Conservative Resolver Rules

The generic resolver selects a field only when:

- a candidate exists;
- confidence is at or above the configured threshold;
- no close competing candidate has a different normalized value;
- the candidate does not carry a review warning.

Examples:

- one clear `Total Carrier Pay` amount can resolve `rate`;
- detention/lumper/fee amounts do not become the final rate;
- multiple strong rate candidates with different values become `conflict`;
- generic stop labels can produce lower-confidence stop candidates;
- missing fields remain missing rather than being guessed.

Hard-layout resolver behavior for repeated headers, multi-page terms, table-like
stops, header-only broker identity, typed references, conflicting appointments,
and buried special requirements is documented in
`docs/RATECON_TEMPLATE_RESOLVER_HARDENING.md`.

## Fake Fixture Policy

Tracked tests and fixtures must be fake/anonymized only.

Allowed:

- `FAKE BROKER LLC`
- `MC000000`
- `FAKE-LOAD-001`
- `Fake City, ST 00000`
- fake dollar amounts and fake commodities

Forbidden:

- private RateCon text;
- real broker/customer/contact names;
- real MCs;
- real addresses;
- phone numbers;
- emails;
- reference numbers;
- appointment details or private snippets.

## Fake CLI

Run:

```powershell
py scripts/run_fake_ratecon_candidate_extraction.py
py scripts/run_fake_ratecon_candidate_extraction.py --include-hard-layouts
```

The CLI reads only fake/anonymized text fixtures by default and prints:

- fixture name;
- candidate counts by field;
- resolved field names;
- missing field names;
- needs-check field names;
- conflict field names;
- intake status;
- warnings.

It does not print full fixture text or candidate values.

## Future Extension Points

OCR and Vision AI are not implemented in this layer. Later, they can plug in as
additional candidate sources after PDF triage routes a document to the correct
extractor.

The fake/anonymized broker template registry is documented in
`docs/RATECON_BROKER_TEMPLATES.md`.

Broker templates add matching, confidence boosts, and penalties around existing
candidates. They do not directly assign final field values or make dispatch
decisions.

Private broker template overlays are local-only measurement inputs. They can
improve template matching and candidate scoring during a private run, but safe
outputs must show only template aliases such as `PRIVATE_TEMPLATE_001`, source,
confidence bucket, aliases, field names, statuses, and blockers. Private
template files, real broker identifiers, raw text, and values must never be
committed or pasted into chat.

Future Event Timeline wiring can record:

- PDF triaged;
- text artifact created;
- candidates extracted;
- field resolution completed;
- RateCon review required.

Those writes require a separate explicit implementation block.
