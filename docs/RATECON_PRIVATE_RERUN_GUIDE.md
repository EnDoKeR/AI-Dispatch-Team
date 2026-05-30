# Private RateCon Triage Rerun Guide

This guide prepares a future local-only private RateCon triage rerun. It does
not authorize committing private PDFs, extracted text, private values, or local
CSV outputs.

## Current Boundary

This block added fake/anonymized PDF triage support and safe extraction artifact
metadata. It did not run private RateCons and did not add OCR, Vision AI, cloud
APIs, DispatchCase creation, or event writing.

Since then, fake/anonymized candidate extraction, broker-template matching,
template-aware scoring, conservative resolution, and hard-layout resolver tests
have been added. Private reruns should measure that deterministic pipeline with
safe summaries only; they should not claim production extraction accuracy.

Before running private documents, use a local-only wrapper that prints only the
safe triage summary fields listed below. Do not add raw text preview modes.

## Safe Fields To Share

Safe summary fields:

- anonymized label, such as `RATECON_001`;
- `page_count`;
- `char_count`;
- `chars_per_page`;
- `has_text_layer`;
- `likely_image_based`;
- `mixed_pdf`;
- `encrypted`;
- `broken`;
- `recommended_route`;
- generic warning categories.

Do not share:

- private filenames;
- raw extracted text;
- broker/customer names;
- MCs;
- addresses;
- phone numbers;
- emails;
- reference numbers;
- appointment details;
- document snippets.

## Route Interpretation

`DIGITAL_TEXT`

- The PDF appears to have usable digital text.
- Candidate extraction can be measured later.
- This does not mean field extraction is correct.

`OCR_NEEDED`

- The PDF has empty or very sparse extracted text, or mixed text coverage.
- OCR is not implemented yet.
- The document may still be valid and useful.

`MANUAL_REVIEW`

- The PDF is uncertain, encrypted, or cannot be safely classified.
- Human review or a later workflow decision is required.

`UNSUPPORTED`

- The file is broken, invalid, unreadable, unsupported, or zero-page.

`VISION_REVIEW_CANDIDATE`

- Future gated fallback only.
- Not a default path and not implemented now.

## Comparing With Previous Safe Rerun

Previous safe private summary:

- `RATECON_001`: `TEXT_EXTRACTED`, 4636 chars, 2 pages.
- `RATECON_002`: `EMPTY_TEXT`, 0 chars, 2 pages.
- `RATECON_003`: `TEXT_EXTRACTED`, 10694 chars, 3 pages.

Future triage should compare:

- whether `TEXT_EXTRACTED` maps to `DIGITAL_TEXT`;
- whether `EMPTY_TEXT` maps to `OCR_NEEDED`;
- whether page count remains stable;
- whether `chars_per_page` explains sparse extraction;
- whether a document is `mixed_pdf`;
- whether warnings reveal extraction-quality issues separately from parser gaps.

Future candidate/resolver measurement should compare:

- candidate counts by field;
- template match status and selected template ID when safe/anonymized;
- whether template scoring was applied or limited;
- resolved field names;
- missing field names;
- needs-check field names;
- conflict field names;
- generic warning categories.

## Local Output Rules

Private value-review CSVs and private triage summaries remain local-only and
untracked. Store local summaries only in ignored private dry-run folders. Do not
paste private values into tracked docs, tests, fixtures, or chat reports.

## Next Safe Step

The next implementation should add a local-only private triage wrapper only if
the user explicitly asks for it. That wrapper should use the same safe fields
listed here and must not print raw text.

After hard-layout resolver hardening, the next safe block is a local-only private
measurement harness. It should not add OCR, Vision AI, cloud APIs, DispatchCase
creation, event writes, or private value reporting.
