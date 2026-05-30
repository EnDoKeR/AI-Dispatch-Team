# Testing Roadmap

This roadmap defines the test coverage needed before the project grows from
foundation helpers into a Dispatch Operating Intelligence System.

## Current Test Categories Found

Current tests already cover:

- load filtering, selection, duplicate handling, and simulated load flows;
- market rules, quality/risk rules, and DecisionEngine comparison helpers;
- DecisionResult contracts and report-only timeline previews;
- DispatchCase factory/matcher/update helpers and event-builder compatibility;
- event taxonomy, payload, normalizer, report, timeline contract, and dry-run CLIs;
- intake records, parser contracts, parser confidence, intake repository/report,
  RateCon dry-runs, PDF dry-run safety, redacted diagnostics, and CSV export;
- IntakeCaseLinkCandidate helper/report;
- Telegram formatting, duplicate keys, summary metadata, notifier metadata, sender
  behavior, outbox logging, and search/watch formatting;
- document AI scaffolding contracts, PDF triage, safe extraction artifacts,
  candidate extraction, broker template matching/scoring, conservative resolver,
  and intake draft handoff;
- architecture boundary tests for adapter/core/parser separation.

## Missing Tests Before Future Development

Before major feature growth, add coverage for:

- RateCon parser regression corpus using fake/anonymized broker examples only;
- expanded PDF triage with more mixed, encrypted, and broken PDF edge cases;
- safe extraction artifact propagation into later evidence records;
- OCR fallback routing without invoking OCR in unit tests;
- additional template-specific resolver hardening as safe private measurement
  reveals new fake/anonymized cases;
- additional broker template unknown/conflict fallback regression cases;
- confidence/evidence propagation from extraction artifact to intake contract;
- ReviewRequired gating for missing, low-confidence, and conflicting critical data;
- DispatchCase creation from validated intake, with approval and idempotency gates;
- Event Timeline append/read/idempotency over persisted case history;
- broker memory scoring, sample-size protection, and reason reporting;
- driver compatibility hard constraints vs soft preferences;
- Telegram formatting safety for DecisionResult and review-required outputs;
- duplicate alerts and notification idempotency;
- missed-load and replay/backtesting reports;
- SQLite persistence, migrations, and data compatibility;
- future DAT/API adapter contract tests with fake responses only.

## Business Rule Test Rule

Every new business rule needs:

- positive test;
- negative test;
- missing-data test;
- low-confidence test;
- regression test if the rule fixes a bug.

Business rules must be tested in the domain or decision layer, not only through
Telegram formatting or script output.

## Parser Test Rule

Every new broker/template needs:

- fake or anonymized fixture text;
- expected structured output;
- expected missing fields;
- expected needs-check fields;
- confidence and evidence expectations;
- coverage for ambiguous or conflicting candidates;
- proof that no raw private text is committed.

Private RateCon PDFs and extracted private text must never be committed as
fixtures.

## Event Timeline Test Rule

Every new event writer needs:

- event type taxonomy test;
- payload contract test;
- idempotency test;
- JSON serialization test;
- ordering/report test;
- no private raw text in event payloads;
- proof that runtime behavior changed only in the approved wiring block.

## Document AI Test Rule

Document AI tests should use fake PDFs, mocked extraction helpers, or synthetic
artifact records. OCR/Vision tests must be routed through explicit adapter
contracts and should not make network or paid API calls in unit tests.

Required future coverage:

- triage route selection;
- fake-only triage CLI summaries;
- extraction artifact metadata;
- no raw text by default;
- safe redacted evidence;
- manual review route when extraction is empty or unsupported.

## RateCon Candidate Extraction Test Rule

Candidate extraction tests must use fake/anonymized text artifacts only.

Required coverage for candidate generators and resolvers:

- money/rate candidates, including accessorial amounts that must not become final rate;
- broker identity and broker MC candidates;
- typed reference candidates;
- pickup/delivery location, date, and time candidates;
- equipment, commodity, weight, special requirement, and accessorial-term candidates;
- multiple candidates for one field;
- low-confidence candidate behavior;
- conflict behavior;
- intake draft handoff without DispatchCase creation;
- fake-only CLI summaries with no raw fixture text.
- hard-layout regression coverage for repeated headers, rate/accessorial traps,
  table-like stops, broker identity confusion, typed references, appointment
  conflicts, and buried requirements.

## Broker Template Test Rule

Every broker template needs:

- fake/anonymized template JSON;
- fake/anonymized text fixture;
- matched-template test;
- unknown fallback test;
- conflict fallback test when labels overlap another template;
- rate/accessorial safety test when money labels are present;
- typed-reference coverage when reference labels are present;
- proof that templates do not contain broker memory or business-risk fields.
- proof that weak, conflicting, or unknown template matches cannot overboost
  candidates or bypass validation.

## Persistence Test Rule

Persistence and SQLite changes require:

- schema/migration tests;
- insert/read/update tests;
- idempotency/duplicate tests;
- replay/read-only report tests;
- compatibility tests for existing records;
- no business decision invention inside repositories.

## Adapter Test Rule

Adapters should be tested for formatting, transport boundaries, retries, and
safe failure modes. They must not own dispatch decisions.

Future DAT/API tests must use fake payloads and must prove:

- core logic does not require a live DAT/API adapter;
- credentials are not required for unit tests;
- adapter output is normalized before decision logic sees it.
