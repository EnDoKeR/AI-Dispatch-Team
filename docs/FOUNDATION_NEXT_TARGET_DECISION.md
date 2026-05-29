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

## Product Alignment Closeout

Completed product-alignment foundation:

- `docs/PRODUCT_STRATEGY.md` reframes the project as a Dispatch Operating Intelligence System for small and mid-size carriers.
- `FLOW.md` describes the intended flow from intake to DispatchCase, DecisionEngine, adapters, Event Timeline, documents, and future accounting/replay layers.
- `README_SETUP.md` documents the current dependency position: core foundation work uses the Python standard library, while `pypdf`, `gspread`, Google auth, and `geopy` remain optional/manual or legacy dependencies.
- `docs/DEVELOPMENT_RULES.md` now separates core domain logic from adapters and requires new modules to identify their responsibility category.

Options evaluated:

1. requirements/setup cleanup
2. DecisionEngine architecture audit
3. DispatchCase/Event Timeline gap audit
4. accounting/factoring document model audit
5. pasted-text parser adapter continuation
6. reload-chain DispatchCase policy audit

Recommended next target:

```text
DecisionEngine architecture audit
```

Why:

- product direction now depends on the DecisionEngine being core and interface-independent
- current work has already hardened intake, metadata, reload-watch dry-runs, and parser boundaries
- before accounting/factoring, replay, or missed-opportunity logic is added, decision/risk logic should be audited for Telegram coupling, mixed responsibilities, and explainability gaps
- this can be audit-only first, with no runtime behavior change

Recommended second target:

```text
DispatchCase/Event Timeline gap audit
```

Why:

- DispatchCase is the operational backbone of the product
- intake records, future documents, dispatcher feedback, and accounting/factoring packets need a reliable timeline policy
- this audit should happen before any new case-writing behavior is added

Not recommended next:

- requirements/setup cleanup: basic setup policy is now documented, and no required third-party dependencies need to be added
- accounting/factoring document model audit: valuable, but should follow DecisionEngine and DispatchCase/Event Timeline audits
- pasted-text parser continuation: stable enough to pause while core architecture is reviewed
- reload-chain DispatchCase policy audit: still important, but less urgent than the general DispatchCase/Event Timeline gap audit

Do not implement during the next audit:

- live Telegram behavior
- Telegram buttons
- DAT/API
- Google Maps
- Gmail/email integration
- Google Sheets integration
- PDF/OCR parser behavior
- real factoring submission
- autonomous booking or financial/legal commitments

## DecisionEngine Architecture Audit Closeout

Completed DecisionEngine audit/design foundation:

- `docs/DECISION_ENGINE_AUDIT.md` inventories where current decision/risk/recommendation logic lives.
- `docs/DECISION_ENGINE_CONTRACT.md` proposes the future DecisionEngine output shape and boundary rules.
- `docs/DECISION_ENGINE_CONTRACT.md` also maps future input signal groups.
- `docs/DECISION_ENGINE_RISK_FLAGS.md` defines a first risk flag taxonomy.

Options evaluated:

1. pure DecisionEngine result model/helper
2. risk flag constants module
3. DecisionEngine adapter around current `MarketLoad` decision logic
4. DecisionEngine dry-run scenario runner
5. postpone and do DispatchCase/Event Timeline gap audit

Recommended next target:

```text
Decision risk flag constants/helper
```

Why:

- the taxonomy is documented but not yet protected by code
- constants/helper can be pure and side-effect-free
- it does not change `MarketLoad.apply_search_request(...)`
- it does not change Telegram, DispatchCase, storage, or live behavior
- it creates a stable vocabulary for future DecisionEngine results and tests

Suggested scope:

```text
app/market_intelligence/decision_risk_flags.py
tests/test_decision_risk_flags.py
```

The helper should expose flag names, categories, usual action levels, and lookup/validation helpers only. It should not apply flags to loads yet.

Recommended second target:

```text
DecisionEngine result model/helper
```

Why:

- after stable flags exist, a pure result builder can normalize `decision`, `category`, reasons, flags, missing fields, confidence, approval, and recommended next action
- it can be tested without wrapping current `MarketLoad` behavior yet
- it prepares the future adapter around existing decision logic

Not recommended next:

- adapter around current `MarketLoad` decision logic: useful, but should wait until risk flags and result shape have pure helpers
- DecisionEngine scenario runner: should wait until a result helper exists
- DispatchCase/Event Timeline gap audit: still important, but can follow the first two pure DecisionEngine helpers unless a product decision requires timeline policy first

Do not implement in the next DecisionEngine helper block:

- live Telegram behavior
- DispatchCase writes
- file moves/package migration
- external APIs
- parser/PDF/OCR behavior
- accounting/factoring behavior
- changes to existing `MATCH` / `REVIEW_ONCE` / `BLOCK` decisions

## Pure DecisionEngine Foundation Closeout

Completed pure DecisionEngine foundation:

- `app/market_intelligence/decision_engine/risk_flags.py`
  - stable risk flag constants
  - normalization
  - deduplication
  - category/action/metadata lookup
- `app/market_intelligence/decision_engine/result.py`
  - JSON-ready DecisionResult builder
  - safe defaults
  - risk flag normalization
  - confidence and decision normalization
  - source signal normalization
- `app/market_intelligence/decision_engine/approval_modes.py`
  - conservative approval mode helper
  - no autonomous booking, financial, legal, or factoring commitments
- `app/market_intelligence/decision_engine/signals.py`
  - JSON-ready DecisionEngine signal bundle helper
  - load, notes, driver, broker, market, dispatch memory, intake, and approval signal groups

Current status:

- pure helpers only
- no runtime wiring
- no `MarketLoad.apply_search_request(...)` change
- no Telegram behavior change
- no DispatchCase behavior change
- no market snapshot behavior change

Options evaluated:

1. DecisionEngine dry-run scenario runner
2. adapter around existing `MarketLoad` decision logic
3. DispatchCase/Event Timeline gap audit
4. synthetic load decision scenario dataset planning
5. reload-chain DispatchCase policy audit

Recommended next target:

```text
DecisionEngine dry-run scenario runner
```

Why:

- pure helpers are stable enough to exercise together
- a dry-run runner can use synthetic signal bundles and expected DecisionResults without touching current runtime behavior
- it will prove the shape of signal bundle -> DecisionResult before any adapter wraps existing `MarketLoad` logic
- it can stay fully synthetic and side-effect-free

Suggested scope:

```text
app/market_intelligence/decision_engine/scenario_runner.py
tests/test_decision_engine_scenario_runner.py
```

The runner should not evaluate real loads yet. It should process synthetic scenarios that already provide expected decisions/flags/reasons.

Recommended second target:

```text
Adapter around existing MarketLoad decision logic
```

Only after the dry-run runner is accepted, add a small adapter that reads current `MarketLoad` decision fields and returns a DecisionResult. It should preserve current behavior exactly.

Recommended major audit after that:

```text
DispatchCase/Event Timeline gap audit
```

This remains important before new case-writing behavior, intake-to-case linking, accounting/factoring documents, or replay/missed-opportunity expansion.

Not recommended next:

- synthetic 100-200 load dataset: too early before DecisionEngine dry-run scenarios
- reload-chain DispatchCase policy audit: important but separate from core DecisionEngine result flow
- accounting/factoring model: should wait until DispatchCase/Event Timeline gap audit

## DecisionEngine Dry-run Scenario Status

Completed:

- synthetic DecisionEngine scenario fixtures
- pure scenario runner
- manual scenario CLI

Command:

```powershell
py scripts/run_decision_engine_scenarios.py
```

Current status:

- synthetic-only
- no real load evaluation
- no runtime wiring
- no `MarketLoad.apply_search_request(...)` wrapper yet
- no Telegram/DispatchCase/market snapshot behavior change

Next target should be decided separately after reviewing dry-run output and risk.
