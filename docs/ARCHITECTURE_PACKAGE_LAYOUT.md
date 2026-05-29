# Architecture Package Layout Proposal

Date: 2026-05-29

This proposal defines a future package layout before more Foundation Hardening work adds new modules.

Scope is documentation only. No files are moved here, no imports are changed, and no runtime behavior changes.

## Goals

- keep domain logic discoverable
- prevent large mixed-responsibility files
- make future migrations small and reversible
- preserve old import paths through compatibility wrappers
- avoid migrating high-risk domains too early

## Proposed Packages

### `app/market_intelligence/intake/`

Belongs here:

- JSON-ready intake records
- parser output contract helpers
- dry-run intake summaries
- local intake record repository/reporting
- synthetic intake scenario runner
- future parser adapters after a separate design is accepted

Does not belong here:

- PDF/OCR parsing until explicitly approved
- Telegram upload handling
- Google Sheets writes
- DispatchCase event writes
- Gmail/email integration
- load scoring or dispatch decisions

Current package files:

- `intake/record.py`
- `intake/parser_contract.py`
- `intake/summary.py`
- `intake/repository.py`
- `intake/status.py`
- `intake/report.py`
- `intake/scenario_runner.py`

Migration priority:

```text
Migrated first with compatibility wrappers at the old import paths.
```

### `app/market_intelligence/telegram/`

Belongs here:

- Telegram formatters
- Telegram metadata helpers
- Telegram selection helpers
- Telegram sender/notifier boundaries
- Telegram sent-state helpers

Does not belong here:

- dispatch decisions
- DispatchCase construction
- repository/memory logic
- parser behavior
- reload-watch state transitions

Current files that may eventually move:

- `telegram_sender.py`
- `telegram_notifier.py`
- `telegram_*_formatter.py`
- `telegram_*_metadata.py`
- `telegram_load_selection.py`
- `telegram_chain_selection.py`
- `telegram_sent_state.py`
- `telegram_outbox_logger.py`

Migration priority:

```text
Do not migrate yet. Telegram has many active call paths.
```

### `app/market_intelligence/dispatch_cases/`

Belongs here:

- DispatchCase building
- case matching
- case update application
- event building
- case id resolution

Does not belong here:

- Telegram text parsing as a primary data source
- parser behavior
- storage repository internals
- live Telegram sending

Current files that may eventually move:

- `dispatch_case.py`
- `case_factory.py`
- `case_matcher.py`
- `case_update_applier.py`
- `case_event_builder.py`
- `case_id_resolver.py`

Migration priority:

```text
Do not migrate yet. DispatchCase is core timeline behavior.
```

### `app/market_intelligence/reload_watch/`

Belongs here:

- reload-watch state decisions
- reload-watch event payloads
- action planning
- watch records/repository/service/reporting
- manual reload-watch CLIs and preview helpers when appropriate

Does not belong here:

- Telegram sending/buttons
- scheduler/background loop
- DispatchCase writes
- Google Maps calls
- live DAT/API

Current files that may eventually move:

- `reload_watch_state.py`
- `reload_watch_event_builder.py`
- `reload_watch_action_planner.py`
- `reload_watch_record.py`
- `reload_watch_repository.py`
- `reload_watch_service.py`
- `reload_watch_report.py`
- `reload_watch_manual_cli.py`
- `reload_watch_start_cli.py`
- `market_reload_watch_scenario_runner.py`

Migration priority:

```text
Do not migrate yet. Reload-watch foundation is stable and should stay paused before live wiring.
```

### `app/market_intelligence/market_context/`

Belongs here:

- current market baselines
- city/state zone snapshots
- exit market classification
- market scenario context helpers

Does not belong here:

- Telegram sending
- DispatchCase writes
- reload-watch persistence
- chain scoring beyond market context inputs

Current files that may eventually move:

- `market_baseline.py`
- `market_zone_snapshot.py`
- `market_exit_classifier.py`

Migration priority:

```text
Not first. Keep stable until intake migration proves the wrapper pattern.
```

### `app/market_intelligence/chains/`

Belongs here:

- two-load chain scoring
- reload-chain candidate scoring/rules
- chain identity/location helpers

Does not belong here:

- Telegram formatting/sending
- reload-watch lifecycle
- DispatchCase writes
- Google Maps road miles until explicitly approved

Current files that may eventually move:

- `chain_scoring.py`
- `reload_chain.py`
- `reload_chain_identity.py`
- `reload_chain_location.py`
- `reload_chain_rules.py`
- `reload_chain_scoring.py`

Migration priority:

```text
Do not migrate yet. Reload-chain DispatchCase policy still needs audit.
```

### `app/market_intelligence/memory/`

Belongs here:

- SQLite memory facade/submodules
- broker memory
- driver memory
- feedback memory
- repository/query helpers

Does not belong here:

- formatting
- parsers
- Telegram senders
- live external integrations

Current files that may eventually move:

- `sqlite_memory*.py`
- `broker_memory*.py`
- `driver_learning*.py`
- `driver_preference*.py`
- memory repository/query modules

Migration priority:

```text
Do not migrate yet. Memory has broad dependencies and reporting scripts.
```

### `app/market_intelligence/shared/`

Belongs here:

- small pure helpers shared across domains
- identity helpers
- city/state normalization helpers
- safe numeric/text normalization
- constants that genuinely cross domains

Does not belong here:

- domain-specific business logic
- repositories
- senders
- parsers
- large orchestrators

Current files that may eventually move:

- `load_identity.py`
- small text/location helpers after audit

Migration priority:

```text
Only after a specific shared helper has more than one domain user.
```

## Migration Policy

All package migrations must follow this pattern:

1. propose the target package
2. migrate one domain at a time
3. keep old import path compatibility wrappers
4. add import compatibility tests
5. avoid changing runtime behavior
6. run focused tests
7. run full test discovery
8. update docs

## First Migration Target

The first migration target was:

```text
app/market_intelligence/intake/
```

Reasons:

- intake foundation is new and focused
- modules are mostly pure and dry-run only
- fewer live call paths than Telegram, DispatchCase, reload-watch, or memory
- old import wrappers can preserve compatibility

Migration status:

- intake foundation modules now live in `app/market_intelligence/intake/`
- old root-level intake module paths remain thin wrappers
- scripts and existing tests continue to use old import paths safely until a later import cleanup
- `tests/test_intake_package_boundaries.py` protects the package from forbidden live/integration imports
- Telegram, DispatchCase, reload-watch, chains, memory, and market-context packages are not migrated yet

## Packages Not To Migrate Yet

Do not migrate these in the first package-layout phase:

- Telegram
- DispatchCase
- reload-watch
- reload-chain/chains
- memory/SQLite
- market snapshot orchestrators

These areas have broader behavior surfaces and should get separate audits before any move.
