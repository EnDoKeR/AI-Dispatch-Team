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
