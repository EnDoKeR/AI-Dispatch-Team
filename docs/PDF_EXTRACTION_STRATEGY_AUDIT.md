# PDF Extraction Strategy Audit

Date: 2026-05-29

This audit documents the first local-only PDF text extraction strategy for private RateCon dry-runs. It does not implement OCR, parser changes, storage, Telegram upload, Gmail/email, Google Sheets, DispatchCase creation/linking/events, DAT/API, Google Maps, accounting/factoring, reload-chain metadata, or synthetic 100-200 load dataset work.

## Current Dependency State

`requirements.txt` intentionally keeps active foundation work standard-library-only. Local runtime inspection found:

```text
pypdf: available
PyPDF2: not available
pdfplumber: not available
fitz / PyMuPDF: not available
```

No new dependency is needed for the first local dry-run because `pypdf` is already available in the current environment.

## Extractor Candidates

### pypdf

Recommended first extractor.

Why:

- already available locally;
- pure Python and light enough for a dry-run helper;
- sufficient for first text-layer extraction attempts;
- does not require OCR or external services.

Limits:

- scanned/image-only PDFs may return empty text;
- layout order may be imperfect;
- tables, headers, footers, and multi-column sections may be jumbled;
- extraction quality should be judged through safe summaries only.

### PyPDF2

Fallback candidate only if already installed in a future environment.

Current state:

- not available locally;
- not worth adding while `pypdf` is available.

### pdfplumber

Possible future audit candidate for layout-sensitive extraction.

Current state:

- not available locally;
- should not be added without a separate dependency decision block.

### fitz / PyMuPDF

Possible future audit candidate for stronger document handling.

Current state:

- not available locally;
- should not be added without a separate dependency decision block.

## Recommended First Extractor

Use `pypdf` for the first helper:

```text
extract_pdf_text_local(file_path)
```

The helper should:

- read one local PDF path;
- return extracted text to the caller only;
- return safe metadata such as extractor name, page count, character count, extraction status, and warnings;
- never save extracted text;
- never write output files;
- never print full raw text from CLI reports.

## Fallback Behavior

If `pypdf` is unavailable:

- return `UNSUPPORTED`;
- include a warning that no local extractor dependency is available;
- do not attempt OCR;
- do not install dependencies automatically.

If extraction fails:

- return `EXTRACTION_FAILED`;
- include a concise warning without private document text.

If extraction succeeds but returns no text:

- return `EMPTY_TEXT`;
- treat the document as not ready for parser dry-run from PDF text alone;
- do not run OCR in this phase;
- recommend manual pasted-text dry-run or later PDF/OCR strategy audit.

## OCR Policy

OCR is out of scope for this phase.

Reasons:

- OCR introduces a larger dependency and privacy surface;
- scanned/low-quality documents need a separate safety/design audit;
- OCR output is still private extracted text and must not be committed;
- current goal is to validate local text-layer extraction only.

## Privacy Rules

Private PDFs stay local under:

```text
data/private_ratecons/originals/
```

Do not commit:

- private PDFs;
- extracted private text;
- private dry-run outputs containing raw text;
- real broker/customer/driver/company names;
- phone numbers, emails, addresses, MCs, reference numbers, or document snippets.

Safe reports may include only:

- anonymized label such as `RATECON_001`;
- extraction status;
- extractor name;
- page count;
- character count;
- warning counts or generic warning labels;
- intake missing/needs-check summaries;
- result categories.

## Next Safe Implementation

The next implementation should be a local helper only:

```text
app/market_intelligence/intake/pdf_text_extraction.py
```

It should be tested with mocked extractor behavior or temp fake files only. Tests must not use private PDFs or private text.
