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
