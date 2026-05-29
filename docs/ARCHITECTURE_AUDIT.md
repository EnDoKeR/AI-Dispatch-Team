# Architecture Audit

Date: 2026-05-29

This audit was run after the reload-watch dry-run/manual foundation was closed out.

Scope:

- audit only
- no runtime behavior changes
- no Telegram sender wiring
- no Telegram buttons
- no scheduler or live loop
- no DispatchCase writes
- no Google Maps, RateCon expansion, DAT/API, or live board integration

## Checks performed

Reviewed:

- largest `app/market_intelligence` files by line count
- reload-watch module boundaries
- Telegram sender/notifier imports
- DispatchCase/event logger imports in pure helpers
- scheduler/time-loop imports
- legacy candidates
- documentation consistency
- duplicate/repost/chain helper overlap

## Current structure notes

Reload-watch foundation boundaries remain clean.

The current reload-watch files are split by responsibility:

- state decision
- event payload building
- action planning
- Telegram preview formatting
- JSON-ready record building
- JSON repository I/O
- manual service orchestration
- manual report/event/start CLIs
- synthetic market/reload-watch scenario runner

The foundation is still dry-run/manual only. It does not send Telegram messages, attach buttons, run a scheduler, write DispatchCase events, call Google Maps, parse RateCons, or use DAT/API.

## Largest files to keep an eye on

Current larger files are not automatically problems, but they should be watched before adding new logic:

```text
market_models.py
notes_parser.py
telegram_notifier.py
market_baseline.py
market_reload_watch_scenario_runner.py
reload_watch_record.py
market_snapshot_stats.py
telegram_duplicate_keys.py
sqlite_memory_repository.py
dispatch_case.py
telegram_outbox_logger.py
```

Recommendation: do not split these just because they are large. Split only when a clear responsibility boundary or testable bug appears.

## Findings

### 1. Reload-watch foundation is ready for dry-run use

The current reload-watch architecture is suitable for manual testing and scenario previews.

Do not wire it to live Telegram, scheduler loops, buttons, DispatchCase events, or live boards until a separate integration plan is accepted.

### 2. Reload-chain Telegram selection had a limit-order risk

Audit finding: `telegram_chain_selection.py` sliced candidates by `limit` before filtering duplicates and already-sent history.

This could hide later unsent reload-chain candidates when the top candidates were already sent. The normal load selector was already hardened against this pattern.

Follow-up:

```text
Telegram reload-chain selection safety completed.
```

`telegram_chain_selection.py` now scans unique candidates in order and applies `limit` to unsent chains, not to the initial top slice.

### 3. Telegram outbox logging remains text-parser dependent

`telegram_outbox_logger.py` still derives structured data from formatted Telegram text.

This is acceptable for the current foundation, but it is a future risk because formatter text changes can break case matching.

Recommended later mini-block:

```text
Telegram outbox structured metadata audit
```

Do not wire new metadata behavior until the audit defines a small compatibility path.

### 4. Legacy intake remains intentionally isolated

`app/load_intake/` remains a legacy/prototype candidate. It should not be deleted or merged into `market_intelligence` until a separate RateCon/intake design exists.

### 5. Non-chain Telegram metadata foundation is complete enough

Structured sender metadata is now wired for:

- `LOAD_OPPORTUNITY`
- `REVIEW_ONCE`
- `MARKET_SNAPSHOT`
- `SEARCH_HEALTH_CHECK`

The old text parser fallback remains in place for compatibility with historical records and any sender path that does not pass metadata.

Reload-chain alerts still rely on text parsing for live metadata. That should wait because reload-chain needs a separate DispatchCase/search-level policy before metadata can be safely interpreted downstream.

### 6. Compileall warning is noise, not a runtime failure

The recurring command:

```text
py -m compileall app scripts main.py test_sheet_connection.py
```

returns success, but prints `Can't list 'test_sheet_connection.py'` because the old root script has already been moved to `scripts/manual_test_sheet_connection.py`.

This is a good small cleanup candidate: update the standard command references and user workflow so the warning stops distracting from real failures.

## Recommended next targets

1. `Compileall warning cleanup`
   - Safe because the old root `test_sheet_connection.py` no longer exists.
   - Important because a noisy standard command can hide real validation problems.
   - Should update docs/user checklists only unless a test proves code needs changing.

2. `Legacy intake boundary review`
   - Safe if kept audit-only.
   - Important because `app/load_intake/` still mixes intake, scoring, and manual integrations.

3. `Reload-chain DispatchCase policy audit`
   - Important before any reload-chain metadata wiring.
   - Should stay audit-only first because reload-chain is not a simple single-load alert.

Do not start the synthetic 100-200 load dataset yet. It will be more useful after the remaining boundary/policy issues are quieter.

## Do not touch yet

Do not proceed yet with:

- real Telegram reload-watch sending
- Telegram reload-watch buttons
- scheduler or 2-3 minute watch loop
- DispatchCase reload-watch event writes
- Google Maps mileage
- RateCon parsing expansion
- DAT/API or live board integration
- deleting or merging `app/load_intake/`
