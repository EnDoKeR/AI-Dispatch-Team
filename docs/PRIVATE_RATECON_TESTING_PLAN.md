# Private RateCon Testing Plan

Date: 2026-05-29

This plan describes how to test future RateCon/document intake with real private documents without committing private operational data.

This is documentation only. It does not add parser behavior, OCR, PDF reading, Telegram upload handling, Gmail/email, Google Sheets, DispatchCase writes, DAT/API, Google Maps, or scheduler/background processing.

## Storage Rule

Real RateCons and broker documents must stay local under:

```text
data/private_ratecons/
```

That folder is gitignored.

Do not commit:

- real RateCon PDFs
- screenshots or scans of real documents
- real broker/customer/driver/contact data
- real reference numbers
- real appointment details
- phone numbers, emails, names, signatures, addresses, or contact notes

## First Testing Batch

The first real local-only testing batch should be small:

```text
10-15 varied RateCons
```

Do not start with 100+ real files. A small varied batch is easier to review manually and safer while parser behavior is still being designed.

## Suggested First Batch Categories

Include one or two examples from these categories:

1. simple clean RateCon
2. missing weight
3. missing commodity
4. multiple pickup/delivery
5. appointment times
6. detention/layover notes
7. reference number in unusual place
8. broker MC missing
9. unusual equipment/special requirements
10. poor scan / hard-to-read file

## Public Test Conversion

When turning a real RateCon case into a public test:

- create a synthetic or anonymized fixture
- remove broker/customer/driver/contact data
- replace real MC/reference numbers with synthetic values
- replace real appointment details with fake dates/times
- preserve only the structural challenge being tested

Public fixtures belong in synthetic test folders such as:

```text
tests/fixtures/intake_sample_records/
tests/fixtures/parser_contract_outputs.py
```

## Future Dry-run Flow

When a parser exists later, the safe local flow should be:

```text
private RateCon -> parser dry-run -> intake record -> dry-run summary/report
```

The first parser dry-run should not:

- send Telegram
- write Google Sheets
- write DispatchCase events
- call Gmail/email APIs
- run scheduler/background processing
- commit extracted private data

## Review Checklist

Before expanding real local testing:

- confirm `git status` does not show private documents
- confirm generated records do not include full private file paths
- confirm any saved dry-run records are in gitignored runtime files
- manually inspect missing/needs-check fields
- compare parser output against the source document by hand

## Expansion Rule

Only after the first 10-15 private examples are reviewed should the project expand to a larger local private batch.

Larger batches should still remain local/private until parser accuracy, redaction rules, and dry-run reporting are stable.
