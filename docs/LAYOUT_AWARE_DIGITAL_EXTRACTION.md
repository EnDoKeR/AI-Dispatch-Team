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
-> candidate source fusion / stop association
-> candidate scoring with evidence
-> conservative resolver
-> RateConfirmationIntake draft
-> validation / REVIEW_REQUIRED
```

## Layout Provider Status

The dependency-free scaffold has now been extended with a controlled
`pdfplumber` provider pilot:

- `app/document_ai/layout_provider.py` defines the provider boundary and safe
  provider statuses.
- `app/document_ai/pdfplumber_layout_provider.py` converts local digital-text
  PDFs into normalized `LayoutExtractionArtifact` objects.
- `app/document_ai/layout_pipeline.py` connects provider artifacts to
  layout-aware candidate generation.
- `scripts/run_private_ratecon_measurement.py` can use the provider only when
  explicitly invoked with `--layout-provider pdfplumber
  --enable-layout-candidates`.
- Experimental layout/text fusion runs only when explicitly invoked with
  `--enable-layout-fusion`.

The provider is a local measurement tool. It is not a production automation
claim and does not add OCR, Vision, PyMuPDF, Camelot, or cloud extraction.

## Layout Evidence Fusion

The first safe layout-provider rerun improved rate candidate coverage but left
stop/location/date fields worsened or unresolved. Fusion now has explicit
guardrails:

- text and layout candidates are merged, not blindly replaced;
- strong text baselines are preserved when layout evidence is weak;
- layout rate evidence from rate-summary sections can improve rate fields;
- terms, legal, quick-pay, deduction, and TONU amounts are not normal main rate
  by default;
- stop grouping uses table rows or pickup/delivery sections when those
  structures are available;
- conflicts remain review-required instead of being hidden.

The first safe fusion rerun attempted fusion on 6 normal-load documents and
produced 0 stop groups from current provider artifacts. Rate evidence improved,
but stop/date/location association still needs provider-to-section/table
calibration before adding another dependency.

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
- `PyMuPDF`;
- `Camelot`;
- real broker templates;
- private PDF parsing as production behavior;
- DispatchCase creation;
- DecisionEngine calls;
- Telegram calls;
- Event Timeline writes;
- production accuracy claims.

## Safe Private Measurement With Layout Provider

Run locally only:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --compare-layout-to-text-baseline --write-json --write-csv --write-md
```

Safe to share:

- provider status counts;
- layout attempted/success/failure/skipped counts;
- candidate count deltas by field;
- field names in improved/worsened/unchanged buckets;
- fusion attempted counts;
- stop group counts;
- blocker counts.

Do not share raw text, filenames, broker names, MC numbers, rates, addresses,
dates/times, load/reference numbers, local paths, or private notes.

## Success Criteria

The scaffold block is successful when dependency-free layout contracts,
synthetic layout fixtures, layout indexing helpers, label-value proximity
helpers, layout-aware candidate generators, fake-only CLI validation, the first
explicit provider pilot, and opt-in fusion guardrails exist. The next work
should use safe measurement deltas to calibrate provider-to-table/section
structure and stop/date/location association before evaluating a table-specific
provider or queuing OCR design for empty-text documents.
