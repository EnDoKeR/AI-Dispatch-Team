# Load Identifier Source-Line Forensics

Google Sheets sync remains paused until a valid local service account
credential exists. This workflow stays local-first and uses only safe counts,
statuses, aliases, label categories, and stage categories.

## Why This Exists

The previous load identifier work improved contracts, synthetic fixtures,
typed reference handling, audit artifacts, and constrained generic
header-reference behavior. It did not move the private corpus:

- primary identifier candidates stayed 3;
- typed references stayed 11;
- rejected non-primary references stayed 11;
- core load-number mappings stayed 1;
- load-number candidate gap stayed 8;
- true intake blockers stayed 51;
- readiness stayed `extraction_review_ready=14`, `not_ready=4`.

That result means the next useful question is not "which broader load-number
regex should be added?" The question is whether a primary load/order/tender
identifier is visible in extracted text or layout lines at all, and if so,
where it disappears.

## Source-Line Pipeline

The audit traces the load identifier path by safe counters only:

1. source text or layout line exists;
2. line feature recognizes identifier-like content;
3. label is detected;
4. label is classified;
5. typed candidate is generated;
6. candidate is classified as primary or non-primary;
7. primary candidate maps to core `load_number`;
8. review row is emitted.

No private line text, identifier values, broker names, file names, local paths,
addresses, rates, dates, or references may be written to committed docs or
console output.

## Failure Categories

- `source_line_absent`: no identifier-like line was visible in extracted text
  or layout evidence.
- `source_line_present_label_missing`: an identifier-like line was counted, but
  the label detector did not emit a label.
- `label_detected_unclassified`: a label was detected, but category remains
  unknown.
- `label_classified_non_primary`: the label was correctly classified as PO,
  BOL, pickup, delivery, appointment, customer, carrier, or other non-primary
  reference.
- `primary_candidate_not_generated`: a primary label exists, but no primary
  candidate was emitted.
- `primary_candidate_not_core_mapped`: a primary candidate exists, but the
  core field row remains missing.
- `only_non_primary_refs_visible`: references are visible, but none should be
  promoted to primary load number.
- `source_line_scope_filtered`: section or document scope excluded the source.
- `image_or_logo_only`: the identifier likely sits in non-text logo/header
  material.
- `ocr_needed_or_weak_text`: the document lacks enough usable text for this
  deterministic path.
- `no_shared_root_cause`: aliases disagree enough that one code fix is not
  justified.

## When Not To Implement A Fix

Do not implement another load identifier extraction fix when:

- identifiers are absent from extracted text/layout lines;
- only PO/BOL/pickup/delivery/appointment/customer/carrier references are
  visible;
- each alias has a different failure reason;
- the likely source is image-only or weak text that belongs in a future OCR
  design block;
- the next step is local human review rather than safer automation.

The hard rule is that a code fix requires a shared, code-fixable root cause
affecting at least three aliases. Otherwise the correct output is a local
review recommendation.

## Non-Goals

This workflow does not run Google sync, add OCR/Vision/cloud document AI, add
Camelot/PyMuPDF/Tesseract/PaddleOCR, create DispatchCases, call DecisionEngine,
call Telegram, write Event Timeline events, or claim production readiness.
