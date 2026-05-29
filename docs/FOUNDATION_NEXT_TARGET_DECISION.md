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

## Architecture Structure Update

Current structural state:

```text
app/market_intelligence/intake/
```

The intake foundation modules now live in a dedicated package:

- `record.py`
- `parser_contract.py`
- `summary.py`
- `repository.py`
- `status.py`
- `report.py`
- `scenario_runner.py`

Old root-level intake module paths remain thin compatibility wrappers so existing scripts and tests keep working during the package migration phase.

Current structural guard:

```text
Intake package boundary tests
```

These tests protect the new package from Telegram, DispatchCase, parser/OCR, Gmail/email, Google Sheets, scheduler, DAT/API, Google Maps, and legacy `app/load_intake` imports before any private RateCon parser audit begins.

## Architecture Structure Closeout

Completed structure work:

- package layout proposal is documented
- development structure rules are updated
- intake foundation modules live under `app/market_intelligence/intake/`
- old intake import paths remain compatibility wrappers
- intake package import compatibility tests exist
- intake package boundary tests exist

Recommended next target:

```text
Private RateCon parser audit
```

Why this is next:

- intake now has a stable package boundary and parser-output contract
- parser risk should be reviewed before any text/PDF parsing behavior exists
- no real documents need to be committed or processed for the audit
- the audit can define field extraction risk, confidence handling, missing-field expectations, and future test scenarios

Secondary candidate:

```text
Reload-chain DispatchCase policy audit
```

This remains important before reload-chain metadata wiring, but it is less urgent than confirming the RateCon/parser boundary now that the intake package has been isolated.

Not recommended next:

- intake parser manual text dry-run adapter: should wait for the parser audit
- synthetic intake scenario expansion: useful later, but current fixtures are enough for the next audit
- reload-watch package migration: reload-watch is stable and should stay paused before live wiring
- Telegram package migration: too broad while metadata and outbox behavior are still being stabilized

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
Parser interface contract - complete
Intake record status helper - complete
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

## Parser Contract Decision

Completed mini-block:

```text
Parser interface contract foundation
```

Files:

```text
app/market_intelligence/intake_parser_contract.py
tests/test_intake_parser_contract.py
```

The helper normalizes future parser output into the existing intake record shape. It does not parse PDFs, read files, write files, send Telegram, call Gmail/email APIs, write Google Sheets, create DispatchCases, write event logs, use DAT/API, call Google Maps, run scheduler/background work, or import legacy `app/load_intake`.

Recommended next intake target:

```text
Intake JSON repository policy audit
```

This should decide whether local JSON persistence is needed before any storage helper is implemented.

## Intake JSON Repository Policy

Completed audit:

```text
docs/INTAKE_JSON_REPOSITORY_POLICY.md
```

Recommended implementation:

```text
app/market_intelligence/intake_record_repository.py
tests/test_intake_record_repository.py
```

Policy summary:

- use a gitignored JSON list file at `data/intake_records.json`
- store JSON-ready intake records only
- do not store PDFs, OCR text, email bodies, Telegram file bytes, or DispatchCase events
- repository should not decide status or generate IDs
- upsert by `intake_id` when available
- tests must use temp files only

Implementation status:

```text
Intake JSON repository foundation - complete
```

Intake status helper status:

```text
Intake record status helper foundation - complete
```

CLI save status:

```text
Intake repository dry-run CLI optional save - complete
```

Next safe target:

```text
Intake foundation follow-up target selection
```

## Intake Follow-up Target Selection

Completed foundation since the parser contract:

```text
Explicit intake id for dry-run CLI - complete
Intake repository report CLI - complete
Parser contract scenario tests - complete
Private RateCon local testing plan - complete
```

Options evaluated:

1. Parser dry-run adapter with manual text input
2. Simple text-to-field manual parser stub
3. Intake repository cleanup/status report improvements
4. Private RateCon parser audit
5. Pause intake and do reload-chain DispatchCase policy audit

Recommended next target:

```text
Private RateCon parser audit
```

Why:

- Current intake foundation is now strong enough to receive parser output.
- But implementing even a simple text-to-field parser would start parser behavior before parser risks are understood.
- A parser audit can inspect expected RateCon layouts, legacy/prototype boundaries, output fields, confidence handling, and missing-field behavior without reading or committing real documents.
- It keeps PDF/OCR/Gmail/Telegram/Google Sheets/DispatchCase work out of scope.

Recommended follow-up after audit:

```text
Parser dry-run adapter with manual text input
```

This should be implemented only if the audit defines a narrow adapter contract. It should remain dry-run only and should not parse PDFs, run OCR, upload Telegram files, send emails, write Sheets, or create DispatchCases.

Not recommended next:

- Simple text-to-field parser stub: too easy to become hidden parser behavior without audit.
- Repository cleanup/report improvements: useful later, but current report is enough for foundation dry-run.
- Reload-chain DispatchCase policy audit: still important, but can wait until intake parser audit decides whether intake remains the active foundation target.

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

## Parser Preparation Closeout

Completed parser preparation:

- private RateCon parser audit
- private RateCon sample checklist
- synthetic parser expected-output fixtures
- parser confidence policy/helper
- synthetic parser scenario runner and CLI

Options evaluated:

1. manual text parser dry-run adapter
2. private RateCon parser interface CLI that accepts pasted text only
3. first PDF text extraction audit
4. synthetic parser scenario runner
5. pause parser and do reload-chain DispatchCase policy audit

Recommended next target:

```text
Manual pasted-text parser adapter design
```

Why this is safest:

- synthetic parser reporting now exists
- the next risk is defining how pasted text should enter the parser boundary
- design should come before any extraction logic
- it keeps PDF parsing, OCR, Telegram upload, Gmail/email, Google Sheets, DispatchCase writes, DAT/API, Google Maps, and scheduler work out of scope

The pasted-text adapter should remain design-first. It should not start extracting fields until the input/output contract, confidence policy, and test scenarios are accepted.

Not recommended next:

- first PDF text extraction audit: still too close to file/document handling before synthetic parser reporting exists
- private RateCon parser interface CLI: should wait until pasted-text adapter design is accepted
- reload-chain DispatchCase policy audit: important, but separate from parser preparation

## Next Parser Target Decision

Completed since the previous parser decision:

- synthetic parser scenario runner helper
- synthetic parser scenario CLI
- parser scenario README/docs sync
- manual pasted-text parser adapter design

Options evaluated:

1. manual pasted-text parser adapter foundation
2. parser scenario expansion
3. private RateCon field inventory preparation
4. first PDF text extraction audit
5. pause parser and do reload-chain DispatchCase policy audit

Recommended next target:

```text
Manual pasted-text parser adapter foundation
```

Why:

- pasted text avoids PDF/file/OCR risk
- the adapter can be pure and test-first
- existing parser expected-output fixtures define the target shape
- existing parser scenario runner can verify normalized output behavior
- it creates business value by letting synthetic or manually pasted text be dry-run before private documents are touched

Required constraints:

- synthetic text fixtures first
- no private RateCon text in tests
- no file reading
- no PDF parsing
- no OCR
- no Telegram upload/sending
- no Gmail/email
- no Google Sheets
- no DispatchCase writes
- no DAT/API
- no Google Maps
- no scheduler/background processing

Suggested first implementation:

```text
app/market_intelligence/intake/pasted_text_parser_adapter.py
tests/test_pasted_text_parser_adapter.py
```

The first adapter should be conservative. It should return structured parser output with confidence values and blanks for unknown fields rather than pretending uncertain text is reliable.

Secondary target:

```text
Parser scenario expansion
```

Add more synthetic text/parser-output scenarios only after the adapter shape is accepted.

Not recommended next:

- first PDF text extraction audit: too early before pasted-text dry-run proves the boundary
- private RateCon field inventory preparation: useful later, but should wait until the pasted-text adapter gives us a manual dry-run path
- reload-chain DispatchCase policy audit: still important, but not part of parser preparation

## Pasted-text Parser Closeout

Completed pasted-text parser preparation:

- synthetic pasted-text RateCon fixtures
- conservative pasted-text parser adapter
- pasted-text scenario runner
- pasted-text parser dry-run CLI
- pasted-text scenario CLI

Current commands:

```powershell
py scripts/run_pasted_text_parser_dry_run.py
py scripts/run_pasted_text_parser_dry_run.py --text "Broker: Synthetic Broker..."
py scripts/run_pasted_text_scenarios.py
```

Options evaluated:

1. expand synthetic pasted-text scenarios
2. private RateCon field inventory plan
3. first PDF text extraction audit
4. parser confidence refinement
5. pause parser and do reload-chain DispatchCase policy audit

Recommended next target:

```text
Private RateCon field inventory plan
```

Why:

- pasted-text dry-run is stable enough to show how parser output flows into intake summaries
- before touching real files, the project should define how a human will inventory private RateCon fields safely
- this can stay docs/local-process only
- it prepares eventual private review without parser/OCR/PDF work

What it should include:

- private local-only review template
- fields to record manually from each private RateCon
- expected missing/needs-check notes
- confidence notes
- rules for anonymizing any public fixture derived from private review
- explicit reminder not to commit private documents or extracted private records

Not recommended next:

- PDF text extraction audit: still too early
- OCR: not yet
- live Telegram upload: not yet
- Gmail/email/Google Sheets: not yet
- reload-chain DispatchCase policy audit: important but separate from intake/parser preparation
