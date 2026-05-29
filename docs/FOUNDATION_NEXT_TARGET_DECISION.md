# Foundation Next Target Decision

Date: 2026-05-29

Scope:

- recommendation only
- no implementation
- no parser changes
- no storage implementation
- no Gmail/email, Google Sheets, Telegram upload, OCR, DAT/API, Google Maps, scheduler, or live automation
- no reload-chain metadata work

## Context

Completed foundation documents:

```text
docs/LOAD_INTAKE_BOUNDARY_REVIEW.md
docs/RATECON_INTAKE_WORKFLOW.md
docs/INTAKE_RECORD_MODEL.md
```

Current conclusion:

- `app/load_intake/` remains isolated legacy/prototype code.
- Future RateCon/document intake should produce structured evidence, not dispatch decisions.
- The JSON-ready record shape is now documented.

## Recommended Next Implementation Target

Recommended next target:

```text
JSON-ready intake record helper
```

Suggested future module:

```text
app/market_intelligence/intake_record.py
```

Suggested future tests:

```text
tests/test_intake_record.py
```

Why this is the safest next step:

- It implements only the accepted record contract.
- It does not require PDF/OCR/Gmail/Telegram/Google Sheets integration.
- It can be fully test-first.
- It gives future parser work a stable output target.
- It keeps `app/load_intake/` isolated instead of expanding legacy behavior.

## First Helper Scope

The first helper should only:

- build a normalized JSON-ready record from dict/object input
- apply safe defaults
- calculate `missing_fields`
- calculate `needs_check_fields`
- keep records JSON-serializable
- avoid mutating inputs

It should not:

- parse PDFs
- read files
- write files
- send Telegram
- write Google Sheets
- call Gmail/email APIs
- write DispatchCase events
- make dispatch decisions
- import `pypdf`, `gspread`, Telegram sender/notifier, DispatchCase, event logger, scheduler, DAT/API, or Google Maps code

## Recommended Test Cases

First helper tests should cover:

- full clean record
- missing mandatory fields
- broker name / broker MC pair rule
- safe defaults for missing inputs
- needs-check fields for partial broker/date/location/equipment data
- special requirements as a normalized list
- JSON serialization
- no input mutation
- no forbidden imports

## Secondary Targets

After the helper:

1. Manual intake dry-run CLI
   - should accept synthetic/dict-like data first
   - should print a human-readable summary
   - should not parse PDFs yet

2. Synthetic RateCon/intake scenarios
   - small scenario tests only
   - not the 100-200 load dataset

3. Reload-chain DispatchCase policy audit
   - should happen before reload-chain metadata wiring
   - should remain audit-only first

## Not Next

Do not build next:

- Gmail/email ingestion
- Google Sheets export
- Telegram upload handling
- OCR service integration
- PDF parser expansion
- DispatchCase writes from intake records
- broker follow-up email
- DAT/API or Google Maps integration
- scheduler/background processing
- reload-chain metadata
- synthetic 100-200 load dataset

## Decision

Implemented:

```text
JSON-ready intake record helper
```

Files:

```text
app/market_intelligence/intake_record.py
tests/test_intake_record.py
```

The helper is pure and does not implement parser, storage, Telegram, Gmail/email, Google Sheets, DispatchCase, DAT/API, Google Maps, scheduler, or legacy `app/load_intake` behavior.

## Intake Foundation Status

```text
JSON-ready intake record helper - complete
Manual intake dry-run summary helper/CLI - complete
Synthetic intake fixtures - complete
Synthetic intake scenario runner - complete
Private RateCon fixture safety - complete
```

## Next Target Evaluation

Candidate: manual intake dry-run CLI with JSON input.

- Recommended next.
- Safe because it can accept typed/pasted JSON data without parsing PDFs.
- Useful because future parsers, Telegram upload handlers, and email intake can all target the same record shape.
- Should not read real PDF files or write storage.

Candidate: simple JSON repository for intake records.

- Good second target.
- Should wait until manual JSON input is proven useful.
- Would be local JSON persistence only, not SQLite/DispatchCase.

Candidate: parser interface contract only.

- Useful after JSON input CLI.
- Should define input/output interface without implementing PDF parsing.

Candidate: Telegram upload design audit.

- Not next.
- Should wait until manual JSON dry-run and parser interface contract are stable.

Candidate: RateCon parser audit.

- Not next.
- Should wait until manual JSON dry-run and parser interface contract are stable.

Candidate: reload-chain DispatchCase policy audit.

- Still important.
- Keep separate from intake work and do before reload-chain metadata wiring.

## Decision

Completed mini-block:

```text
Manual intake dry-run CLI with JSON input
```

Scope should be:

- accept JSON from a command-line string only
- normalize through `build_intake_record(...)`
- summarize through `build_intake_record_summary(...)`
- print dry-run output
- no file input
- no storage
- no parser
- no Telegram/Gmail/Google Sheets/DispatchCase integration

The CLI accepts command-line JSON strings only. JSON file input remains a separate design decision and is not implemented yet.

Recommended next target:

```text
Intake sample JSON fixture foundation
```

This should add synthetic JSON examples only. It should not implement file input yet.

Recommended follow-up target:

```text
Intake dry-run CLI JSON file input
```

This is approved only for explicit local JSON object files after synthetic sample fixtures exist.

Design reference:

```text
docs/INTAKE_JSON_FILE_INPUT_AUDIT.md
```

## Still Not Next

Do not build next:

- live PDF parsing
- OCR
- Telegram upload handling
- Gmail/email ingestion
- Google Sheets export
- DispatchCase writes
- event logger writes
- DAT/API
- Google Maps
- scheduler/background processing
- reload-chain metadata
- synthetic 100-200 load dataset
