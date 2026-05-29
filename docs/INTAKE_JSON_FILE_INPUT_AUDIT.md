# Intake JSON File Input Audit

This audit decides whether the manual intake dry-run CLI should later accept a local JSON file.

It is design-only. It does not implement file input, parser behavior, storage, Telegram upload handling, Gmail/email, Google Sheets, DispatchCase writes, OCR, Google Maps, DAT/API, or scheduler behavior.

## Current State

Current dry-run input paths:

```text
scripts/run_intake_record_dry_run.py
  sample mode
  --json command-line JSON object
```

Both paths normalize through `build_intake_record(...)` and summarize through `build_intake_record_summary(...)`.

The CLI does not read files today.

## Recommendation

`--json-file` is a safe next implementation target if it stays narrow:

- explicit local file path only
- one JSON object only
- no JSON list/batch mode in the first version
- no directory scans or glob expansion
- no PDF/OCR parsing
- no storage writes
- no DispatchCase writes
- no Telegram/Gmail/Google Sheets integration

The command should behave like `--json` after reading the object:

```text
local JSON object -> build_intake_record(...) -> dry-run summary text
```

## Sample JSON Location

Public examples should live under:

```text
tests/fixtures/intake_sample_records/
```

Those files must be synthetic only. They must not contain real broker, customer, driver, contact, reference, appointment, or RateCon data.

Private local JSON extracted from real RateCons should stay outside Git. Preferred local paths:

```text
data/private_ratecons/
data/private_intake_records/
```

`data/private_ratecons/` is already gitignored. If `data/private_intake_records/` is introduced later, it should be gitignored before use.

## Safety Rules

- Missing file should fail with a readable error.
- Invalid JSON should fail with a readable error.
- JSON list should be rejected clearly in the first version.
- A JSON object should run the same dry-run summary as `--json`.
- Tests must use temp files or synthetic fixture files only.
- The CLI must not read real runtime/private paths in tests.

## Tests Needed Before Implementation

- valid JSON file produces dry-run summary
- missing file returns a readable error
- invalid JSON returns a readable error
- JSON list is rejected clearly
- summary output includes the dry-run warning
- tests use temp files or synthetic fixtures only
- no parser/storage/Telegram/Gmail/Google Sheets/DispatchCase imports

## Decision

Approved next implementation target:

```text
Intake sample JSON fixture foundation
```

Then implement:

```text
Intake dry-run CLI JSON file input
```

only after the synthetic sample files exist and remain clearly fake.
