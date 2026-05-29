# DecisionEngine Contract Proposal

This document proposes the future DecisionEngine result shape. It does not implement a new engine or change runtime behavior.

## Purpose

The future DecisionEngine should turn structured evidence into an explainable decision result.

It should answer:

- What is the decision?
- Why was that decision made?
- What evidence was used?
- What is missing or uncertain?
- What should the dispatcher do next?
- Is human approval required?

## Proposed Output Shape

```python
{
    "decision": "MATCH",
    "category": "LOAD OPPORTUNITY",
    "risk_flags": [],
    "missing_fields": [],
    "needs_check_fields": [],
    "review_reasons": [],
    "block_reasons": [],
    "positive_signals": [],
    "explanation": "",
    "confidence": "MEDIUM",
    "source_signals": {},
    "approval_required": True,
    "recommended_next_action": "",
    "linked_load_id": "",
    "reference_id": "",
}
```

## Core Fields

### `decision`

Allowed first-version values:

- `MATCH`
- `REVIEW_ONCE`
- `BLOCK`
- `NO_ACTION`

Meaning:

- `MATCH`: clean enough to show as a strong opportunity.
- `REVIEW_ONCE`: uncertain or potentially useful, but needs dispatcher check.
- `BLOCK`: clear incompatibility or unacceptable risk.
- `NO_ACTION`: no actionable alert or decision should be produced.

### `category`

Human-readable category for routing and reporting.

Examples:

- `LOAD OPPORTUNITY`
- `RATE CHECK`
- `CONESTOGA VERIFY`
- `BROKER REVIEW`
- `DOCUMENTS REQUIRED`
- `TIME CHECK`
- `WEIGHT CHECK`
- `TARPS REQUIRED`
- `BLOCK`

### `risk_flags`

Stable machine-readable flags. These should not replace human-readable reasons.

Examples:

- `RATE_MISSING`
- `NO_CONESTOGA`
- `BROKER_MC_MISSING`
- `WEAK_EXIT_MARKET`

### `missing_fields`

Structured list of required fields that are absent.

Examples:

- `rate`
- `broker_mc`
- `weight`
- `pickup_date`

### `needs_check_fields`

Structured list of fields that exist but are uncertain, partial, suspicious, or low confidence.

Examples:

- `pickup_time`
- `delivery_time`
- `equipment`
- `broker_mc`

### `review_reasons`

Human-readable reasons that explain why a dispatcher should review the load.

These may be shown in Telegram, CLI dry-runs, future dashboard cards, or audit reports.

### `block_reasons`

Human-readable reasons that explain hard blocks.

Hard blocks should remain reserved for clear incompatibilities or accepted safety/business rules.

### `positive_signals`

Human-readable reasons that support the load.

Examples:

- strong gross
- good RPM
- low empty miles
- broker memory positive signal
- clean exit available

### `explanation`

Short dispatcher-facing summary of the decision.

It should be understandable without reading raw code or raw rule state.

### `confidence`

Suggested first-version values:

- `HIGH`
- `MEDIUM`
- `LOW`
- `UNKNOWN`

Confidence should describe the quality of the decision evidence, not the confidence of booking success.

### `source_signals`

Structured evidence used to reach the decision.

Examples:

```python
{
    "load_facts": {...},
    "parsed_notes": {...},
    "driver_profile": {...},
    "broker_memory": {...},
    "market_context": {...},
    "intake_record": {...},
}
```

This field is important for replay and audit.

### `approval_required`

Boolean.

Initial policy:

- `MATCH` should usually still require dispatcher approval before booking.
- `REVIEW_ONCE` requires dispatcher review.
- `BLOCK` does not require booking approval because it should not be booked.
- `NO_ACTION` normally does not require approval.

Future approval modes may change routing, but should not allow autonomous financial/legal commitments without explicit accepted design.

### `recommended_next_action`

Short structured action hint.

Examples:

- `CALL_NOW`
- `CALL_IF_AVAILABLE`
- `CHECK_RATE`
- `VERIFY_CONESTOGA`
- `CHECK_DOCUMENTS`
- `DO_NOT_SEND`
- `MONITOR`

### `linked_load_id` / `reference_id`

Identifiers for linking the decision to load records, DispatchCase, outbox records, replay, and future documents.

## Boundary Rules

The future DecisionEngine must not:

- send Telegram messages
- format Telegram text
- write DispatchCase records or events
- write JSONL/SQLite records directly
- call DAT/API, Google Maps, Gmail/email, Google Sheets, or any external service
- parse PDFs or OCR output
- make autonomous booking, legal, financial, or factoring commitments

The DecisionEngine may:

- consume structured facts and context
- apply business rules
- produce explainable structured decisions
- produce risk flags and reasons
- produce recommended next actions
- indicate whether approval is required

## Layer Responsibilities

Parser/intake should provide structured evidence, missing fields, and confidence.

Market context helpers should provide statistical context and risk labels.

Memory helpers should provide historical context and confidence/sample quality.

DecisionEngine should combine evidence into an explainable decision result.

Formatters should only transform a final result into interface-specific text.

Repositories should only read/write records.

DispatchCase should store timeline/state after a separate policy decides what event should be written.

## Compatibility Principle

The first implementation must wrap existing behavior rather than replacing it.

Current `MarketLoad` fields and existing tests should remain valid until a migration is explicitly accepted.

## Implementation Status

`app/market_intelligence/decision_engine/result.py` now provides a pure JSON-ready DecisionResult helper matching this contract.

It normalizes decision values, confidence, list fields, source signals, approval defaults, and risk flags. It is not wired into current runtime flow yet and does not change existing `MATCH` / `REVIEW_ONCE` / `BLOCK` behavior.

## Input Signal Map

The future DecisionEngine should consume structured signal groups. It should not parse Telegram text or raw PDFs directly.

### 1. Load Facts

Typical source:

- `MarketLoad`
- load-board snapshot
- simulation load
- future normalized intake/load record

Signals:

- pickup
- delivery
- rate
- loaded miles
- empty miles
- total miles
- total RPM
- weight
- commodity
- dimensions
- posted trailer/equipment
- pickup date
- pickup time
- delivery date
- delivery time
- reference ID
- broker name
- broker MC

Decision use:

- rate/RPM quality
- lane fit
- weight/dimension compatibility
- timing review
- missing data review
- load identity/linking

### 2. Parsed Notes Facts

Typical source:

- `notes_parser.py`
- `notes_parser_*`
- future document/parser extracted notes evidence

Signals:

- tarp requirement
- tarp size
- no Conestoga language
- Conestoga allowed/preferred/denied language
- flatbed or step-deck compatibility language
- tracking required
- hazmat required
- TWIC required
- tanker required
- ramps/dunnage/wood required
- OD/oversize/permit language
- dimensions
- actual pickup
- multiple loads/stops
- appointment requirement
- contact override
- payment risk language

Decision use:

- equipment compatibility
- document requirement review/block
- Conestoga verification
- payment/broker risk warning
- needs-check fields

### 3. Driver Profile

Typical source:

- `driver_profile.py`
- `driver_profile_loader.py`
- `SearchRequest`

Signals:

- driver name
- equipment
- max weight
- max empty miles
- target direction
- target city/radius
- target direction mode
- tarp capability
- max tarp size
- OD/permit capability
- hazmat/TWIC/tanker status
- ramps/dunnage status
- tracking tolerance
- blocked lanes/states later
- preferences and notes

Decision use:

- driver/load compatibility
- target-direction fit
- hard blocks for known incompatibilities
- review when capability is unknown

### 4. Broker Memory

Typical source:

- `broker_memory_core.py`
- `broker_memory_rules.py`
- broker memory SQLite/query helpers

Signals:

- broker MC
- broker status
- broker risk level
- prior bad broker feedback
- rate negotiation history
- watchlist status
- positive broker history
- sample size/confidence later

Decision use:

- add review warning
- add positive signal
- never override hard business blocks

### 5. Market Context

Typical source:

- `market_baseline.py`
- `market_zone_snapshot.py`
- `market_exit_classifier.py`
- `chain_scoring.py`
- market snapshot helpers

Signals:

- market median RPM
- market median rate
- mileage bucket stats
- market status
- qualified load count
- clean match count
- review-once count
- blocked count
- delivery city/state exit status
- clean exit count
- review exit count
- rate-check exit count
- chain score/status
- secondary exit risk

Decision use:

- context, priority, and review warnings
- reload-watch recommendation
- avoid treating weak market/weak zone as an automatic hard block
- compare load quality against current snapshot instead of only static thresholds

### 6. Dispatch Memory

Typical source:

- DispatchCase timeline
- dispatcher feedback
- driver preference helpers
- driver lane preference helpers
- broker memory helpers
- SQLite memory later

Signals:

- prior feedback
- rejected reasons
- booked outcomes
- sent-to-driver outcomes
- ratecon received outcomes
- skipped/covered/rate-too-low feedback
- driver/lane sample quality
- can-affect-decision policy

Decision use:

- add review context
- add positive/negative historical signals
- avoid overriding hard business logic unless a future policy explicitly allows it

### 7. Intake / Parser Evidence

Typical source:

- `app/market_intelligence/intake/record.py`
- `app/market_intelligence/intake/parser_contract.py`
- pasted-text parser adapter
- future PDF/OCR parser output

Signals:

- intake ID
- source type
- source file name
- broker name/MC
- rate
- pickup/delivery fields
- commodity
- weight
- reference ID
- equipment
- special requirements
- missing fields
- needs-check fields
- field confidence
- linked DispatchCase ID later

Decision use:

- attach document-derived evidence
- explain missing/uncertain fields
- prepare for future DispatchCase linking
- never let parser output make the dispatch decision by itself

### 8. Approval Mode

Potential source:

- future configuration
- dispatcher/user settings
- operational policy

Initial modes:

- `COPILOT`
- `SUPERVISED`
- `AUTOPILOT` later, only if explicitly designed and accepted

Decision use:

- decide how recommendations are routed
- decide whether a dispatcher must approve before action
- never bypass explicit approval for booking, factoring, legal, or financial commitments

Initial policy:

- `COPILOT`: recommendation and explanation only
- `SUPERVISED`: can prepare actions, but dispatcher confirms
- `AUTOPILOT`: future concept only; not implemented and not approved

Implementation status:

`app/market_intelligence/decision_engine/approval_modes.py` now provides a conservative pure helper for approval mode normalization and action approval checks. Booking, rate commitments, factoring, financial, and legal actions still require approval in every mode.

### Signal Ownership Rule

Each signal group should be built before entering the DecisionEngine.

The DecisionEngine should combine signals. It should not own:

- raw PDF/OCR parsing
- Telegram text parsing
- Google Maps calls
- DAT/API calls
- Gmail/Google Sheets calls
- DispatchCase writes
- accounting/factoring submission

### Minimal First Implementation Input

A safe first DecisionEngine wrapper can start with:

```python
{
    "load": load,
    "search_request": search_request,
    "market_context": {},
    "intake_record": {},
    "memory_context": {},
    "approval_mode": "COPILOT",
}
```

This keeps the first implementation small while preserving the target architecture.

Implementation status:

`app/market_intelligence/decision_engine/signals.py` now provides a pure JSON-ready signal bundle helper for these groups. It does not extract facts, mutate inputs, decide `MATCH` / `REVIEW_ONCE` / `BLOCK`, or wire into runtime flow.

## Dry-run Scenario Status

`app/market_intelligence/decision_engine/scenario_runner.py` and `scripts/run_decision_engine_scenarios.py` now validate synthetic DecisionEngine scenarios against the signal bundle and DecisionResult shape.

This is dry-run only. The runner compares expected scenario fields to the current DecisionEngine foundation helpers. It does not evaluate real loads, wrap `MarketLoad.apply_search_request(...)`, send Telegram messages, write DispatchCases, change market snapshots, or call external services.

## Read-only MarketLoad Adapter Status

`app/market_intelligence/decision_engine/marketload_adapter.py` now provides a read-only adapter that converts existing load decision fields into `DecisionResult`.

Current scope:

- reads existing `driver_match_status`, category/review fields, reasons, and identifiers
- preserves existing `MATCH` / `REVIEW_ONCE` / `BLOCK` outcomes
- preserves human-readable review/block/positive reason text
- maps only conservative existing signals into risk flags
- supports a dry-run preview command: `py scripts/run_decision_engine_adapter_dry_run.py`

Current non-scope:

- no call to `MarketLoad.apply_search_request(...)`
- no runtime wiring
- no load selection changes
- no Telegram behavior changes
- no DispatchCase writes
- no market snapshot behavior changes
- no external service calls

The adapter is ready for report-only comparison tooling, but not for changing production decision flow.

## Comparison Report Status

`app/market_intelligence/decision_engine/comparison_report.py` and `scripts/run_decision_engine_comparison_report.py` now provide a report-only comparison between existing load decision fields and the normalized `DecisionResult` produced by the read-only adapter.

Current scope:

- uses synthetic/fake load-like fixtures
- compares original decision/category fields with adapter decision/category fields
- summarizes adapter risk flags
- reports missing decision/category/reference warnings
- supports a dry-run command: `py scripts/run_decision_engine_comparison_report.py`

Current non-scope:

- no decision correctness evaluation
- no call to `MarketLoad.apply_search_request(...)`
- no runtime wiring
- no load selection changes
- no Telegram behavior changes
- no DispatchCase writes
- no market snapshot behavior changes
- no external service calls

The report is a compatibility lens only. It helps validate adapter coverage before any future timeline/case integration is considered.

## Timeline Preview Status

`app/market_intelligence/decision_engine/timeline_preview.py`, `app/market_intelligence/decision_engine/timeline_preview_report.py`, and `scripts/run_decision_result_timeline_preview.py` now provide a report-only preview of future `AI_DECISION_CREATED` timeline payloads that include nested `DecisionResult` data.

Command:

```powershell
py scripts/run_decision_result_timeline_preview.py
```

Current scope:

- uses synthetic DecisionResult fixtures only
- builds base event payload previews with `event_type = AI_DECISION_CREATED`
- embeds normalized `decision_result`
- marks every payload with `preview_only = True` and `runtime_wired = False`
- summarizes decisions, risk flags, case IDs, and validation warnings

Current non-scope:

- no event writes
- no DispatchCase reads or writes
- no `case_event_builder.py` changes
- no runtime DecisionResult wiring
- no Telegram behavior changes
- no load selection or market snapshot changes

This preview shows a possible future event payload shape. It is not a migration and is not production event behavior.
