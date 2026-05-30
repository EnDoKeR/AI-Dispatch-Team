# RateCon Template Resolver Hardening

This document records the fake/anonymized hard-layout resolver behavior now
covered by tests. The goal is safer resolution, not optimistic extraction.

## Why This Layer Exists

Generic candidates and broker templates can identify possible RateCon values, but
hard layouts create traps:

- repeated headers and footer terms;
- multiple rate-like amounts;
- accessorials near the carrier-pay amount;
- stop-table layouts;
- broker name in the header only;
- carrier name near broker identity fields;
- references near the wrong stop;
- conflicting appointment times;
- special requirements buried in notes.

The resolver must select a field only when evidence is strong. Otherwise it must
preserve missing, conflict, or review signals.

## Hard-Layout Fixtures

Fake hard-layout fixtures live in:

```text
tests/fixtures/document_ai/ratecon_text/hard_layouts/
```

They are fake/anonymized only. They contain no private RateCon text, no real
broker templates, no real MCs, and no private values.

The covered fixture categories are:

- repeated headers with terms-page rate traps;
- multi-page rate and accessorial terms;
- table-like pickup/delivery stops;
- missing broker MC with header-only broker identity;
- carrier-vs-broker identity confusion;
- typed references near stops;
- conflicting appointment times;
- notes with special requirements;
- revised/current rate versus original/prior rate;
- unknown hard layout with generic fallback.

## Rate Resolution

Rate resolution now treats carrier-pay evidence differently from accessorial or
terms evidence.

Positive carrier-pay labels include:

- `Carrier Pay`
- `Total Carrier Rate`
- `Agreed Amount`
- `Linehaul`
- `Total Rate`
- `Carrier Rate`

Negative or accessorial labels include:

- detention
- layover
- lumper
- TONU
- quick pay
- fee
- deduction
- penalty
- accessorial

Rules:

- one strong carrier-pay candidate can resolve the rate;
- accessorial-only amounts cannot resolve the main rate;
- multiple strong, different carrier-pay values become a conflict;
- explicit revised/current rate labels can beat original/prior rate labels;
- weak revised/current evidence still routes to review or conflict.

## Stop And Appointment Resolution

Stop/date/time resolution remains conservative.

Rules:

- `Shipper` and `Origin` usually support pickup candidates;
- `Consignee`, `Receiver`, and `Destination` usually support delivery candidates;
- `Stop 1` and `Stop 2` can support table-like stop candidates;
- time windows such as `PU Appt 08:00-10:00` are preserved as one candidate;
- conflicting appointment candidates are marked as conflict/review signals;
- missing pickup/delivery dates are not invented.

This layer does not calculate miles and does not call Google Maps.

The layout-aware scaffold adds readiness tests showing that synthetic table-row
evidence can preserve pickup/delivery association before the resolver runs. The
resolver still treats multiple strong, different values as conflict/review
signals. Multi-stop pickup rows are not collapsed into one final pickup value.

## Layout Candidate Readiness

Layout-aware candidates can include page, section, table, cell, bbox, and
proximity evidence. The resolver does not treat that evidence as permission to
be optimistic:

- rate amounts from rate-summary sections can resolve when unambiguous;
- legal/terms/quick-pay/accessorial amounts are not main rate candidates by
  default;
- TONU payments remain separate from normal linehaul rate;
- low-confidence layout money routes to review;
- conflicting table-derived stop values remain conflicts.

Real provider extraction is not implemented in this hardening layer. Current
layout readiness tests use synthetic fixtures only.

## Broker Identity

Broker identity hardening separates broker templates from broker memory.

Rules:

- a trusted matched template can add a broker-name candidate from a header
  identity match;
- broker MC is never invented from a template;
- carrier labels penalize broker-name confusion;
- carrier name must not become broker name;
- missing broker MC remains optional for current RateCon review policy.

## Typed References

Typed references are preserved as evidence. They are not collapsed into one
generic `reference_id`.

Supported fake reference types include:

- broker load number;
- PO number;
- BOL number;
- pickup number;
- delivery number;
- pickup confirmation;
- delivery confirmation;
- customer reference;
- appointment number;
- unknown reference.

References near stops may remain review evidence if association is ambiguous.

## Special Requirements

The candidate layer preserves operational notes such as:

- tarp required;
- straps required;
- chains required;
- driver assist;
- no touch;
- must call before pickup;
- check in with pickup number.

These notes are extraction evidence only. They do not trigger driver
compatibility decisions, load rejection, or dispatch recommendations.

## Template Trust Rules

Template confidence can help candidate scoring only when the template match is
trusted.

Rules:

- matched template above the trusted threshold can apply template scoring;
- low-confidence template selection does not apply strong boosts;
- conflict template selection does not apply strong boosts;
- unknown template selection uses generic candidates only;
- template context cannot override field conflicts;
- template context cannot turn accessorial-only money into rate;
- template context cannot create missing values.

## Intake Draft Behavior

The intake draft builder now preserves hard-layout resolution outcomes:

- resolved fields populate the draft;
- missing fields remain explicit;
- low-confidence and conflict fields remain visible;
- typed references can be preserved;
- special requirements and accessorial terms can be preserved;
- template match metadata remains in extraction context;
- no DispatchCase is created.

The resulting `RateConfirmationIntake` still goes through validation. Critical
missing, low-confidence, or conflicting fields must route to review.

## Not Solved Here

This block did not implement:

- private RateCon reruns;
- OCR;
- Vision AI;
- cloud extraction APIs;
- real broker templates;
- DispatchCase creation;
- Event Timeline writes;
- Telegram formatting for extractor output;
- production extraction claims.

## Safe Private Measurement Preparation

This hardening prepares the next block: safe private RateCon measurement. That
future block should report only safe summaries such as triage route, candidate
counts by field, template status, resolved/missing/needs-check/conflict field
names, and generic warnings. It must not print raw text or private values.

After measurement showed template gaps across all digital-text private docs, the
next local-only layer is private broker template overlay support and redacted
pattern collection. Private overlays may help template scoring, but resolver
hardening rules remain unchanged: templates cannot invent values, cannot override
field conflicts, cannot turn accessorial-only money into rate, and cannot bypass
validation or review-required gates.

## Classification-First Resolver Input

Safe measurement now classifies document type, page roles, section roles, and
extraction scopes before the resolver sees candidates. This means:

- BOL, certificate, carrier-info, and signature-only documents should not create
  missing RateCon core fields.
- Terms and billing pages do not feed core rate/stops unless the allowed scope is
  payment or requirements related.
- TONU / truck-order-not-used documents are classified separately and should not
  be treated as normal load movement when stops are absent.
- Resolver conflicts are reported separately from pure missing fields.

If conflicts remain after classification, the next hardening should focus on
layout-aware digital extraction and field association, not OCR or Vision by
default.

After calibration, safe private measurement identified 10 extraction-relevant
documents out of 18, with 6 normal load movement documents and 4 TONU/payment
confirmations. Resolver missing/conflict counts should be interpreted against
those calibrated denominators. BOL, signature/certificate, driver/carrier
information, billing-only, terms-only, unknown-review, and OCR-needed documents
must not be counted as failed normal RateCon resolver cases.

## Layout Fusion Guardrails

The layout-provider pilot now feeds an opt-in fusion layer during safe
measurement only. Resolver hardening expectations remain conservative:

- layout candidates can improve missing or weak evidence when source, scope, and
  confidence are stronger than baseline text evidence;
- weak layout evidence cannot downgrade a strong text baseline;
- conflicting strong text/layout evidence remains review-required;
- rate-summary evidence can improve rate while terms, quick-pay, deductions,
  and TONU payments stay out of normal main-rate resolution;
- stop grouping must preserve pickup/delivery sequence and must not invent
  missing dates or times.

The first safe private fusion rerun improved rate evidence but produced no stop
groups from provider artifacts. That points to provider-to-section/table
calibration and stop association work, not OCR, Vision, or new broker templates.
