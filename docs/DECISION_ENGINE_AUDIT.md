# DecisionEngine Architecture Audit

This audit prepares a future DecisionEngine boundary. It does not implement a new engine, move files, or change runtime behavior.

## Mini-block 1: Decision Logic Inventory

### Current Decision Shape

Current load-level decisions are represented primarily through:

- `driver_match_status`: `MATCH`, `REVIEW_ONCE`, `BLOCK`, or `UNKNOWN`
- `driver_fit_status`: `CLEAN_MATCH`, `REVIEW_ONCE`, `BLOCKED`, or `UNKNOWN`
- `match_reasons`
- `review_reasons`
- `block_reasons`
- `driver_match_notes`
- scoring helpers such as `opportunity_score()`, `priority()`, `suggested_action()`, and `opportunity_reason()`

The main orchestration point is currently `MarketLoad.apply_search_request(...)` in `app/market_intelligence/market_models.py`.

### Modules That Decide MATCH / REVIEW / BLOCK

These modules currently mutate the load or contribute directly to the final decision state:

- `market_models.py`
  - orchestrates rule application through `MarketLoad.apply_search_request(...)`
  - resets decision state, calls focused rule helpers, calls broker memory, then finalizes status
- `market_match_status.py`
  - converts `is_blocked` / `is_review_once` flags into final `driver_match_status`
  - final priority order is block first, review second, match last
- `market_local_load_rules.py`
  - blocks local/same-city style loads
- `market_weight_rules.py`
  - reviews or blocks overweight loads depending on driver/equipment context
- `market_od_permit_rules.py`
  - blocks Conestoga OD/permit/wide loads and reviews non-Conestoga OD/permit/wide loads
- `market_quality_rules.py`
  - marks rate missing as `REVIEW_ONCE`
  - marks high empty miles as `REVIEW_ONCE`
  - records low RPM as a quality signal
- `market_document_requirements.py`
  - reviews or blocks required documents depending on driver profile fields
- `market_document_triggers.py`
  - detects hazmat, tanker, TWIC, legal status, ramps, and dunnage requirements and delegates to document rules
- `market_tarp_requirements.py`
  - blocks/reviews tarp requirements for flatbed-style equipment and treats Conestoga as covering tarp-required freight
- `market_tracking_requirements.py`
  - handles tracking-required decisions from driver profile context
- `market_direction_matcher.py`
  - applies target direction/city/route decision context
- `market_conestoga_rules.py`
  - blocks explicit no-Conestoga language
  - reviews flatbed/step-deck compatibility for Conestoga
- `market_broker_memory.py`
  - can move a load to review based on broker memory
  - can add positive broker match reasons
- `market_payment_risk_rules.py`
  - adds payment/factoring/no-buy style risk context
- `market_scoring.py`
  - computes qualification, good-load status, score, priority, suggested action, and opportunity reason

Important observation: the decision is not one explicit result object today. It is built by mutating `MarketLoad` fields across several helpers and then serialized later.

### Modules That Only Extract Facts Or Context

These modules should generally be reusable as future DecisionEngine input suppliers:

- `notes_parser.py` and `notes_parser_*`
  - extract notes facts such as tarp, dimensions, OD, weight, equipment terms, document terms, pickup clues, contact override, and payment language
  - should remain evidence extraction, not final dispatch decision
- `market_contact_extractor.py`
  - extracts email/phone from broker contact fields and notes
- `market_basic_metrics.py`
  - calculates numeric basics such as RPM, bucket, lane key, broker key
- `market_target_helpers.py`
  - determines target states, route fallback relationships, off-target exceptions, and target city/state checks
- `market_baseline.py`
  - computes current snapshot market statistics by equipment and mileage bucket
- `market_zone_snapshot.py`
  - computes city/state exit-market context from current snapshot
- `market_exit_classifier.py`
  - produces exit context labels and reload-watch recommendations, but does not mutate the load
- `chain_scoring.py`
  - scores a two-load chain without mutating loads
- `intake/record.py`
  - normalizes intake records and missing/needs-check fields
- `intake/parser_contract.py`
  - normalizes parser output into intake records
- `intake/pasted_text_parser_adapter.py`
  - extracts conservative parser-output evidence from pasted text only
- `driver_profile.py`, `driver_profile_loader.py`, and `search_request.py`
  - supply driver/search input context

### Modules That Format Decisions For Telegram

These modules should stay adapter/interface code:

- `telegram_opportunity_formatter.py`
  - formats clean opportunity messages and currently calls load scoring methods for text
  - includes some presentation-specific risk wording such as reload-risk text
- `telegram_review_once_formatter.py`
  - formats review-once messages and deduplicates review reasons for readability
- `telegram_search_health_formatter.py`
  - formats search health messages
  - currently derives adjustment suggestions from blocker reason text
- `telegram_market_summary_formatter.py`
  - formats market summary context
- `telegram_chain_formatter.py`
  - formats reload-chain messages
- `telegram_watch_formatter.py`
  - formats reload-watch preview-only messages
- `telegram_broker_block.py`
  - formats broker/factoring/contact/status text
  - also reads broker memory for display context, so it is an adapter-coupling area to audit before future package migration

Formatter risk: some formatters still contain light interpretation or reason counting. A future DecisionEngine result should give formatters structured reasons so they do less inference from text.

### Modules That Log Decisions

Decision logging currently records the result after `MarketLoad` has already been mutated:

- `decision_logger.py`
  - writes decision history and run summaries to JSONL
- `decision_serializer.py`
  - serializes load facts, decision, category, score, priority, suggested action, reasons, and market recommendation context
- `decision_logger_helpers.py`
  - builds load IDs, gets decision/category from `driver_match_status`, and dedupes reason lists
- `decision_run_builder.py`
  - counts `MATCH`, `REVIEW_ONCE`, and `BLOCK`

These are logging/serialization helpers, not the source of business rules.

### Modules That Handle DispatchCase State

DispatchCase state is separate from load decision calculation:

- `dispatch_case.py`
  - orchestrates case/event creation from decisions, feedback, eligible Telegram outbox records, and simulation events
- `case_factory.py`
  - builds case records from decision, feedback, or outbox records
- `case_event_builder.py`
  - builds structured case event payloads
- `case_matcher.py`
  - matches feedback/outbox/simulation events to cases
- `case_update_applier.py`
  - applies outbox/feedback updates to a case
- `case_status_engine.py`
  - updates case status from dispatcher feedback

DispatchCase should remain timeline/state behavior. It should not become the future DecisionEngine.

### Where Risk Flags Exist Today

Risk is currently represented as reason text, booleans, and status labels rather than a stable taxonomy:

- `block_reasons`, `review_reasons`, `match_reasons`, `driver_match_notes`
- `is_blocked`, `is_review_once`, `is_clean_match`
- `is_overweight`, `is_low_rpm`, `is_too_far_empty`, `is_local_load`, `is_od`
- broker memory statuses such as `BAD_BROKER_REVIEW`, `RATE_NEGOTIATION_REQUIRED`, `WATCHLIST`, `GOOD`
- broker memory risk levels: `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`
- driver/lane memory sample qualities and `can_affect_decision`
- market status labels such as `LOW_DATA`, `SOFT_MARKET`, `NORMAL_MARKET`, `STRONG_MARKET`
- exit context labels such as `LOW_EXIT_CONFIDENCE`, `WEAK_EXIT_MARKET`, `RISKY_EXIT_MARKET`, `CLEAN_EXIT_AVAILABLE`, `RATE_CHECK_EXITS_AVAILABLE`
- reload-watch/chain labels such as `STRONG_PAY_RELOAD_WATCH_RECOMMENDED`, `HIGH_PAY_EXIT_PLAN_NEEDED`, `STRONG_CHAIN`, `WORKABLE_CHAIN`, `WEAK_CHAIN`, `RATE_CHECK_CHAIN`

Future work should convert common reason-text patterns into stable risk flags without removing the current human-readable reasons.

### Where Missing / Needs-check Data Exists Today

Missing and needs-check concepts currently exist in several forms:

- intake records:
  - `missing_fields`
  - `needs_check_fields`
  - `field_confidence`
- parser contract and pasted-text adapter:
  - missing fields and low-confidence extraction evidence
- Telegram metadata helpers:
  - empty load-specific fields for non-load messages
- market/load decisions:
  - review reasons such as missing rate, needs time check, needs driver document, or needs broker verification
- formatter text:
  - phrases such as `NEEDS CHECK`, `RATE CHECK`, and `TIME CHECK`

Future DecisionEngine output should preserve both structured missing/needs-check lists and human-readable explanations.

### Where Telegram Coupling Exists

Known coupling areas:

- `telegram_notifier.py` calls selection, formatters, metadata helpers, sender, and sent-state modules
- Telegram formatters call load scoring methods and inspect decision notes
- `telegram_search_health_formatter.py` derives adjustment suggestions from blocker reason strings
- `telegram_broker_block.py` formats broker status and also calls broker memory display logic
- `telegram_outbox_logger.py` still preserves text parsing fallback for compatibility

Accepted current state:

- Telegram is an adapter, but it still depends on current load decision fields.
- Existing behavior should not be changed until a DecisionEngine result contract and compatibility plan exist.

### Logic Safe To Reuse

Safe reusable pieces for a future DecisionEngine include:

- focused market rule helpers that already have tests
- notes parser fact extraction helpers
- intake record missing/needs-check logic
- broker memory classification helpers
- driver and lane preference classification helpers
- market baseline and zone snapshot helpers
- exit classifier and two-load chain scoring helpers
- decision serializer field mapping, after a result object exists

Safe reuse does not mean immediate file moves. Current import paths should remain stable until a migration block is accepted.

### Logic That Should Eventually Move Behind A DecisionEngine Interface

Candidates for a future DecisionEngine boundary:

- `MarketLoad.apply_search_request(...)` orchestration
- final `MATCH` / `REVIEW_ONCE` / `BLOCK` status assembly
- conversion from rule booleans/reason text to stable risk flags
- scoring/category/priority/suggested-action output
- market context and exit risk attachment
- broker/driver/lane memory influence policy
- parser/intake missing/needs-check signal attachment
- approval-required and recommended-next-action policy

The future interface should return a structured result while preserving the existing behavior until tests prove a safe migration path.

### Current Audit Recommendation

Do not create a new broad DecisionEngine module yet.

Next design step should define the future output contract, input signal map, and risk flag taxonomy before implementation.
