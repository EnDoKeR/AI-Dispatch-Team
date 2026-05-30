# Domain Contract Inventory

This inventory records current and planned domain contracts for AI Dispatch Team. It is documentation only. It does not add runtime behavior, schema migration, DispatchCase writes, PDF/OCR work, Google Sheets, DAT/API, Google Maps, Telegram behavior, or accounting/factoring actions.

Status values:

- `implemented`: concrete helper/model exists and is tested.
- `partial`: some fields/helpers exist, but the canonical contract is not complete.
- `planned`: contract is architectural target only.
- `unclear`: concept exists in behavior/docs, but ownership or shape needs audit.

## DispatchCase

Purpose:

- operational case for a load opportunity, alert, feedback path, and later document/accounting timeline.

Owner module:

- `app/market_intelligence/dispatch_case.py`
- helpers: `case_factory.py`, `case_matcher.py`, `case_update_applier.py`, `case_status_engine.py`, `case_id_resolver.py`

Current status:

- `implemented`

Current required fields:

- `case_id`
- driver/load/reference/broker identity fields as available
- current status and outcome fields
- decision/outbox/feedback-derived fields depending builder source

Must not do:

- auto-create cases from low-confidence RateCon intake;
- treat reporting-only market snapshots/search health as load-level cases;
- hide duplicate identity ambiguity;
- own Telegram formatting.

Suggested test coverage:

- build from decision, outbox, feedback;
- matching by identity fields;
- no case for reporting-only records;
- status preservation and final outcome protection;
- event generation compatibility.

## TimelineEvent

Purpose:

- auditable record of decisions, alerts, feedback, document actions, and future accounting/factoring milestones.

Owner module:

- current runtime source: `app/market_intelligence/case_event_builder.py`
- taxonomy/helper/reporting: `case_event_types.py`, `case_event_payload.py`, `case_event_report.py`, `case_event_normalizer.py`

Current status:

- `partial`

Required fields now:

- current builder envelope fields vary by event type;
- base payload helper supports `event_type`, `event_group`, `case_id`, `timestamp_utc`, `source`, `details`, `related_ids`.

Planned required fields:

- `event_id`
- `case_id`
- `event_type`
- `created_at`
- `actor_type`
- `actor_id`
- `payload`
- `evidence_refs`
- `source`
- `idempotency_key`
- `schema_version`

Must not do:

- replace `case_event_builder.py` without compatibility tests;
- write future DecisionResult events until an explicit wiring block;
- turn search/reporting events into load-level events accidentally.

Suggested test coverage:

- taxonomy coverage for every builder-emitted type;
- JSON serialization;
- report support for legacy and normalized wrapper records;
- future idempotency behavior.

## DecisionInput

Purpose:

- structured input bundle for decision logic.

Owner module:

- `app/market_intelligence/decision_engine/signals.py`

Current status:

- `partial`

Current fields:

- signal groups such as load, driver, broker, market, parser, notes, memory, approval context.

Must not do:

- import Telegram;
- read PDFs;
- write repositories or events;
- mutate source load objects.

Suggested test coverage:

- safe defaults;
- JSON serialization;
- source object/dict support;
- no forbidden imports;
- low-confidence parser signal propagation.

## DecisionResult

Purpose:

- canonical structured recommendation output.

Owner module:

- `app/market_intelligence/decision_engine/result.py`

Current status:

- `partial`

Current fields:

- `decision`
- `category`
- `risk_flags`
- `missing_fields`
- `needs_check_fields`
- `review_reasons`
- `block_reasons`
- `positive_signals`
- `explanation`
- `confidence`
- `source_signals`
- `approval_required`
- `recommended_next_action`
- `linked_load_id`
- `reference_id`

Planned additional fields:

- `recommendation`
- `rules_fired`
- `evidence_refs`
- `decision_version`

Must not do:

- format Telegram text;
- write events;
- call external services;
- accept missing or low-confidence critical data as ready.

Suggested test coverage:

- missing critical fields route to review/no-action policy;
- low confidence prevents accept;
- conflict flags route to review;
- serialization;
- backward compatibility with `MATCH`, `REVIEW_ONCE`, `BLOCK`.

## RiskFlag

Purpose:

- stable taxonomy of risk/review/block signals.

Owner module:

- `app/market_intelligence/decision_engine/risk_flags.py`

Current status:

- `implemented`

Required fields:

- name
- category
- usual action
- meaning

Must not do:

- submit factoring/accounting actions;
- decide by itself without DecisionEngine context;
- become a replacement for missing-field validation.

Suggested test coverage:

- known flag normalization;
- metadata lookup;
- category/action summaries;
- unknown flag safety.

## LoadCandidate

Purpose:

- normalized load opportunity before or during decision evaluation.

Owner module:

- current runtime equivalent: `app/market_intelligence/market_models.py` `MarketLoad`

Current status:

- `partial`

Current fields:

- pickup/delivery, rate, miles, dates/times, weight, equipment, commodity, broker identity, notes, reference id, match/review/block fields.

Must not do:

- become the only long-term domain contract for every source;
- hide source/evidence details from parser or live adapters;
- own Telegram formatting.

Suggested test coverage:

- construction defaults;
- decision field preservation;
- adapter normalization to DecisionResult;
- source-specific alias mapping.

## MarketSnapshot

Purpose:

- reporting/search context for current market and candidate load set.

Owner module:

- `market_snapshot.py`, `market_snapshot_builder.py`, `market_snapshot_stats.py`, `market_snapshot_opportunities.py`

Current status:

- `partial`

Required fields:

- search request context;
- load counts;
- opportunity/review summaries;
- market baseline/zone context where available.

Must not do:

- create load-level DispatchCases;
- become a hidden DecisionEngine;
- mix market summary events into load alert events.

Suggested test coverage:

- search/reporting-only behavior;
- Telegram summary metadata;
- no case creation for market snapshot/search health.

## DriverProfile

Purpose:

- driver equipment, lane preferences, hard constraints, and memory context.

Owner module:

- `driver_profile.py`
- `market_driver_profile_model.py`
- `driver_preference_*`
- `driver_lane_preference_*`

Current status:

- `implemented`

Required fields:

- driver name;
- equipment preferences/constraints;
- home/target/avoid lane context;
- preference memory summaries when available.

Must not do:

- silently override hard safety rules through weak memory;
- live inside Telegram formatting;
- use unprotected low-sample memory as final truth.

Suggested test coverage:

- profile loading defaults;
- preference grouping;
- hard/soft constraints;
- sample-size protection.

## BrokerProfile

Purpose:

- broker identity, payment/factoring context, relationship memory, and risk context.

Owner module:

- `broker_memory_core.py`, `broker_memory_queries.py`, `broker_memory_rules.py`, `market_broker_memory.py`

Current status:

- `partial`

Required fields:

- broker name;
- broker MC when available;
- feedback counts;
- case/outcome counts;
- memory status;
- risk/review reasons.

Must not do:

- require broker MC for every current RateCon core extraction;
- replace hard business rules;
- make financial/factoring commitments.

Suggested test coverage:

- MC normalization;
- memory status classification;
- under-sampled status;
- broker risk applied as review/context.

## RateConfirmationIntake

Purpose:

- normalized RateCon evidence from future document extraction.

Owner module:

- contract helper: `app/market_intelligence/intake/rate_confirmation_intake.py`
- validation helper: `app/market_intelligence/intake/rate_confirmation_validation.py`
- current adjacent modules: `app/market_intelligence/intake/record.py`, `ratecon_core_fields.py`, `ratecon_text_dry_run.py`, `ratecon_pdf_dry_run.py`

Current status:

- `partial`: JSON-ready contract and validation helpers exist, but they are not wired into PDF parsing, case creation, or event writes.

Required fields:

- `document_id`
- broker name and optional broker MC;
- broker contacts;
- carrier info if available;
- load number;
- typed references;
- rate;
- pickup/delivery stops;
- commodity;
- weight;
- equipment;
- dimensions if available;
- special requirements;
- accessorial terms;
- missing fields;
- needs-check fields;
- field confidences;
- evidence refs;
- parser/extractor version;
- source method;
- status.

Must not do:

- store raw private PDF text by default;
- create DispatchCases automatically;
- collapse all references into one untyped `reference_id` long term;
- accept low-confidence critical data as ready.

Suggested test coverage:

- minimal valid intake;
- missing critical fields;
- low-confidence critical fields;
- typed references;
- evidence refs without raw private text;
- serialization round-trip.

## DocumentRecord

Purpose:

- durable metadata record for an operational document.

Owner module:

- contract helper: `app/document_ai/document_record.py`
- document type helper: `app/document_ai/document_types.py`

Current status:

- `partial`: lightweight contract helper exists; no document storage or runtime linking is implemented.

Required fields:

- `document_id`
- `document_type`
- source;
- received timestamp;
- local file label or storage reference;
- privacy classification;
- page count;
- linked case id if later approved;
- warnings.

Must not do:

- commit private files;
- store raw private text in tracked files;
- trigger case creation by itself.

Suggested test coverage:

- document type normalization;
- JSON serialization;
- privacy fields;
- no raw text requirement.

## ExtractedFieldEvidence

Purpose:

- redacted/evidence reference supporting a field candidate.

Owner module:

- helper shape in `app/market_intelligence/intake/rate_confirmation_intake.py`;
- candidate-resolution bridge in `app/document_ai/ratecon_intake_draft.py`.

Current status:

- `partial`

Required fields:

- `evidence_id`
- `document_id`
- page/block/table reference;
- source method;
- redacted label/shape;
- confidence;
- warnings.

Must not do:

- store private raw snippets in tracked data;
- expose phone/email/address/reference values in reports;
- decide field truth alone.

Suggested test coverage:

- placeholder/redacted context;
- JSON serialization;
- evidence refs linked to candidates.

## FieldCandidate

Purpose:

- candidate value for one extracted field before resolver/validation.

Owner module:

- `app/document_ai/ratecon_candidates.py`
- candidate generators: `app/document_ai/ratecon_candidate_generators.py`

Current status:

- `implemented`

Required fields:

- field name;
- raw candidate value if local/private only;
- normalized value;
- confidence;
- source method;
- evidence ref;
- warnings.

Must not do:

- overwrite conflicting candidates silently;
- become final field truth without validation;
- leak private values into tracked fixtures.

Suggested test coverage:

- candidate conflict handling;
- confidence thresholds;
- evidence reference coverage;
- fake/anonymized fixtures only.

## FieldResolution

Purpose:

- selected, missing, low-confidence, or conflicting field state after candidate resolution.

Owner module:

- `app/document_ai/ratecon_field_resolution.py`

Current status:

- `implemented`

Required fields:

- field name;
- status;
- selected candidate;
- rejected candidates;
- confidence;
- reasons;
- evidence refs;
- warnings.

Must not do:

- create DispatchCases;
- emit dispatch recommendations;
- hide conflicts;
- populate low-confidence values as final truth.

Suggested test coverage:

- single resolved field;
- missing field;
- low-confidence field;
- conflict field;
- serialization;
- intake draft validation handoff.

## ExtractionArtifact

Purpose:

- metadata about extraction route and output summary.

Owner module:

- contract helper: `app/document_ai/extraction_artifacts.py`
- current adjacent: `pdf_text_extraction.py`;
- planned richer document AI package.

Current status:

- `partial`

Current fields:

- text returned to caller only;
- extractor name;
- page count;
- char count;
- extraction status;
- warnings;
- private text saved flag.

Planned fields:

- artifact id;
- document id;
- method;
- page range;
- text summary only by default;
- word/block/table counts;
- artifact version.

Must not do:

- save extracted private text by default;
- print raw private text;
- make parser decisions.

Suggested test coverage:

- empty text;
- unavailable dependency;
- JSON-serializable metadata;
- no OCR dependency in current helper.

## Stop

Purpose:

- pickup, delivery, or intermediate stop.

Owner module:

- planned domain contract;
- current fields are flat on `MarketLoad` and `IntakeRecord`.

Current status:

- `planned`

Required fields:

- stop type;
- sequence;
- location;
- date;
- time/window;
- appointment status;
- evidence refs.

Must not do:

- call Google Maps;
- infer route/miles without explicit mileage layer;
- hide multi-stop ambiguity.

Suggested test coverage:

- pickup/delivery minimal stops;
- missing date/location;
- appointment windows;
- multi-stop review flag.

## Reference

Purpose:

- typed identifiers for load, broker, shipment, PO, pickup, delivery, ratecon, or other external references.

Owner module:

- planned domain contract;
- current fields: `reference_id`, `load_number`, `load_id` in various modules.

Current status:

- `planned`

Required fields:

- reference type;
- value;
- source;
- confidence;
- evidence ref.

Must not do:

- collapse all identifiers into one generic field long term;
- use low-confidence references for case linking without review.

Suggested test coverage:

- multiple typed references;
- duplicate/conflicting references;
- serialization.

## MoneyAmount

Purpose:

- normalized monetary amount for rate, accessorials, charges, invoice, and future accounting fields.

Owner module:

- planned domain contract;
- current rate fields are numbers/strings in `MarketLoad` and intake helpers.

Current status:

- `planned`

Required fields:

- amount;
- currency;
- amount type;
- source method;
- confidence;
- evidence ref.

Must not do:

- confuse accessorial amounts with total carrier pay;
- create financial commitments;
- submit invoices/factoring packets.

Suggested test coverage:

- total rate vs accessorials;
- missing/ambiguous amounts;
- currency normalization.

## BrokerContact

Purpose:

- broker phone/email/contact evidence.

Owner module:

- current adjacent: `contact_parser.py`, `market_contact_extractor.py`, `notes_parser_contact.py`, `MarketLoad` contact fields.

Current status:

- `partial`

Required fields:

- name if available;
- phone;
- email;
- role;
- source;
- confidence.

Must not do:

- leak private contact data into tracked outputs;
- decide broker trust/factoring status alone;
- trigger outbound email.

Suggested test coverage:

- phone/email extraction;
- raw contact normalization;
- private-output redaction.

## FactoringPacket

Purpose:

- future readiness packet for factoring/accounting workflow.

Owner module:

- planned.

Current status:

- `planned`

Required fields:

- case id;
- broker profile;
- required documents;
- rate/invoice summary;
- missing document list;
- approval status;
- evidence refs.

Must not do:

- submit packets;
- email outside parties;
- create financial/legal commitments without explicit approval.

Suggested test coverage:

- readiness-only reports;
- missing document detection;
- approval gating.

## AccountingIssue

Purpose:

- future tracking for accounting/factoring exceptions.

Owner module:

- planned.

Current status:

- `planned`

Required fields:

- issue id;
- case id;
- issue type;
- status;
- opened/closed timestamps;
- related documents;
- evidence refs;
- notes.

Must not do:

- send money, submit invoices, or contact outside parties automatically;
- alter DispatchCase final outcomes without policy.

Suggested test coverage:

- open/close status;
- document links;
- no external side effects.

## Duplicate And Overlapping Concepts

Status concepts:

- `MarketLoad` uses match/review/block booleans and review/block reason lists.
- `DecisionResult` uses `decision`, `category`, `confidence`, risk flags, missing fields, and reasons.
- Intake uses generic `missing_fields`, `needs_check_fields`, and dry-run status.
- RateCon core policy uses `missing_core_fields`, optional missing fields, and deferred fields.
- PDF extraction uses `TEXT_EXTRACTED`, `EMPTY_TEXT`, `EXTRACTION_FAILED`, and `UNSUPPORTED`.
- Case status uses DispatchCase-specific lifecycle state.

Recommended direction:

- do not merge these blindly;
- document owner status for each layer;
- user-facing RateCon dry-run should emphasize RateCon core fields;
- DecisionEngine should own recommendation semantics;
- Event Timeline should record state transitions, not recalculate them.

Parser result shapes:

- `IntakeRecord` from `record.py`;
- parser output normalized through `parser_contract.py`;
- RateCon core summary from `ratecon_core_fields.py`;
- PDF dry-run summary from `ratecon_pdf_dry_run.py`;
- redacted diagnostics and layout diagnostics;
- private value-review CSV row shape.

Recommended direction:

- introduce `RateConfirmationIntake`, `FieldCandidate`, `ExtractedFieldEvidence`, and `ExtractionArtifact` before more parser hardening;
- keep private values local-only;
- do not patch one regex parser into a hidden domain model.

Decision result shapes:

- runtime `MarketLoad` decision fields;
- read-only MarketLoad adapter output;
- `DecisionResult` helper output;
- decision logger/run records.

Recommended direction:

- keep adapter/report-only comparison tools until runtime wiring is explicitly approved;
- harden `DecisionResult` before adding new decision writes.

Telegram formatting overlap:

- opportunity, review-once, chain, market summary, search health, broker block, and watch formatters are split;
- `telegram_broker_block.py` still formats broker/factoring/contact status text.

Recommended direction:

- Telegram should display structured results;
- Telegram should not calculate parser, decision, or factoring truth.

Broker memory overlap:

- `broker_memory_core.py`, `broker_memory_rules.py`, `market_broker_memory.py`, and Telegram broker text all touch broker risk/status context.

Recommended direction:

- broker profile/status should become a domain contract before future factoring/accounting work;
- Telegram broker text should remain display-only.

Driver preference overlap:

- driver profile model, driver preference rules, lane preference rules, and MarketLoad decision application all use driver context.

Recommended direction:

- keep hard constraints separate from memory preferences;
- preserve sample-size protection;
- expose reasons in DecisionResult rather than only formatted messages.
