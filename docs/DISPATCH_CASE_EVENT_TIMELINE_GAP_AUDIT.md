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

Policy proposal mini-block:

```text
DispatchCase/Event ownership policy proposal
```

It should define stable ownership categories before any new runtime case-writing behavior is added.

## Event Ownership Policy Proposal

This section proposes ownership rules for future case/event work. It is documentation only and does not change runtime behavior.

### Ownership Principle

Every record or event should have one clear owner:

- load-level DispatchCase
- future search/session entity
- document/intake evidence record
- reporting-only output
- repository/storage record

If ownership is unclear, keep the record reporting-only until a separate policy is accepted.

## 1. Load-level DispatchCase Events

Load-level events belong on one specific freight opportunity/load case.

Current load-level event types:

- `AI_DECISION_CREATED`
- `TELEGRAM_ALERT_SENT`
- `DISPATCHER_FEEDBACK_ADDED`
- `RATECON_RECEIVED`
- `LOAD_APPEARED` when matched to an existing case

Future load-level event types may include:

- `LOAD_UPDATED`
- `LOAD_REMOVED`
- `BROKER_CALLED`
- `SENT_TO_DRIVER`
- `DRIVER_REJECTED`
- `BOOKED`
- `COVERED`
- `PICKUP_CONFIRMED`
- `DELIVERY_CONFIRMED`

Rules:

- event must have a credible load identity
- prefer reference ID or load ID
- lane-only matching must be conservative
- case status changes must be explicit and tested
- final outcomes must not be downgraded by later working events

Before adding any load-level event:

- add focused event builder tests
- add case builder/matcher tests
- add status transition tests if the event can affect status
- prove `LOAD_OPPORTUNITY` and `REVIEW_ONCE` behavior remains unchanged

## 2. Future Search/session-level Events

Search/session-level events describe driver/search state, not one load.

Future candidate entity:

```text
DispatchSearchSession
```

Future event types may include:

- `MARKET_SNAPSHOT_SENT`
- `SEARCH_HEALTH_CHECK_SENT`
- `NO_CLEAN_MATCHES_FOUND`
- `SEARCH_SETTINGS_CHANGED`
- `SEARCH_STARTED`
- `SEARCH_STOPPED`
- `SEARCH_PAUSED`
- `SEARCH_RESUMED`
- `RELOAD_WATCH_STATUS_SENT` if treated as search/watch-level later

Current policy:

- no `DispatchSearchSession` exists
- market summaries remain outbox/reporting-only
- search health checks remain outbox/reporting-only

Before adding search/session-level events:

- define session IDs
- define whether sessions are per driver, per active search request, or per search window
- define storage location
- add tests proving market/search records do not create load-level cases
- add replay/report policy

## 3. Reporting-only Records

Reporting-only records are useful for audit and debugging but should not create cases/events.

Current reporting-only records:

- `MARKET_SNAPSHOT` outbox records
- `SEARCH_HEALTH_CHECK` outbox records
- dry-run scenario outputs
- reload-watch manual/dry-run records
- intake dry-run summaries
- parser scenario reports
- DecisionEngine scenario reports
- DecisionEngine adapter dry-run output

Rules:

- keep them out of load-level case creation
- do not infer cases from empty load fields
- do not attach them by accidental lane text
- preserve them in their own report/repository layer

Future change requires:

- explicit owner entity
- accepted matching policy
- tests proving current load-level behavior remains unchanged

## 4. Intake / Document Evidence

Intake and document records are evidence first.

Current policy:

- `IntakeRecord` stays separate until linked
- parser output should not create a case automatically
- `RATECON_RECEIVED` currently comes only from dispatcher feedback with `document_path`

Future document event types may include:

- `INTAKE_RECORD_CREATED`
- `INTAKE_RECORD_LINKED`
- `RATECON_PARSED`
- `DOCUMENT_FIELDS_IMPORTED`
- `DOCUMENT_NEEDS_CHECK`
- `DOCUMENT_APPROVED`

Rules:

- parser extracts evidence only
- parser must not decide `MATCH` / `REVIEW_ONCE` / `BLOCK`
- intake records should link to a case only after matching confidence is tested
- missing/needs-check fields should remain review context, not dispatch decisions
- real documents and private data must stay out of Git

Before linking intake to cases:

- define link confidence rules
- test reference ID, broker MC, lane, rate, and date matching
- test unlinked records stay repository-only
- test linked records do not create duplicate cases

## 5. DecisionEngine Evidence

DecisionEngine output should be evidence on a case only when a load-level case exists.

Current policy:

- DecisionResult adapter is report/dry-run only
- current `MarketLoad` decision behavior remains source-of-truth for runtime

Future storage policy:

- `AI_DECISION_CREATED` may include a nested `decision_result` payload
- current flat `decision`, `category`, `score`, and `reasons` fields should remain for compatibility
- report-only comparison should come before runtime event writes

Before storing DecisionResult on cases:

- test old event payload fields remain stable
- test nested DecisionResult is JSON-ready
- test no Telegram/DispatchCase behavior changes from adapter use
- test comparison report output against existing decision records

## 6. Reload-watch Ownership

Reload-watch currently has:

- state helper
- event payload builder
- action planner
- Telegram preview formatter
- JSON record/repository
- manual service
- manual start/event/report CLI
- synthetic market/reload-watch scenario runner

Current policy:

- dry-run/manual only
- no live Telegram sending
- no DispatchCase writes

Future ownership options:

- parent load case event
- exit load case event
- future watch-level entity
- future search/session-level event
- reporting-only alert stream

Do not wire reload-watch until ownership is explicitly chosen and tested.

## 7. Reload-chain Ownership

Reload-chain alerts are not currently load-level DispatchCase inputs.

Potential future owners:

- parent/inbound load case
- exit load case
- chain-specific case/entity
- report-only chain context

Open question:

- A chain contains at least two loads, so attaching all context to one load-level case may distort the timeline.

Before reload-chain metadata or events:

- audit reload-chain DispatchCase policy separately
- decide whether chain context belongs to parent, exit, or chain entity
- protect existing `LOAD_OPPORTUNITY` and `REVIEW_ONCE` behavior

## Required Tests Before Behavior Changes

Any future case/event behavior change should add focused tests for:

- no accidental case creation from reporting-only records
- `LOAD_OPPORTUNITY` unchanged
- `REVIEW_ONCE` unchanged
- failed outbox records ignored
- market summary/search health exclusions protected
- event payload shape stable
- case ID stability
- case matching rules
- final outcome downgrade protection
- duplicate event protection
- JSON serializability
- no forbidden adapter imports in core helpers

## Event Type Taxonomy Foundation

`app/market_intelligence/case_event_types.py` now defines stable event type constants and group helpers for current and future timeline events.

Current scope:

- pure constants/helper only
- normalizes event type strings
- validates known event types
- returns event group/category
- lists event types by group

Current non-scope:

- no event writing
- no DispatchCase runtime behavior changes
- no changes to `case_event_builder.py`
- no DecisionResult case/event writes
- no Telegram behavior changes
- no storage/schema changes

This foundation gives future timeline work a shared vocabulary, but it is not wired into existing case creation, matching, update, or event-writing paths yet.

## Base Event Payload Foundation

`app/market_intelligence/case_event_payload.py` now provides a pure JSON-ready base payload helper.

Current scope:

- builds an event envelope with `event_type`, `event_group`, `case_id`, `timestamp_utc`, `source`, `details`, and `related_ids`
- normalizes the event type through the taxonomy helper
- keeps `details` and `related_ids` as dictionaries
- handles unknown event types safely

Current non-scope:

- no event writes
- no replacement of `case_event_builder.py`
- no DispatchCase updates
- no runtime event creation changes
- no DecisionResult timeline writes

This helper is a future payload foundation only. Existing event builders remain the runtime source for current case events.

## Event Timeline Report Foundation

The Event Timeline foundation now includes:

- `app/market_intelligence/case_event_types.py`
- `app/market_intelligence/case_event_payload.py`
- `app/market_intelligence/case_event_report.py`
- `scripts/run_case_event_report.py`
- synthetic fixtures in `tests/fixtures/case_event_records.py`

Current scope:

- stable event type vocabulary
- JSON-ready base event payload helper
- read-only event list summary helper
- synthetic event report CLI

Current non-scope:

- no runtime DispatchCase behavior changes
- no changes to `case_event_builder.py`
- no new event writes
- no DecisionResult timeline events
- no storage reads/writes
- no Telegram behavior changes

The next safe step is a compatibility audit of existing `case_event_builder.py` payloads against the new taxonomy and base payload shape.

## Event Report Wrapper Support

`app/market_intelligence/case_event_report.py` now accepts both:

- current legacy event dictionaries;
- normalized wrapper records with `legacy_payload`, `normalized_payload`, and `warnings`.

Current scope:

- read-only reporting only;
- legacy events remain supported;
- wrapper records prefer normalized payload fields for report grouping;
- wrapper warnings are summarized;
- the `--wrapped` CLI mode uses synthetic wrapper fixtures only.

Current non-scope:

- no runtime event writing;
- no changes to `case_event_builder.py`;
- no DispatchCase build/match/update changes;
- no DecisionResult event writes;
- no runtime storage reads.

Manual dry-run command:

```powershell
py scripts/run_case_event_report.py --wrapped
```

## Current Recommended Next Target

Recommended next implementation target after this policy:

```text
DispatchCase event builder compatibility audit
```

Why:

- the taxonomy/payload/report helpers are now in place
- existing `case_event_builder.py` remains the runtime source for current events
- a compatibility audit can compare current builder payloads against the new vocabulary without changing behavior
- this should happen before any DecisionResult timeline preview or case-writing change

Alternative next target:

```text
report-only DecisionResult timeline preview
```

Use this only after builder compatibility is understood and keep it dry-run/report-only.

Not next:

- runtime DecisionResult case writes
- intake-to-case linking
- reload-chain DispatchCase wiring
- reload-watch live case events
- Telegram UX runtime work
