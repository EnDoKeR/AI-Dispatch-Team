# Load Identifier Coverage Audit

Google Sheets sync remains paused until a valid local service account
credential exists. This workflow uses local-only review, candidate coverage, and
measurement outputs to explain why `load_number` is still a true intake-core
blocker.

## Why This Exists

The first load identifier hardening added typed primary identifiers, typed
references, resolver mapping, coverage counters, and review workbook columns.
It improved synthetic coverage and diagnostics, but it did not improve private
readiness:

- load-number candidate gap moved from 7 to 8 under a more specific taxonomy;
- total candidate-not-generated count stayed 14;
- primary identifier candidates observed: 3;
- typed references observed: 11;
- rejected non-primary references observed: 11;
- load-number intake blockers moved from 7 to 9;
- readiness stayed `extraction_review_ready=14`, `not_ready=4`.

The `7 -> 8` load-number candidate gap is not automatically a regression. It
can reflect better classification of previously broad candidate gaps into
load-identifier-specific reasons. The next step is to identify the precise
stage where each identifier disappears.

## Primary Identifier Policy

A primary load identifier is a load/order/tender-like identifier that can
support intake review. Examples include:

- load number;
- order number;
- tender ID;
- PRO number;
- freight bill number;
- shipment number;
- dispatch or trip number when clearly in a load identity context;
- generic header reference only when the document context supports review.

PO, BOL, pickup, delivery, appointment, customer, and carrier references are
useful review fields, but they must not automatically become `load_number`.
Rejected non-primary references are therefore useful diagnostics, not
necessarily extraction failures.

## Audit Pipeline

The audit traces the load identifier path by safe counts and categories only:

1. line or text exists;
2. identifier-like label is detected;
3. label is classified;
4. typed candidate is generated;
5. primary versus non-primary status is determined;
6. primary candidate maps to core `load_number`;
7. typed references are preserved;
8. review row is emitted.

No private values, raw text, filenames, local paths, broker names, rates,
addresses, or reference values are included in committed docs or console
summaries.

## Failure Categories

- `identifier_absent_in_document`: no visible identifier evidence is available.
- `identifier_label_not_detected`: identifier-like text exists, but no label
  feature was found.
- `identifier_label_detected_but_unclassified`: a label feature exists, but the
  classifier does not know the category.
- `primary_candidate_not_generated`: a primary label exists, but no primary
  candidate is emitted.
- `primary_candidate_rejected_as_non_primary`: candidate evidence was generated
  but incorrectly treated as secondary reference evidence.
- `only_non_primary_references_found`: typed references were found, but none
  should be promoted to primary load number.
- `primary_candidate_generated_but_not_core_mapped`: primary candidates exist,
  but the core `load_number` row remains missing.
- `multiple_primary_identifiers_conflict`: multiple primary IDs disagree and
  require review.
- `context_missing_header_or_load_identity`: identifier-like labels are present
  but lack enough header/load-section context to promote safely.
- `scope_filtered`: document or section scope intentionally filtered the field.
- `ocr_needed`: document lacks usable digital text.

## Decision Rule

Do not implement another load identifier extraction change until the audit
selects one root cause. Possible targets are:

- label classification;
- primary candidate classification;
- primary-to-core mapping;
- generic header reference review candidates;
- header/load identity context coverage;
- local human review when only non-primary references are present.

## Non-Goals

This workflow does not run Google sync, add OCR/Vision/cloud document AI, create
DispatchCases, call DecisionEngine, call Telegram, write Event Timeline events,
or make production automation claims.
