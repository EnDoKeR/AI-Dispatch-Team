# PDF Triage

PDF triage classifies document quality before RateCon field extraction. It does
not parse business fields, run OCR, call Vision AI, create DispatchCases, or
write timeline events. Optional local/shadow OCR diagnostics are separate and
disabled by default.

## Why It Exists

Private dry-runs showed two different problems:

- some PDFs have no extractable text;
- some PDFs have extractable text, but field extraction still misses core fields.

Those are different failure modes. Triage separates document-quality routing from
field extraction so later parser work can measure the right problem.

## PdfTriageResult Fields

The triage result includes:

- `document_id`
- `file_name`
- `pdf_kind`
- `page_count`
- `char_count`
- `chars_per_page`
- `has_text_layer`
- `likely_image_based`
- `mixed_pdf`
- `encrypted`
- `broken`
- `recommended_route`
- `page_profiles`
- `warnings`
- `triage_version`

It does not include raw text, extracted text, broker names, addresses, reference
numbers, appointment details, or document snippets.

## Recommended Routes

`DIGITAL_TEXT`

- Text layer appears usable.
- Candidate extraction can be attempted later.

`OCR_NEEDED`

- Text is empty, extremely sparse, or mixed by page.
- Production OCR is not implemented by this route.
- The route only records that OCR should be considered later.

`VISION_REVIEW_CANDIDATE`

- Reserved for future gated Vision fallback.
- Not a default path and not called by current code.

`UNSUPPORTED`

- Broken, unreadable, invalid, zero-page, or unsupported input.

`MANUAL_REVIEW`

- Encrypted or uncertain documents that need a human or future workflow decision.

## Threshold Examples

Current conservative route examples:

- `broken=True` -> `UNSUPPORTED`
- `encrypted=True` -> `MANUAL_REVIEW`
- `page_count == 0` -> `UNSUPPORTED`
- `char_count == 0 and page_count > 0` -> `OCR_NEEDED`
- very low `chars_per_page` -> `OCR_NEEDED`
- all pages have meaningful text -> `DIGITAL_TEXT`
- some pages have text and some pages do not -> `mixed_pdf=True` and `OCR_NEEDED`
- uncertain state -> `MANUAL_REVIEW`

The current low text-density threshold is intentionally conservative and should
be tuned only with fake/anonymized fixtures or safe aggregate private summaries.

## Empty Text Is Not Useless

`EMPTY_TEXT` means the current digital extractor could not read text. It does
not mean the document is useless. It may still be a valid scanned RateCon that
needs OCR, manual review, or a later Vision candidate path.

## Privacy Rules

Triage may read a local PDF only in approved local workflows. It must not:

- save raw extracted text;
- print raw text;
- commit private PDFs;
- commit private CSVs;
- create fixtures from private documents.

Tests must use fake/anonymized PDFs generated in temp directories or test
doubles.

## Fake Fixture Policy

Fake triage tests use generated temp fixtures from
`tests/fixtures/document_ai/pdf_triage/`. Checked-in private PDFs are forbidden.

The fake-only CLI is:

```powershell
py scripts/run_fake_pdf_triage_dry_run.py
```

It prints only safe metrics and route summaries.
