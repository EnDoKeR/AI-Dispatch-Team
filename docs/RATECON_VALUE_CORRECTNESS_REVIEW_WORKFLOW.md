# RateCon Value Correctness Review Workflow

This document defines the local-only value correctness review workflow for
RateCon extraction. It follows the provider-line stop span extractor block.

## Why This Block Exists

The stop span extractor improved stop fragmentation:

- old normalized stops: 112;
- span-normalized stops: 29;
- span passthrough detected: no.

That is a real structural improvement, but it is not enough for production
readiness. The latest safe rerun still showed:

- all 29 span stops require review;
- date/time fields are still missing on many stops;
- value correctness is unknown;
- span type counts do not add up cleanly, which requires integrity checks.

Status improvement is not correctness. A smaller stop set is useful only after
a local reviewer verifies whether predicted values match the source documents.

## Review Packet, Not Final Truth

The workbook is a review packet. It is not a final truth source, not a
DispatchCase, and not a production automation signal.

Definitions:

- extracted candidate: a value-like signal found by text, layout, table, or
  span extraction;
- resolved field: the current deterministic resolver selection or status;
- reviewed field: a user-reviewed row marked correct, incorrect, or unknown;
- corrected field: a reviewer-provided expected value in a local-only workbook;
- trusted intake field: a field eligible for intake use after review policy,
  validation, and later correction import rules.

## Local-Only Workbook Policy

The review workbook and CSVs are local-only ignored outputs under
`.local_outputs/private_ratecon_measurement/`.

The workbook may include predicted private values only when the user explicitly
passes the local-only private value flag. Those values are for local review only.

Safe local workbook content may include:

- predicted private values;
- evidence labels and page numbers;
- status and confidence buckets;
- user review fields;
- user correction fields;
- local document stems for user navigation.

The console, committed docs, tests, and final reports must never include:

- private predicted or expected values;
- raw text;
- filenames or local paths by default;
- broker names;
- MC numbers;
- rates;
- addresses;
- references.

## Readiness Statuses

Readiness is split into three levels:

- Extraction Review Ready: enough statuses or candidates exist for human
  review, but values may be wrong or incomplete.
- Intake Core Ready: core intake fields are resolved or reviewable:
  broker/customer identity candidate, load identifier candidate, rate/payment
  candidate, pickup location/date candidate, and delivery location/date
  candidate. Commodity, weight, and equipment may still need review but must be
  visible.
- Dispatch Decision Ready: stricter than intake readiness. It requires
  high-confidence operational fields, including equipment, weight, commodity,
  special requirements, time windows, rate, broker identity/risk inputs, and
  driver compatibility inputs.

Do not mark a document Dispatch Decision Ready merely because it has an intake
draft. Dispatch decisions require higher certainty and additional business
context.

## Google Sheets Review Flow

Run the local-only review export with the stop span extractor enabled:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "<local-folder>" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-json --write-csv --write-md --write-stop-review-packet --write-stop-provenance-report --write-google-sheet-export --write-review-workbook --write-review-csvs --include-private-review-values-local-only --natural-sort-inputs
```

The console prints only aliases, counts, statuses, and output basenames. The
ignored local outputs include:

- `ratecon_review_workbook.xlsx`, when an existing workbook writer is available;
- `ratecon_review_document_summary.csv`;
- `ratecon_review_stop_review.csv`;
- `ratecon_review_field_review.csv`;
- `ratecon_review_rate_review.csv`.

The user should import the local CSVs into Google Sheets or open the workbook
locally:

1. Start with `Document_Summary` to pick the normal-load digital documents.
2. Review `Stop_Review` for stop type, sequence, location, date, time, and
   reference.
3. Review `Field_Review` for core fields such as broker identity, load number,
   rate, equipment, weight, and commodity.
4. Review `Rate_Review` for main-rate versus payment/terms noise.
5. Mark `User Correct?` as `yes`, `no`, or `unknown`.
6. Add `User Issue Type` for incorrect or unknown rows.
7. Export completed review CSVs for a later local feedback-import pass.

Safe status summaries can be shared back as aliases, counts, statuses, issue
types, and field names. Private workbook values and notes must stay local.

## Integrity Checks

The review export runs count-only integrity checks before generating review
rows. These checks detect issues such as:

- span normalized stop count not matching pickup + delivery + unknown counts;
- review-required stop count exceeding the stop denominator;
- date/time status counts not matching the stop denominator;
- negative count fields;
- OCR-needed documents being counted as normal-load extraction failures.

The latest safe run reported one integrity issue:
`SPAN_TYPE_COUNT_MISMATCH`. This matches the known aggregate where 29
span-normalized stops were reported, but pickup + delivery + unknown added to
27. That is a reporting/integrity issue to fix before any downstream trust
claim.

## Feedback Import

Completed review CSVs can be imported later through local-only feedback import
contracts. The import summary reports counts only:

- rows loaded;
- correct / incorrect / unknown counts;
- issue type counts;
- fields and aliases with high error rates.

Private expected values may be read locally for future correction workflows,
but they are not printed and this block does not write corrections to a
database or production intake record.

## Non-Goals

This block does not add OCR, Vision AI, cloud APIs, Camelot, PyMuPDF, broker
templates, DispatchCase creation, DecisionEngine calls, Telegram calls, Event
Timeline writes, or production automation claims.
