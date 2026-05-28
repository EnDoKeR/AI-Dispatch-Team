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

### 1.3 Completed: Telegram notifier hardening

Completed formatter/state modules include:

~~~text
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

Current direction:

- `telegram_notifier.py` should remain send/orchestration logic.
- Message formatting should stay in formatter modules.

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

### 1.6 Next candidates for hardening

Candidate files:

~~~text
sqlite_memory.py
driver_preference_rules.py
broker_memory_rules.py
reload_chain.py
market_snapshot.py
telegram_notifier.py
market_models.py
~~~

Recommended order:

1. Documentation update.
2. Architecture/import audit.
3. `driver_preference_rules.py` or `broker_memory_rules.py`.
4. `sqlite_memory.py` repository split.
5. `market_snapshot.py` final cleanup.
6. `telegram_notifier.py` final cleanup.

---

## Phase 2 - DispatchCase and Event Timeline

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

## Phase 3 - Simulation and Replay

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

## Phase 4 - SQLite Dispatch Memory

Status: in progress.

Goal:

Move from JSONL-only operational memory toward SQLite-backed dispatch memory.

Completed:

- SQLite memory database exists.
- Memory report exists.
- Dispatch cases, events, feedback, and Telegram alerts can be summarized.

Next steps:

- Split `sqlite_memory.py` into repository modules.
- Add case repository.
- Add event repository.
- Add feedback repository.
- Add Telegram alert repository.
- Add ratecon repository.
- Keep JSONL as append-only audit/backup.
- Evaluate Postgres later if local SQLite becomes limiting.

---

## Phase 5 - Broker, Driver, and Lane Memory

Status: in progress.

Goal:

Convert dispatcher feedback into useful decision context.

Completed:

- Broker memory rules exist.
- Driver preference rules exist.
- Driver lane preference rules exist.
- Sample-size protection exists.
- Lane preference core/groups/queries were split.

Rules:

- Memory may add context.
- Memory may add reasons.
- Memory may suggest review.
- Memory must not override hard business rules.
- Under 50 signals, memory remains informational/review context.

Next steps:

- Strengthen driver preference tests.
- Strengthen broker memory tests.
- Add memory-vs-hard-block tests.
- Add lane memory replay examples.
- Add reports that show why memory did or did not affect a decision.

---

## Phase 6 - Telegram Feedback UX

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

## Phase 7 - Documentation and Engineering Rules

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

## Phase 8 - Live DAT/API Integration

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

## Phase 9 - AI Dispatch Observer / Shadow Dispatcher

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