# Intake Record Model Proposal

Date: 2026-05-29

Scope:

- design only
- no parser implementation
- no storage implementation
- no Gmail/email integration
- no Google Sheets export
- no Telegram upload handling
- no DispatchCase writes
- no OCR, DAT/API, Google Maps, scheduler, or live automation

## Purpose

An intake record is the future normalized evidence object produced from a RateCon or broker document.

It should be JSON-ready, deterministic, and safe to inspect before it is connected to live workflows.

The record should answer:

- What source produced this information?
- What dispatch fields were extracted?
- What is missing?
- What needs human verification?
- Is this record linked to a DispatchCase yet?

## Proposed Record Shape

```json
{
  "intake_id": "",
  "source_type": "",
  "source_file_name": "",
  "source_file_path": "",
  "received_at_utc": "",
  "parser_version": "",
  "broker_name": "",
  "broker_mc": "",
  "rate": 0,
  "pickup_location": "",
  "pickup_date": "",
  "pickup_time": "",
  "delivery_location": "",
  "delivery_date": "",
  "delivery_time": "",
  "commodity": "",
  "weight": 0,
  "reference_id": "",
  "equipment": "",
  "special_requirements": [],
  "missing_fields": [],
  "needs_check_fields": [],
  "field_confidence": {},
  "raw_text_available": false,
  "linked_dispatch_case_id": "",
  "notes": "",
  "source": "ratecon_intake"
}
```

## Field Rules

Use empty strings, `0`, `false`, empty lists, or empty dicts for missing values.

Do not omit expected keys in the normalized record.

Do not store parser uncertainty only in prose. Use:

```text
missing_fields
needs_check_fields
field_confidence
```

`field_confidence` should be optional for early implementation, but the shape should allow future parser confidence without changing the record contract.

Example:

```json
{
  "rate": "HIGH",
  "pickup_location": "MEDIUM",
  "weight": "LOW"
}
```

## Required For Dispatch Review

These fields should trigger `missing_fields` when absent:

- `broker_name` or `broker_mc`
- `rate`
- `pickup_location`
- `delivery_location`
- `pickup_date`
- `delivery_date`
- `reference_id`
- `equipment`
- `weight`

`broker_name` and `broker_mc` are a pair rule:

- if both are missing, broker identity is missing
- if only broker MC is missing, mark broker MC as `needs_check_fields`
- if only broker name is missing, mark broker name as `needs_check_fields`

## Missing Field Warnings

Missing fields mean the system did not find enough data to use the record safely without dispatcher review.

Examples:

- no rate
- no pickup location
- no delivery location
- no reference/load number
- no equipment
- no pickup or delivery date
- no weight

Missing fields should not crash intake creation.

They should produce a record with clear warnings.

## Needs-Check Warnings

Needs-check fields mean data exists, but it is ambiguous or risky.

Examples:

- broker MC missing while broker name exists
- rate extracted but currency/format is unclear
- pickup or delivery location lacks state
- date extracted without appointment time
- multiple possible load numbers found
- multiple weights found and summed
- equipment looks incompatible with driver equipment
- special requirements mention tarps, OD, oversize, permits, escorts, hazmat, TWIC, or tracking
- commodity text indicates coil/pipe/steel but securement details are unclear

Needs-check fields should feed future human summary text.

They should not automatically become hard dispatch blocks.

## Special Requirements

`special_requirements` should be a list of normalized labels, not one free-form blob.

Possible early labels:

```text
TARPS
OD
OVERSIZE
PERMIT
ESCORT
HAZMAT
TWIC
TRACKING
APPOINTMENT_REQUIRED
NO_CONESTOGA
FLATBED_ONLY
```

The original raw requirement text can be kept in `notes` or future `raw_extracts`, but the normalized record should expose machine-readable labels.

## DispatchCase Link Later

`linked_dispatch_case_id` should remain empty until matching is explicit and tested.

Future matching candidates:

- `reference_id`
- `broker_mc`
- `broker_name`
- `pickup_location`
- `delivery_location`
- `rate`

If matching confidence is low, keep the intake record unlinked and show it as needing dispatcher action.

Do not create a DispatchCase from an intake record until that policy is designed separately.

## Future Tests

Before implementation, add focused tests for:

- full clean record defaults
- safe defaults for missing fields
- required field validation
- broker name / broker MC pair rule
- needs-check field generation
- special requirement normalization
- JSON serialization
- no mutation of input data
- no parser, Telegram, Google Sheets, Gmail, DispatchCase, or scheduler imports in pure helpers

## Recommended First Implementation

Implemented first helper:

```text
app/market_intelligence/intake/record.py
```

Focused tests:

```text
tests/test_intake_record.py
```

Expected helper responsibilities:

- build a normalized record from dict/object input
- apply safe defaults
- calculate `missing_fields`
- calculate `needs_check_fields`
- keep output JSON-serializable

Current helper remains pure. It does not parse PDFs, read/write files, send Telegram, write Google Sheets, call Gmail/email APIs, write DispatchCase events, import legacy `app/load_intake`, or make dispatch decisions.

## Parser Contract

Implemented parser boundary helper:

```text
app/market_intelligence/intake/parser_contract.py
tests/test_intake_parser_contract.py
```

`normalize_parser_output(...)` accepts dict/object parser output, applies optional source metadata, and returns a JSON-ready intake record through `build_intake_record(...)`.

Parser contract scenarios exist in:

```text
tests/fixtures/parser_contract_outputs.py
tests/test_parser_contract_scenarios.py
```

They use fake parser outputs only and prove that future parser outputs normalize into intake records and dry-run summaries.

This is a contract only. Future parser implementations may read PDF text, OCR text, email body text, Telegram upload content, or manual JSON, but their output must be structured fields. The parser layer must not make dispatch decisions, send Telegram, write Google Sheets, create DispatchCases, write event logs, or import legacy `app/load_intake`.

Parser confidence policy is represented by:

```text
app/market_intelligence/intake/parser_confidence.py
tests/test_parser_confidence.py
```

Accepted levels are `HIGH`, `MEDIUM`, `LOW`, and `UNKNOWN`. Missing or invalid confidence values normalize to `UNKNOWN`. This is extraction confidence only and does not decide dispatch behavior.

## Record Status

Implemented pure status helper:

```text
app/market_intelligence/intake/status.py
tests/test_intake_record_status.py
```

It classifies normalized records from `missing_fields` and `needs_check_fields` only:

- `MISSING_FIELDS`
- `NEEDS_CHECK`
- `READY_FOR_REVIEW`

This status is intake-review context only. It is not a dispatch MATCH/BLOCK/REVIEW decision.

## Manual Dry-Run Summary

Implemented dry-run summary layer:

```text
app/market_intelligence/intake/summary.py
scripts/run_intake_record_dry_run.py
tests/test_intake_record_summary.py
```

The summary layer normalizes source data through `build_intake_record(...)`, returns structured status/missing/needs-check data, and formats a human-readable dry-run summary.

It is still manual and local only. The CLI can accept a pasted JSON object through `--json` or one explicit JSON object file through `--json-file`, but it does not parse PDFs, write files, send Telegram, write Google Sheets, call Gmail/email APIs, write DispatchCase events, or import legacy `app/load_intake`.

Example:

```powershell
py scripts/run_intake_record_dry_run.py --json '{""broker_name"":""Acme Logistics"",""broker_mc"":""123456"",""rate"":3200,""pickup_location"":""Dallas, TX"",""pickup_date"":""2026-05-30"",""delivery_location"":""Denver, CO"",""delivery_date"":""2026-05-31"",""commodity"":""Steel coils"",""weight"":42000,""reference_id"":""REF-123"",""equipment"":""Conestoga""}'
py scripts/run_intake_record_dry_run.py --json-file tests\fixtures\intake_sample_records\clean_full_ratecon.json
```

## Synthetic Fixtures

Synthetic intake fixtures now exist for focused dry-run testing:

```text
tests/fixtures/synthetic_intake_records.py
tests/test_synthetic_intake_records.py
```

The fixtures cover clean records, missing broker fields, missing dates, missing weight, missing commodity, missing reference id, special requirements, weak confidence fields, and missing rate. They are fake data only.

Plain synthetic JSON sample records also exist for future CLI file-input dry-runs:

```text
tests/fixtures/intake_sample_records/
tests/test_intake_sample_json_fixtures.py
```

They are fake JSON objects only and can be used with the dry-run CLI `--json-file` command.

The fixtures are exercised by:

```text
app/market_intelligence/intake/scenario_runner.py
scripts/run_intake_scenarios.py
tests/test_intake_scenario_runner.py
```

This runner is dry-run only and uses synthetic data only.

Compatibility note:

```text
app/market_intelligence/intake_record.py
app/market_intelligence/intake_parser_contract.py
app/market_intelligence/intake_record_summary.py
app/market_intelligence/intake_record_repository.py
app/market_intelligence/intake_record_status.py
app/market_intelligence/intake_record_report.py
app/market_intelligence/intake_scenario_runner.py
```

These old import paths are thin wrappers around the package modules so existing scripts/tests remain stable.
