# RateCon Fixture Safety

Date: 2026-05-29

Scope:

- docs and `.gitignore` only
- no real RateCons added
- no parser changes
- no Telegram upload, OCR, Gmail/email, Google Sheets, DispatchCase, DAT/API, Google Maps, or scheduler work

## Private Local Folder

Future real RateCon/manual document testing should use:

```text
data/private_ratecons/
```

This folder is gitignored.

Do not commit real RateCons, broker documents, customer details, driver details, phone numbers, emails, reference numbers, broker MCs, appointment details, or any private operational document content.

## Public Synthetic Fixtures

Public fixtures belong in:

```text
tests/fixtures/
```

Current public fixture:

```text
tests/fixtures/synthetic_intake_records.py
```

Public fixtures must be synthetic or anonymized. They should not include real broker/customer/driver/contact data.

## First Real Testing Batch

When parser/dry-run tooling is ready, first real testing should use a small local-only batch:

```text
10-15 varied RateCons
```

Do not start with 100+ real documents.

Detailed private testing plan:

```text
docs/PRIVATE_RATECON_TESTING_PLAN.md
```

The first private batch should cover:

- clean standard RateCon
- missing broker MC
- missing or unclear appointment time
- missing commodity
- multiple weight lines
- special requirements
- equipment ambiguity
- unusual broker layout

## Safe Order

Safe future order:

1. Keep synthetic fixtures public and fake.
2. Keep real documents under `data/private_ratecons/`.
3. Build dry-run parser/output before any live upload or export.
4. Review extracted fields manually.
5. Only then consider DispatchCase linking or export workflows.

## Not Allowed Yet

Do not add yet:

- real RateCon files
- OCR
- live PDF parser expansion
- Telegram upload handling
- Gmail/email ingestion
- Google Sheets export
- DispatchCase writes from parsed documents
- DAT/API or Google Maps integration
- scheduler/background processing
