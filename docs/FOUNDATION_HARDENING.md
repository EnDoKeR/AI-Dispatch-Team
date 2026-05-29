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
- `market_snapshot.py` still needs final boundary cleanup.
- `reload_chain.py` still needs architecture review before scaling reload intelligence.
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

Current problem:

`market_snapshot.py` does too much.

Target split:

- `market_snapshot.py` as orchestrator only
- `market_summary_builder.py`
- `load_ranker.py`
- `review_once_selector.py`
- `telegram_dispatcher.py`
- `search_health_checker.py`

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