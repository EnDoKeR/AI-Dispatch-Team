# Safe Private RateCon Measurement

This document defines the local-only measurement harness for private RateCon
PDFs. It is a measurement block, not a feature expansion block.

## Why Private Measurement Is Needed

The deterministic RateCon pipeline is now stronger on fake/anonymized fixtures:

- PDF triage;
- safe extraction artifacts;
- safe text artifacts;
- generic candidates;
- broker template matching;
- template-aware scoring;
- conservative resolver;
- RateConfirmationIntake draft;
- validation.

Private measurement is needed to answer whether this pipeline improves field
status on real local test documents without exposing private text or values.

## What This Block Measures

The harness measures document and extraction quality only through safe summary
fields.

PDF quality:

- `page_count`
- `char_count`
- `has_text_layer`
- `likely_image_based`
- `recommended_route`

Candidate quality:

- candidate counts by field;
- candidate coverage for critical fields.

Layout provider quality when explicitly enabled:

- layout provider status counts;
- layout attempted/success/failure/skipped counts;
- layout candidate counts by field;
- layout evidence type counts;
- layout quality bucket counts;
- table and table-cell counts;
- stop label signal counts;
- likely issue bucket counts;
- prevented regression counts;
- candidate-count deltas versus text-only baseline;
- improved/worsened/unchanged field-name buckets only.

Classification quality:

- document type;
- RateCon eligibility;
- supplemental-only status;
- page role counts;
- section role counts;
- classification warnings;
- extraction-scope skips.

Template quality:

- template status: `matched`, `unknown`, `conflict`, or `low_confidence`;
- selected template ID only when safe and non-private.

Resolver quality:

- field status: `resolved`, `missing`, `needs_review`, `low_confidence`,
  or `conflict`;
- missing critical fields;
- unresolved fields where candidates exist but cannot be selected safely;
- low-confidence fields;
- conflict fields;
- needs-check fields.

Validation quality:

- intake status;
- review-required status;
- review-required reasons through field names and warning codes only.

Blocker category:

- `OCR_NEEDED`
- `DIGITAL_TEXT_EXTRACTION_GAP`
- `LAYOUT_EXTRACTION_GAP`
- `TEMPLATE_GAP`
- `RESOLVER_GAP`
- `VALIDATION_GAP`
- `MANUAL_REVIEW_REQUIRED`
- `UNSUPPORTED_OR_BROKEN_PDF`
- `NON_RATECON_DOCUMENT`
- `SUPPLEMENTAL_DOCUMENT_ONLY`
- `UNKNOWN_DOCUMENT_TYPE_REVIEW`

## Classification-First Measurement

Safe measurement now classifies text before RateCon extraction:

```text
PDF triage
-> in-memory text artifact
-> DocumentType / PageRole / SectionRole
-> ExtractionScope
-> RateCon candidate extraction only when eligible
-> resolver / validation
-> safe status summary
```

Recognized supplemental documents such as BOL-like pages, carrier/driver
information sheets, signature certificates, billing pages, and terms-only pages
do not inflate missing RateCon field counts. Their RateCon core fields are
reported as `non_applicable_fields` and `skipped_fields`, not failed extraction.

Critical-field missing rates are measured against honest denominators, not the
total document count. Normal pickup/delivery/equipment/weight field rates use
`normal_load_movement_count`. TONU documents are counted separately as
payment/status extraction relevant, and OCR-needed or supplemental-only
documents stay visible without being treated as failed RateCon parses.

## What This Block Does Not Do

This block does not add:

- OCR;
- Vision AI;
- cloud APIs;
- PyMuPDF;
- Tesseract;
- PaddleOCR;
- live DAT/API integration;
- real broker templates;
- DispatchCase creation;
- DecisionEngine calls;
- Telegram calls;
- Event Timeline writes;
- production extraction claims.

## Official Pipeline Being Measured

```text
PDF triage
-> safe extraction artifact / in-memory text artifact if available
-> generic candidates
-> broker template matching
-> template-aware scoring
-> conservative resolver
-> RateConfirmationIntake draft
-> validation/status summary
```

Older direct parser paths are not the official pipeline and must not be revived:

- `scripts/import_ratecon.py`
- `scripts/read_ratecon.py`
- old regex-to-field flows that bypass candidates, resolver, and validation.

## Safe Outputs

Safe shareable outputs:

- document alias such as `RATECON_001`;
- page count;
- character count;
- triage route;
- extraction status;
- document type;
- extraction-relevant status;
- normal load movement status;
- TONU count;
- classification status counts;
- page role, section role, and extraction scope counts;
- template match status;
- candidate counts by field;
- field resolution status by field;
- confidence buckets, not values;
- missing field names;
- needs-check field names;
- conflict field names;
- warning codes;
- blocker categories;
- recommended next engineering path.

## Unsafe Outputs

Unsafe by default:

- private filenames;
- broker/customer/contact names;
- MC numbers;
- load numbers;
- rate amounts;
- pickup or delivery addresses;
- dates and times;
- reference numbers;
- raw extracted text;
- extracted snippets;
- full evidence text;
- local private paths;
- full file hashes.

## Local-Only Output Policy

Generated private measurement output must go to an ignored local-only directory.

Preferred path:

```text
.local_outputs/private_ratecon_measurement/
```

Outputs may include safe JSON, safe CSV, safe Markdown summaries, and a
local-only human value-review template. Generated files must not be committed.

The local review analysis loop reads the ignored review CSVs and writes:

- `local_review_analysis.md`
- `local_review_analysis.json`
- `core_field_gap_analysis.md`
- `core_field_gap_analysis.json`
- `candidate_coverage.md`
- `candidate_coverage.json`
- `candidate_coverage_analysis.md`
- `candidate_coverage_analysis.json`
- `load_identifier_coverage.md`
- `load_identifier_coverage.json`
- `load_identifier_coverage_audit.md`
- `load_identifier_coverage_audit.json`

Those reports contain aliases, counts, statuses, field names, and issue
categories only. They are used to choose one targeted deterministic hardening
focus per block.

Candidate coverage artifacts are written with:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-json --write-csv --write-md --write-review-workbook --write-review-csvs --write-candidate-coverage --natural-sort-inputs
```

Then analyze the local-only coverage report:

```powershell
py scripts/analyze_candidate_coverage.py --write-md --write-json
```

The coverage reports trace required intake fields through line features,
anchors, spans, span field candidates, normalized fields, core field mapping,
and review rows. They contain counts/statuses only.

Load identifier coverage can be emitted with the same measurement command by
adding `--write-load-identifier-audit`, then analyzed with:

```powershell
py scripts/analyze_load_identifier_coverage.py --write-md --write-json
```

This report traces load-identifier source lines, label classification, typed
candidates, primary candidate classification, rejected non-primary references,
core load-number mappings, and review-row status. It contains counts,
categories, and aliases only.

Current safe local review metrics after policy-aware blocker cleanup:

- documents analyzed: 18;
- readiness counts: `extraction_review_ready=14`, `not_ready=4`;
- OCR-needed count: 4;
- span-normalized stops: 29;
- span date resolved / missing: 8 / 21;
- span time resolved / missing: 10 / 19.

Policy cleanup reports `optional_field_misclassified_as_core=0`. Optional
missing fields remain visible for review and dispatch decisioning, but they are
not counted as intake-core blockers. The next block should use true intake
blocker counts, not the all-gap list, to select work.

Core-field forensics now breaks broad `missing_core_field` and
`conflict_core_field` blockers down by concrete fields, policy level, and safe
root-cause buckets. Reports separate extraction-review blockers, true
intake-core blockers, dispatch-decision blockers, optional missing fields, and
non-applicable fields. The current clean selection gate points to stop-span
evidence/candidate generation and coverage before more datetime or mapping
heuristics.

After candidate coverage instrumentation, the first selected fix was broker
identity candidate generation. Safe local delta:

- broker-name candidate-not-generated count: 10 -> 7;
- total candidate-not-generated count: 27 -> 22;
- field review rows: 154;
- readiness unchanged: `extraction_review_ready=14`, `not_ready=4`;
- OCR-needed unchanged: 4.

Remaining true blockers should be selected from the policy-cleaned coverage
counts. Do not repeat generic datetime or mapping heuristics unless the
coverage stage data proves that exact failure point.

The next selector pass selected `stop_span_date_candidate_generation` because
eight date records were missing specifically at `span_field_candidate`. After
the focused table-row date fix:

- selected date candidate-not-generated count: 8 -> 0;
- total candidate-not-generated count: 22 -> 14;
- span date resolved / missing: 8 / 21 -> 10 / 19;
- span time resolved / missing: 10 / 19 unchanged;
- readiness unchanged: `extraction_review_ready=14`, `not_ready=4`;
- OCR-needed unchanged: 4;
- next selected target: `load_identifier_candidate_generation`.

The load identifier pass added typed identifier contracts, deterministic label
helpers, typed candidate generation, primary-ID resolver mapping, candidate
coverage counters, and review workbook columns. Safe local delta after rerun:

- primary identifier candidates observed: 3;
- typed references observed: 11;
- rejected non-primary references: 11;
- load-number candidate gap: 7 -> 8 under the more specific taxonomy;
- load-number intake blockers: 7 -> 9;
- total candidate gap count stayed 14;
- readiness unchanged: `extraction_review_ready=14`, `not_ready=4`;
- OCR-needed unchanged: 4.

The result is diagnostic improvement, not extraction improvement on the private
corpus. The next load-identifier block should audit missing identifier labels
and load-identity section coverage before adding broader regexes.

The follow-up load identifier audit added local-only audit artifacts and a
constrained generic header-reference review-candidate fix. Safe private counts
did not change: primary identifier candidates stayed 3, typed references stayed
11, rejected non-primary references stayed 11, core load-number mappings stayed
1, and OCR-needed stayed 4. The next measured work should inspect label and
section coverage, not relax PO/BOL/pickup/delivery reference safety.

## Command

Run locally only:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --write-json --write-csv --write-md
```

Optional local review template:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --write-json --write-csv --write-md --write-value-review-template
```

The CLI refuses to run unless `--confirm-private-local-run` is supplied.
Replace `C:\Users\YOUR_NAME\Documents\RateCons` with a real local folder that
contains RateCon PDFs. Do not paste your real local folder path back into chat.
If the folder does not exist, or if the input still looks like an example
placeholder, the CLI exits safely with a friendly error instead of a traceback.

Optional private template overlay measurement:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --private-template-dir ".local_private\broker_templates" --allow-private-template-overlay --write-json --write-csv --write-md
```

Private overlay summaries use safe aliases such as `PRIVATE_TEMPLATE_001`. Do
not share private template files, real broker names, MC numbers, rates,
addresses, references, raw text, filenames, local paths, or private notes.

Optional layout provider measurement:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --write-json --write-csv --write-md
```

This runs the `pdfplumber` provider only on digital, extraction-relevant normal
load movement documents. OCR-needed, supplemental-only, non-RateCon, unknown,
and TONU/payment-only documents are skipped for core layout extraction and
reported through safe status counts.

Layout fusion is also explicit. Without `--enable-layout-fusion`, layout
candidates are measured but do not feed the resolver. With the flag, text and
layout candidates are fused conservatively and only safe field/status deltas are
written.

Optional table-profile diagnostics:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-pdfplumber-table-profiles --compare-layout-to-text-baseline --write-json --write-csv --write-md
```

Use `--pdfplumber-table-profile default|lines|text|lines_strict|text_strict` to
select a profile for the main run. Profile comparison writes only safe counts.
It does not write table contents or private values.

Optional normalized stop review packet:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --write-json --write-csv --write-md --write-stop-review-packet
```

Default stop review packets are status-only. They include aliases, stop ids,
stop type, sequence, field name, status, confidence bucket, evidence type, page
number, and warnings. They do not include private stop values. The
`--include-private-stop-values-local-only` flag is explicit local review mode
only, is ignored, must not be committed, and must not be pasted into chat.

Optional stop provenance report:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --write-json --write-csv --write-md --write-stop-review-packet --write-stop-provenance-report
```

The provenance report is local-only and ignored. It includes aliases, counts,
source types, grouping keys, trigger categories, stage counts, and suspected
root-cause labels. It must not include raw text, filenames, broker names, MCs,
rates, addresses, exact dates/times, references, or local paths.

Optional Google Sheets-compatible local review export:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --write-json --write-csv --write-md --write-stop-review-packet --write-stop-provenance-report --write-google-sheet-export --natural-sort-inputs
```

This writes ignored local files:

- `ratecon_review_google_sheet.csv`
- `ratecon_review_workbook.xlsx`, when a workbook writer is already available
  in the local environment

This export remains local and file-based. It does not use OCR, Vision, Camelot,
or new dependencies. Local document stems may appear inside the ignored export
so the user can map aliases to local document order. They must not be printed
to console or copied into chat.

Optional local value-correctness review workbook and CSVs:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-json --write-csv --write-md --write-stop-review-packet --write-stop-provenance-report --write-google-sheet-export --write-review-workbook --write-review-csvs --include-private-review-values-local-only --natural-sort-inputs
```

This writes ignored local review files:

- `ratecon_review_workbook.xlsx`, when a workbook writer is already available;
- `ratecon_review_document_summary.csv`;
- `ratecon_review_stop_review.csv`;
- `ratecon_review_field_review.csv`;
- `ratecon_review_rate_review.csv`.

The `--include-private-review-values-local-only` flag is explicit local review
mode. It may write predicted private values to the ignored workbook/CSVs, but
the console still prints only counts, statuses, issue counts, and basenames.
Do not paste workbook rows into chat and do not commit generated review files.

Optional Google Sheets review sync:

```powershell
python scripts/init_google_sheets_review_config.py --spreadsheet-id "YOUR_SPREADSHEET_ID" --credentials-json ".local_private\google-service-account.json"
```

Share the spreadsheet with:

```text
ai-dispatch-sheet@ai-dispatch-team.iam.gserviceaccount.com
```

If the credential JSON is not already under `.local_private`, import a full
service account JSON safely:

```powershell
python scripts/import_google_service_account_local.py --from-file "C:\path\to\service-account.json"
```

The service account email is not the credential. A short key ID, hash, API key,
or private key fragment is not enough for Google Sheets writes.

Run a safe local preflight first:

```powershell
py scripts/sync_ratecon_review_to_google_sheet.py --preflight-only
```

If preflight reports invalid review CSV headers, regenerate the review workbook
and CSVs with the current measurement command before attempting a Google sync.

```powershell
py scripts/sync_ratecon_review_to_google_sheet.py --confirm-google-review-sync --status-only
```

Optional explicit private-values test sync:

```powershell
py scripts/sync_ratecon_review_to_google_sheet.py --confirm-google-review-sync --include-private-review-values-google-test-only
```

Private-values Google sync also requires `allow_private_review_value_sync: true`
in `.local_private/google_sheets_review_config.json`. This extra config gate is
intentional so the explicit flag cannot upload values by accident.

Optional measurement-and-sync command:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-review-csvs --sync-review-google-sheet --confirm-google-review-sync --natural-sort-inputs
```

Google sync updates only the dedicated tabs `RC_Document_Summary`,
`RC_Stop_Review`, `RC_Field_Review`, `RC_Rate_Review`, `RC_Instructions`, and
`RC_Feedback_Summary`. It refuses unexpected tab names and does not overwrite
operational tabs. It requires local ignored config or environment variables. It
prints tab names, row counts, sync mode, and safety booleans only. It must not
print private values, service account key material, spreadsheet IDs, local
paths, or private filenames.

Download completed Google feedback:

```powershell
py scripts/download_ratecon_review_feedback_from_google_sheet.py --confirm-google-feedback-download
```

Downloaded feedback is written to ignored local CSVs:

- `google_feedback_stop_review.csv`;
- `google_feedback_field_review.csv`;
- `google_feedback_rate_review.csv`.

Collect redacted template patterns before drafting private templates:

```powershell
py scripts/run_private_ratecon_template_pattern_collection.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --write-pattern-json --write-family-md --write-template-drafts
```

Default local output directory:

```text
.local_outputs/private_ratecon_measurement/
```

Generated files:

- `safe_summary.json`
- `safe_summary.csv`
- `safe_aggregate.json`
- `safe_aggregate.md`
- `value_review_template.csv` when requested
- `stop_review_packet.csv` and `stop_review_packet.md` when requested
- `stop_group_provenance.json` and `stop_group_provenance_report.md` when
  requested
- `ratecon_review_google_sheet.csv` and optional `ratecon_review_workbook.xlsx`
  when requested
- `ratecon_review_document_summary.csv`, `ratecon_review_stop_review.csv`,
  `ratecon_review_field_review.csv`, and `ratecon_review_rate_review.csv` when
  local value-correctness review exports are requested
- `candidate_coverage.json` and `candidate_coverage.md` when candidate
  coverage is requested
- `load_identifier_coverage.json` and `load_identifier_coverage.md` when load
  identifier audit is requested

These outputs are local-only and ignored by Git.

## Raw Text Policy

Raw extracted text may exist only in memory long enough to build safe candidate
and resolver summaries. It must not be printed, saved, logged, committed, or
included in tracked fixtures.

## Private Value Policy

Private field values must not appear in shareable measurement summaries.

The measurement row should record:

- whether a candidate exists;
- confidence bucket;
- field status;
- warning codes;
- blocker categories.

It should not record the selected candidate value.

## Architecture Boundaries

The measurement harness must not:

- create DispatchCases;
- call DecisionEngine;
- call Telegram;
- write Event Timeline events;
- emit accept/reject recommendations;
- bypass RateConfirmationIntake validation.

## Previous Safe Private Baseline

Known prior safe private results:

- `RATECON_001`: `TEXT_EXTRACTED`, 4636 chars, 2 pages, still missing core
  fields around customer/load identity, stops/dates, rate, and weight.
- `RATECON_002`: `EMPTY_TEXT`, 0 chars, 2 pages, extraction-quality issue.
- `RATECON_003`: `TEXT_EXTRACTED`, 10694 chars, 3 pages, still missing most
  core fields; low-confidence categories were rate and special requirements.

These baseline notes are status-only. They do not contain private values.

## Calibrated Classification Baseline

The calibrated safe private rerun reported:

- total documents: 18
- `DIGITAL_TEXT`: 14
- `OCR_NEEDED` / `EMPTY_TEXT`: 4
- extraction-relevant documents: 10
- normal load movement documents: 6
- TONU/payment confirmations: 4
- supplemental-only documents: 2
- non-RateCon or unknown-review documents: 6

This means OCR remains queued for empty-text documents, but it is not the next
default block. The layout provider pilot targets the 6 normal load movement
digital-text documents, while TONU stays on a separate payment/status path.

## pdfplumber Layout Provider Baseline

The first safe private layout-provider rerun reported:

- documents measured: 18
- layout attempted: 6
- layout success: 6
- layout skipped: 12
- layout failed: 0
- OCR-needed unchanged: 4

These are status-only counts. They do not include private values, filenames,
raw text, or local paths.

The first safe private layout-fusion rerun reported:

- documents measured: 18
- layout attempted: 6
- layout success: 6
- layout skipped: 12
- layout failed: 0
- fusion attempted: 6
- stop groups produced from provider artifacts: 0
- OCR-needed unchanged: 4
- rate evidence improved, while stop/location/date association remained the
  main unresolved blocker

These results keep OCR, Vision, Camelot, and new broker templates deferred. The
next safe block should focus on provider-to-table/section structure and
stop/date/location association using fake fixtures and safe deltas.

The calibrated diagnostics and no-regression rerun reported:

- documents measured: 18
- layout attempted: 6
- layout success: 6
- layout skipped: 12
- layout failed: 0
- fusion attempted: 6
- total tables: 22
- total table cells: 710
- stop label signals: pickup 37, delivery 44, stop 26, date 5, time 23
- stop groups produced: 78
- fusion worsened fields: none
- OCR-needed unchanged: 4

The no-regression guard prevents layout fusion from worsening protected critical
fields by default. The safe diagnostic result indicates that `pdfplumber`
produces useful table and stop evidence; the next blocker is resolver/evaluation
readiness for stop/date/location fields, not Camelot, OCR, Vision, or broker
template onboarding.

The first normalized stop rerun reported:

- documents measured: 18
- layout attempted: 6
- fusion attempted: 6
- raw stop groups: 78
- normalized stops: 78
- pickup / delivery / unknown stops: 43 / 32 / 0
- stop review required: 78
- duplicate / noise removed: 0 / 0
- stop field statuses: location resolved 78, date missing 78, time missing 76
  and resolved 2, reference resolved 11
- fusion worsened fields: none
- OCR-needed unchanged: 4

This means provider visibility and no-regression guardrails are working, but the
stop resolver is not correctness-ready. The next blocker is reducing duplicate
or noisy normalized stops and associating date/time/reference fields with the
right stop in a reviewable way.

The stop calibration rerun reported:

- documents measured: 18
- layout attempted: 6
- raw stop groups: 112
- normalized stops: 112
- pickup / delivery / unknown stops: 45 / 37 / 30
- duplicate / noise removed: 0 / 0
- table row / section context merges: 0 / 0
- stop review required: 112
- date candidates generated / attached: 10 / 10
- time candidates generated / attached: 9 / 9
- missing date / time fields: 102 / 103
- stop pattern counts include `LOCATION_DATE_SPLIT`,
  `TABLE_CELL_OVER_GROUPING`, `TABLE_ROW_NOT_MERGED`,
  `TIME_CANDIDATE_NOT_ATTACHED`, and `PICKUP_DELIVERY_OVERCLASSIFIED`
- fusion worsened fields: none
- OCR-needed unchanged: 4

This means date/time evidence now reaches the diagnostics layer, but grouping is
still too fragmented. Because `pdfplumber` is already producing layout evidence,
the next default block is deeper stop grouping/merge hardening. Camelot, OCR,
and Vision remain decision-gated.

The stop provenance rerun after the first grouping-stage refactor reported:

- documents measured: 18
- layout attempted: 6
- raw stop signals/groups: 112 / 112
- premerge group count: 112
- post row merge group count: 112
- post section merge group count: 112
- post noise filter group count: 112
- post dedupe group count: 112
- normalized stop count: 112
- duplicate / noise removed: 0 / 0
- date candidates generated / attached: 10 / 10
- time candidates generated / attached: 9 / 9
- OCR-needed unchanged: 4

This confirms the private run is still a passthrough at every stop grouping
stage. The next default block should rewrite provider-line clustering and
stop-line classification before local private value correctness review.

Layout diagnostic issue buckets:

- `provider_no_tables`: tables were not detected.
- `provider_no_words`: word evidence is missing or too weak.
- `provider_has_tables_but_no_stop_groups`: table evidence exists but grouping
  did not use it.
- `provider_has_stop_labels_but_no_groups`: labels exist but no groups were
  created.
- `scope_filter_excluded_pages`: classification/extraction scope removed likely
  stop pages.
- `association_logic_gap`: evidence exists but association/scoring remains weak.
- `candidate_fusion_regression`: layout fusion worsened field status and needs
  guardrail review.

## Layout-Aware Scaffold Status

The layout-aware digital extraction scaffold started dependency-free and
fake-only. It adds:

- `LayoutExtractionArtifact` contracts for pages, words, lines, blocks, tables,
  cells, reading order variants, and evidence refs;
- synthetic layout fixtures under
  `tests/fixtures/document_ai/layout_artifacts/`;
- layout indexing and label-value proximity helpers;
- layout-aware rate/payment, stop, and operational-detail candidates;
- a fake-only CLI:
  `py scripts/run_fake_layout_candidate_extraction.py`.

The provider pilot adds `pdfplumber==0.11.9` behind explicit CLI flags. Safe
private measurement uses provider output only for candidate counts, evidence
type counts, and status-only deltas.

When a provider exists, private measurement should compare only status deltas:
candidate counts, field statuses, blocker categories, warning codes, and
eligible denominators. It must still not print or save raw private text or
private field values.

## How To Interpret Measurement

Mostly `OCR_NEEDED`:

- design local OCR contracts and privacy gates next;
- do not immediately add OCR dependencies.

Mostly `TEXT_EXTRACTED` with missing fields:

- design layout-aware digital extraction next;
- consider table/word/block extraction only after dependency review.

Mostly `TEMPLATE_GAP`:

- plan real broker template onboarding with redacted/anonymized fixtures.

Mostly `RESOLVER_GAP`:

- add more fake/anonymized resolver scenarios and harden resolver rules.

Tables and stop labels exist, but stop fields remain unresolved:

- harden resolver scoring and build an evaluation corpus before changing
  providers.

Normalized stops are high but all review-required:

- harden stop field association and stop dedupe/noise filtering;
- use local-only review packets to check correctness before changing providers.

No tables but strong words/lines:

- extend line/section stop extraction; consider a table-provider design
  checkpoint only after that measurement.

Weak provider words/lines:

- run an alternative layout provider review.

Mostly high-confidence candidates:

- build a human review/evaluation corpus before any DispatchCase automation.

Vision AI is not the default next step. It should be considered only after
deterministic and local routes have been measured.

## Stop Span Measurement Flags

Use the stop span extractor only with explicit layout flags:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "<local-folder>" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-json --write-csv --write-md --write-stop-review-packet --write-stop-provenance-report --write-google-sheet-export --natural-sort-inputs
```

Safe output adds:

- `old_raw_stop_groups`;
- `old_normalized_stops`;
- `span_anchor_count`;
- `stop_span_count`;
- `span_normalized_stop_count`;
- `span_pickup_count`;
- `span_delivery_count`;
- `span_unknown_count`;
- `span_date_resolved_count`;
- `span_date_missing_count`;
- `span_time_resolved_count`;
- `span_time_missing_count`;
- `span_review_required_count`;
- `span_passthrough_detected`.

The Google Sheets export includes the same old/new comparison columns. It is a
local ignored artifact. It does not use Google APIs, OAuth, or cloud services.

The latest safe result: 6 layout attempts, 112 old normalized stops, 29 span
normalized stops, 0 span passthrough, 8 resolved dates, 10 resolved times, and
29 review-required span stops.

The local value-correctness and policy cleanup rerun produced:

- documents measured: 18
- old normalized stops: 112
- span normalized stops: 29
- stop review rows: 174
- field review rows: 154
- rate review rows: 10
- readiness level counts: `extraction_review_ready=14`, `not_ready=4`
- integrity issue counts: none
- policy misclassification count: 0
- true intake blockers: 56
- dispatch-decision blockers: 128
- optional missing fields: 56
- OCR-needed unchanged: 4

This confirms the next default step is policy-clean target selection from true
intake blockers. Stop-related required fields remain the largest group, but the
dominant reason is `no_candidate`, so the next stop block should audit candidate
generation/coverage instead of stacking regex or mapping heuristics.

## Safe To Paste Back

Safe to paste back:

- aggregate counts;
- per-alias field status;
- missing field names;
- needs-check field names;
- conflict field names;
- blocker categories;
- route/status counts;
- candidate counts by field;
- review-required count;
- baseline comparison status for `RATECON_001`, `RATECON_002`, and
  `RATECON_003` aliases when applicable.

Do not paste back:

- raw text;
- filenames;
- broker/customer/contact names;
- MC numbers;
- rates;
- pickup/delivery addresses;
- dates/times;
- load numbers;
- PO/BOL/reference numbers;
- local file paths;
- private value-review notes.
