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
-> document/page/section classification
-> extraction scope filtering
-> optional synthetic layout artifact candidate scaffold
-> optional candidate source fusion / stop association
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

## Candidate Source Fusion

Layout provider candidates are fused with text candidates only behind explicit
safe-measurement flags. Fusion rules:

- preserve source identity for text regex, text section, layout table, layout
  label-value, layout section, and broker-template candidates;
- do not blindly replace text candidates with layout candidates;
- preserve a strong text baseline when layout evidence is weak;
- route conflicting strong evidence to review;
- keep terms, billing, quick-pay, deduction, and TONU payment amounts from
  becoming normal main-rate candidates;
- group stops by table row or pickup/delivery section when layout structure
  provides that evidence;
- do not create DispatchCase records or emit ACCEPT/REJECT recommendations.

Safe private fusion measurement currently shows rate evidence improvement but
does not yet produce stop groups from provider artifacts, so stop/date/location
association remains the next blocker.

## Contracts

### FieldCandidate

FieldCandidate is an extraction-layer evidence record. Multiple candidates for one
field are expected.

Canonical ownership note: `app/document_ai/field_candidate_provenance.py` is the
canonical candidate contract for new document AI extraction candidates. The
legacy `app/document_ai/ratecon_candidates.py` contract and
`app/document_ai/ratecon_candidate_generators.py` generator surface remain
compatibility surfaces and should not receive new schema logic.

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

Implemented synthetic layout candidate families:

- layout-aware rate/payment candidates with table, section, and proximity
  evidence;
- layout-aware stop candidates for PU/SO sections, pickup/drop rows, route
  details, and multi-stop tables;
- layout-aware equipment, weight, commodity, dimensions, and special requirement
  candidates.

The layout scaffold uses synthetic JSON artifacts only. It does not add a real
PDF layout provider, OCR, Vision, cloud APIs, or new PDF dependencies.

## Layout Evidence

Layout candidates can carry optional evidence fields in addition to the original
candidate contract:

- `layout_evidence_ref`
- `layout_page_number`
- `layout_bbox`
- `layout_line_id`
- `layout_block_id`
- `layout_table_id`
- `layout_cell_ref`
- `layout_section_role`
- `layout_page_role`
- `layout_proximity_type`

These fields are evidence for the resolver and diagnostics. They are not final
field assignments and they do not create DispatchCases.

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
py scripts/run_fake_ratecon_candidate_extraction.py --input-dir tests\fixtures\document_ai\document_classification --classify-document --show-page-roles --show-section-roles --respect-extraction-scope
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

## Classification Before Candidate Extraction

Packet-like PDFs can contain primary Rate Confirmation pages, terms, billing,
signature certificates, carrier information sheets, and BOL-like pages. Candidate
generation should run only on pages and sections whose `ExtractionScope` allows
the relevant evidence.

Rules:

- BOL, certificate, carrier-info, and signature-only pages do not feed RateCon
  core fields.
- Terms and billing pages can support payment terms, deductions, accessorials,
  or special requirements, but should not create primary rate or stop evidence
  by default.
- Carrier load tender, load tender, order confirmation, load confirmation, and
  dispatch confirmation pages are extraction-relevant when load identity,
  route/stop, and rate/payment/equipment signals are strong, even if the title
  is not exactly `Rate Confirmation`.
- TONU / truck-order-not-used documents are payment/status relevant but not
  normal load movement documents; pickup/delivery/equipment/weight may be
  non-applicable.
- Unknown document types route to review.
- Supplemental-only documents are not counted as missing RateCon fields.

Candidate extraction should therefore be evaluated against the calibrated
normal-load denominator, not every PDF in a packet. OCR-needed, supplemental,
unknown-review, and TONU documents remain visible in safe measurement output but
do not inflate normal RateCon missing-field rates.

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
