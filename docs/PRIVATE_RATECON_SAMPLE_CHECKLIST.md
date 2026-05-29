# Private RateCon Sample Checklist

Date: 2026-05-29

This checklist helps collect the first private RateCon batch for future parser dry-run work. It is documentation only. It does not add parser behavior, OCR, file reading, Gmail/email integration, Google Sheets, Telegram upload handling, Telegram sending, DispatchCase writes, DAT/API, Google Maps, scheduler/background processing, or legacy `app/load_intake` changes.

## Batch Size

Start small:

```text
10-15 private RateCons
```

Do not start with 100+ documents. A small varied set is easier to review manually and safer before parser behavior exists.

## Storage Rule

Private RateCons must stay local under:

```text
data/private_ratecons/
```

This folder is gitignored. Do not commit private documents.

Do not commit:

- real broker names
- real customer names
- real driver names
- real company names
- phone numbers
- emails
- signatures
- real reference/load numbers
- real appointment details
- real pickup/delivery addresses from private documents

## First Batch Categories

Try to collect one example per category if possible:

1. Simple clean RateCon
2. Missing weight
3. Missing commodity
4. Missing broker MC
5. Unusual reference/load number placement
6. Multiple pickups
7. Multiple deliveries
8. Appointment times/windows
9. Detention/layover/lumper/fees
10. Equipment/special requirements
11. Bad scan or hard-to-read PDF
12. Rate with accessorials or separate linehaul
13. Broker/customer contact-heavy document
14. One Conestoga-specific example
15. One flatbed-specific example

It is okay if a document covers multiple categories. The goal is variety, not volume.

## File Naming

Use local-only names that describe the structural challenge without exposing private details.

Examples:

```text
01_clean_simple.pdf
02_missing_weight.pdf
03_missing_commodity.pdf
04_missing_broker_mc.pdf
05_unusual_reference_label.pdf
06_multiple_pickups.pdf
07_multiple_deliveries.pdf
08_appointment_window.pdf
09_accessorials_linehaul.pdf
10_bad_scan.pdf
```

Avoid broker/customer names in file names.

## Manual Review Notes

For each private sample, keep a local note outside Git if useful:

- what fields are easy to see
- what fields are missing
- what fields are ambiguous
- whether rate appears more than once
- whether pickup/delivery has exact time or window
- whether equipment is explicit or hidden in notes
- whether the document has multi-stop structure

Do not commit these notes unless fully anonymized.

## Public Fixture Conversion

If a private example becomes useful as a public test:

1. create a synthetic copy
2. remove all broker/customer/driver/company/contact data
3. replace real MC/reference numbers with fake values
4. replace real addresses with fake city/state examples
5. replace real appointment dates/times with fake dates/times
6. preserve only the structural issue being tested

Public synthetic examples can live in:

```text
tests/fixtures/intake_sample_records/
tests/fixtures/parser_contract_outputs.py
tests/fixtures/parser_expected_outputs.py
```

## Before Parser Dry-run

Before any future parser dry-run touches private files:

- confirm `git status` is clean or shows only intentional code/docs
- confirm `data/private_ratecons/` remains ignored
- confirm tests use synthetic fixtures only
- confirm no private file path is hardcoded in tests
- confirm parser output is reviewed before any optional save

## Expansion Rule

Expand only after the first 10-15 private examples have been reviewed and parser dry-run output is stable.

Larger private batches must still remain local and should not be used in automated tests.
