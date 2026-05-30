# Layout-Aware Digital Extraction

This document defines the dependency-free layout-aware extraction scaffold for
Rate Confirmation and tender-style documents. It is a design and test contract
checkpoint, not a production parser.

## Why This Is Next

The calibrated private measurement run showed:

- 18 total documents.
- 10 extraction-relevant documents.
- 6 normal load movement documents.
- 4 TONU/payment confirmations.
- 4 OCR-needed or empty-text documents.
- Normal-load blockers still include broker identity, rate, stops, dates, and
  weight.

Classification is now calibrated enough to separate normal load movement,
TONU/payment confirmations, supplemental documents, unknown-review documents,
and OCR-needed documents. The next measured blocker is therefore not document
eligibility. It is extracting the right field candidates from digital-text pages
whose layout carries the relationships that plain text loses.

## Why Not OCR First

OCR remains queued for the 4 empty-text documents, but it should not lead this
block. Most extraction-relevant documents in the measured corpus already have
digital text. Adding OCR first would not address table association, PU/SO
section pairing, payment-summary context, or terms/billing contamination in the
digital-text documents.

## Why Not Vision First

Vision remains a later gated fallback only. The deterministic path has not yet
used layout evidence from words, lines, blocks, tables, coordinates, or page and
section roles. Vision should be considered only after local deterministic layout
routes are measured and shown insufficient.

## Why Templates Alone Are Not Enough

Private broker template overlay support helps identify document families and
label vocabulary, but the latest safe pattern collection produced many
single-alias, low-confidence families. Even when a template is known, the parser
still needs layout evidence to associate:

- a rate label with the correct amount;
- pickup and delivery dates with the right stop row;
- PU/SO sections with the correct stop type;
- payment summaries with main rate versus accessorial terms;
- terms and billing pages with supplemental-only fields.

Broker templates should guide extraction. They should not replace layout-aware
candidate evidence.

## What Layout-Aware Extraction Means

Layout-aware extraction works with normalized document structure:

- word tokens;
- lines;
- blocks;
- tables;
- bounding boxes;
- page roles;
- section roles;
- label-value proximity;
- reading order variants;
- evidence references.

The layout layer does not decide final values. It produces better candidates
with evidence, then the conservative resolver decides whether anything is safe
enough to use in a `RateConfirmationIntake` draft.

## Observed Layout Families

The scaffold should support fake/synthetic equivalents of these generic layout
families:

1. table-heavy broker confirmation;
2. McLeod-style PU/SO load confirmation;
3. carrier load tender with route details;
4. blue-table confirmation;
5. multi-stop order confirmation;
6. payment summary or rate breakdown page;
7. terms, billing, and signature pages that must be scope-filtered.

Committed fixtures must mimic structure only. They must not include real broker
names, real MC numbers, private addresses, screenshots, private PDFs, raw private
text, or private field values.

## Target Flow

```text
PDF triage
-> document/page/section classification
-> extraction scope selection
-> layout artifact
-> layout-aware candidates
-> candidate scoring with evidence
-> conservative resolver
-> RateConfirmationIntake draft
-> validation / REVIEW_REQUIRED
```

## Layout Artifacts

The layout provider is intentionally deferred. This block defines normalized
contracts that a future provider must return:

- `LayoutWord`
- `LayoutLine`
- `LayoutBlock`
- `LayoutTable`
- `LayoutTableCell`
- `ReadingOrderVariant`
- `LayoutPageArtifact`
- `LayoutExtractionArtifact`
- `LayoutEvidenceRef`

The artifact must not require raw private text. Redacted test text is allowed
for fake fixtures. Private values are redacted by default.

## Candidate Evidence

Layout evidence should be attached to `FieldCandidate` records without breaking
existing candidate extraction. Useful evidence includes:

- page number;
- bounding box;
- line, block, table, or cell reference;
- section role;
- page role;
- proximity type such as same-row, below-label, table-cell, or section context;
- confidence reasons.

The resolver can then prefer candidates from stronger layout context while still
routing ambiguity to review.

## Scope Filtering

Layout-aware extraction must respect the existing classification and extraction
scope layer:

- main confirmation, load, tender, and order pages can feed core extraction;
- payment summary and rate breakdown sections can feed rate/payment candidates;
- terms pages can feed payment terms, deductions, penalties, detention, TONU
  terms, and special requirements when clear;
- billing and quick-pay pages can feed payment terms, not main load/stops;
- signature and certificate pages do not feed core rate or stop extraction;
- BOL pages do not feed RateCon core extraction;
- TONU/payment confirmations feed payment/status candidates and mark normal
  movement fields non-applicable when appropriate.

## Non-Goals

This block does not add:

- OCR;
- Vision AI;
- cloud extraction APIs;
- a new PDF library;
- `pdfplumber`;
- `PyMuPDF`;
- `Camelot`;
- real broker templates;
- private PDF parsing as production behavior;
- DispatchCase creation;
- DecisionEngine calls;
- Telegram calls;
- Event Timeline writes;
- production accuracy claims.

## Success Criteria

The block is successful when dependency-free layout contracts, synthetic layout
fixtures, layout indexing helpers, label-value proximity helpers, layout-aware
candidate generators, and fake-only CLI validation exist. Real provider
implementation and private measurement with provider output belong to the next
block after dependency and licensing review.
