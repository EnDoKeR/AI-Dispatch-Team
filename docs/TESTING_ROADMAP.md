# Testing Roadmap

This roadmap defines the test coverage needed before the project grows from
foundation helpers into a Dispatch Operating Intelligence System.

## Official Test Command

Run the canonical test suite from the project root with:

```powershell
py scripts/run_tests.py
```

Fallback:

```powershell
py -m unittest discover -s tests -p "test_*.py"
```

Do not use bare `py -m unittest discover`. It can discover zero tests from the
repo root. `scripts/run_tests.py` pins discovery to `tests` and fails if the
discovered test count is zero.

## Stop Pipeline Wiring Tests

The stop wiring audit adds invariant tests that must fail if mergeable stop
groups remain passthrough:

- `tests/test_stop_pipeline_trace.py`
- `tests/test_stop_pipeline_wiring_fixtures.py`
- `tests/test_stop_pipeline_wiring.py`
- `tests/test_stop_cluster_date_time.py`
- `tests/test_stop_cluster_noise_filter.py`
- `tests/test_stop_cluster_dedupe.py`

Required invariant behavior:

- mergeable single-line fixtures reduce after `post_single_line_cluster`;
- distinct non-mergeable stops remain distinct;
- signature/footer noise is removed;
- stage trace records the first changed stage;
- private reruns must report `NOT FIXED` if stage counts remain unchanged.

The current private rerun is still `NOT FIXED`, even though synthetic wiring
tests pass. That means the next tests should target provider-style line
clustering from actual `pdfplumber` line/bbox metadata using fake provider
artifacts.

## Stop Span Extractor Tests

The provider-line stop span extractor is covered by focused suites for:

- stop span contracts;
- synthetic provider-line fixtures;
- line feature extraction;
- anchor detection;
- span boundary detection;
- field extraction inside spans;
- normalized stop conversion from spans;
- safe measurement CLI flags and output fields;
- Google Sheets/CSV review export columns.

Regression criteria:

- synthetic provider-line fixtures must produce fewer spans than raw lines when
  mergeable stop sections exist;
- old stop-group counts and new span counts must be reported side by side;
- span passthrough must be explicitly reported if detected;
- tests must not use private PDFs, screenshots, raw private text, or real broker
  values.

## Local Review Export Tests

The local Google Sheets-compatible export is covered by:

- `tests/test_private_measurement_review_export.py`
- `tests/test_ratecon_review_workbook_contracts.py`
- `tests/test_ratecon_review_workbook_export.py`
- `tests/test_extraction_readiness.py`
- `tests/test_measurement_integrity.py`
- `tests/test_review_feedback_import.py`
- `tests/test_run_private_ratecon_measurement.py`

These tests verify CSV generation, optional workbook generation when a writer is
available, natural sorting, local-only output paths, readiness levels, integrity
issue detection, feedback import summaries, explicit local-only private value
guards, and no console printing of local document stems or predicted values.

## Local Review Analysis And Hardening Tests

The local-first hardening loop is covered by:

- `tests/test_local_review_analysis.py`
- `tests/test_analyze_local_ratecon_review_outputs.py`
- `tests/test_ratecon_core_field_policy.py`
- `tests/test_extraction_readiness.py`
- `tests/test_core_field_gap_analysis.py`
- `tests/test_analyze_core_field_gaps.py`
- `tests/test_core_field_hardening_stop_span_field_mapping_fixtures.py`
- `tests/test_stop_span_field_mapping.py`
- `tests/test_candidate_coverage_analysis.py`
- `tests/test_analyze_candidate_coverage.py`
- `tests/test_ratecon_identity_reference_candidates.py`
- `tests/test_local_review_hardening_stop_datetime_fixtures.py`
- `tests/test_local_review_hardening_stop_datetime.py`

Required behavior:

- local review CSV loaders drop private value columns before analysis;
- analysis reports only aliases, counts, statuses, field names, and issue
  categories;
- generated analysis reports stay under ignored local output paths;
- selected hardening fixtures use fake values only;
- stop span date/time hardening covers deterministic formats without attaching
  header, terms, billing, or footer dates to stops.
- core-field gap analysis reports only aliases, counts, statuses, field names,
  and root-cause buckets;
- readiness calibration keeps optional/review-only fields visible without
  making them automatic intake-core blockers;
- supplemental, non-RateCon, unknown-review, OCR-needed, and TONU/payment-only
  rows cannot become dispatch-decision-ready by accident;
- core-field analysis leads with true intake blockers while keeping optional
  missing fields in separate review/dispatch counts;
- stop-span field mapping may fill missing top-level review statuses but must
  preserve existing conflicts.
- candidate coverage reports only aliases, counts, statuses, field names,
  stages, and gap reasons;
- `--write-candidate-coverage` writes ignored local JSON/Markdown artifacts
  without printing values;
- broker identity candidate fixtures use fake names and prove broker-context
  candidates are generated without selecting carrier names as brokers.

If a private rerun does not improve the selected blocker aggregate, document
that result and pick the next blocker from the local analysis rather than
stacking unrelated heuristics.

## Google Sheets Review Sync Tests

The Google Sheets review sync is covered by fake/mocked tests only:

- `tests/test_google_sheets_review_config.py`
- `tests/test_google_sheets_review_client.py`
- `tests/test_google_sheets_review_rows.py`
- `tests/test_sync_ratecon_review_to_google_sheet.py`
- `tests/test_download_ratecon_review_feedback_from_google_sheet.py`

Required behavior:

- local config loads from ignored config or environment variables;
- service account JSON paths are never printed or committed;
- sync refuses to run without `--confirm-google-review-sync`;
- status-only mode redacts predicted values;
- private-values test mode requires an explicit flag;
- only dedicated `RC_` review tabs are updated;
- feedback download refuses to run without confirmation;
- feedback download summaries print counts and issue types only;
- all Google client tests use mocks and make no real API calls.

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
- private measurement harness tests for safe aliases, redacted rows, aggregate
  counts, blocker classification, output writers, confirmation-gated CLI runs,
  and no raw text/private values in outputs.
- private broker template overlay tests for ignored local paths, explicit CLI
  confirmation, safe template aliases, private display-name redaction, redacted
  pattern collection, family grouping, draft skeleton generation, and baseline
  vs overlay status-only comparison.
- document/page/section classification tests for RateCon, tender, BOL,
  terms-only, billing, carrier-info, signature, certificate, TONU, and unknown
  documents.
- classification calibration tests proving carrier load tenders, load tenders,
  order confirmations, load confirmations, and TONU payment confirmations are
  extraction-relevant while BOL, certificate, billing-only, terms-only,
  carrier-agreement-only, and driver/carrier-info-only documents remain
  supplemental or non-RateCon.
- extraction scope tests proving supplemental pages do not feed core RateCon
  candidates and do not inflate missing critical field counts.
- measurement report tests proving normal load movement, TONU, supplemental,
  unknown-review, and OCR-needed denominators stay separate.
- layout artifact contract tests for bounding boxes, words, lines, blocks,
  tables, cells, reading-order variants, and evidence refs.
- synthetic layout fixture tests proving no private PDFs, screenshots, private
  values, real broker names, or real MC numbers are committed.
- layout index and label-value proximity tests for reading order, same-row,
  below-label, section-following, and table-row evidence.
- layout-aware candidate tests for rate/payment, stop association, operational
  details, supplemental terms/billing filtering, TONU payment separation, and
  resolver readiness.
- fake-only layout CLI tests proving candidate counts are printed without raw
  fixture text or private values.
- `pdfplumber` layout provider tests for fake digital PDFs, empty-text PDFs,
  invalid PDFs, safe provider statuses, no raw text printing, and normalized
  `LayoutExtractionArtifact` output.
- layout provider pipeline tests proving provider failures do not crash,
  non-RateCon classifications skip core candidates, and safe measurement layout
  fields remain aliases/counts/statuses only.
- layout fusion tests for safe field delta audits, candidate source priority,
  stop contracts, table/section stop grouping, stop fusion, rate guardrails, and
  operational detail fusion.
- layout provider diagnostics tests for quality buckets, safe stop-signal
  counts, table-profile comparison, likely issue buckets, and local-only report
  writing.
- no-regression fusion tests proving protected critical fields cannot be
  downgraded by weaker layout evidence unless an explicit debug path is used.
- normalized stop tests for stop-set contracts, raw group diagnostics,
  dedupe/noise filtering, sequencing/type resolution, field association,
  stop-set building, safe measurement reporting, and local-only review packets.
- stop calibration tests for local-only pattern classification, table-cell
  over-grouping, table-row-not-merged cases, date/time split from location,
  generic pickup/delivery overclassification, and safe review diagnostics.
- stop provenance tests for source metadata, local-only provenance reports,
  synthetic provenance fixtures, structural dedupe, post-merge date/time
  attachment, and normalized pipeline stage counts.
- next stop grouping tests should assert that provider-style row, cell, section,
  and line fragments merge into plausible logical stops before local value
  correctness review begins.
- because the current private rerun still shows identical raw/premerge/
  post-row/post-section/post-noise/post-dedupe/normalized counts, the next test
  block should prove provider-style single-line fragments cluster into fewer
  logical stops without collapsing true multi-stop loads.
- resolver readiness tests for choosing among provider-derived stop groups,
  preserving unresolved/review status when layout evidence is ambiguous, and
  avoiding private values in evaluation output.

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
- proof that private local templates are never required by tests and that any
  real template onboarding is represented by fake/anonymized committed fixtures.

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
