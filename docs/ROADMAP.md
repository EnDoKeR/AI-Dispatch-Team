# Roadmap

AI Dispatch Team is evolving from a Telegram load alert bot into a Dispatch Operating Intelligence System.

The roadmap is organized by large logical blocks with subcategories.

---

## Phase 1 - Foundation Hardening

Status: in progress, major progress completed.

Goal:

Make the codebase safe to scale before adding larger product features.

### 1.1 Completed: DispatchCase refactor

Completed modules include:

~~~text
case_status_engine.py
case_id_resolver.py
case_event_builder.py
case_matcher.py
case_factory.py
case_update_applier.py
dispatch_case.py
~~~

Current direction:

- `dispatch_case.py` should remain an orchestrator.
- Case status, event creation, matching, and factory logic should stay in focused modules.

### 1.2 Completed: Market model hardening

Completed helper modules include:

~~~text
market_basic_metrics.py
market_load_serializer.py
market_driver_profile_model.py
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

Current direction:

- `market_models.py` should not become overloaded again.
- New market logic should be added in focused helper modules with tests.
- `MarketLoad` compatibility methods should delegate to focused helpers where practical.

### 1.3 Completed: Telegram notifier hardening

Completed formatter/state/transport/selection modules include:

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
telegram_broker_block.py
telegram_sent_state.py
telegram_text_helpers.py
telegram_duplicate_keys.py
~~~

Completed tests:

~~~text
test_telegram_sender.py
test_telegram_load_selection.py
test_telegram_chain_selection.py
test_telegram_market_summary_formatter.py
test_telegram_opportunity_formatter.py
test_telegram_review_once_formatter.py
test_telegram_search_health_formatter.py
test_telegram_chain_formatter.py
test_telegram_broker_block.py
test_telegram_duplicate_keys.py
test_telegram_text_helpers.py
~~~

Current direction:

- `telegram_notifier.py` should remain send/orchestration logic.
- Message formatting should stay in formatter modules.
- `telegram_load_selection.py` now scans unique sorted loads before applying the unsent alert limit, so already-sent top loads do not hide later unsent good loads.
- `telegram_duplicate_keys.py` separates repost identity, Telegram duplicate prevention, legacy sent-history compatibility, and future update signatures.

### 1.4 Completed: Notes parser refactor

`notes_parser.py` is now orchestration-only around `parse_notes()`.

Completed modules:

~~~text
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

Completed tests:

~~~text
test_notes_parser.py
test_notes_parser_text_helpers.py
test_notes_parser_securement.py
test_notes_parser_dimensions.py
test_notes_parser_equipment.py
test_notes_parser_load_requirements.py
test_notes_parser_payment.py
test_notes_parser_documents.py
test_notes_parser_weight_stops.py
test_notes_parser_pickup.py
test_notes_parser_contact.py
test_notes_parser_flags.py
~~~

### 1.5 Completed: Driver lane preference refactor

`driver_lane_preference_rules.py` is now orchestration-only around `get_driver_lane_preference_status()`.

Completed modules:

~~~text
driver_lane_preference_core.py
driver_lane_preference_groups.py
driver_lane_preference_queries.py
driver_lane_preference_rules.py
~~~

Completed tests:

~~~text
test_driver_lane_preference_core.py
test_driver_lane_preference_groups.py
test_driver_lane_preference_queries.py
~~~

### 1.6 Completed: Driver preference, broker memory, and SQLite memory refactors

Completed memory/refactor modules:

~~~text
driver_preference_core.py
driver_preference_queries.py
driver_preference_rules.py

broker_memory_core.py
broker_memory_queries.py
broker_memory_rules.py

sqlite_memory_io.py
sqlite_memory_connection.py
sqlite_memory_schema.py
sqlite_memory_repository.py
sqlite_memory_summary.py
sqlite_memory_rebuild.py
sqlite_memory.py
~~~

Completed tests:

~~~text
test_driver_preference_core.py
test_driver_preference_queries.py
test_broker_memory_core.py
test_broker_memory_queries.py
test_sqlite_memory_io.py
test_sqlite_memory_connection.py
test_sqlite_memory_schema.py
test_sqlite_memory_repository.py
test_sqlite_memory_summary.py
test_sqlite_memory_rebuild.py
~~~

Current state:

- `driver_preference_rules.py` is orchestration-only.
- `broker_memory_rules.py` is orchestration-only.
- `sqlite_memory.py` is a backward-compatible facade with `__all__`.
- `market_snapshot.py` is runner/orchestrator-only for the current scope.
- Recent full test discovery passed with 729 tests.

### 1.7 Completed: Market snapshot refactor

Completed modules:

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

Current state:

- `market_snapshot.py` now coordinates the workflow.
- Snapshot context building is isolated in `market_snapshot_builder.py`.
- Console report output is isolated in `market_snapshot_console_report.py`.
- Telegram delivery is isolated in `market_snapshot_telegram_dispatcher.py`.
- Direct `telegram_notifier.py` imports were removed from `market_snapshot.py`.

### 1.8 Completed: Reload chain refactor

Completed modules:

~~~text
reload_chain.py
reload_chain_identity.py
reload_chain_location.py
reload_chain_rules.py
reload_chain_scoring.py
~~~

Completed tests:

~~~text
test_reload_chain.py
~~~

Current state:

- `reload_chain.py` now coordinates reload-chain candidate building.
- Identity, location/proximity, qualification rules, and scoring are isolated in focused helper modules.
- Reload-chain behavior is protected by focused tests before future reload intelligence work.

### 1.9 Completed: Market context foundation

Completed modules:

~~~text
market_baseline.py
market_zone_snapshot.py
market_exit_classifier.py
chain_scoring.py
~~~

Completed tests:

~~~text
test_market_baseline.py
test_market_zone_snapshot.py
test_market_exit_classifier.py
test_chain_scoring.py
~~~

Current state:

- `market_baseline.py` calculates current snapshot market context by equipment view and mileage bucket.
- `market_zone_snapshot.py` calculates delivery city/state and state exit-market context.
- `market_exit_classifier.py` converts baseline + zone context into explainable exit labels only.
- `chain_scoring.py` scores a two-load inbound + exit chain as context only.
- These helpers do not change Telegram behavior, dispatch decisions, load selection, scheduler behavior, Telegram buttons, or live automation until explicitly wired later.
- Current market/zone statuses are context labels, not hard business decisions.

### 1.10 Completed: Reload watch state foundation

Completed modules:

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

Completed tests:

~~~text
test_reload_watch_state.py
test_reload_watch_event_builder.py
test_reload_watch_action_planner.py
test_telegram_watch_formatter.py
test_reload_watch_record.py
test_reload_watch_repository.py
test_reload_watch_service.py
test_reload_watch_report.py
test_reload_watch_manual_cli.py
test_reload_watch_start_cli.py
test_reload_watch_dry_run_workflow.py
test_market_reload_watch_scenario_runner.py
test_reload_watch_boundaries.py
~~~

Current state:

- `reload_watch_state.py` models state-only reload-watch transitions.
- `reload_watch_event_builder.py` builds structured reload-watch event payloads so future code does not need Telegram text parsing.
- `reload_watch_action_planner.py` combines the state decision and event payload into a side-effect-free next-action plan.
- `telegram_watch_formatter.py` formats structured reload-watch plans into Telegram text only.
- `reload_watch_record.py` builds and updates JSON-ready reload-watch state records only.
- `reload_watch_repository.py` reads, writes, upserts, and filters reload-watch records in one JSON file only.
- `reload_watch_service.py` coordinates manual start/event handling with planner, record update, and repository upsert.
- `reload_watch_report.py` and `scripts/report_reload_watch.py` provide manual dry-run visibility into watch records.
- `reload_watch_manual_cli.py` and `scripts/run_reload_watch_event.py` provide manual one-event dry-run testing for existing watch records.
- `reload_watch_start_cli.py` and `scripts/start_reload_watch.py` provide manual dry-run watch creation from minimal parent-load fields.
- `market_reload_watch_scenario_runner.py` and `scripts/run_market_reload_watch_scenario.py` provide a synthetic scenario dry-run across market context, exit classification, chain scoring, reload-watch service, and Telegram preview-only formatting.
- `test_reload_watch_dry_run_workflow.py` protects the manual start -> report -> event preview -> report workflow with a temp file.
- `test_reload_watch_boundaries.py` protects reload-watch module boundaries before sender, buttons, scheduler, or DispatchCase wiring exists.
- It answers whether a watch should continue, stop, send a normal status, or allow a critical alert.
- Muted watches suppress normal status updates but still allow critical alerts.
- This foundation includes a small JSON repository, manual-call service, dry-run report, manual start CLI, and manual event CLI, but does not implement scheduler/background automation, Telegram buttons, Telegram messages, DispatchCase writes, SQLite, Google Maps, RateCon parsing, DAT/API, or an actual reload-watch loop.

Manual dry-run workflow:

~~~powershell
$watchFile = "$env:TEMP\reload_watch_records.json"
py scripts/start_reload_watch.py --file-path $watchFile --watch-id WATCH-1 --driver-name Alex --parent-load-id LOAD-1 --parent-reference-id REF-1 --pickup "Dallas, TX" --delivery "Denver, CO" --rate 3200 --timestamp 2026-05-29T10:00:00Z
py scripts/report_reload_watch.py --file-path $watchFile
py scripts/run_reload_watch_event.py --file-path $watchFile --watch-id WATCH-1 --event CLEAN_EXIT_FOUND --clean-exits 2 --best-exit-reference-id EXIT-1 --best-exit-pickup "Denver, CO" --best-exit-delivery "Houston, TX" --best-exit-rate 2600 --timestamp 2026-05-29T10:10:00Z --preview-message
py scripts/report_reload_watch.py --file-path $watchFile
~~~

Synthetic scenario dry-run:

~~~powershell
$scenarioFile = "$env:TEMP\market_reload_watch_scenario_records.json"
py scripts/run_market_reload_watch_scenario.py --file-path $scenarioFile
~~~

### 1.11 Next candidates for hardening

Candidate approach:

~~~text
Run a fresh architecture/file-size audit before choosing another target.
~~~

Current audit notes:

~~~text
docs/LEGACY_CANDIDATES.md
docs/DRIVER_PROFILE_SOURCE_OF_TRUTH.md
docs/TELEGRAM_OUTBOX_LOGGING.md
~~~

Recommended order:

1. Continue reload-watch design only in small blocks.
2. Architecture/import audit.
3. Review remaining large files.
4. Choose next target based on layer-boundary risk.
5. Avoid live automation, scheduler, dashboard, DAT/API, Google Maps, and RateCon expansion until the relevant foundation layer is ready.

---

## Phase 2 - Layer Boundary Audit

Status: next priority.

Goal:

Reduce coupling before adding larger intelligence features.

The system should be checked against these layers:

~~~text
Layer 1 - Raw Intake
Layer 2 - Decision Engine
Layer 3 - DispatchCase Builder
Layer 4 - Memory Layer
Layer 5 - Interfaces
~~~

Audit questions:

- Does Decision Engine know too much about Telegram?
- Does Telegram formatting contain business logic?
- Does SQLite memory directly change decisions?
- Does broker memory override hard rules?
- Does replay have enough structured event data?
- Are there circular imports or cross-layer shortcuts?

Expected outcome:

- clearer module ownership
- fewer cross-layer dependencies
- safer replay and testing
- better preparation for parallel agents and future interfaces

---

## Phase 3 - DispatchCase and Event Timeline

Status: partially complete.

Goal:

Create one operational case timeline per load opportunity.

Completed:

- DispatchCase builder exists.
- Event builder exists.
- Feedback, ratecon, and simulation events are supported.
- Case replay report exists.

Next steps:

- Strengthen duplicate event protection.
- Improve case replay reports.
- Add richer event metadata.
- Ensure Telegram alerts are fully connected to cases.
- Keep current status separate from final outcome.
- Protect final outcomes from being downgraded by later working feedback.

---

## Phase 4 - Simulation and Replay

Status: in progress.

Goal:

Use synthetic/timed load board data before live DAT/API integration.

Completed:

- Timed load board simulator exists.
- Load appeared / updated / removed events are supported.
- Replay examples exist.

Next steps:

- Add more realistic broker repost scenarios.
- Test rate changes and RATE CHECK conversion.
- Test duplicate alert behavior.
- Test removed/covered loads.
- Test lane memory impact in replay only.
- Add more report tests around simulation cases.

---

## Phase 5 - SQLite Dispatch Memory

Status: local SQLite facade split completed; operational memory evolution remains in progress.

Goal:

Move from JSONL-only operational memory toward SQLite-backed dispatch memory.

Completed:

- SQLite memory database exists.
- Memory report exists.
- Dispatch cases, events, feedback, Telegram alerts, and ratecons can be summarized.
- `sqlite_memory.py` was split into focused IO, connection, schema, repository, summary, and rebuild modules.
- `sqlite_memory.py` now remains as a backward-compatible facade.

Next steps:

- Keep JSONL as append-only audit/backup.
- Continue using SQLite as local operational memory.
- Add richer repository/query modules only when real workflows require them.
- Evaluate Postgres later if local SQLite becomes limiting.

---

## Phase 6 - Broker, Driver, and Lane Memory

Status: in progress.

Goal:

Convert dispatcher feedback into useful decision context.

Completed:

- Broker memory rules exist and were split into core/queries/orchestrator modules.
- Driver preference rules exist and were split into core/queries/orchestrator modules.
- Driver lane preference rules exist and were split into core/groups/queries/orchestrator modules.
- Sample-size protection exists.

Rules:

- Memory may add context.
- Memory may add reasons.
- Memory may suggest review.
- Memory must not override hard business rules.
- Under 50 signals, memory remains informational/review context.

Next steps:

- Add memory-vs-hard-block tests.
- Add lane memory replay examples.
- Add reports that show why memory did or did not affect a decision.
- Keep memory informational/review-only until enough evidence exists.

---

## Phase 7 - Telegram Feedback UX

Status: partially complete.

Goal:

Make dispatcher feedback fast and structured.

Completed:

- Telegram feedback bot exists.
- Telegram outbox logging exists.
- Feedback commands exist.
- Ratecon attachment saving exists.

Next steps:

- Improve inline feedback buttons.
- Connect button feedback to DispatchCase timeline.
- Connect button feedback to SQLite memory.
- Improve old callback fallback.
- Show clear Reference ID / NO ID behavior.
- Add tests for Telegram feedback parsing.

---

## Phase 8 - Documentation and Engineering Rules

Status: active.

Goal:

Make the project understandable and safe to continue in future chats.

Completed:

- README exists.
- Architecture docs exist.
- Business rules exist.
- Testing docs exist.
- Foundation hardening docs exist.
- Roadmap now exists.

Next steps:

- Add development rules.
- Keep docs updated after each major business-rule or architecture change.
- Add module ownership descriptions.
- Add current command checklist.
- Add release/change log later.

---

## Phase 9 - Dispatch Replay Engine

Status: future, but high priority after memory hardening.

Goal:

Replay historical dispatch opportunities and compare:

- what the AI recommended
- what dispatcher actually did
- what happened later
- whether the AI was too strict or too soft

Replay input:

- historical market snapshots
- loads
- driver state
- AI decisions
- Telegram alerts
- dispatcher feedback
- final outcomes
- broker and lane memory

Replay output:

- case replay report
- AI-vs-human comparison
- missed opportunity candidates
- bad recommendation candidates
- rule regression evidence
- future training dataset

This is a core moat for the product.

---

## Phase 10 - Missed Opportunity Engine

Status: future, after Replay Engine.

Goal:

Find loads that were ignored, missed, or misclassified.

The engine should detect:

- strong loads ignored by dispatcher
- strong loads blocked by AI too aggressively
- RATE CHECK loads that later became good
- brokers that were underestimated
- lanes that repeatedly produce good outcomes
- AI recommendations that turned out bad

This module should not be built until:

- DispatchCase timeline is stable
- SQLite memory is stable
- replay reports are reliable
- final outcome data is consistent

---
## Phase 11 - Live DAT/API Integration

Status: future, not current priority.

Do not connect live DAT/API until:

- Simulation works reliably.
- DispatchCase timeline is stable.
- Duplicate/update/remove logic is tested.
- Telegram feedback loop is usable.
- SQLite memory is stable.
- Reports can replay and explain decisions.

Next steps when ready:

- Define data-source adapter interface.
- Add DAT/API adapter.
- Preserve simulator as a test data source.
- Test live data in read-only mode first.
- Do not auto-book.
- Do not auto-send without dispatcher confirmation.

---

## Phase 12 - AI Dispatch Observer / Shadow Dispatcher

Status: future.

Goal:

Build a local observer that helps dispatchers without taking uncontrolled actions.

Initial observer rules:

~~~text
Observe first.
Do not click.
Do not book.
Do not send without confirmation.
~~~

Future capabilities:

- Observe dispatcher workflow.
- Identify opened loads.
- Compare dispatcher decision vs AI recommendation.
- Capture why a dispatcher rejected or liked a load.
- Learn from real dispatch behavior.
- Suggest next best actions.
- Support semi-autonomous dispatch later.

---

## Current next step

After this documentation update:

1. Run full tests.
2. Commit documentation.
3. Review file sizes again.
4. Choose the next hardening target.
5. Avoid new large files by default.
