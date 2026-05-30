# AI Dispatch Team

AI Dispatch Team is an early-stage Dispatch Operating Intelligence System for flatbed and conestoga freight dispatch.

The project started as a Telegram-based load alert bot, but the long-term direction is broader: to build a dispatch decision engine that can analyze freight opportunities, remember dispatcher decisions, collect feedback, track broker behavior, and eventually support a Shadow Dispatcher / AI Dispatch Observer workflow.

The current MVP focuses on:

- load matching by driver profile
- flatbed / conestoga compatibility logic
- rate check handling
- OD / permit detection
- document requirement detection
- broker/contact parsing
- Telegram alerts
- dispatcher feedback collection
- decision history logging
- DispatchCase and event timeline structure
- timed load board simulation before live DAT/API integration

---

## Project Vision

The long-term goal is not just to send load alerts.

The goal is to create an AI Dispatch Operating Intelligence System that understands:

- what loads appeared on the market
- what the AI recommended
- what the dispatcher actually did
- why the dispatcher made that decision
- what the broker said
- whether a rate confirmation was received
- whether the load was booked, rejected, covered, ignored, or failed
- how broker behavior changes over time
- which rules were correct and which were too strict

This creates a proprietary dispatch memory dataset.

The most valuable data is not only load board data. The most valuable data is:

```text
market data + AI decision + dispatcher action + dispatcher explanation + final outcome
````

---

## Current System Status

The system currently runs locally from:

```text
C:\Projects\AI-Dispatch-Team
```

Main command:

```powershell
py main.py
```

The system processes active search requests, analyzes available loads, applies driver-specific business logic, and sends Telegram alerts.

Current active driver examples:

* Alex
* Sergey
* TestCA
* TestCAFlatbed

---

## Start Here For Development

Core architecture docs:

* [Architecture](docs/ARCHITECTURE.md)
* [Flow](docs/FLOW.md)
* [Development Rulebook](docs/DEVELOPMENT_RULEBOOK.md)
* [Domain Contracts](docs/DOMAIN_CONTRACTS.md)
* [Current RateCon Pipeline State](docs/RATECON_PIPELINE_CURRENT_STATE.md)
* [RateCon Extraction Strategy](docs/RATECON_EXTRACTION_STRATEGY.md)
* [PDF Triage](docs/PDF_TRIAGE.md)
* [RateCon Candidate Extraction](docs/RATECON_CANDIDATE_EXTRACTION.md)
* [RateCon Broker Templates](docs/RATECON_BROKER_TEMPLATES.md)
* [RateCon Template Resolver Hardening](docs/RATECON_TEMPLATE_RESOLVER_HARDENING.md)
* [Legacy RateCon Path Audit](docs/LEGACY_PATH_AUDIT.md)
* [Testing Roadmap](docs/TESTING_ROADMAP.md)
* [Event Timeline Contract](docs/EVENT_TIMELINE_CONTRACT.md)
* [Telegram Output Safety](docs/TELEGRAM_OUTPUT_SAFETY.md)
* [DecisionEngine Contract](docs/DECISION_ENGINE_CONTRACT.md)
* [RateCon Core Field Policy](docs/RATECON_CORE_FIELD_POLICY.md)
* [Roadmap](docs/ROADMAP.md)

Current development order:

1. Foundation architecture/contracts
2. Decision safety
3. Intake validation
4. Event timeline
5. Document AI scaffolding
6. RateCon extraction hardening
7. Simulation/backtesting
8. Future live DAT/API integration

Do not do yet:

* no live DAT/API integration
* no autonomous booking
* no private raw PDF text commits
* no external paid OCR/Vision by default
* no Telegram business logic
* no low-confidence DispatchCase automation

---

## Main Capabilities

### 1. Market Snapshot

The system sends a market summary per active driver search request.

Example output:

```text
MARKET SNAPSHOT
Search Area
Available Time
Equipment
Target Direction
Market Activity
Driver Fit
Action Status
Best Bucket
Clean Matches
Review Once
Blocked
Recommendation
```

---

### 2. Load Opportunity Alerts

The system sends clean matching loads to Telegram.

Example category:

```text
LOAD OPPORTUNITY
```

The alert includes:

* pickup / delivery
* rate
* loaded miles
* empty miles
* total miles
* total RPM
* weight
* trailer type
* delivery zone
* pickup / delivery time
* broker / contact block
* priority
* score
* reason
* driver fit notes

---

### 3. Review Once Alerts

Some loads are not clean matches but may still be worth dispatcher review.

Supported review categories include:

```text
RATE CHECK
OD / PERMIT
DOCUMENTS REQUIRED
CONESTOGA VERIFY
ALONG ROUTE
TIME CHECK
WEIGHT CHECK
TARPS REQUIRED
GENERAL REVIEW
```

---

### 4. Rate Check Logic

Loads with:

```text
rate = 0
```

are not automatically blocked.

If the load otherwise fits the driver and does not contain hard blockers, it is sent as:

```text
REVIEW ONCE вЂ” RATE CHECK
```

Expected reason:

```text
Rate is missing / posted as $0; dispatcher should check rate with broker.
```

---

### 5. Conestoga Logic

Conestoga can take tarp-required freight because the trailer itself covers the load.

Tarp requirement alone should not block Conestoga.

Conestoga should be blocked or reviewed based on:

```text
No Conestoga
No Stogas
Conestoga won't work
Flatbed only
Flat only
Flat or Step only
OD / permit / oversize
overweight
dimensions that do not fit Conestoga
```

Flatbed / Flat or Step / Flatbed or Step Deck postings for Conestoga should usually be:

```text
REVIEW ONCE вЂ” CONESTOGA VERIFY
```

unless there is a clear hard blocker.

---

### 6. OD / Permit Logic

Flatbed OD / permit / wide loads are sent as:

```text
REVIEW ONCE вЂ” OD / PERMIT
```

Conestoga should not take OD / permit / wide / oversize loads.

For Conestoga, OD / permit is treated as a hard blocker.

---

### 7. Driver Document Logic

The system supports driver document profile fields:

```text
hazmat
tanker_endorsement
twic
us_citizen
green_card_holder
work_permit
ramps
dunnage
tracking_ok
```

Document logic:

```text
true    в†’ driver can take it
false   в†’ block
null    в†’ REVIEW ONCE / DOCUMENTS REQUIRED
```

This allows the dispatcher to ask the driver once and later update the driver profile.

---

### 8. Broker / Contact Parsing

Telegram alerts include a broker/contact block:

```text
Broker / Contact:
Broker:
MC:
Phone:
Email:
Reference ID:
Credit Score:
Days to Pay:
Factoring:
Broker Status:
```

The system attempts to extract broker information from structured fields and notes.

Reference ID behavior:

```text
If found в†’ show Reference ID
If not found в†’ show Reference ID: NO ID
```

---

### 9. Telegram Duplicate Protection

The system uses local sent-lock files to avoid sending the same alerts repeatedly:

```text
data/sent_market_summaries.txt
data/sent_telegram_loads.txt
data/sent_review_once_loads.txt
data/sent_search_health_alerts.txt
```

These files are runtime state and should not be committed to GitHub.

---

## Current Project Structure

```text
main.py

app/
  market_intelligence/
    contact_parser.py
    decision_logger.py
    dispatch_case.py
    driver_profile.py
    driver_profile_loader.py
    event_logger.py
    load_source.py
    market_models.py
    market_snapshot.py
    notes_parser.py
    reload_chain.py
    search_request.py
    telegram_notifier.py
    telegram_outbox_logger.py

data/
  current_loads.json
  driver_profiles.json
  manual_test_loads.json
  search_requests/
  drivers/
  simulation/

scripts/
  add_dispatcher_feedback.py
  append_json_document_test_load.py
  build_dispatch_cases.py
  import_loads_csv.py
  log_decisions_snapshot.py
  run_load_board_simulation.py
  telegram_feedback_bot.py
```

---

## Data Files

### Imported Loads

```text
data/current_loads.json
```

Generated from CSV import.

### Manual Test Loads

```text
data/manual_test_loads.json
```

Contains stable business-case test loads that should not be overwritten by CSV imports.

Used for testing:

* clean flatbed match
* rate check
* OD / permit
* tarp required
* No Conestoga
* ISO tanks

### Driver Profiles

```text
data/driver_profiles.json
```

Defines driver equipment, max weight, tarp ability, OD/permit ability, document status, and other driver-specific rules.

### Search Requests

```text
data/search_requests/
```

Each active JSON file defines one driver search request.

Example:

```text
alex_active.json
sergey_active.json
testca_active.json
testcaflatbed_active.json
```

---

## Decision Logging

The system can log AI decisions into:

```text
data/decision_history.jsonl
data/decision_runs.jsonl
```

Run:

```powershell
py scripts/log_decisions_snapshot.py
```

This records:

* driver
* load
* broker
* AI decision
* review category
* score
* reasons
* market status

These files are private operational data and should not be committed.

---

## Dispatcher Feedback

Dispatcher feedback can be added manually through CLI:

```powershell
py scripts/add_dispatcher_feedback.py MANUAL-CLEAN-FLATBED-001 booked "Good broker, booked at posted rate"
```

Feedback is saved to:

```text
data/dispatcher_feedback.jsonl
```

Supported feedback types include:

```text
booked
skipped
called_broker
sent_to_driver
driver_rejected
rate_too_low
bad_broker
wrong_equipment
weight_issue
time_issue
covered
duplicate
good_option
not_interested
other
```

---

## Telegram Feedback Bot

The project includes a Telegram feedback bot:

```powershell
py scripts/telegram_feedback_bot.py
```

This allows the dispatcher to train the system directly from Telegram.

Example commands:

```text
/booked MANUAL-CLEAN-FLATBED-001 booked at posted rate
/rate_too_low MANUAL-RATECHECK-001 broker offered only 3200
/driver_rejected 3010980 driver does not want permit load
/bad_broker 5617793 broker did not answer
```

### Rate Confirmation PDF Upload

The dispatcher can send a PDF rate confirmation to Telegram with caption:

```text
/ratecon MANUAL-CLEAN-FLATBED-001 rate con received
```

The PDF is saved locally in:

```text
data/ratecons/<date>/
```

and connected to dispatcher feedback.

Later, PDF parsing will extract:

* broker
* rate
* pickup
* delivery
* reference ID
* equipment
* weight
* appointment times

---

## Telegram Outbox Logging

Every outgoing Telegram message is logged locally into:

```text
data/telegram_outbox.jsonl
```

This file records:

* message type
* category
* driver name
* pickup
* delivery
* rate
* broker
* broker MC
* reference ID
* Telegram message ID
* full message text

This file answers the question:

```text
What exactly did the bot send to the dispatcher?
```

---

## DispatchCase System

The project now includes an early DispatchCase builder.

Run:

```powershell
py scripts/build_dispatch_cases.py
```

This reads:

```text
data/decision_history.jsonl
data/dispatcher_feedback.jsonl
```

and builds:

```text
data/dispatch_cases.jsonl
data/dispatch_events.jsonl
```

Current event types:

```text
AI_DECISION_CREATED
DISPATCHER_FEEDBACK_ADDED
RATECON_RECEIVED
```

Planned event types:

```text
LOAD_APPEARED
LOAD_UPDATED
LOAD_REMOVED
TELEGRAM_ALERT_SENT
BROKER_CALLED
SENT_TO_DRIVER
DRIVER_REJECTED
BOOKED
COVERED
BAD_BROKER_REPORTED
```

The goal is to track the full lifecycle of every dispatch opportunity.

---

## Timed Load Board Simulator

Before connecting DAT API, the project uses a timed simulation layer.

Timeline file:

```text
data/simulation/load_board_timeline.json
```

Runtime active simulated loads:

```text
data/simulation/current_simulated_loads.json
```

Run simulation:

```powershell
py scripts/run_load_board_simulation.py --step 1 --clear-sent
py main.py
```

Next steps:

```powershell
py scripts/run_load_board_simulation.py --step 2 --clear-sent
py main.py

py scripts/run_load_board_simulation.py --step 3 --clear-sent
py main.py
```

Simulation supports:

```text
LOAD_APPEARED
LOAD_UPDATED
LOAD_REMOVED
```

This allows testing:

* new load appearance
* rate = 0 / RATE CHECK
* rate updates
* covered / removed loads
* broker reposts
* duplicate alert behavior
* DispatchCase creation
* event timeline behavior

This simulator is used before connecting live DAT/API data.

---

## Setup

### 1. Clone repository

```powershell
git clone https://github.com/EnDoKeR/AI-Dispatch-Team.git
cd AI-Dispatch-Team
```

### 2. Create `.env`

Create a local `.env` file in the project root:

```text
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Do not commit `.env`.

### 3. Install requirements

The project currently uses mostly Python standard library.

See `README_SETUP.md` for the current dependency policy and optional legacy/manual integration notes.

If dependencies are added later, install them with:

```powershell
pip install -r requirements.txt
```

### 4. Run main bot

```powershell
py main.py
```

### 5. Run decision logging

```powershell
py scripts/log_decisions_snapshot.py
```

### 6. Build DispatchCases

```powershell
py scripts/build_dispatch_cases.py
```

### 7. Run Telegram feedback bot

In a separate PowerShell window:

```powershell
py scripts/telegram_feedback_bot.py
```

---

## Important Git Ignore Rules

The following files contain private runtime or operational data and should not be committed:

```text
.env
data/credentials/
data/decision_history.jsonl
data/decision_runs.jsonl
data/dispatcher_feedback.jsonl
data/dispatch_cases.jsonl
data/dispatch_events.jsonl
data/telegram_outbox.jsonl
data/telegram_feedback_state.json
data/ratecons/
data/simulation/current_simulated_loads.json
data/simulation/load_board_simulation_events.jsonl
data/sent_market_summaries.txt
data/sent_telegram_loads.txt
data/sent_review_once_loads.txt
data/sent_search_health_alerts.txt
data/sent_reload_chain_alerts.txt
```

---

## Current Roadmap

### Phase 1 вЂ” Current MVP

Status: in progress.

* load matching
* Telegram alerts
* driver profiles
* rate check
* review once categories
* broker/contact parsing
* decision logging
* dispatcher feedback
* Telegram feedback bot
* rate con attachment saving
* DispatchCase builder
* event timeline builder
* timed load board simulator

### Phase 2 вЂ” DispatchCase + Event Timeline

Next priority:

* connect Telegram outbox to DispatchCase events
* add `TELEGRAM_ALERT_SENT`
* add `LOAD_APPEARED`, `LOAD_UPDATED`, `LOAD_REMOVED`
* add case replay report
* add case status report

### Phase 3 вЂ” Simulation Runner

Build a controlled mini load board before DAT API.

Goals:

* step-by-step load appearance
* rate updates
* removal / covered events
* broker repost testing
* duplicate alert testing
* RATE CHECK testing
* event timeline validation

### Phase 4 вЂ” SQLite Dispatch Memory

Move from JSONL-only logs toward:

```text
data/dispatch_memory.db
```

Planned tables:

```text
dispatch_cases
dispatch_events
loads
ai_decisions
dispatcher_feedback
ratecons
brokers
simulation_events
```

SQLite is the next local operational memory layer.

### Phase 5 вЂ” Broker Memory

Build broker intelligence from feedback and outcomes.

Broker memory should track:

* MC
* broker name
* contact history
* factoring status
* rate behavior
* bad broker flags
* negotiation behavior
* fake appointment patterns
* Conestoga restrictions
* rate=0 behavior
* payment / trust notes

### Phase 6 вЂ” Telegram Feedback Buttons

Improve feedback UX with inline buttons:

```text
Booked
Called broker
Sent to driver
Rate too low
Driver rejected
Bad broker
Covered
Rate con received
```

### Phase 7 вЂ” Desktop Observer

Future Shadow Dispatcher mode.

The agent will observe dispatcher work locally:

* clipboard tracking
* browser/context observation
* opened load detection
* dispatcher action logging
* optional OCR/screen reading later

Initial rule:

```text
Observe first.
Do not click.
Do not book.
Do not send without confirmation.
```

### Phase 8 вЂ” DAT/API Integration

DAT/API or other live data integration should come after:

* simulation works
* DispatchCase model is stable
* event timeline works
* duplicate/update/remove logic is tested
* feedback loop is usable

---

## Development Principles

### 1. Business logic first

The system is built around real dispatch logic, not generic AI suggestions.

### 2. No premature model training

The current goal is not fine-tuning or training a custom LLM.

The current goal is to build high-quality structured dispatch memory.

### 3. Human-in-the-loop

The dispatcher remains the decision maker.

The AI observes, recommends, records, compares, and learns.

### 4. Explain every decision

Every match, review, and block should have reasons.

### 5. Do not build JSON chaos

JSONL is acceptable for MVP logs, but the architecture is moving toward:

```text
DispatchCase
Event Timeline
SQLite Memory
Broker Memory
Replay
```

### 6. Test with simulation before live data

Do not connect live DAT/API before the simulator can prove that the logic handles:

* new loads
* updates
* removed loads
* duplicate broker reposts
* rate changes
* review once logic
* feedback
* case timeline

---

## Current Product Direction

AI Dispatch Team is evolving toward:

```text
Dispatch Operating Intelligence System
```

The long-term product is not only an alert bot.

It is a memory-driven dispatch assistant that can answer:

```text
Why did we book this load?
Why did we reject this broker?
Which RATE CHECK loads became good?
Which brokers waste time?
Which drivers accept which exceptions?
Which lanes are profitable?
Where was AI too strict?
Where was AI too soft?
What did the dispatcher do differently?
```

That is the foundation for a future AI Dispatch Observer and eventually a semi-autonomous dispatch assistant.

```
```


---

## Current Foundation Status

The project is currently in the Foundation Hardening phase.

Completed foundation refactors:

- `DispatchCase` logic was split into focused case modules.
- `market_snapshot.py` is now a runner/orchestrator around focused snapshot modules.
- `market_models.py` was reduced by moving decision helpers, serialization, and driver-profile model helpers into focused market modules.
- `telegram_notifier.py` was reduced into send/orchestration logic with separate formatter/state/transport/selection modules.
- Market context foundation helpers now calculate current snapshot baseline, city/state exit context, exit labels, two-load chain context, and reload-watch state decisions.
- `notes_parser.py` is now an orchestration file around `parse_notes()`.
- `driver_lane_preference_rules.py` is now an orchestration file around `get_driver_lane_preference_status()`.
- `driver_preference_rules.py` is now an orchestration file around `get_driver_preference_status()`.
- `broker_memory_rules.py` is now an orchestration file around `get_broker_memory_status()`.
- `sqlite_memory.py` is now a backward-compatible facade around focused SQLite memory modules.
- `reload_chain.py` is now an orchestrator/facade around focused reload-chain helper modules.

Current modular notes parser structure:

~~~text
notes_parser.py
notes_parser_text_helpers.py
notes_parser_securement.py
notes_parser_dimensions.py
notes_parser_equipment.py
notes_parser_load_requirements.py
notes_parser_payment.py
notes_parser_documents.py
notes_parser_weight_stops.py
notes_parser_pickup.py
notes_parser_contact.py
notes_parser_flags.py
~~~

Current driver lane preference structure:

~~~text
driver_lane_preference_rules.py
driver_lane_preference_core.py
driver_lane_preference_groups.py
driver_lane_preference_queries.py
~~~

Current driver preference structure:

~~~text
driver_preference_rules.py
driver_preference_core.py
driver_preference_queries.py
~~~

Current broker memory structure:

~~~text
broker_memory_rules.py
broker_memory_core.py
broker_memory_queries.py
~~~

Current SQLite memory structure:

~~~text
sqlite_memory.py
sqlite_memory_io.py
sqlite_memory_connection.py
sqlite_memory_schema.py
sqlite_memory_repository.py
sqlite_memory_summary.py
sqlite_memory_rebuild.py
~~~

Current market model structure:

~~~text
market_models.py
market_load_serializer.py
market_driver_profile_model.py
market_basic_metrics.py
market_contact_extractor.py
market_target_helpers.py
market_tracking_requirements.py
market_broker_memory.py
market_document_triggers.py
market_payment_risk_rules.py
market_quality_rules.py
market_od_permit_rules.py
market_weight_rules.py
market_local_load_rules.py
market_conestoga_rules.py
market_direction_matcher.py
~~~

Current market snapshot structure:

~~~text
market_snapshot.py
market_snapshot_builder.py
market_snapshot_console_report.py
market_snapshot_explanation.py
market_snapshot_opportunities.py
market_snapshot_route_fallback.py
market_snapshot_stats.py
market_snapshot_telegram_dispatcher.py
~~~

Current market context foundation structure:

~~~text
market_baseline.py
market_zone_snapshot.py
market_exit_classifier.py
chain_scoring.py
~~~

These helpers provide context only. They do not yet change Telegram behavior, dispatch decisions, load selection, scheduler behavior, Telegram buttons, Google Maps, RateCon parsing, or live DAT/API behavior.

Current reload watch state foundation structure:

~~~text
reload_watch_state.py
reload_watch_event_builder.py
reload_watch_action_planner.py
telegram_watch_formatter.py
reload_watch_record.py
reload_watch_repository.py
reload_watch_service.py
reload_watch_report.py
reload_watch_manual_cli.py
reload_watch_start_cli.py
market_reload_watch_scenario_runner.py
scripts/report_reload_watch.py
scripts/run_reload_watch_event.py
scripts/start_reload_watch.py
scripts/run_market_reload_watch_scenario.py
~~~

These helpers provide state decisions, structured event payloads, side-effect-free action plans, Telegram text formatting, JSON-ready state records, a small JSON-file repository, a manual-call service, a dry-run report, manual start CLI, manual event CLI, and synthetic scenario runner only. They do not send Telegram messages, handle buttons, run a scheduler, write DispatchCase events, write JSONL/SQLite, call Google Maps, parse RateCons, connect DAT/API, or start an automatic reload-watch loop.

Reload-watch Telegram text formatting is isolated in `telegram_watch_formatter.py`. It formats structured plans and payloads only; it does not send messages or decide whether a message should be sent.

Reload-watch records are isolated in `reload_watch_record.py`. It builds and updates JSON-ready dict records only; JSON file I/O stays in the repository module.

Reload-watch JSON persistence is isolated in `reload_watch_repository.py`. It reads and writes a JSON list only; it does not decide watch behavior or send messages.

Reload-watch service orchestration is isolated in `reload_watch_service.py`. It coordinates records, plans, and repository upserts only; it does not format or send Telegram messages.

Reload-watch visibility is isolated in `reload_watch_report.py` and `scripts/report_reload_watch.py`. It reads records and prints a dry-run report only.

Reload-watch manual event testing is isolated in `reload_watch_manual_cli.py` and `scripts/run_reload_watch_event.py`. It can simulate one event for one existing watch record and optionally preview Telegram text without sending anything.

Reload-watch manual start testing is isolated in `reload_watch_start_cli.py` and `scripts/start_reload_watch.py`. It can create or upsert one watch record from minimal parent-load fields without starting automation.

Manual dry-run workflow:

~~~powershell
$watchFile = "$env:TEMP\reload_watch_records.json"
py scripts/start_reload_watch.py --file-path $watchFile --watch-id WATCH-1 --driver-name Alex --parent-load-id LOAD-1 --parent-reference-id REF-1 --pickup "Dallas, TX" --delivery "Denver, CO" --rate 3200 --timestamp 2026-05-29T10:00:00Z
py scripts/report_reload_watch.py --file-path $watchFile
py scripts/run_reload_watch_event.py --file-path $watchFile --watch-id WATCH-1 --event CLEAN_EXIT_FOUND --clean-exits 2 --best-exit-reference-id EXIT-1 --best-exit-pickup "Denver, CO" --best-exit-delivery "Houston, TX" --best-exit-rate 2600 --timestamp 2026-05-29T10:10:00Z --preview-message
py scripts/report_reload_watch.py --file-path $watchFile
~~~

This workflow is manual dry-run only. It writes only to the file path you provide and sends no Telegram messages.

Market + reload-watch scenario dry-run:

~~~powershell
$scenarioFile = "$env:TEMP\market_reload_watch_scenario_records.json"
py scripts/run_market_reload_watch_scenario.py --file-path $scenarioFile
~~~

This synthetic scenario validates market context, exit classification, chain scoring, watch start, clean-exit event simulation, and Telegram preview-only output without live automation.

Reload-watch boundary tests protect these modules from importing sender, scheduler, Telegram, or DispatchCase layers before those are explicitly wired later.

Current intake / RateCon dry-run foundation:

~~~text
app/market_intelligence/intake/record.py
app/market_intelligence/intake/parser_contract.py
app/market_intelligence/intake/summary.py
app/market_intelligence/intake/scenario_runner.py
scripts/run_intake_record_dry_run.py
scripts/run_intake_scenarios.py
~~~

Older `market_intelligence` intake import paths remain as compatibility wrappers for existing tests and scripts. The deleted `app/load_intake/` prototype is not part of the active intake path.

Manual intake dry-run commands:

~~~powershell
py scripts/run_intake_record_dry_run.py
py scripts/run_intake_record_dry_run.py --json '{""broker_name"":""Acme Logistics"",""broker_mc"":""123456"",""rate"":3200,""pickup_location"":""Dallas, TX"",""pickup_date"":""2026-05-30"",""delivery_location"":""Denver, CO"",""delivery_date"":""2026-05-31"",""commodity"":""Steel coils"",""weight"":42000,""reference_id"":""REF-123"",""equipment"":""Conestoga""}'
py scripts/run_intake_record_dry_run.py --json-file tests\fixtures\intake_sample_records\clean_full_ratecon.json
py scripts/run_intake_record_dry_run.py --json-file tests\fixtures\intake_sample_records\clean_full_ratecon.json --intake-id INTAKE-001 --save --records-file data\intake_records.json
py scripts/report_intake_records.py --file-path data\intake_records.json
py scripts/run_intake_scenarios.py
py scripts/run_parser_scenarios.py
py scripts/run_pasted_text_parser_dry_run.py
py scripts/run_manual_ratecon_text_dry_run.py --text "Broker: FAKE BROKER LLC ..."
py scripts/private_ratecon_inventory.py
py scripts/run_private_ratecon_pdf_extraction_inventory.py --limit 3
py scripts/run_private_ratecon_pdf_dry_run.py --limit 3
py scripts/run_private_ratecon_redacted_diagnostics.py --limit 3
py scripts/run_private_ratecon_layout_diagnostics.py --limit 3
py scripts/run_fake_ratecon_candidate_extraction.py
py scripts/run_fake_ratecon_candidate_extraction.py --include-hard-layouts
py scripts/export_ratecon_dry_run_csv.py --limit 3
py scripts/export_private_ratecon_value_review_csv.py --limit 3
py scripts/run_pasted_text_scenarios.py
py scripts/run_decision_engine_scenarios.py
py scripts/run_decision_engine_adapter_dry_run.py
py scripts/run_decision_engine_comparison_report.py
py scripts/run_decision_engine_timeline_report.py
py scripts/run_case_event_report.py
py scripts/run_case_event_report.py --wrapped
py scripts/run_case_event_builder_compatibility.py
py scripts/run_case_event_normalizer_report.py
py scripts/run_current_built_events_normalization_report.py
py scripts/run_intake_case_link_candidate_report.py
py scripts/run_decision_result_timeline_preview.py
~~~

This is dry-run only. It normalizes pasted JSON, one explicit JSON file, manually pasted text, or limited local private PDF text extraction into intake summaries, can optionally save JSON dry-run records to a gitignored local JSON repository, uses synthetic fixtures for intake/parser scenarios, and defines the internal parser output contract. The manual RateCon text dry-run command accepts sample text, `--text`, or safe stdin only; it saves no private text. The private PDF extraction inventory, PDF dry-run, and redacted diagnostics commands read local private PDFs only and print safe summaries with no raw extracted text or private values. The intake-to-case candidate report uses synthetic fixtures only and does not link or create cases. It does not run OCR, send Telegram, write Google Sheets, call Gmail/email APIs, or write DispatchCase events. Synthetic JSON examples live in `tests/fixtures/intake_sample_records/`; synthetic parser-shaped examples live in `tests/fixtures/parser_expected_outputs.py`; synthetic pasted-text examples live in `tests/fixtures/pasted_text_ratecon_examples.py`. Real RateCons must stay local/private; see `docs/RATECON_FIXTURE_SAFETY.md`.

The current official RateCon architecture is documented in `docs/RATECON_PIPELINE_CURRENT_STATE.md`: PDF triage, safe extraction artifacts, fake/anonymized text artifacts, generic candidates, broker template matching, template-aware scoring, conservative resolution, RateConfirmationIntake drafts, and validation. Hard-layout resolver behavior is documented in `docs/RATECON_TEMPLATE_RESOLVER_HARDENING.md`. Older `scripts/import_ratecon.py` and `scripts/read_ratecon.py` are deprecated prototypes and are blocked by default.

DecisionEngine dry-run scenarios are synthetic-only. They validate the new result/signal/risk-flag foundation shape and do not change existing `MarketLoad`, Telegram, DispatchCase, or market snapshot behavior. The adapter dry-run command previews read-only normalization of existing load decision fields into `DecisionResult`; the comparison report checks that the adapter reflects current fields. The case event report command summarizes synthetic event records only, the builder compatibility command compares synthetic current-style builder outputs against the event taxonomy/base payload foundation, the normalizer report previews legacy-plus-normalized event wrapper output, the built-events normalization report runs current-style synthetic events through the wrapper/report layer, and the timeline preview command shows future `AI_DECISION_CREATED` payloads with nested DecisionResult data. These commands are not wired into runtime flow.

Telegram UX planning is documented in `docs/TELEGRAM_UX_PLAN.md`. Current Telegram behavior remains simple and unchanged; future menu/cards/settings/digest work should wait until backend event ownership is stable.

Intake docs:

- `docs/RATECON_INTAKE_WORKFLOW.md`
- `docs/INTAKE_RECORD_MODEL.md`
- `docs/RATECON_FIXTURE_SAFETY.md`

Current Telegram notifier structure:

~~~text
telegram_notifier.py
telegram_sender.py
telegram_load_selection.py
telegram_chain_selection.py
telegram_market_summary_formatter.py
telegram_opportunity_formatter.py
telegram_review_once_formatter.py
telegram_search_health_formatter.py
telegram_chain_formatter.py
telegram_watch_formatter.py
telegram_broker_block.py
telegram_sent_state.py
telegram_text_helpers.py
telegram_duplicate_keys.py
~~~

Current reload chain structure:

~~~text
reload_chain.py
reload_chain_identity.py
reload_chain_location.py
reload_chain_rules.py
reload_chain_scoring.py
~~~

Current testing baseline:

~~~powershell
py -m compileall app scripts main.py
py -m unittest discover -s tests -p "test_*.py"
~~~

Recent full test discovery passed with 1036 tests.

See also:

- `docs/ARCHITECTURE.md`
- `docs/DRIVER_PROFILE_SOURCE_OF_TRUTH.md`
- `docs/FOUNDATION_HARDENING.md`
- `docs/LEGACY_CANDIDATES.md`
- `docs/DEVELOPMENT_RULES.md`
- `docs/ROADMAP.md`
- `docs/TESTING.md`
- `docs/TELEGRAM_OUTBOX_LOGGING.md`
- `docs/TELEGRAM_UX_PLAN.md`
---

## Detailed Roadmap

The detailed roadmap is maintained in:

~~~text
docs/ROADMAP.md
~~~

The roadmap is organized by large logical blocks:

- Foundation Hardening
- DispatchCase and Event Timeline
- Simulation and Replay
- SQLite Dispatch Memory
- Broker / Driver / Lane Memory
- Telegram Feedback UX
- Documentation and Development Rules
- Future DAT/API Integration
- Future AI Dispatch Observer

---

## Engineering Rule Going Forward

New project logic should not be added into already-large files.

Default pattern:

~~~text
small focused module + matching test file + orchestrator import
~~~

Examples:

~~~text
app/market_intelligence/example_feature_core.py
tests/test_example_feature_core.py
~~~

Orchestrator files should coordinate workflow only. They should not become large business-rule containers again.
