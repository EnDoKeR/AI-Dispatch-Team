# Private RateCon Batch 3 Findings

This document records safe/anonymized findings from the local private RateCon batch 3 dry-run. It must not contain private PDFs, extracted text, broker/customer/contact names, MCs, addresses, phone numbers, emails, reference numbers, appointment details, or document snippets.

## Baseline Run

Commands run locally:

```powershell
py scripts/run_private_ratecon_redacted_diagnostics.py --limit 3
py scripts/run_private_ratecon_layout_diagnostics.py --limit 3
py scripts/run_private_ratecon_pdf_dry_run.py --limit 3
py scripts/export_ratecon_dry_run_csv.py --limit 3
```

The CSV command was also rerun with an alternate ignored output path after the default CSV path was unavailable due to a local permission/lock condition.

## Safe Baseline Summary

| Label | Extraction | Chars | Pages | Result Category |
| --- | --- | ---: | ---: | --- |
| RATECON_001 | TEXT_EXTRACTED | 4636 | 2 | NEEDS_FIELD_FIX |
| RATECON_002 | EMPTY_TEXT | 0 | 2 | BAD_TEXT_EXTRACTION |
| RATECON_003 | TEXT_EXTRACTED | 10694 | 3 | NEEDS_FIELD_FIX |

## Repeating Missing Fields

- `broker_name`
- `broker_mc`
- `rate`
- `pickup_location`
- `delivery_location`
- `pickup_date`
- `delivery_date`
- `weight`
- `commodity`
- `equipment`

Additional missing field on one extracted document:

- `reference_id`

## Low-confidence Fields

Observed low-confidence categories:

- `rate`
- `special_requirements`

## Repeating Parser Gap Categories

Detected signals were present, but parser coverage still reported gaps for:

- `broker_name`
- `broker_mc`
- `rate`
- `pickup_location`
- `delivery_location`
- `weight`
- `commodity`
- `equipment`

Additional gap categories observed on one extracted document:

- `delivery_date`
- `reference_id`
- `special_requirements`

## Redacted Layout Shapes Observed

Only placeholder-safe shapes were reported:

- `load number: <ID>`
- `total carrier pay: <AMOUNT>`

## CSV Export

Safe CSV export produced 3 rows when written to an alternate ignored output path.

The default CSV path returned a local permission/lock error. This should be handled more gracefully by the export CLI, but it did not expose private text or values.

## Interpretation

PDF text extraction is working for two of three sampled documents. One sampled document produced `EMPTY_TEXT`, which belongs to PDF extraction refinement rather than parser hardening.

The main parser gaps are still value extraction around detected labels and document layouts. Parser improvements must continue to be driven by fake/anonymized scenarios that represent safe categories and placeholder shapes only.
