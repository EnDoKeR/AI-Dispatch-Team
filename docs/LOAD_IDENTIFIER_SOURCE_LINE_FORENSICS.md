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

## Local Artifacts And CLI

Private measurement can emit safe source-line audit artifacts with:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-json --write-csv --write-md --write-stop-review-packet --write-stop-provenance-report --write-google-sheet-export --write-review-workbook --write-review-csvs --include-private-review-values-local-only --write-candidate-coverage --write-load-identifier-audit --write-load-identifier-source-line-audit --natural-sort-inputs
```

This writes ignored local-only artifacts:

- `load_identifier_source_line_audit_raw.json`;
- `load_identifier_source_line_audit_raw.md`.

Analyze the latest local-only audit with:

```powershell
py scripts/analyze_load_identifier_source_lines.py --write-md --write-json
```

The analyzer writes:

- `load_identifier_source_line_audit.json`;
- `load_identifier_source_line_audit.md`.

All four artifacts contain only safe counts, statuses, aliases, label
categories, section categories, and root-cause buckets. They do not contain
identifier values or line text.

## Latest Local Result

The source-line audit ran after the load identifier coverage audit and measured
the missing `load_number` aliases by source-line stage. Safe result:

- documents analyzed: 18;
- identifier-like source lines: 96;
- header/load-identity source lines: 11;
- stop/billing/terms source lines: 73;
- labels detected / classified: 96 / 24;
- primary candidates: 3;
- core mappings: 2 in source-line accounting;
- rejected non-primary references: 11;
- top reasons: `unknown=5`, `ocr_needed_or_weak_text=4`,
  `source_line_absent=4`, `only_non_primary_refs_visible=3`, and
  `label_classified_non_primary=2`;
- shared code-fixable root-cause candidates: none;
- `fix_allowed=false`;
- recommended next action: `local_human_review`.

Because no shared code-fixable root cause affected at least three aliases, this
block intentionally did not add fixtures or another extraction hardening rule.
The candidate coverage selector may still name load identifier generation as a
broad target, but source-line forensics says the current private-corpus evidence
does not justify another generic load-id code change.

## Non-Goals

This workflow does not run Google sync, add OCR/Vision/cloud document AI, add
Camelot/PyMuPDF/Tesseract/PaddleOCR, create DispatchCases, call DecisionEngine,
call Telegram, write Event Timeline events, or claim production readiness.
