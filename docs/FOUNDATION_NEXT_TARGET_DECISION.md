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

- Historical note: `app/load_intake/` was isolated legacy/prototype code at the time of this early decision. It has since been removed after a dedicated salvage/delete cleanup.
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
- It avoided expanding legacy behavior. The former `app/load_intake/` package was later removed after safe label knowledge was preserved.

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

## DecisionEngine Scenario Dry-run Closeout

Completed:

- synthetic DecisionEngine scenarios
- pure dry-run scenario runner
- manual scenario CLI
- README/docs sync

Current command:

```powershell
py scripts/run_decision_engine_scenarios.py
```

Options evaluated:

1. adapter around existing `MarketLoad` decision fields
2. DispatchCase/Event Timeline gap audit
3. expand synthetic DecisionEngine scenarios
4. risk flag mapping from notes/parser/intake
5. pause DecisionEngine and do reload-chain DispatchCase policy audit

Recommended next target:

```text
DecisionResult adapter around existing MarketLoad decision fields
```

Why:

- the pure signal/result/risk-flag foundation is now stable
- the dry-run runner proves the result shape without touching runtime
- an adapter can be read-only and not wired into live flow
- it can preserve existing `MATCH` / `REVIEW_ONCE` / `BLOCK` behavior exactly by reading current `MarketLoad` fields after existing logic has run
- it prepares future scenario comparisons without changing Telegram, DispatchCase, or market snapshot behavior

Suggested scope:

```text
app/market_intelligence/decision_engine/market_load_adapter.py
tests/test_decision_engine_market_load_adapter.py
```

Strict rules:

- do not call `MarketLoad.apply_search_request(...)`
- do not mutate load or search request
- do not change current decision behavior
- do not send Telegram
- do not write DispatchCase
- do not write storage
- do not call external services

Recommended second target:

```text
DispatchCase/Event Timeline gap audit
```

Do this before any new case-writing behavior, intake-to-case linking, accounting/factoring document events, or replay/missed-opportunity expansion.

Not recommended next:

- expand synthetic DecisionEngine scenarios: useful later, but current set is enough for adapter foundation
- risk flag mapping from notes/parser/intake: should wait until adapter confirms current field compatibility
- reload-chain DispatchCase policy audit: still important, but separate from core DecisionEngine adapter work

## Read-only MarketLoad Adapter Closeout

Completed:

- MarketLoad decision field audit
- read-only `decision_result_from_market_load(...)` adapter
- adapter regression fixtures
- adapter dry-run CLI

Command:

```powershell
py scripts/run_decision_engine_adapter_dry_run.py
```

Current status:

- report/dry-run only
- no runtime wiring
- no `MarketLoad.apply_search_request(...)` call
- no current `MATCH` / `REVIEW_ONCE` / `BLOCK` behavior change
- no Telegram behavior change
- no DispatchCase behavior change
- no market snapshot behavior change

Options evaluated:

1. integrate adapter into report-only tooling
2. DecisionEngine comparison report: current MarketLoad fields vs DecisionResult
3. DispatchCase/Event Timeline gap audit
4. expand DecisionEngine synthetic scenarios
5. reload-chain DispatchCase policy audit

Recommended next target:

```text
DispatchCase/Event Timeline gap audit
```

Why:

- the adapter now gives a normalized DecisionResult view of existing load decisions
- before writing any DecisionResult to cases/events, the project needs a clear case/timeline policy
- intake records, documents, dispatcher feedback, Telegram outbox records, and future accounting/factoring packet events all depend on stable event ownership
- this can remain audit-only and does not require runtime behavior changes

Recommended secondary target:

```text
DecisionEngine comparison report
```

Why:

- a report-only comparison could show current MarketLoad fields beside normalized DecisionResult output
- it would help validate adapter coverage before any production wiring
- it should wait until the DispatchCase/Event Timeline gap audit confirms where such reports should live

Not recommended next:

- runtime DecisionEngine wiring: too early before case/timeline policy
- expanding synthetic DecisionEngine scenarios: useful later, but current coverage is enough for the adapter phase
- risk flag mapping from notes/parser/intake: should wait until event/report needs are clearer
- reload-chain DispatchCase policy audit: still important, but narrower than the general DispatchCase/Event Timeline gap audit

## Telegram UX Planning Note

Completed:

```text
docs/TELEGRAM_UX_PLAN.md
```

Purpose:

- capture future interface ideas before backend audit work continues
- keep Telegram positioned as an adapter, not the business core
- define future menu/cards/settings/digest direction without changing runtime behavior

Current status:

- documentation only
- no Telegram runtime commands
- no Telegram buttons
- no Telegram formatter text changes
- no load alert changes
- no DispatchCase behavior changes

This does not change the next backend recommendation:

```text
DispatchCase/Event Timeline gap audit
```

## DispatchCase/Event Timeline Audit Closeout

Completed:

```text
docs/DISPATCH_CASE_EVENT_TIMELINE_GAP_AUDIT.md
```

What was decided:

- `LOAD_OPPORTUNITY` and `REVIEW_ONCE` remain load-level case inputs.
- `MARKET_SNAPSHOT` and `SEARCH_HEALTH_CHECK` remain outbox/reporting-only until a search/session entity exists.
- reload-watch remains dry-run/manual only.
- intake records remain separate evidence records until explicit linking policy exists.
- DecisionResult remains report/dry-run only until a timeline storage policy is accepted.
- reload-chain DispatchCase ownership still needs a separate audit before metadata/case wiring.

Options evaluated:

1. DecisionEngine comparison report: current MarketLoad fields vs DecisionResult
2. DispatchCase timeline event type constants/helper
3. Intake-to-DispatchCase link audit
4. reload-chain DispatchCase policy audit
5. synthetic load decision dataset planning
6. Telegram UX implementation later

Recommended next target:

```text
DecisionEngine comparison report
```

Why:

- it can stay report-only
- it uses the accepted read-only MarketLoad adapter
- it validates current decision fields against normalized DecisionResult output
- it does not write DispatchCases or events
- it does not change Telegram, market snapshot, load selection, or runtime decision behavior
- it provides useful evidence before any future DecisionResult timeline storage

Suggested scope:

```text
app/market_intelligence/decision_engine/comparison_report.py
scripts/run_decision_engine_comparison_report.py
tests/test_decision_engine_comparison_report.py
```

The report should use synthetic/fake records first or existing decision history only in explicit manual mode. It must not mutate cases, write events, send Telegram, or call external services.

## DecisionEngine Comparison Report Closeout

Completed:

- pure comparison helper: `app/market_intelligence/decision_engine/comparison_report.py`
- synthetic comparison fixtures: `tests/fixtures/decision_engine_comparison_loads.py`
- manual dry-run CLI: `scripts/run_decision_engine_comparison_report.py`

Command:

```powershell
py scripts/run_decision_engine_comparison_report.py
```

Current status:

- report-only
- synthetic/fake load-like fixtures only
- compares existing decision/category fields with adapter output
- summarizes adapter risk flags and missing-field warnings
- does not evaluate whether a dispatch decision is correct
- does not call `MarketLoad.apply_search_request(...)`
- does not change runtime behavior
- does not write DispatchCases or events
- does not change Telegram, market snapshot, load selection, or current decision behavior

The comparison report is now enough to show adapter coverage before deciding whether timeline/event vocabulary or further report-only previews should come next.

## Post-Comparison Backend Target Decision

Options evaluated:

1. DispatchCase/Event Timeline event type constants/helper
2. report-only DecisionResult timeline preview
3. adapter coverage expansion
4. risk flag mapping from notes/parser/intake
5. reload-chain DispatchCase policy audit
6. synthetic 100-200 load dataset planning

Recommended next target:

```text
DispatchCase/Event Timeline event type constants/helper
```

Why:

- the DispatchCase/Event Timeline ownership policy is now documented
- the DecisionEngine comparison report is stable and report-only
- before any DecisionResult, intake, reload-watch, or reload-chain case writes, the project needs a stable event vocabulary
- this can be pure constants/helper work with tests and no runtime behavior change
- it reduces the chance that future case-writing blocks invent overlapping event names

Suggested scope:

```text
app/market_intelligence/case_event_types.py
tests/test_case_event_types.py
```

The helper should only define and validate stable event type names. It should not write events, change `case_event_builder.py`, migrate existing DispatchCase behavior, send Telegram, or alter outbox handling.

Recommended second target:

```text
report-only DecisionResult timeline preview
```

Why:

- useful after event types exist
- can show what a future DecisionResult timeline event might look like without writing it
- should remain dry-run/report-only until explicit DispatchCase write policy is accepted

Not recommended next:

- runtime DecisionResult case writes
- intake-to-DispatchCase linking
- reload-chain DispatchCase wiring
- reload-chain metadata
- synthetic 100-200 load dataset
- risk flag mapping expansion
- Telegram UX implementation
- DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, or live automation

## Event Timeline Foundation Closeout

Completed:

- event type taxonomy helper: `app/market_intelligence/case_event_types.py`
- base JSON-ready event payload helper: `app/market_intelligence/case_event_payload.py`
- read-only event report helper: `app/market_intelligence/case_event_report.py`
- synthetic event report CLI: `scripts/run_case_event_report.py`
- synthetic event fixtures: `tests/fixtures/case_event_records.py`

Command:

```powershell
py scripts/run_case_event_report.py
```

Current status:

- pure helpers/reporting only
- no runtime DispatchCase behavior change
- no case creation/matching/update change
- no `case_event_builder.py` migration
- no DecisionResult case/event writes
- no Telegram behavior change
- no storage reads/writes

Options evaluated:

1. report-only DecisionResult timeline preview
2. compare current events against event taxonomy
3. DispatchCase event builder compatibility audit
4. intake-to-case link audit
5. reload-chain DispatchCase policy audit
6. synthetic 100-200 load dataset planning

Recommended next target:

```text
DispatchCase event builder compatibility audit
```

Why:

- the taxonomy and base payload helper now exist
- current runtime events are still produced by `case_event_builder.py`
- before any builder migration or DecisionResult timeline preview, we should confirm current event payloads map cleanly to the taxonomy
- this can be audit/test-only and should not change runtime behavior

Recommended second target:

```text
report-only DecisionResult timeline preview
```

Why:

- useful after current event builder compatibility is understood
- can show a future `AI_DECISION_CREATED` payload shape with nested DecisionResult without writing it
- should remain dry-run/report-only

Not recommended next:

- modifying `build_cases_and_events(...)`
- replacing `case_event_builder.py`
- writing DecisionResult events
- intake-to-case linking
- reload-chain DispatchCase wiring
- synthetic 100-200 load dataset
- Telegram UX runtime work
- DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, or live automation

## Case Event Builder Compatibility Closeout

Completed:

- compatibility audit doc: `docs/DISPATCH_CASE_EVENT_BUILDER_COMPATIBILITY.md`
- focused builder taxonomy compatibility tests
- read-only shape report helper: `app/market_intelligence/case_event_builder_report.py`
- synthetic builder output fixtures: `tests/fixtures/case_event_builder_outputs.py`
- manual compatibility CLI: `scripts/run_case_event_builder_compatibility.py`

Command:

```powershell
py scripts/run_case_event_builder_compatibility.py
```

Current findings:

- current builder-emitted event types are recognized by the taxonomy
- load-level and load-board simulation groups map correctly
- current builder payloads remain JSON-serializable
- current runtime event envelope is intentionally not the same as the base payload helper
- current builder output is still the runtime source of DispatchCase events

Options evaluated:

1. report-only DecisionResult timeline preview
2. case_event_builder migration plan
3. event payload wrapper around existing builder, no runtime wiring
4. DispatchCase timeline report over current built events
5. reload-chain DispatchCase policy audit
6. synthetic 100-200 load dataset planning

Recommended next target:

```text
report-only DecisionResult timeline preview
```

Why:

- the builder compatibility audit did not find taxonomy blockers
- the current event envelope should remain unchanged
- a preview can show a future `AI_DECISION_CREATED` payload shape with nested DecisionResult without writing it
- it keeps DecisionResult timeline work dry-run/report-only before any runtime case event writes

Recommended second target:

```text
case_event_builder migration plan
```

Why:

- useful before any actual builder wrapper/migration
- should stay docs-only unless a later block explicitly accepts code changes

Not recommended next:

- replacing `case_event_builder.py`
- writing nested DecisionResult into runtime events
- modifying DispatchCase build/update flow
- intake-to-case linking
- reload-chain DispatchCase wiring
- synthetic 100-200 load dataset
- DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, or live automation

## DecisionResult Timeline Preview Closeout

Completed:

- preview helper: `app/market_intelligence/decision_engine/timeline_preview.py`
- synthetic preview fixtures: `tests/fixtures/decision_result_timeline_previews.py`
- preview report helper: `app/market_intelligence/decision_engine/timeline_preview_report.py`
- manual dry-run CLI: `scripts/run_decision_result_timeline_preview.py`

Command:

```powershell
py scripts/run_decision_result_timeline_preview.py
```

Current status:

- report-only
- synthetic DecisionResult fixtures only
- no event writes
- no DispatchCase reads/writes
- no `case_event_builder.py` changes
- no runtime DecisionResult wiring
- no Telegram, MarketLoad, market snapshot, or load selection behavior changes

Options evaluated:

1. DispatchCase event builder migration plan
2. event payload wrapper around existing builder, no runtime wiring
3. DecisionEngine comparison + timeline preview combined report
4. intake-to-case link audit
5. reload-chain DispatchCase policy audit
6. synthetic 100-200 load dataset planning

Recommended next target:

```text
case_event_builder migration plan
```

Why:

- timeline preview now shows the desired future nested DecisionResult payload shape
- existing builder compatibility is clean but the runtime envelope is intentionally different from the base payload helper
- before any wrapper or migration, document exactly how current flat event fields will be preserved
- this can remain docs-only and avoid runtime behavior changes

Recommended second target:

```text
event payload wrapper around existing builder, no runtime wiring
```

Why:

- useful only after the migration plan is accepted
- should remain unused by runtime until a later explicit wiring block

Not recommended next:

- modifying `build_cases_and_events(...)`
- replacing `case_event_builder.py`
- writing DecisionResult events
- intake-to-case linking
- reload-chain DispatchCase wiring
- synthetic 100-200 load dataset
- DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, or live automation

## Case Event Builder Migration Plan Closeout

Completed:

- migration strategy doc: `docs/CASE_EVENT_BUILDER_MIGRATION_PLAN.md`
- event builder migration safety rules in `docs/DEVELOPMENT_RULES.md`
- normalized wrapper design audit
- DecisionResult event wiring prerequisites

Recommended next target:

```text
normalized event wrapper helper, report-only
```

Why:

- the migration plan selected wrapper-first as the safest path
- the helper can preserve the legacy event dict while producing a normalized/base-payload-compatible view
- it can stay report-only and avoid DispatchCase runtime changes
- it prepares event reports to understand both current and future shapes

Suggested scope:

```text
app/market_intelligence/case_event_normalizer.py
tests/test_case_event_normalizer.py
```

Recommended second target:

```text
event report support for wrapper output
```

Why:

- once wrapper output exists, reports can summarize both legacy and normalized payload views
- should still avoid runtime event writes

Not recommended next:

- `case_event_builder.py` replacement
- runtime DecisionResult writes
- DispatchCase build/update behavior changes
- SearchSession implementation
- intake-to-case linking
- reload-chain DispatchCase wiring
- synthetic 100-200 load dataset
- DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, or live automation

Recommended second target:

```text
DispatchCase timeline event type constants/helper
```

Why:

- useful if upcoming timeline work needs a stable event vocabulary
- should be pure constants/helper only
- should preserve existing event payloads and behavior

Not recommended next:

- runtime DecisionResult case writes
- intake-to-case linking
- reload-chain DispatchCase wiring
- Telegram UX implementation
- synthetic 100-200 load dataset
- DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, or accounting/factoring implementation

## Normalized Event Wrapper Closeout

Completed:

- pure wrapper helper: `app/market_intelligence/case_event_normalizer.py`
- synthetic/current-style wrapper fixtures: `tests/fixtures/normalized_event_wrapper_cases.py`
- wrapper report helper: `app/market_intelligence/case_event_normalizer_report.py`
- manual dry-run CLI: `scripts/run_case_event_normalizer_report.py`

Command:

```powershell
py scripts/run_case_event_normalizer_report.py
```

Current status:

- report-only
- synthetic fixtures only for the CLI
- preserves the existing event dict as `legacy_payload`
- builds a base-payload-compatible `normalized_payload`
- reports warnings for missing identity/source fields and unknown event types
- does not write events
- does not change `case_event_builder.py`
- does not change DispatchCase build/match/update behavior
- does not wire DecisionResult into runtime events

Options evaluated:

1. event report support for wrapper output
2. DecisionEngine comparison + timeline preview combined report
3. current built-events normalization report
4. DispatchCase builder migration dry-run
5. intake-to-case link audit
6. reload-chain DispatchCase policy audit
7. synthetic 100-200 load dataset planning

Recommended next target:

```text
event report support for wrapper output
```

Why:

- the normalized wrapper shape is stable and report-only
- event reports can now learn to summarize normalized wrapper records without changing runtime writers
- this keeps old event envelopes intact while preparing future reporting tools for both legacy and normalized views

Recommended second target:

```text
DecisionEngine comparison + timeline preview combined report
```

Why:

- useful after reports understand wrapper output
- can remain synthetic/report-only
- should still avoid event writes and DispatchCase runtime changes

Not recommended next:

- replacing `case_event_builder.py`
- storing normalized payloads on runtime events
- writing DecisionResult events
- DispatchCase build/match/update behavior changes
- intake-to-case linking
- reload-chain DispatchCase wiring
- synthetic 100-200 load dataset
- DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, or live automation

## Event Report Wrapper Support Status

Completed:

- `case_event_report.py` accepts both legacy event dicts and normalized wrapper records.
- Wrapper report input prefers `normalized_payload` for event type, event group, case ID, timestamp, and source.
- Wrapper warnings are summarized in `warnings_count` and `warnings_by_type`.
- `scripts/run_case_event_report.py --wrapped` demonstrates the report over synthetic wrapper fixtures.

Current status:

- report-only
- legacy event reports remain backward-compatible
- no runtime event writes
- no `case_event_builder.py` changes
- no DispatchCase build/match/update changes
- no DecisionResult event writes

The next target should be selected separately now that event reports can read both legacy and normalized wrapper shapes.

## Event Report Wrapper Support Closeout

Completed:

- event report wrapper-input audit
- `case_event_report.py` support for legacy + wrapper records
- wrapper warning summaries in event reports
- `scripts/run_case_event_report.py --wrapped`
- docs and roadmap sync

Current command:

```powershell
py scripts/run_case_event_report.py --wrapped
```

Options evaluated:

1. DecisionEngine comparison + timeline preview combined report
2. current built-events normalization report
3. DispatchCase builder migration dry-run
4. intake-to-case link audit
5. reload-chain DispatchCase policy audit
6. synthetic 100-200 load dataset planning

Recommended next target:

```text
DecisionEngine comparison + timeline preview combined report
```

Why:

- DecisionEngine comparison report is already report-only;
- DecisionResult timeline preview is already report-only;
- event reports can now read wrapper-style normalized records;
- a combined report can show how existing load decisions, normalized DecisionResult, and future timeline preview payloads line up before any runtime wiring;
- it avoids changing `case_event_builder.py`, DispatchCase runtime behavior, Telegram, MarketLoad decisions, or event writing.

Recommended second target:

```text
current built-events normalization report
```

Why:

- useful after the combined report if we want a focused view of current generated builder-style events through the wrapper;
- should stay synthetic/report-only unless a later block explicitly allows reading real runtime event data.

Not recommended next:

- DispatchCase builder migration dry-run: wait until reporting views are stronger;
- intake-to-case link audit: important, but less urgent than finishing the report-only DecisionEngine/timeline bridge;
- reload-chain DispatchCase policy audit: still needed before reload-chain metadata/case wiring, but not part of this event wrapper lane;
- synthetic 100-200 load dataset: too early before report-only backend views are complete;
- runtime event writes, DecisionResult event writes, DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, replay/missed-opportunity, or live automation.

## DecisionEngine Timeline Combined Report Closeout

Completed:

- combined report design audit
- pure helper: `app/market_intelligence/decision_engine/combined_report.py`
- synthetic/fake load fixtures: `tests/fixtures/decision_engine_combined_report_loads.py`
- manual CLI: `scripts/run_decision_engine_timeline_report.py`
- README command reference

Current command:

```powershell
py scripts/run_decision_engine_timeline_report.py
```

Current status:

- report-only
- synthetic/fake load-like fixtures only
- reads existing decision fields through the accepted read-only adapter
- builds future `AI_DECISION_CREATED` timeline preview payloads
- normalizes preview payloads into wrapper/report views
- writes no events
- changes no DispatchCase runtime behavior
- changes no Telegram, MarketLoad, load selection, or market snapshot behavior

Options evaluated:

1. current built-events normalization report
2. DispatchCase builder migration dry-run
3. intake-to-case link audit
4. reload-chain DispatchCase policy audit
5. synthetic 100-200 load dataset planning
6. dependency adoption audit

Recommended next target:

```text
current built-events normalization report
```

Why:

- current builder-style event samples already exist;
- the normalizer and wrapper-aware event report are now stable;
- this can inspect generated current-style events through the normalizer without changing runtime writers;
- it should stay synthetic/report-only and avoid runtime JSONL reads.

Recommended second target:

```text
intake-to-case link audit
```

Why:

- after event reporting views are stable, intake evidence linkage is the next important backend policy;
- it should be audit/design first before any DispatchCase writes.

Not recommended next:

- DispatchCase builder migration dry-run: still premature before built-event normalization reporting;
- reload-chain DispatchCase policy audit: important, but separate from the current event-reporting lane;
- synthetic 100-200 load dataset: still too early;
- runtime event writes, DecisionResult event writes, DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, replay/missed-opportunity, or live automation.

## Current Built-events Normalization Report Closeout

Completed:

- design doc: `docs/CURRENT_BUILT_EVENTS_NORMALIZATION_REPORT.md`
- synthetic/current-style event samples: `tests/fixtures/current_built_event_samples.py`
- report helper: `app/market_intelligence/case_event_built_report.py`
- manual CLI: `scripts/run_current_built_events_normalization_report.py`
- README command reference

Current command:

```powershell
py scripts/run_current_built_events_normalization_report.py
```

Current status:

- report-only
- synthetic/current-style event samples only
- no runtime JSONL reads
- no event writes
- no `case_event_builder.py` changes
- no DispatchCase build/match/update behavior changes
- no DecisionResult event writes
- no Telegram, MarketLoad, market snapshot, or load selection behavior changes

Options evaluated:

1. DispatchCase builder migration dry-run
2. event payload wrapper around existing builder, unused by runtime
3. intake-to-case link audit
4. reload-chain DispatchCase policy audit
5. synthetic 100-200 load dataset planning
6. private RateCon field inventory plan

Recommended next target:

```text
intake-to-case link audit
```

Why:

- the event-reporting bridge is stable enough for audit/design work around evidence linkage;
- intake records, parser output, documents, and RateCon dry-run data still do not create cases;
- before any intake evidence can link to DispatchCase, ownership and linking rules should be documented;
- this can stay audit-only and avoid runtime behavior changes.

Recommended second target:

```text
reload-chain DispatchCase policy audit
```

Why:

- reload-chain metadata/case ownership still needs a separate policy before any wiring;
- it should remain audit-only first.

Not recommended next:

- DispatchCase builder migration dry-run: still too early before intake/document ownership is settled;
- event payload wrapper around existing builder in runtime: report-only wrapper already exists, runtime use should wait;
- synthetic 100-200 load dataset: still too early;
- private RateCon field inventory plan: useful, but intake-to-case ownership should be clarified first;
- DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting/factoring, replay/missed-opportunity, live automation, or runtime event writes.

## Intake-to-Case Link Audit Closeout

Completed:

- current intake and DispatchCase boundary audit;
- conservative link/create/keep-unlinked policy proposal;
- future `IntakeCaseLinkCandidate` model design;
- future intake-to-case event/timeline policy;
- roadmap and event timeline policy sync.

Current status:

- IntakeRecords remain structured evidence.
- IntakeRecords do not create DispatchCases.
- IntakeRecords do not link to DispatchCases in runtime.
- parser output does not write DispatchCase events.
- `linked_dispatch_case_id` is not set by current helpers.
- existing `RATECON_RECEIVED` behavior remains tied to dispatcher feedback with `document_path`.

Options evaluated:

1. IntakeCaseLinkCandidate pure helper
2. intake-to-case dry-run report
3. private RateCon field inventory plan
4. reload-chain DispatchCase policy audit
5. synthetic 100-200 load dataset planning
6. PDF extraction strategy audit

Recommended next target:

```text
IntakeCaseLinkCandidate pure helper
```

Why:

- the policy is now documented and conservative;
- the helper can be pure, JSON-ready, and report-only;
- it can preserve missing/needs-check/confidence evidence without writing cases;
- it sets up a later dry-run report before any runtime linking exists;
- it does not require PDF/OCR, private RateCons, Telegram upload, Gmail/email, Google Sheets, DispatchCase writes, DAT/API, Google Maps, accounting/factoring, replay, or reload-chain metadata.

Recommended second target:

```text
intake-to-case dry-run report
```

This should wait until the candidate helper exists and should remain synthetic/report-only.

Useful alternative:

```text
private RateCon field inventory plan
```

Use this if private document preparation becomes more important than link-candidate helpers.

Not recommended next:

- automatic case creation from intake;
- writing intake link events;
- setting `linked_dispatch_case_id`;
- PDF/OCR parser work;
- reading private RateCon files;
- Telegram upload handling;
- Gmail/email or Google Sheets integration;
- reload-chain DispatchCase wiring;
- synthetic 100-200 load dataset.

## IntakeCaseLinkCandidate Helper Closeout

Completed:

- pure helper: `app/market_intelligence/intake/case_link_candidate.py`;
- synthetic fixtures: `tests/fixtures/intake_case_link_candidates.py`;
- report helper: `app/market_intelligence/intake/case_link_candidate_report.py`;
- manual CLI: `scripts/run_intake_case_link_candidate_report.py`;
- README command reference.

Current command:

```powershell
py scripts/run_intake_case_link_candidate_report.py
```

Current status:

- report-only/dry-run only;
- synthetic fixtures only for the CLI;
- no DispatchCase creation;
- no runtime linking;
- no `linked_dispatch_case_id` writes;
- no event writes;
- no `case_event_builder.py` changes;
- no Telegram, parser, private RateCon, PDF/OCR, Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, replay, or reload-chain metadata changes.

Options evaluated:

1. intake-to-case dry-run report refinement
2. private RateCon field inventory plan
3. manual real RateCon text dry-run protocol
4. PDF extraction strategy audit
5. reload-chain DispatchCase policy audit
6. synthetic 100-200 load dataset planning

Recommended next target:

```text
private RateCon field inventory plan
```

Why:

- candidate helper/reporting is stable enough to support review planning;
- before any real parser or PDF extraction work, the project should define a local-only human inventory process;
- it can clarify which fields should be captured from the first private samples without committing documents or extracted private text;
- it keeps case linking, event writes, parser behavior, Gmail/email, Google Sheets, Telegram upload, DAT/API, Google Maps, accounting/factoring, and replay out of scope.

Recommended second target:

```text
manual real RateCon text dry-run protocol
```

This should be a design/protocol step only and should not process private files, add OCR/PDF parsing, or commit private text.

Not recommended next:

- intake-to-case runtime linking;
- automatic case creation;
- `RATECON_PARSED` event writes;
- PDF extraction implementation;
- reading private RateCon files in tests;
- reload-chain DispatchCase wiring;
- synthetic 100-200 load dataset.

## Private RateCon Inventory Planning Closeout

Completed:

- field inventory plan: `docs/PRIVATE_RATECON_FIELD_INVENTORY_PLAN.md`;
- blank safe template: `docs/templates/PRIVATE_RATECON_FIELD_INVENTORY_TEMPLATE.md`;
- manual text dry-run protocol: `docs/MANUAL_RATECON_TEXT_DRY_RUN_PROTOCOL.md`;
- readiness checklist: `docs/RATECON_TEST_READINESS_CHECKLIST.md`.

Current status:

- docs/local-process only;
- no private RateCons read;
- no private text committed;
- no parser behavior changes;
- no PDF/OCR;
- no intake repository behavior changes;
- no DispatchCase creation/linking/events;
- no Telegram, Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, replay, or reload-chain changes.

Options evaluated:

1. manual real RateCon text dry-run protocol execution support
2. anonymized RateCon synthetic scenario expansion
3. PDF extraction strategy audit
4. private RateCon parser audit refresh
5. reload-chain DispatchCase policy audit
6. synthetic 100-200 load dataset planning

Recommended next target:

```text
manual real RateCon text dry-run protocol execution support
```

Conditions:

- readiness checklist must pass;
- user must select 3-5 private documents locally;
- no private files or private text may be committed;
- execution support must stay manual/local/dry-run;
- no PDF/OCR or file extraction should be added.

Recommended fallback target:

```text
anonymized RateCon synthetic scenario expansion
```

Use this if the readiness checklist does not pass or if private sample review should wait.

Recommended later target:

```text
PDF extraction strategy audit
```

This should remain audit/design first and should happen only after manual text dry-runs produce clear lessons.

Not recommended next:

- PDF extraction implementation;
- OCR;
- private file processing in tests;
- committing private text;
- Telegram upload handling;
- Gmail/email or Google Sheets integration;
- DispatchCase linking/event writes;
- synthetic 100-200 load dataset;
- reload-chain metadata/case wiring.

## Manual RateCon Text Dry-run Execution Support Closeout

Completed:

- protocol sync: `docs/MANUAL_RATECON_TEXT_DRY_RUN_PROTOCOL.md`;
- pure pipeline helper: `app/market_intelligence/intake/ratecon_text_dry_run.py`;
- manual CLI: `scripts/run_manual_ratecon_text_dry_run.py`;
- result checklist: `docs/MANUAL_RATECON_DRY_RUN_RESULT_CHECKLIST.md`;
- README command reference.

Current command:

```powershell
py scripts/run_manual_ratecon_text_dry_run.py --text "Broker: FAKE BROKER LLC ..."
```

Current status:

- local/manual/dry-run only;
- supports fake sample mode, `--text`, and safe terminal stdin;
- no file input mode;
- no private text saved by default;
- no private RateCon files read;
- no PDF/OCR;
- no Telegram upload;
- no Gmail/email or Google Sheets;
- no DispatchCase creation/linking/events;
- no `linked_dispatch_case_id` updates.

Options evaluated:

1. first private manual text dry-run with user-provided local text
2. anonymized synthetic RateCon scenario expansion
3. PDF extraction strategy audit
4. pdfplumber/PyMuPDF dependency audit
5. private PDF test harness design
6. reload-chain DispatchCase policy audit

Recommended next target:

```text
first private manual text dry-run protocol execution
```

Conditions:

- readiness checklist must pass;
- user provides/uses local pasted text manually;
- no private files or private text are committed;
- any results shared back into docs/tests must be anonymized.

Recommended fallback target:

```text
anonymized RateCon synthetic scenario expansion
```

Use this if private dry-run execution should wait or if the first manual dry-run reveals parser gaps that can be represented synthetically.

Recommended later target:

```text
PDF extraction strategy audit
```

This should remain audit/design only until manual pasted-text dry-runs are understood.

Not recommended next:

- PDF extraction implementation;
- OCR;
- private file processing in tests;
- committing private text or extracted private values;
- Telegram upload handling;
- Gmail/email or Google Sheets integration;
- DispatchCase linking/event writes;
- synthetic 100-200 load dataset;
- reload-chain metadata/case wiring.

## Private RateCon Local Batch Readiness Closeout

Completed:

- private RateCon folder safety verification for `originals`, `text_exports`, `dry_run_results`, and `inventory`;
- local-only inventory command: `scripts/private_ratecon_inventory.py`;
- manual batch protocol update: `docs/MANUAL_RATECON_TEXT_DRY_RUN_PROTOCOL.md`;
- safe dry-run result summary template: `docs/templates/PRIVATE_RATECON_DRY_RUN_RESULT_SUMMARY_TEMPLATE.md`.

Current status:

- private files stay under `data/private_ratecons/` and remain gitignored;
- the inventory command counts files and emits anonymized `RATECON_###` labels without reading contents;
- no private text is committed;
- no PDF/OCR extraction exists;
- no DispatchCase creation/linking/events exist;
- no Telegram upload, Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, synthetic 100-200 load dataset, or reload-chain metadata work was added.

Options evaluated:

1. user manually runs first private text dry-run and shares a safe summary
2. anonymized synthetic scenario expansion based on issues found
3. PDF extraction strategy audit
4. pdfplumber/PyMuPDF local extraction helper later
5. reload-chain DispatchCase policy audit

Recommended next target:

```text
first private manual text dry-run protocol execution
```

Conditions:

- user runs 1-3 private dry-runs locally first;
- user shares only safe summary fields/categories, not private text or filenames;
- do not share real broker/customer/driver names, contact details, addresses, MCs, reference numbers, appointment notes, or copied document text;
- do not add PDF/OCR extraction yet.

Recommended fallback target:

```text
anonymized RateCon synthetic scenario expansion
```

Use this if the local dry-run output reveals parser gaps that can be represented safely with fake data, or if private testing should pause.

Recommended later target:

```text
PDF extraction strategy audit
```

This should remain audit/design only until manual text dry-runs produce enough safe summary evidence.

Not recommended next:

- PDF extraction implementation;
- OCR;
- committing private documents or extracted private text;
- creating tracked fixtures from private documents;
- Telegram upload handling;
- Gmail/email or Google Sheets integration;
- DispatchCase linking/event writes;
- DAT/API or Google Maps;
- accounting/factoring implementation;
- synthetic 100-200 load dataset;
- reload-chain metadata/case wiring.

## Private PDF Text Extraction Dry-run Closeout

Completed:

- PDF extraction strategy audit: `docs/PDF_EXTRACTION_STRATEGY_AUDIT.md`;
- local-only extraction helper: `app/market_intelligence/intake/pdf_text_extraction.py`;
- private PDF extraction inventory CLI: `scripts/run_private_ratecon_pdf_extraction_inventory.py`;
- PDF-to-RateCon dry-run helper: `app/market_intelligence/intake/ratecon_pdf_dry_run.py`;
- limited private PDF dry-run CLI: `scripts/run_private_ratecon_pdf_dry_run.py`;
- README and manual protocol command references.

Current commands:

```powershell
py scripts/run_private_ratecon_pdf_extraction_inventory.py --limit 3
py scripts/run_private_ratecon_pdf_dry_run.py --limit 1
```

Current status:

- local/private/dry-run only;
- first extractor is `pypdf`, already available locally;
- no OCR;
- no raw extracted text printed by the CLIs;
- no extracted text saved;
- no tracked fixtures from private documents;
- no DispatchCase creation/linking/events;
- no Telegram upload, Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, reload-chain metadata, or synthetic 100-200 dataset work.

Options evaluated:

1. user runs private PDF dry-run locally and shares only safe summaries
2. anonymized synthetic RateCon scenario expansion from observed issues
3. parser field extraction improvements based on anonymized patterns
4. PDF extraction dependency refinement
5. OCR strategy audit later

Recommended next target:

```text
user runs private PDF dry-run locally and shares only safe summaries
```

Conditions:

- start with `--limit 1`;
- share only anonymized labels, extraction status, character count, missing/needs-check fields, low-confidence field names, and result category;
- do not share raw extracted text, private filenames, broker/customer/contact details, addresses, MCs, reference numbers, or document snippets;
- do not commit local dry-run outputs.

Recommended fallback target:

```text
anonymized synthetic RateCon scenario expansion from observed issues
```

Use this if the safe summaries reveal parser gaps that can be represented with fake data.

Recommended later target:

```text
PDF extraction dependency refinement
```

Only consider `pdfplumber` or PyMuPDF after the first local summaries show `pypdf` is insufficient and after a separate dependency decision block.

Recommended later audit:

```text
OCR strategy audit
```

OCR remains out of scope until text-layer PDF extraction has been evaluated safely.

Not recommended next:

- parser field extraction improvements using private text directly;
- committing extracted text or private-derived fixtures;
- OCR implementation;
- Telegram upload handling;
- Gmail/email or Google Sheets integration;
- DispatchCase creation/linking/events;
- DAT/API or Google Maps;
- accounting/factoring implementation;
- synthetic 100-200 load dataset;
- reload-chain metadata/case wiring.

## Redacted RateCon Field Diagnostics Closeout

Completed:

- redacted diagnostic process doc: `docs/RATECON_REDACTED_FIELD_DIAGNOSTICS.md`;
- field-label signal detector: `app/market_intelligence/intake/ratecon_field_diagnostics.py`;
- parser coverage diagnostic helper: `app/market_intelligence/intake/ratecon_parser_coverage.py`;
- local private diagnostics CLI: `scripts/run_private_ratecon_redacted_diagnostics.py`;
- README command reference.

Current command:

```powershell
py scripts/run_private_ratecon_redacted_diagnostics.py --limit 1
```

Current status:

- local/private/dry-run only;
- inspects extracted PDF text in memory only;
- prints label signal counts and parser coverage statuses only;
- prints no raw extracted text, values, snippets, filenames, broker/customer/contact data, MCs, addresses, emails, phone numbers, reference numbers, or appointment details;
- saves no extracted text;
- creates no fixtures from private documents;
- creates/links no DispatchCases;
- writes no DispatchCase events;
- adds no OCR, Telegram upload, Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, reload-chain metadata, or synthetic 100-200 dataset work.

Options evaluated:

1. user runs redacted diagnostics on `RATECON_001` and shares safe summary
2. anonymized synthetic RateCon scenario expansion from observed parser gaps
3. parser field extraction improvements based on synthetic/fake patterns
4. PDF extraction dependency refinement if diagnostics show poor text extraction
5. OCR strategy audit later

Recommended next target:

```text
user runs redacted diagnostics locally and shares safe summary
```

Conditions:

- start with `--limit 1`;
- share only anonymized label, extraction status, char/page counts, signal counts, field status categories, suspected parser gap field names, result category, and generic warnings;
- do not share raw extracted text, private filenames, private values, document snippets, broker/customer/contact details, MCs, addresses, emails, phone numbers, reference numbers, or appointment details.

Recommended follow-up target:

```text
anonymized synthetic RateCon scenario expansion from observed parser gaps
```

Use the safe diagnostic summary to create fake examples that reproduce the label patterns the parser missed. Parser improvements should be made against those synthetic examples, not against private text.

Recommended later target:

```text
parser field extraction improvements based on synthetic/fake patterns
```

This should happen only after synthetic cases exist and tests define expected behavior.

Recommended fallback:

```text
PDF extraction dependency refinement
```

Use this only if diagnostics show the text layer itself is poor. OCR remains a separate later audit.

Not recommended next:

- parser improvements using private text directly;
- committing extracted text or private-derived fixtures;
- printing raw diagnostics snippets;
- OCR implementation;
- Telegram upload handling;
- Gmail/email or Google Sheets integration;
- DispatchCase creation/linking/events;
- DAT/API or Google Maps;
- accounting/factoring implementation;
- synthetic 100-200 load dataset;
- reload-chain metadata/case wiring.

## Legacy Load Intake Salvage Audit Closeout

Completed:

- legacy `app/load_intake/` salvage/delete audit: `docs/LOAD_INTAKE_LEGACY_SALVAGE_AUDIT.md`;
- safe legacy label candidates documented;
- synthetic legacy-label examples added: `tests/fixtures/legacy_ratecon_label_examples.py`;
- redacted diagnostics tests cover the safe legacy label concepts;
- deletion impact audit documented.

Current status after deletion cleanup:

- `app/load_intake/` has been removed;
- legacy-only import tests were removed;
- active intake remains under `app/market_intelligence/intake/`;
- no runtime behavior changed;
- no legacy code is wired into current intake;
- no legacy parser is used directly;
- no Google Sheets behavior was added;
- no private RateCons were processed;
- no private text or private values were committed.

Findings:

- useful salvage exists only at the label-vocabulary level;
- old parser/scoring/storage flow is unsafe for reuse;
- safe label vocabulary is preserved in synthetic diagnostics fixtures/docs;
- active `app/market_intelligence/intake/` code does not depend on deleted `app/load_intake/`.

Options evaluated:

1. deletion cleanup completed
2. keep removed legacy flow out of architecture
3. migrate only safe label aliases into new redacted diagnostics/parser tests
4. run private redacted diagnostics locally and share safe summary
5. anonymized synthetic RateCon scenario expansion from observed issues

Recommended next target:

```text
anonymized synthetic RateCon scenario expansion from observed parser gaps and safe legacy label ideas
```

Why:

- useful label aliases exist;
- parser improvements should be driven by fake examples, not private text;
- safe label ideas are represented outside the deleted legacy folder;
- this avoids runtime behavior changes and prevents legacy parser/scoring reuse.

Recommended second target:

```text
parser field extraction improvements based on synthetic/fake patterns
```

Only after synthetic examples define expected behavior.

Useful parallel next step:

```text
user runs redacted diagnostics locally and shares safe summary
```

This can provide more safe field-gap categories for synthetic examples.

Not recommended next:

- direct parser changes from private text;
- direct reuse of legacy regex implementation;
- reuse of Google Sheets writer;
- reuse of old decision/reload/zone/mileage/broker scoring;
- reintroducing deleted `app/load_intake/` runtime logic;
- DispatchCase creation/linking/events;
- OCR, Telegram upload, Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, reload-chain metadata, or synthetic 100-200 dataset work.

## Legacy Load Intake Deletion Cleanup Closeout

Completed:

- pre-deletion import/reference audit;
- safe legacy label preservation verification;
- deletion of the legacy `app/load_intake/` package;
- removal of legacy-only import tests;
- docs/roadmap cleanup after deletion.

Current status:

- active intake path is `app/market_intelligence/intake/`;
- useful legacy label vocabulary is preserved in synthetic fixtures and docs;
- current RateCon text/PDF dry-run behavior is unchanged;
- private RateCons were not processed during deletion cleanup;
- no DispatchCase, Telegram, MarketLoad, parser, or reload-chain runtime behavior changed.

Options evaluated:

1. anonymized synthetic RateCon scenario expansion from observed parser gaps and preserved legacy label ideas
2. parser field extraction improvements based on synthetic/fake patterns
3. user runs redacted diagnostics locally and shares safe summary
4. PDF extraction dependency refinement if `pypdf` text order is weak
5. OCR strategy audit later
6. reload-chain DispatchCase policy audit

Recommended next target:

```text
anonymized synthetic RateCon scenario expansion from observed parser gaps and preserved safe legacy label ideas
```

Recommended follow-up:

```text
parser field extraction improvements based on synthetic/fake patterns
```

Not recommended next:

- direct parser changes from private extracted text;
- restoring deleted `app/load_intake` runtime logic;
- reusing old Google Sheets, parser-to-`MarketLoad`, decision, reload, zone, mileage, or broker scoring behavior;
- OCR implementation;
- Telegram upload handling;
- Gmail/email or Google Sheets integration;
- DispatchCase creation/linking/events;
- synthetic 100-200 load dataset.
