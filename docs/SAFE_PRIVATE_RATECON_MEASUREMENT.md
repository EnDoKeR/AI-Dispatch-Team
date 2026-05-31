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

The export is file-based only. It does not use Google APIs, OAuth, cloud
services, OCR, Vision, Camelot, or new dependencies. Local document stems may
appear inside the ignored export so the user can map aliases to local document
order. They must not be printed to console or copied into chat.

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
