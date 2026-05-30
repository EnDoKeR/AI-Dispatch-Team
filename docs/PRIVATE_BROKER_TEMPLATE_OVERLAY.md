# Private Broker Template Overlay

This document defines the local-only private broker template overlay workflow for
RateCon extraction measurement. It is a safe onboarding layer, not production
automation.

## Why This Layer Exists

The latest safe private measurement showed:

- 14 of 18 documents had digital text, or 77.8%.
- 4 of 18 documents were `OCR_NEEDED`, or 22.2%.
- 18 of 18 documents had `unknown` template status.
- 14 of 14 text-extracted documents had `TEMPLATE_GAP`.
- 13 of 14 text-extracted documents had `RESOLVER_GAP`.

That initial result justified building a local-only overlay and redacted pattern
collection workflow. A later classification-calibrated rerun showed that the
template gap should be interpreted after document/page/section eligibility:

- 10 of 18 documents were extraction-relevant;
- 6 of 18 were normal load movement documents;
- 4 of 18 were TONU/payment confirmations;
- 2 of 18 were supplemental-only;
- 6 of 18 were non-RateCon or unknown-review;
- 4 of 18 were OCR-needed / empty-text.

That means OCR is needed later, but it is still not the first measured blocker.
Private overlay work remains useful for eligible documents, but the next default
checkpoint after calibrated measurement is layout-aware digital extraction and
field association for eligible digital-text documents.

## Overlay Concept

Broker templates describe document layout, labels, section vocabulary, and
extraction hints. They are not broker memory, broker profile, payment history,
risk scoring, dispatcher experience, or business policy.

Template categories:

- Committed fake templates: safe fixtures used for tests and examples.
- Committed generic templates: future non-private templates with no real broker
  identifiers.
- Ignored local private templates: real local templates for private measurement
  only.
- Future customer or tenant templates: separately governed templates that must
  have explicit privacy and deployment rules.

Private overlays let local measurement load ignored private templates while safe
summaries continue to show only aliases, statuses, counts, field names, blocker
categories, and warning codes.

## Storage Policy

Private templates must live only in ignored paths such as:

```text
.local_private/broker_templates/
.local_outputs/private_ratecon_measurement/private_template_drafts/
```

Do not commit private template files. Do not paste them into chat. Do not store
raw PDFs, raw extracted text, real broker names, real MC numbers, rates,
addresses, load numbers, or reference numbers in committed docs, tests, or
fixtures.

Local private paths are ignored by Git. The private template directory is for
operator-owned local files only; committed code should load it only when the user
explicitly enables a private overlay. Pattern collection outputs and template
draft skeletons are local-only artifacts and should remain under the ignored
measurement output tree.

Committed tests for generalized template behavior must use fake/anonymized
fixtures only.

## Onboarding Workflow

1. Safe private measurement identifies a template gap.
2. Redacted pattern collection groups aliases into template family candidates.
3. A private local template draft is created in an ignored folder.
4. Safe measurement reruns with the private overlay enabled.
5. Only safe status improvements are shared.
6. If a pattern can be generalized, create a fake/anonymized committed fixture
   and tests before changing committed template logic.

## Template Versioning

Every template needs an explicit:

- `template_id`
- `broker_key`
- `display_name`
- `version`
- `source`

Private local templates should be marked with a private source, such as
`private_local`, and must remain local unless explicitly approved by a separate
review.

## Test Requirements

Every generalized template must include:

- a fake/anonymized input fixture;
- expected template match status;
- expected candidate fields;
- expected missing, needs-check, and conflict fields;
- an unknown-template fallback test;
- a conflict or low-confidence test when labels overlap with other templates.

Templates must not bypass validation. Low-confidence or conflicting critical
fields still route to review. Template matching does not create DispatchCase,
call DecisionEngine, call Telegram, write Event Timeline events, or emit
accept/reject recommendations.

## Review Required Rules

Private overlay measurement can improve template matching and candidate scoring,
but it cannot make extraction production-ready by itself. `REVIEW_REQUIRED`
remains mandatory when critical fields are missing, low-confidence, or
conflicting.

## Non-Goals

This overlay workflow does not add OCR, Vision AI, cloud APIs, live DAT/API,
DispatchCase creation, DecisionEngine decisions, Telegram business logic, or
production extraction claims.

## Classification Gate Before Overlay

Private overlays are evaluated only after document/page/section classification.
The overlay does not turn supplemental documents into RateCons. A private broker
template may improve candidate scoring for eligible RateCon, load confirmation,
or tender pages, but BOL, carrier-info, certificate, billing-only, signature-only,
and terms-only documents remain supplemental or non-RateCon according to the
classifier.

The safe measurement report separates:

- total documents;
- extraction-relevant documents;
- normal load movement documents;
- TONU/payment confirmations;
- supplemental-only documents;
- non-RateCon or unknown-review documents;
- OCR-needed documents.

Template overlay improvement should be measured against eligible documents and
status-only deltas, not private values.
