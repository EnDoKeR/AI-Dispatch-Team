# DecisionEngine MarketLoad Adapter Audit

This audit defines how a future read-only adapter may normalize existing `MarketLoad` decision fields into the new `DecisionResult` shape.

It does not change runtime behavior, load selection, Telegram formatting/sending, DispatchCase behavior, market snapshots, or `MarketLoad.apply_search_request(...)`.

## Current Source Of Truth

`MarketLoad.apply_search_request(...)` is the current runtime decision path. It resets decision state, applies focused rule helpers, then calls `finalize_driver_match(...)`.

The adapter must not call `apply_search_request(...)`. It may only read fields that already exist on a load-like object after current logic has run.

## Existing Decision Fields

Primary decision:

- `driver_match_status`
  - `MATCH`
  - `REVIEW_ONCE`
  - `BLOCK`
  - `UNKNOWN`

Supporting status:

- `driver_fit_status`
  - `CLEAN_MATCH`
  - `REVIEW_ONCE`
  - `BLOCKED`
  - `UNKNOWN`

Internal booleans used by the current rule flow:

- `is_blocked`
- `is_review_once`
- `is_clean_match`

These booleans are important for current rule execution, but the read-only adapter should treat `driver_match_status` as the final decision field when it exists.

## Existing Category Fields

There is no stored category field on `MarketLoad`.

Current category is computed:

- `MATCH` -> `LOAD OPPORTUNITY`
- `BLOCK` -> `BLOCK`
- `REVIEW_ONCE` -> `load.review_category()` when available, otherwise `GENERAL REVIEW`

`review_category()` delegates to `market_review_category.classify_review_category(...)` and derives categories from existing reason text, notes, and commodity.

Known review categories include:

- `RATE CHECK`
- `BROKER REVIEW`
- `OD / PERMIT`
- `CONESTOGA VERIFY`
- `ALONG ROUTE`
- `DOCUMENTS REQUIRED`
- `STRONG OFF-TARGET`
- `TIME CHECK`
- `WEIGHT CHECK`
- `TARPS REQUIRED`
- `GENERAL REVIEW`

The adapter should preserve this category text where possible. It should not invent new routing categories.

## Existing Reason Fields

Positive/match reasons:

- `match_reasons`
- `driver_match_notes` when `driver_match_status == "MATCH"`
- `opportunity_reason()` may summarize positive scoring context, but the first adapter should avoid calling scoring methods unless tests explicitly cover it.

Review reasons:

- `review_reasons`
- `driver_match_notes` when `driver_match_status == "REVIEW_ONCE"`

Block reasons:

- `block_reasons`
- `driver_match_notes` when `driver_match_status == "BLOCK"`
- `reject_reasons()` currently returns block reasons for blocked loads.

The adapter should preserve human-readable reasons exactly. It may dedupe repeated text through the existing `DecisionResult` list normalization, but it must not rewrite reason wording.

## Existing Selection Dependencies

Market snapshot selection currently depends on existing load behavior:

- top opportunities require `load.is_good()` and `driver_match_status == "MATCH"`
- review-once candidates require `driver_match_status == "REVIEW_ONCE"` and either `load.is_good()` or rate-check reason text

Telegram formatters currently consume:

- load facts such as pickup, delivery, rate, miles, weight, equipment, times, notes, broker fields
- `driver_match_notes`
- scoring helpers such as `priority()`, `opportunity_score()`, `suggested_action()`, `opportunity_reason()`
- `review_category()` for review-once messages

The adapter must not become part of selection or Telegram formatting until a separate wiring block is accepted.

## Safe First Mapping To DecisionResult

The first adapter can safely map:

- `driver_match_status` -> `decision`
- computed category -> `category`
- `review_reasons` and REVIEW_ONCE `driver_match_notes` -> `review_reasons`
- `block_reasons` and BLOCK `driver_match_notes` -> `block_reasons`
- `match_reasons` and MATCH `driver_match_notes` -> `positive_signals`
- `reference_id` -> `reference_id`
- `load_id` or existing stable id fields, if present -> `linked_load_id`

Safe defaults:

- unknown or missing decision should become `NO_ACTION`
- missing category should become empty string or `UNKNOWN` only when already present
- missing lists should become empty lists
- missing identifiers should become empty strings

## Conservative Risk Flag Mapping

The adapter may map only obvious current fields/reason text to existing risk flags. It must not create new business decisions.

Potential safe mappings:

- missing or zero rate reason -> `RATE_MISSING`, `RATE_CHECK_REQUIRED`
- `is_low_rpm` or low RPM reason -> `LOW_RPM`
- `is_overweight` or overweight reason -> `OVERWEIGHT`
- `is_local_load` or same-city/local reason -> `LOCAL_LOAD`
- `is_too_far_empty` or empty-miles-over-setting reason -> `PICKUP_TOO_FAR`
- `is_od` or OD/permit/wide-load reason -> `OD_PERMIT_LOAD`
- Conestoga rejection reason -> `NO_CONESTOGA`
- Conestoga verification reason -> `CONESTOGA_VERIFY`
- tracking-required block/review reason -> `TRACKING_REQUIRED`
- Hazmat/TWIC/Tanker document reasons -> `HAZMAT_REQUIRED`, `TWIC_REQUIRED`, `TANKER_REQUIRED`
- ramps/dunnage/legal-status reasons -> `RAMPS_REQUIRED`, `DUNNAGE_REQUIRED`, `LEGAL_STATUS_REQUIRED`
- broker memory review/watchlist/rate-negotiation reasons -> `BROKER_RISK`, `BROKER_WATCHLIST`, `BROKER_RATE_NEGOTIATION_RISK`
- Cash/Zelle/no-buy payment reason -> `PAYMENT_RISK`
- QuickPay/broker-MC-check reason -> `PAYMENT_RISK` or `BROKER_MC_MISSING` only if MC is actually missing
- time marked `NEEDS CHECK` -> `PICKUP_TIME_NEEDS_CHECK` / `DELIVERY_TIME_NEEDS_CHECK`
- strong off-target or pickup-too-far reasons -> `TARGET_DIRECTION_MISMATCH` / `PICKUP_TOO_FAR`

If mapping is ambiguous, preserve the original reason text and leave `risk_flags` empty for that signal.

## Missing And Needs-check Fields

`MarketLoad` does not currently have structured `missing_fields` or `needs_check_fields`.

The first adapter can safely infer only narrow fields:

- missing/zero rate with existing rate-check reason -> `missing_fields=["rate"]`
- `pickup_time == "NEEDS CHECK"` -> `needs_check_fields=["pickup_time"]`
- `delivery_time == "NEEDS CHECK"` -> `needs_check_fields=["delivery_time"]`

It should not infer broad missing data from every empty load attribute yet. Existing load-board records often omit fields, and treating every blank field as a decision signal could change reporting semantics.

## Fields Not Mapped Yet

Do not map these in the first read-only adapter:

- market baseline and zone snapshot context unless already represented on the load
- reload-watch context
- chain scoring context
- parser confidence or intake evidence
- DispatchCase state
- outbox/Telegram metadata
- broker memory internals beyond already attached reason text
- scoring thresholds into new block/review behavior
- future accounting/factoring flags

These belong in later explicit signal-bundle or runtime integration blocks.

## Required Non-changes

The adapter must keep these boundaries:

- no call to `MarketLoad.apply_search_request(...)`
- no mutation of the load
- no Telegram imports, formatting, or sending
- no DispatchCase imports or writes
- no repository/storage writes
- no market snapshot or load selection changes
- no DAT/API, Google Maps, Gmail/email, Google Sheets, PDF/OCR, scheduler, accounting, or factoring calls

## Recommended Next Implementation

Add `app/market_intelligence/decision_engine/marketload_adapter.py` with a single read-only helper:

```python
decision_result_from_market_load(load)
```

The helper should return a JSON-ready `DecisionResult`, preserve existing reason text, map only conservative risk flags, and remain report-only until a separate integration block is accepted.
