# DispatchCase / Event Timeline Gap Audit

Date: 2026-05-29

Status:

```text
Audit only. No runtime behavior changes.
```

Scope:

- no DispatchCase behavior changes
- no DecisionEngine runtime wiring
- no Telegram runtime changes
- no new case/event writes
- no schema changes
- no DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, or reload-chain metadata work

## Current Case Builder Flow

Manual script:

```text
scripts/build_dispatch_cases.py
```

Current inputs:

```text
data/decision_history.jsonl
data/dispatcher_feedback.jsonl
data/telegram_outbox.jsonl
data/simulation/load_board_simulation_events.jsonl
```

Current outputs:

```text
data/dispatch_cases.jsonl
data/dispatch_events.jsonl
```

Core orchestrator:

```text
app/market_intelligence/dispatch_case.py
```

Focused helpers:

```text
case_id_resolver.py
case_factory.py
case_matcher.py
case_update_applier.py
case_event_builder.py
case_status_engine.py
event_logger.py
```

## What Currently Creates DispatchCases

### 1. Decision History Records

Every decision record creates or replaces a case snapshot via:

```text
build_case_from_decision(...)
```

Current event:

```text
AI_DECISION_CREATED
```

This is load-level behavior.

### 2. Successful Load-level Telegram Outbox Records

Successful outbox records are eligible for load-level case processing only when:

```text
message_type in {"LOAD_OPPORTUNITY", "REVIEW_ONCE"}
```

The builder tries to match an existing case with:

```text
outbox_matches_case(...)
```

If no case matches, it can create an outbox-only load case with:

```text
build_case_from_outbox(...)
```

Current event:

```text
TELEGRAM_ALERT_SENT
```

This is load-level behavior only for `LOAD_OPPORTUNITY` and `REVIEW_ONCE`.

### 3. Dispatcher Feedback Records

Feedback records try to match an existing case with:

```text
feedback_matches_case(...)
```

If no case matches, feedback can create a fallback case with:

```text
build_case_from_feedback(...)
```

Current event:

```text
DISPATCHER_FEEDBACK_ADDED
```

If feedback includes `document_path`, an additional event is emitted:

```text
RATECON_RECEIVED
```

This is currently load-level behavior.

## What Currently Creates Events

Current event builders:

- `build_ai_decision_created_event(...)`
- `build_telegram_alert_sent_event(...)`
- `build_load_board_simulation_event(...)`
- `build_dispatcher_feedback_added_event(...)`
- `build_ratecon_received_event(...)`

Current event types protected by tests:

```text
AI_DECISION_CREATED
TELEGRAM_ALERT_SENT
LOAD_APPEARED
DISPATCHER_FEEDBACK_ADDED
RATECON_RECEIVED
```

`case_event_builder.py` can build payloads for `LOAD_UPDATED` and `LOAD_REMOVED`, but `dispatch_case.build_cases_and_events(...)` currently attaches simulation events only when `event_type == "LOAD_APPEARED"` and the event matches an existing case.

## Current Load-level Records

Load-level records today:

- decision history records
- `LOAD_OPPORTUNITY` outbox records
- `REVIEW_ONCE` outbox records
- dispatcher feedback tied to load/reference identity
- ratecon feedback/document events when tied to feedback
- simulation `LOAD_APPEARED` events when they match an existing case

Load-level matching uses:

- driver name
- load ID
- reference ID
- pickup/delivery lane
- broker MC where available

## Current Search/session-level Records

There is no dedicated `DispatchSearchSession` model yet.

Search/session-shaped records today:

- `MARKET_SNAPSHOT`
- `SEARCH_HEALTH_CHECK`
- future search settings changes
- future no-clean-match events
- possible future search-level reload-watch status

Current policy:

- `MARKET_SNAPSHOT` is outbox/reporting-only.
- `SEARCH_HEALTH_CHECK` is outbox/reporting-only.
- Neither creates or updates load-level DispatchCases.

## Current Reporting-only Records

Reporting-only records today:

- `MARKET_SNAPSHOT` outbox records
- `SEARCH_HEALTH_CHECK` outbox records
- reload-watch dry-run reports
- market/reload-watch synthetic scenario runner output
- intake dry-run summaries
- parser scenario reports
- DecisionEngine scenario reports
- DecisionEngine adapter dry-run output

These records should not create load-level cases without a separate accepted policy.

## DecisionResult Status

Current DecisionEngine foundation:

- risk flag helper
- DecisionResult helper
- approval mode helper
- signal bundle helper
- synthetic scenario runner
- read-only MarketLoad adapter

Current policy:

```text
DecisionResult is report/dry-run only.
```

Where it should appear later:

- as evidence inside `AI_DECISION_CREATED` payloads when a load-level case already exists
- as report-only comparison output before runtime wiring
- as source evidence for replay once timeline policy is stable

What should not happen yet:

- DecisionResult should not write cases.
- DecisionResult should not replace current `MarketLoad` behavior.
- DecisionResult should not change Telegram alerts.
- DecisionResult should not create DispatchCase events until a wiring policy is accepted.

## IntakeRecord Status

Current intake foundation:

- JSON-ready intake record helper
- parser contract
- dry-run summary
- JSON repository
- report CLI
- synthetic scenarios
- pasted-text parser dry-run

Current policy:

```text
IntakeRecord does not create DispatchCases.
```

Where it should link later:

- to an existing load-level DispatchCase after explicit matching policy
- to a future document evidence record
- to a future accounting/factoring packet flow

What should not happen yet:

- parser output should not create a case automatically
- intake records should not write events automatically
- missing fields should not become dispatch decisions by themselves
- private RateCon files should not be committed or processed in tests

## Document / Factoring Event Status

Current document-related event:

```text
RATECON_RECEIVED
```

It is emitted only when feedback has a `document_path`.

Future document/factoring events may include:

- `RATECON_PARSED`
- `DOCUMENT_FIELDS_IMPORTED`
- `DOCUMENT_NEEDS_CHECK`
- `POD_RECEIVED`
- `INVOICE_CREATED`
- `FACTORING_PACKET_PREPARED`
- `FACTORING_PACKET_APPROVED`
- `FACTORING_PACKET_SENT`

These are not implemented.

Future factoring/accounting events require a separate policy because they can imply financial or legal commitments.

## Records That Should Not Create Load-level Cases

Current protected exclusions:

- `MARKET_SNAPSHOT`
- `SEARCH_HEALTH_CHECK`

Current dry-run/non-runtime records that should remain excluded:

- reload-watch dry-run/manual records
- reload-watch scenario runner output
- intake repository records
- parser scenario output
- DecisionEngine scenario output
- DecisionEngine adapter dry-run output
- Telegram UX planning artifacts

Future candidates that should remain excluded until policy exists:

- reload-chain alerts
- reload-watch live alerts
- market digests
- search settings changes
- accounting/factoring packet status

## Current Test Protection

Protected behavior includes:

- decision records create cases and `AI_DECISION_CREATED`
- successful `LOAD_OPPORTUNITY` outbox records create/update load cases
- successful `REVIEW_ONCE` outbox records create/update load cases
- failed outbox records are ignored
- `MARKET_SNAPSHOT` does not attach to or create load-level cases
- `SEARCH_HEALTH_CHECK` does not attach to or create load-level cases
- feedback can create fallback cases
- feedback updates status
- `RATECON_RECEIVED` becomes a final status/outcome
- final outcomes are not downgraded by later working feedback
- event deduplication removes exact duplicate event keys
- `LOAD_APPEARED` simulation event can attach to an existing case

Relevant tests:

```text
tests/test_dispatch_case_builder.py
tests/test_case_factory.py
tests/test_case_matcher.py
tests/test_case_update_applier.py
tests/test_case_event_builder.py
tests/test_foundation_rules.py
```

## Gaps Blocking Future Runtime Wiring

### Gap 1: No Search/session Entity

`MARKET_SNAPSHOT` and `SEARCH_HEALTH_CHECK` have no natural home except outbox/reporting.

Needed before wiring:

- decide whether to create `DispatchSearchSession`
- define IDs for driver/search/session records
- define events such as `MARKET_SNAPSHOT_SENT` and `SEARCH_HEALTH_CHECK_SENT`

### Gap 2: DecisionResult Storage Policy Is Undefined

The new `DecisionResult` shape is ready, but the timeline does not yet define where it belongs.

Needed before wiring:

- decide whether `AI_DECISION_CREATED` payload should include a nested DecisionResult
- decide whether old `ai_decision` fields remain as compatibility fields
- add tests to preserve current decision history behavior

### Gap 3: Intake-to-case Linking Policy Is Undefined

Intake records can represent RateCon/broker document evidence, but there is no accepted matching policy yet.

Needed before wiring:

- define confidence rules for matching intake records to cases
- decide whether unlinked intake records stay repository-only
- add tests for reference ID, broker MC, lane, rate, and date matching

### Gap 4: Document Event Taxonomy Is Incomplete

Only `RATECON_RECEIVED` exists today.

Needed before expansion:

- define document event names
- separate document received, parsed, reviewed, approved, and packet-ready states
- protect against accidental factoring/accounting commitments

### Gap 5: Simulation Update/remove Events Are Not Fully Attached

`case_event_builder.py` can build payloads for `LOAD_UPDATED` and `LOAD_REMOVED`, but `dispatch_case.build_cases_and_events(...)` only attaches `LOAD_APPEARED`.

Needed before changing:

- audit desired simulation replay behavior
- test `LOAD_UPDATED` and `LOAD_REMOVED` case attachment rules
- decide how `LOAD_REMOVED` affects case status, if at all

### Gap 6: Reload-watch Is Dry-run Only

Reload-watch has records, action plans, event payloads, and preview formatting, but no live case-writing policy.

Needed before wiring:

- decide whether reload-watch events are load-level, search-level, or watch-level
- define event names and matching rules
- keep muted normal updates separate from critical alerts

### Gap 7: Reload-chain DispatchCase Policy Is Separate

Reload-chain alerts are not currently case-eligible.

Needed before metadata/case wiring:

- audit whether reload-chain belongs to parent load case, exit load case, chain case, or report-only flow
- define event names and identifiers
- protect current load-level `LOAD_OPPORTUNITY` and `REVIEW_ONCE` behavior

## Recommended Next Policy Work

Next mini-block:

```text
DispatchCase/Event ownership policy proposal
```

It should define stable ownership categories before any new runtime case-writing behavior is added.
