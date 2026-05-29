# Architecture

AI Dispatch Team is an early-stage Dispatch Operating Intelligence System for flatbed and Conestoga freight dispatch.

The project is no longer just a Telegram load alert bot. The architectural direction is a memory-driven dispatch intelligence platform built around:

- load intake
- decision engine
- DispatchCase lifecycle
- event timeline
- dispatcher feedback
- broker / driver / lane memory
- replay and backtesting
- future observer interfaces

---

## 1. Core architecture principle

The system must be designed in layers.

Each layer should have a clear responsibility and should avoid knowing too much about other layers.

The long-term structure is:

~~~text
Raw Intake -> Decision Engine -> DispatchCase Builder -> Memory Layer -> Interfaces
~~~

The main risk at this stage is coupling.

If market analysis, decision logic, Telegram formatting, event logging, broker memory, reload logic, and SQLite all depend directly on each other, the system will become hard to test, replay, and scale.

---

## 2. Layer 1 - Raw Intake

Raw Intake only handles:

- parsing
- normalization
- ingestion
- source-specific cleanup

Output should be normalized load data, usually represented as `MarketLoad` or a compatible data structure.

Raw Intake must not know about:

- Telegram
- SQLite
- dispatcher feedback
- broker scoring
- driver lane memory
- final decisions

Examples:

~~~text
load_source.py
contact_parser.py
notes_parser.py
notes_parser_*.py
market_contact_extractor.py
~~~

---

## 3. Layer 2 - Decision Engine

Decision Engine produces a decision.

It should answer:

~~~text
Should this load be MATCH, REVIEW_ONCE, BLOCK, or UNKNOWN?
Why?
What category?
What reasons?
~~~

The Decision Engine may use:

- driver profile
- equipment rules
- weight rules
- OD / permit logic
- document requirements
- rate logic
- broker risk context
- memory context when safe

The Decision Engine must not directly handle:

- Telegram sending
- SQLite writes
- PDF/ratecon files
- JSONL persistence
- UI actions

Output should be a structured `LoadDecision`-style result.

---

## 4. Layer 3 - DispatchCase Builder

DispatchCase Builder connects:

- market data
- AI decision
- Telegram alert evidence
- dispatcher feedback
- ratecon evidence
- final outcome
- event timeline

This layer answers:

~~~text
What happened to this opportunity?
What did the AI recommend?
What did the dispatcher do?
What was the final result?
~~~

Examples:

~~~text
dispatch_case.py
case_factory.py
case_event_builder.py
case_matcher.py
case_status_engine.py
case_update_applier.py
case_id_resolver.py
~~~

DispatchCase is the operational backbone of the system.

---

## 5. Layer 4 - Memory Layer

Memory Layer stores and reads structured operational truth.

Current direction:

~~~text
JSONL audit logs -> SQLite operational memory -> future Postgres if needed
~~~

Memory should support:

- broker history
- driver behavior
- lane behavior
- feedback learning

Current SQLite memory structure:

~~~text
sqlite_memory.py                 # backward-compatible facade
sqlite_memory_io.py              # JSONL loading and JSON serialization
sqlite_memory_connection.py      # database path and connection setup
sqlite_memory_schema.py          # table and index creation / cleanup
sqlite_memory_repository.py      # case, event, and child inserts
sqlite_memory_summary.py         # table counts and summary printing
sqlite_memory_rebuild.py         # rebuild orchestration from JSONL
~~~

Memory modules should not contain Telegram formatting, dispatcher UI behavior, or decision-engine hard rules.
- event replay
- case reports
- future probabilistic scoring

Memory must not silently override hard business logic.

Memory can:

- add context
- add reasons
- suggest review
- improve confidence

Memory must not override:

- equipment mismatch
- explicit No Conestoga
- OD / permit hard block
- overweight hard block
- broker MC requirement
- date/time incompatibility
- dimensions that do not fit equipment

---

## 6. Layer 5 - Interfaces

Interfaces expose system output to humans or external tools.

Current interface:

- Telegram alerts
- Telegram feedback bot
- reports

Future interfaces:

- dashboard
- desktop observer
- browser/clipboard observer
- DAT/API adapter
- dispatcher assistant UI

Interfaces must not own core business logic.

Current market model boundary:

~~~text
market_models.py                          # MarketLoad facade/model and match orchestration
market_load_serializer.py                 # MarketLoad dictionary payload
market_driver_profile_model.py            # compatibility DriverProfile model
market_*_rules.py                         # focused decision-rule helpers
market_*_helpers.py                       # focused metric/target/contact helpers
~~~

Current market snapshot boundary:

~~~text
market_snapshot.py                         # runner/orchestrator
market_snapshot_builder.py                 # snapshot context calculation
market_snapshot_console_report.py          # console report formatting
market_snapshot_telegram_dispatcher.py     # Telegram delivery orchestration
~~~

Current market context boundary:

~~~text
market_baseline.py                         # current snapshot baseline by equipment view and mileage bucket
market_zone_snapshot.py                    # delivery city/state and state exit-market context
market_exit_classifier.py                  # context labels for load exit risk; no mutation
chain_scoring.py                           # two-load inbound + exit chain scoring context
~~~

Market context helpers provide review context only at this stage.

They must not:

- send Telegram messages
- mutate loads
- start reload watches
- decide MATCH / REVIEW_ONCE / BLOCK
- call Google Maps or live DAT/API

Until explicitly wired later, these helpers calculate current snapshot context only.

Current reload watch boundary:

~~~text
reload_watch_state.py                      # reload-watch state transition decisions only
reload_watch_event_builder.py              # structured reload-watch event payloads only
reload_watch_action_planner.py             # side-effect-free reload-watch action plans only
telegram_watch_formatter.py                # structured reload-watch plan/payload to text only
reload_watch_record.py                     # JSON-ready reload-watch state records only
~~~

`reload_watch_state.py` is state foundation only. It decides whether a watch should continue, stop, send a normal status, or allow a critical alert.

`reload_watch_event_builder.py` builds structured payloads for future reload-watch events. It does not write DispatchCase events, parse Telegram text, or persist anything.

`reload_watch_action_planner.py` combines state decisions and structured event payloads into explicit action plans. It does not send messages, write events, or decide Telegram text.

`telegram_watch_formatter.py` formats structured reload-watch action plans into Telegram text. It does not decide whether to send, import Telegram senders, parse Telegram text, or attach buttons.

`reload_watch_record.py` builds and updates JSON-ready reload-watch records. It does not read or write files, SQLite, DispatchCase events, or Telegram state.

It must not:

- send Telegram messages
- write JSONL or SQLite
- write DispatchCase events
- run a scheduler
- handle Telegram buttons
- start an automatic watch loop
- call Google Maps or live DAT/API

Future reload-watch integration should stay separated:

~~~text
reload_watch_persistence.py                # future watch state storage only
telegram_watch_sender.py                   # future send/wiring only, if needed
telegram_watch_buttons.py                  # future button callbacks only
reload_watch_case_events.py                # future DispatchCase event wiring only
~~~

Boundary tests protect the current foundation modules from importing sender, persistence, scheduler, or DispatchCase layers early.

Current reload chain boundary:

~~~text
reload_chain.py                            # runner/facade for chain candidate building
reload_chain_identity.py                   # load and chain identity helpers
reload_chain_location.py                   # city/state proximity helpers
reload_chain_rules.py                      # first-load and reload qualification rules
reload_chain_scoring.py                    # total chain score calculation
~~~

Current Telegram notifier boundary:

~~~text
telegram_notifier.py                       # send orchestration by message type
telegram_sender.py                         # .env loading and Telegram HTTP send
telegram_load_selection.py                 # load dedupe/limit/sent-history filtering
telegram_chain_selection.py                # reload-chain dedupe/limit/sent-history filtering
telegram_*_formatter.py                    # message formatting only
telegram_watch_formatter.py                # reload-watch message formatting only
telegram_sent_state.py                     # sent-alert text-file state
~~~

Telegram formatting should not decide whether a load is good.

Dashboard views should not mutate decisions directly.

Observer tools must follow:

~~~text
Observe first.
Do not click.
Do not book.
Do not send without confirmation.
~~~

---

## 7. Replay architecture

Replay is a major future architecture block.

Dispatch Replay Engine should be able to take:

- historical market snapshot
- historical loads
- historical driver state
- historical AI decisions
- dispatcher actions
- final outcomes

and replay:

- what AI would recommend
- what dispatcher actually did
- what happened later
- whether the AI was too strict or too soft

Replay supports:

- backtesting
- evaluation
- AI-vs-human comparison
- training dataset creation
- missed opportunity detection
- rule regression testing

---

## 8. Missed Opportunity Engine

Missed Opportunity Engine is a future intelligence module.

It should identify:

- strong loads that were ignored
- weak loads that AI recommended
- RATE CHECK loads that later became good
- brokers or lanes that were underestimated
- lanes where dispatcher behavior differs from AI recommendations

This should be built after the event timeline, SQLite memory, and replay engine are stable.

---

## 9. Probabilistic memory direction

Broker, driver, and lane memory are currently rules-based.

That is acceptable for MVP and foundation hardening.

Future memory should become more probabilistic.

Possible future signals:

~~~text
broker_reliability_score
broker_negotiation_score
conestoga_acceptance_probability
late_appointment_probability
lane_profitability_score
driver_acceptance_probability
rate_check_conversion_probability
~~~

This must be added carefully after enough structured history exists.

Do not add probabilistic scoring before replay and memory consistency are reliable.

---

## 10. Current architecture discipline

Current development rule:

~~~text
small focused module + matching test file + orchestrator import
~~~

Orchestrator files should coordinate workflow only.

Examples of orchestrator-only direction:

~~~text
notes_parser.py -> parse_notes()
driver_lane_preference_rules.py -> get_driver_lane_preference_status()
dispatch_case.py -> build_cases_and_events()
~~~

New logic should not be added to already-large files without first checking whether it belongs in a focused helper module.

---

## 11. What not to build yet

Do not focus now on:

- autonomous booking
- voice AI
- AI agents everywhere
- huge dashboards
- uncontrolled browser automation
- live DAT/API write actions

Current stage:

~~~text
intelligence infrastructure
~~~

The correct focus is:

- strict layers
- stable entities
- event discipline
- replay architecture
- memory consistency
- tests
