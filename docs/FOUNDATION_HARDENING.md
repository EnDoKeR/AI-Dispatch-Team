# Foundation Hardening Plan

AI Dispatch Team is moving from a Telegram load alert bot into a Dispatch Operating Intelligence System.

Before adding more growth features, the project needs a stronger engineering foundation.

## Why this phase exists

The current MVP already includes:

- load intake
- AI decision engine
- Telegram alerts
- dispatcher feedback
- DispatchCase timeline
- SQLite dispatch memory
- broker memory
- driver preference memory
- driver lane preference memory
- feedback learning reports
- replay reports
- load board simulation

This is enough functionality to prove the direction.

The next risk is not lack of features.
The next risk is architectural growth without stable boundaries.

## Current foundation status

### Strong areas

- Product logic is strong.
- DispatchCase + event timeline is the correct core.
- Feedback loop is already valuable.
- Broker memory and driver memory are moving in the right direction.
- Sample-size protection prevents premature automation.
- Reports provide useful explainability.

### Weak areas

- Some modules still need layer-boundary review.
- `market_models.py` has been reduced further with serializer and driver-profile model helpers.
- `market_snapshot.py` has been split into focused builder/report/dispatcher/helper modules.
- `telegram_notifier.py` has been split into focused sender/selection/formatter/state modules.
- `reload_chain.py` has been split into focused identity/location/rules/scoring helper modules.
- Market context helpers now exist for current-snapshot baseline, city/state exit context, exit labels, and two-load chain scoring.
- SQLite is now split into focused memory modules, but it is still mostly rebuild/export memory rather than primary operational memory.
- Tests are much stronger now, but every new module still needs focused test coverage from the beginning.
- README is too long for external presentation.

## Core principle

Do not grow into an automatic dispatcher too early.

The correct roadmap is:

1. Decision Engine
2. DispatchCase Memory
3. Feedback Loop
4. RateCon Evidence
5. Replay / Backtesting
6. Shadow Dispatcher
7. Semi-autonomous agent

The project is currently between stages 2 and 4.

## Hard rules for this phase

### 1. No aggressive automation yet

Driver memory, broker memory, and lane memory must not silently override hard business logic.

Memory can add context.
Memory can add reasons.
Memory can flag review.
Memory should not auto-block unless there is enough evidence and a specific rule.

### 2. Hard business logic wins

Examples:

- Equipment mismatch remains a block.
- OD / permit / overweight remains a block when applicable.
- Explicit "No Conestoga" remains a block for Conestoga.
- Missing broker MC must not show BUY.
- Rate = 0 should not auto-block if the load otherwise fits.
- Conestoga can accept tarp-required loads because Conestoga covers the load.

### 3. Sample size protection

Driver behavior should not be trusted from only a few examples.

Signal levels:

- 0-9 signals: INSUFFICIENT_SAMPLE
- 10-24 signals: EARLY_SIGNAL
- 25-49 signals: DEVELOPING_PATTERN
- 50+ signals: RELIABLE_PATTERN

Only 50+ reliable patterns may later be considered for decision influence.

Before that, memory should be informational only.

## Refactor priorities

### Phase 1 — Documentation and boundaries

Create:

- `docs/FOUNDATION_HARDENING.md`
- `docs/ARCHITECTURE.md`
- `docs/BUSINESS_RULES.md`
- `docs/TESTING.md`
- `docs/ROADMAP.md`

Goal:

Document what exists, what each module owns, and what must not be mixed together.

### Phase 2 — Tests

Add tests for:

- Conestoga tarp logic
- No Conestoga blockers
- Flatbed or Step Deck -> Conestoga verify
- Rate = 0 -> REVIEW_ONCE / RATE CHECK, not BLOCK
- Missing broker MC -> UNKNOWN / MC REQUIRED, not BUY
- Feedback status transitions
- Final outcome protection
- RateCon received protection
- Broker memory rules
- Driver preference sample protection
- Driver lane sample protection
- DispatchCase matching
- Telegram outbox matching
- Simulation load appeared / updated / removed

### Phase 3 — DispatchCase refactor

Current problem:

`dispatch_case.py` does too much.

Target split:

- `case_id_resolver.py`
- `case_status_engine.py`
- `case_matcher.py`
- `case_event_builder.py`
- `dispatch_case.py` as orchestrator only

Goal:

Keep the same outputs:

- `data/dispatch_cases.jsonl`
- `data/dispatch_events.jsonl`

But move logic into smaller modules.

### Phase 4 — Market snapshot refactor

Status: completed for the current Foundation Hardening scope.

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

Completed tests:

~~~text
test_market_snapshot_builder.py
test_market_snapshot_console_report.py
test_market_snapshot_explanation.py
test_market_snapshot_opportunities.py
test_market_snapshot_route_fallback.py
test_market_snapshot_stats.py
test_market_snapshot_telegram_dispatcher.py
~~~

Current state:

- `market_snapshot.py` is now runner/orchestrator logic.
- Market snapshot calculation context is built in `market_snapshot_builder.py`.
- Console report formatting is in `market_snapshot_console_report.py`.
- Telegram delivery is in `market_snapshot_telegram_dispatcher.py`.
- Stats, opportunities, explanation, and route fallback are in focused helper modules.
- Direct `telegram_notifier.py` imports were removed from `market_snapshot.py`.

Goal:

Keep behavior the same while making the code easier to maintain.

### Phase 5 — SQLite repository layer

Status: completed for the current local SQLite facade split.

Completed modules:

~~~text
sqlite_memory.py
sqlite_memory_io.py
sqlite_memory_connection.py
sqlite_memory_schema.py
sqlite_memory_repository.py
sqlite_memory_summary.py
sqlite_memory_rebuild.py
~~~

Completed tests:

~~~text
test_sqlite_memory_io.py
test_sqlite_memory_connection.py
test_sqlite_memory_schema.py
test_sqlite_memory_repository.py
test_sqlite_memory_summary.py
test_sqlite_memory_rebuild.py
~~~

Current state:

- `sqlite_memory.py` is now a backward-compatible facade.
- SQLite IO, connection, schema, repository, summary, and rebuild responsibilities are separated.
- JSONL remains the append-only audit source for now.
- SQLite remains local operational memory and reporting memory.

Target future:

- SQLite/Postgres becomes primary operational memory when the live workflow is ready.
- JSONL remains append-only audit log / backup.
- `driver_memory_repository.py`

### Phase 6 - Reload chain refactor

Status: completed for the current Foundation Hardening scope.

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

- `reload_chain.py` is now runner/facade logic for building chain candidates.
- Load identity, chain identity, and duplicate matching live in `reload_chain_identity.py`.
- City/state normalization and first-delivery-to-reload-pickup proximity live in `reload_chain_location.py`.
- First-load and reload-load qualification checks live in `reload_chain_rules.py`.
- Total chain score calculation lives in `reload_chain_scoring.py`.

### Phase 7 - Telegram notifier refactor

Status: completed for the current Foundation Hardening scope.

Completed modules:

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

Current state:

- `telegram_notifier.py` is now send orchestration by message type.
- `.env` loading and Telegram HTTP sending live in `telegram_sender.py`.
- Top/review-once load dedupe, limit, and sent-history filtering live in `telegram_load_selection.py`.
- Reload-chain candidate dedupe, limit, and sent-history filtering live in `telegram_chain_selection.py`.
- Message formatting remains in formatter modules.

### Phase 8 - Market model follow-up refactor

Status: completed for the current Foundation Hardening scope.

Completed modules:

~~~text
market_models.py
market_load_serializer.py
market_driver_profile_model.py
~~~

Completed tests:

~~~text
test_market_load_serializer.py
test_market_driver_profile_model.py
test_market_models.py
~~~

Current state:

- `market_models.py` remains the compatibility home for `MarketLoad`.
- `MarketLoad.to_dict()` now delegates to `market_load_serializer.py`.
- The compatibility `DriverProfile` model now lives in `market_driver_profile_model.py`.
- Existing market rule helpers remain focused modules.

### Phase 9 - Market context foundation

Status: completed for the current Foundation Hardening scope.

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

- `market_baseline.py` calculates current snapshot baseline statistics by mileage bucket and equipment view.
- `market_zone_snapshot.py` calculates delivery city/state and state exit-market context.
- `market_exit_classifier.py` returns context labels such as `LOW_EXIT_CONFIDENCE`, `CLEAN_EXIT_AVAILABLE`, and `STRONG_PAY_RELOAD_WATCH_RECOMMENDED`.
- `chain_scoring.py` evaluates only a two-load inbound + exit chain.
- These modules are foundation/context helpers only. They do not change Telegram behavior, dispatch decisions, load selection, scheduler behavior, Telegram buttons, or live automation.

### Phase 10 - Reload watch state foundation

Status: completed for the current Foundation Hardening scope.

Completed modules:

~~~text
reload_watch_state.py
reload_watch_event_builder.py
reload_watch_action_planner.py
telegram_watch_formatter.py
reload_watch_record.py
reload_watch_repository.py
reload_watch_service.py
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
test_reload_watch_boundaries.py
~~~

Current state:

- `reload_watch_state.py` models reload-watch state transitions and alert decisions without side effects.
- `reload_watch_event_builder.py` builds structured reload-watch event payloads without side effects.
- `reload_watch_action_planner.py` returns side-effect-free next-action plans from state decisions and event payloads.
- `telegram_watch_formatter.py` formats structured reload-watch action plans into Telegram text without sending anything.
- `reload_watch_record.py` builds and updates JSON-ready reload-watch records without actual persistence I/O.
- `reload_watch_repository.py` persists reload-watch records as a JSON list only.
- `reload_watch_service.py` coordinates manual start/event handling with planner, record update, and repository upsert.
- `test_reload_watch_boundaries.py` protects reload-watch module boundaries before future sender, buttons, scheduler, or DispatchCase wiring.
- It can decide whether a watch should continue, stop, send a normal status, or allow a critical alert.
- Muted watches suppress normal status updates but still allow critical alerts.
- This foundation includes a small JSON repository and manual-call service, but does not implement scheduler/background automation, Telegram buttons, Telegram messages, DispatchCase writes, SQLite, Google Maps, RateCon parsing, DAT/API, or an actual reload-watch loop.

## Definition of done for this sprint

This foundation sprint is successful when:

- Core docs exist.
- Core business rules are documented.
- First tests are added.
- DispatchCase logic is split safely.
- Existing reports still work.
- Existing Telegram flow still works.
- Existing SQLite memory reports still work.
- No runtime data is committed.
- GitHub structure is understandable to another engineer.

## Current best next step

Do not add new product features.

Start with:

1. docs
2. tests
3. DispatchCase refactor
4. market snapshot refactor
5. SQLite repository layer
6. reload chain refactor
7. Telegram notifier refactor
8. market model follow-up refactor
9. market context foundation
10. reload watch state foundation

Next safe candidates:

1. Continue reload-watch design only in small blocks.
2. Run a fresh architecture/file-size audit before choosing another target.
