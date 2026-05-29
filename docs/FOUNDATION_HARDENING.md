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
- `market_snapshot.py` has been split into focused builder/report/dispatcher/helper modules.
- `telegram_notifier.py` has been split into focused sender/selection/formatter/state modules.
- `reload_chain.py` has been split into focused identity/location/rules/scoring helper modules.
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

Next safe candidates:

1. `market_models.py`
