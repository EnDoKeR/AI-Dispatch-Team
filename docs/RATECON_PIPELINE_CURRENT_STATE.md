# RateCon Pipeline Current State

This document records the official current Rate Confirmation extraction pipeline
as implemented. It is a control checkpoint, not a new feature.

## Official Implemented Flow

```text
PDF triage
-> extraction artifact
-> safe text artifact
-> document type / page role / section role classification
-> extraction scope filtering
-> layout artifact / layout-aware candidates
-> optional candidate source fusion / stop association
-> generic candidates
-> broker template matching
-> template-aware scoring
-> conservative resolver
-> RateConfirmationIntake draft
-> validation
```

The pipeline is evidence-first and review-gated. It does not create DispatchCases,
write events, call Telegram, call DecisionEngine, or decide accept/reject/review.

## Step Owners

| Step | Owner modules | Current status |
| --- | --- | --- |
| PDF triage | `app/document_ai/pdf_triage.py`, `app/document_ai/pdf_triage_contract.py` | Implemented safe metadata route |
| Extraction artifact | `app/document_ai/extraction_artifacts.py`, `app/document_ai/pdf_extraction_artifact.py` | Implemented safe metadata artifact |
| Local PDF text extraction | `app/market_intelligence/intake/pdf_text_extraction.py` | Local dry-run helper only |
| Safe text artifact | `app/document_ai/text_artifacts.py` | Implemented for fake/anonymized candidate extraction |
| Document/page/section classification | `app/document_ai/document_classification.py` | Implemented deterministic text classifier |
| Extraction scope filtering | `app/document_ai/extraction_scope.py` | Implemented page selection before RateCon candidates |
| Layout artifact scaffold | `app/document_ai/layout_artifacts.py`, `app/document_ai/layout_index.py`, `app/document_ai/layout_proximity.py` | Implemented dependency-free contracts and helpers with synthetic fixtures |
| Layout provider pilot | `app/document_ai/layout_provider.py`, `app/document_ai/pdfplumber_layout_provider.py`, `app/document_ai/layout_pipeline.py`, `app/document_ai/layout_provider_diagnostics.py` | Implemented `pdfplumber` provider, safe diagnostics, and table-profile comparison behind explicit safe measurement flags |
| Layout-aware candidate scaffold | `app/document_ai/layout_candidate_extraction.py`, `app/document_ai/layout_rate_candidates.py`, `app/document_ai/layout_stop_candidates.py`, `app/document_ai/layout_operational_candidates.py` | Implemented for synthetic layout artifacts only |
| Layout fusion and stop association | `app/document_ai/candidate_fusion.py`, `app/document_ai/stop_association.py`, `app/document_ai/rate_fusion.py`, `app/document_ai/operational_fusion.py` | Implemented behind explicit safe measurement flags |
| Normalized stops and review readiness | `app/document_ai/normalized_stops.py`, `app/document_ai/stop_normalization.py`, `app/document_ai/stop_group_diagnostics.py`, `app/document_ai/stop_group_provenance.py`, `app/document_ai/stop_group_provenance_report.py`, `app/document_ai/stop_review_packet.py` | Implemented normalized stop contracts, provenance metadata/reporting, dedupe/noise filtering, sequencing, field association, safe measurement reporting, and local-only review packets |
| Provider-line stop spans | `app/document_ai/stop_span_extractor.py`, `scripts/run_private_ratecon_measurement.py` | Implemented behind `--enable-stop-span-extractor`; compares old stop groups to direct line-span normalized stops in safe measurement and review exports |
| Local value correctness review | `app/document_ai/extraction_readiness.py`, `app/document_ai/measurement_integrity.py`, `app/document_ai/ratecon_review_workbook.py`, `app/document_ai/review_feedback_import.py`, `app/document_ai/local_review_analysis.py`, `app/document_ai/core_field_gap_analysis.py`, `app/document_ai/ratecon_core_field_policy.py` | Implemented local-only review workbook/CSV rows, readiness status contracts, count integrity checks, safe feedback import summaries, local issue analysis reports, policy-aware core field gap forensics, and clean target selection |
| Google Sheets review sync | `app/integrations/google_sheets_review.py`, `scripts/sync_ratecon_review_to_google_sheet.py`, `scripts/download_ratecon_review_feedback_from_google_sheet.py` | Implemented explicit confirmation-gated review-tab sync and feedback download using local ignored config; no operational tab overwrite |
| Generic candidates | `app/document_ai/ratecon_candidates.py`, `app/document_ai/ratecon_candidate_generators.py`, `app/document_ai/ratecon_candidate_extraction.py` | Implemented for fake/anonymized text artifacts |
| Broker template contract/registry | `app/document_ai/broker_templates.py`, `app/document_ai/broker_template_registry.py` | Implemented for fake/anonymized JSON templates |
| Private broker template overlay | `app/document_ai/broker_template_registry.py`, `scripts/run_private_ratecon_measurement.py` | Implemented as explicit local-only overlay support |
| Redacted pattern collection | `app/document_ai/private_template_pattern_collector.py`, `app/document_ai/private_template_pattern_families.py`, `scripts/run_private_ratecon_template_pattern_collection.py` | Implemented for safe local pattern grouping |
| Broker template matching | `app/document_ai/broker_template_matcher.py` | Implemented deterministic fake-template matcher |
| Template-aware scoring | `app/document_ai/broker_template_scoring.py`, `app/document_ai/broker_template_candidate_extraction.py` | Implemented candidate adjustment layer |
| Conservative resolver | `app/document_ai/ratecon_field_resolution.py` | Implemented generic and template-aware resolution |
| Intake draft | `app/document_ai/ratecon_intake_draft.py` | Implemented draft builder from resolved fields |
| Intake validation | `app/market_intelligence/intake/rate_confirmation_validation.py`, `app/market_intelligence/intake/rate_confirmation_intake.py` | Implemented validation and status gating |

## Implemented

- PDF triage contract and safe route selection.
- ExtractionArtifact metadata contract without raw text by default.
- Safe text artifact contract for fake/anonymized text.
- FieldCandidate and CandidateExtractionResult contracts.
- Generic candidate generators for:
  - money/rate vs accessorials;
  - broker identity and broker MC;
  - load number and typed references;
  - pickup/delivery location/date/time;
  - equipment, weight, commodity, special requirements, accessorial terms.
- BrokerTemplate contract, fake JSON fixtures, registry, matcher, and template-aware scoring.
- Conservative field resolver and template-aware resolver wrapper.
- Hard-layout resolver guards for multi-page terms, accessorial rate traps,
  table-like stops, header-only broker identity, typed references, conflicting
  appointment times, and buried special requirements.
- RateConfirmationIntake draft builder from resolved fields.
- Validation that computes missing and needs-check fields.
- Fake-only candidate/template dry-run CLI.
- Local-only private measurement harness that reports safe aliases, counts,
  field statuses, blocker categories, and aggregate summaries.
- Local-only private broker template overlay loading with safe template aliases.
- Redacted template pattern collection and local-only template draft skeletons.
- Deterministic document type, page role, section role, and extraction scope
  classification before RateCon candidate extraction.
- Provider-line stop span extraction behind explicit safe measurement flags.
- Local-only review export now compares old stop-group counts with span
  extractor counts.
- Stop span type count reporting now includes generic `stop` counts so
  pickup + delivery + generic stop + unknown can reconcile to the normalized
  stop denominator.
- Google Sheets review sync can publish local review rows to dedicated
  `RC_` tabs when `--confirm-google-review-sync` is passed. Status-only mode is
  default; private-value test sync requires an additional explicit flag.
- Google Sheets feedback download can write completed review tabs to ignored
  local CSVs and summarize correct/incorrect/unknown counts and issue types.
- Google Sheets live sync is currently paused until a full local service account
  JSON is available. Local review analysis and workbook review continue without
  Google credentials.
- Local review analysis reports summarize ignored review CSVs into safe issue
  category counts, top fields needing review, readiness counts, and next-fix
  buckets.
- Core field gap forensics breaks `missing_core_field` and
  `conflict_core_field` into concrete field names, root-cause buckets, and
  readiness blocker levels.
- RateCon core field policy separates extraction-review blockers, true
  intake-core blockers, dispatch-decision blockers, review-only fields,
  optional missing fields, and non-applicable fields.
- Policy-aware local analysis now reports `optional_field_misclassified_as_core`
  separately from extraction targets. Current cleanup result is zero policy
  misclassifications, 56 true intake blockers, 128 dispatch-decision blockers,
  and 56 optional missing fields.
- Stop-span flat-field mapping now surfaces resolved pickup/delivery
  location/date/time evidence into top-level field review statuses when those
  statuses are missing or not applicable, without overwriting conflicts.
- Stop span date/time extraction now handles additional deterministic formats
  in synthetic tests: dotted dates, ISO dates, compact time windows, right-side
  PU/SO date/time lines, target windows, and shipping/receiving hours.
- Private measurement rows and aggregates now separate eligible RateCon documents
  from supplemental-only, non-RateCon, unknown-review, and OCR-needed documents.
- Classification eligibility has been calibrated so carrier load tenders, load
  tenders, order confirmations, dispatch/load confirmations, and TONU payment
  confirmations are extraction-relevant even when broker templates are unknown.
- Safe measurement reports now separate extraction-relevant documents, normal
  load movement documents, TONU/payment confirmations, supplemental-only
  documents, unknown-review documents, and OCR-needed documents.
- Dependency-free layout artifact contracts, synthetic layout fixtures, layout
  indexing helpers, label-value proximity helpers, and layout-aware candidate
  generators for rate/payment, stops, and operational details.
- Fake-only layout candidate CLI:
  `scripts/run_fake_layout_candidate_extraction.py`.
- First real digital-text layout provider pilot using `pdfplumber==0.11.9`,
  behind `--layout-provider pdfplumber --enable-layout-candidates`.
- Safe layout-provider measurement fields for provider status counts, layout
  candidate counts, evidence type counts, and candidate-count deltas.
- Layout field delta audit, candidate source fusion contracts, stop association
  contracts, table/section stop grouping, rate fusion guardrails, and
  operational detail fusion.
- Safe measurement flag `--enable-layout-fusion`, which remains off by default.
- Safe pdfplumber diagnostics for word, line, table, table-cell, stop-signal,
  quality-bucket, and likely-issue counts.
- Configurable pdfplumber table settings profiles: `default`, `lines`, `text`,
  `lines_strict`, and `text_strict`.
- No-regression fusion guardrails for protected critical fields.
- Normalized stop set contracts, raw stop group diagnostics, conservative
  dedupe/noise filtering, sequencing/type resolution, field association, and
  local-only stop review packets.
- Stop group provenance metadata, local-only provenance reports, synthetic
  provenance fixtures, and normalized stop stage counts for raw/premerge,
  row-merge, section-merge, noise-filter, dedupe, and normalized stages.

## Scaffolding Only

- PDF triage route values for future OCR/Vision decisioning.
- ExtractionArtifact method values for future `pdfplumber`, OCR, or Vision.
- LayoutExtractionArtifact provider boundary for additional future providers.
- Broker template structure for future real broker templates.
- Event Timeline append points described in docs only.
- DispatchCase creation from validated intake is not implemented.

## Not Implemented Yet

- OCR.
- Vision AI.
- Cloud extraction APIs.
- Production private RateCon parser path.
- Real broker templates.
- Production real broker templates.
- Broker template privacy review workflow beyond local-only overlay measurement.
- Candidate field resolver for difficult layout pairing beyond current fake fixtures.
- Resolver/evaluation calibration for choosing among provider-derived stop
  groups and layout-backed stop/date/location candidates.
- DispatchCase creation from RateCon extraction.
- Event writes from document extraction.
- Telegram business logic for RateCon extraction.
- Live DAT/API integration.
- Google Sheet review feedback applying corrections to production intake data.

## Test Coverage

Current relevant tests include:

- PDF triage and artifacts:
  - `tests/test_pdf_triage_contract.py`
  - `tests/test_pdf_triage.py`
  - `tests/test_pdf_extraction_artifact.py`
  - `tests/test_fake_pdf_triage_dry_run_cli.py`
- Text artifacts and generic candidates:
  - `tests/test_text_artifacts.py`
  - `tests/test_ratecon_candidates_contract.py`
  - `tests/test_ratecon_candidate_extraction.py`
  - `tests/test_ratecon_money_candidates.py`
  - `tests/test_ratecon_identity_reference_candidates.py`
  - `tests/test_ratecon_stop_candidates.py`
  - `tests/test_ratecon_operational_detail_candidates.py`
- Layout-aware synthetic scaffold:
  - `tests/test_layout_artifacts.py`
  - `tests/test_layout_artifact_fixtures.py`
  - `tests/test_layout_index.py`
  - `tests/test_layout_proximity.py`
  - `tests/test_layout_candidate_adapter.py`
  - `tests/test_layout_rate_candidates.py`
  - `tests/test_layout_stop_candidates.py`
  - `tests/test_layout_operational_candidates.py`
  - `tests/test_layout_candidate_extraction.py`
  - `tests/test_layout_resolver_readiness.py`
  - `tests/test_run_fake_layout_candidate_extraction.py`
  - `tests/test_layout_provider.py`
  - `tests/test_pdfplumber_layout_provider.py`
  - `tests/test_layout_pipeline.py`
  - `tests/test_layout_provider_comparison.py`
  - `tests/test_layout_provider_diagnostics.py`
  - `tests/test_layout_field_delta_audit.py`
  - `tests/test_candidate_fusion.py`
  - `tests/test_stop_association.py`
  - `tests/test_stop_table_association.py`
  - `tests/test_stop_section_association.py`
  - `tests/test_stop_candidate_fusion.py`
  - `tests/test_rate_fusion.py`
  - `tests/test_operational_fusion.py`
  - `tests/test_normalized_stops.py`
  - `tests/test_stop_group_diagnostics.py`
  - `tests/test_stop_normalization_fixtures.py`
  - `tests/test_stop_group_dedupe_noise.py`
  - `tests/test_stop_sequence_type_resolution.py`
  - `tests/test_stop_field_association.py`
  - `tests/test_normalized_stop_set_builder.py`
  - `tests/test_normalized_stop_field_resolution.py`
  - `tests/test_stop_review_packet.py`
  - `tests/test_stop_group_provenance.py`
  - `tests/test_stop_group_provenance_report.py`
  - `tests/test_stop_provenance_fixtures.py`
  - `tests/test_stop_date_time_merge.py`
  - `tests/test_stop_pipeline_ordering.py`
- Broker templates:
  - `tests/test_broker_templates_contract.py`
  - `tests/test_broker_template_fixtures.py`
  - `tests/test_broker_template_registry.py`
  - `tests/test_broker_template_matcher.py`
  - `tests/test_broker_template_scoring.py`
  - `tests/test_broker_template_candidate_extraction.py`
  - `tests/test_broker_template_resolver_context.py`
  - `tests/test_broker_template_intake_context.py`
  - `tests/test_broker_template_regression_matrix.py`
  - `tests/test_ratecon_hard_layout_regression_matrix.py`
- Intake and validation:
  - `tests/test_ratecon_intake_draft.py`
  - `tests/test_rate_confirmation_intake.py`
  - `tests/test_rate_confirmation_validation.py`
- Boundaries:
  - `tests/architecture/test_architecture_boundaries.py`

## Fake-Only Scripts

- `py scripts/run_fake_pdf_triage_dry_run.py`
- `py scripts/run_fake_ratecon_candidate_extraction.py`
- `py scripts/run_fake_layout_candidate_extraction.py`

These scripts use fake/anonymized fixtures and should not be pointed at private
RateCons.

## Local Private Dry-Run Scripts

The following scripts exist for local-only private testing and must not commit or
print raw private text:

- `py scripts/private_ratecon_inventory.py`
- `py scripts/run_private_ratecon_pdf_extraction_inventory.py --limit 3`
- `py scripts/run_private_ratecon_pdf_dry_run.py --limit 3`
- `py scripts/run_private_ratecon_redacted_diagnostics.py --limit 3`
- `py scripts/run_private_ratecon_layout_diagnostics.py --limit 3`
- `py scripts/export_ratecon_dry_run_csv.py --limit 3`
- `py scripts/export_private_ratecon_value_review_csv.py --limit 3`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\path\to\private\ratecons" --confirm-private-local-run --write-json --write-csv --write-md`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --compare-layout-to-text-baseline --write-json --write-csv --write-md`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --compare-layout-to-text-baseline --write-json --write-csv --write-md`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-pdfplumber-table-profiles --compare-layout-to-text-baseline --write-json --write-csv --write-md`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --write-json --write-csv --write-md --write-stop-review-packet`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --write-json --write-csv --write-md --write-stop-review-packet --write-stop-provenance-report`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-json --write-csv --write-md --write-stop-review-packet --write-stop-provenance-report --write-google-sheet-export --write-review-workbook --write-review-csvs --include-private-review-values-local-only --natural-sort-inputs`
- `py scripts/run_private_ratecon_template_pattern_collection.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --write-pattern-json --write-family-md --write-template-drafts`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --private-template-dir ".local_private\broker_templates" --allow-private-template-overlay --write-json --write-csv --write-md`

Private value-review CSV output is local-only and ignored.

## Safety Rules

- Do not commit private PDFs.
- Do not commit private extracted text.
- Do not commit private field values.
- Do not create tracked fixtures from private documents.
- Do not add OCR or Vision AI without a separate approved block.
- Do not add cloud extraction APIs in this pipeline.
- Do not create DispatchCases from extraction output.
- Do not write DispatchCase events from extraction output.
- Do not call DecisionEngine from document extraction.
- Do not put extraction logic in Telegram modules.
- BrokerTemplate is not BrokerProfile or broker memory.
- Private broker templates must stay in ignored local paths and must not be
  committed.

## Known Limitations

- Some PDFs have no text layer and need future OCR/PDF route handling.
- Template-specific fixtures are fake and do not prove real broker coverage.
- Hard-layout behavior is tested on fake fixtures only and still needs safe
  private measurement before production claims.
- Calibrated measurement still shows missing and conflicting fields on normal
  load movement documents. The first `pdfplumber` provider run succeeded on 6
  normal-load digital-text documents and produced candidate-count deltas, but it
  does not resolve final fields by itself.
- The first layout-fusion rerun attempted fusion on 6 documents and produced no
  stop groups from provider artifacts. The follow-up diagnostics and calibration
  rerun produced rich layout on all 6 attempted documents, 22 tables, 710 table
  cells, 78 stop groups, and no worsened fused fields. Stop/location/date fields
  still need resolver/evaluation calibration because many remain unchanged or
  unresolved.
- The normalized stop rerun converted 78 raw stop groups into 78 normalized
  stops with pickup / delivery / unknown counts of 43 / 32 / 0. All 78 stops
  still require review, no duplicates/noise were removed, dates remained
  missing, and OCR-needed stayed at 4. This means the provider is useful, but
  stop correctness depends on stronger dedupe/noise filtering and field
  association.
- The stop calibration rerun generated date/time diagnostics but exposed more
  fragmentation: 112 raw groups became 112 normalized stops, duplicate/noise and
  row/section merge counts remained zero, 102 date fields and 103 time fields
  remained missing, and all stops still required review. The safe pattern counts
  point to location/date split, table-cell over-grouping, row-not-merged, and
  residual pickup/delivery overclassification. Fusion worsened fields stayed at
  zero.
- The provenance rerun after the first grouping-stage refactor still reported
  passthrough counts at every stage: raw/premerge/post-row/post-section/
  post-noise/post-dedupe/normalized were all 112. Source types were
  `single_line=70` and `table_row=42`; root causes remained
  `NORMALIZER_PASSTHROUGH`, `ONE_GROUP_PER_LINE`, and
  `DATE_TIME_SPLIT_FROM_LOCATION`. The next block should rewrite provider-line
  clustering and table-row stop classification before local value correctness
  review.
- The stop wiring audit added synthetic invariant tests, a first-class stage
  trace, a `post_single_line_cluster` stage, and a local Google Sheets-compatible
  review export. Synthetic fixtures now reduce mergeable line groups, but the
  private safe rerun remained `NOT FIXED`: raw, premerge, post-single-line,
  post-row, post-section, post-noise, post-dedupe, and normalized counts all
  stayed at 112; first changed stage counts were empty; passthrough aliases were
  6. The next block must inspect provider line evidence directly and derive
  better cluster keys from line order, bbox/proximity, page/section context, and
  field context.
- Template scoring adjusts candidates but does not guarantee final field resolution.
- The provider-line stop span extractor reduced private normalized stops from
  112 to 29 without span passthrough. Local review exports now produce
  `Document_Summary`, `Stop_Review`, `Field_Review`, and `Rate_Review` rows
  with predicted values only in explicit local-only mode. The latest safe
  review export reported 18 document rows, 174 stop review rows, 154 field
  review rows, 10 rate review rows, readiness counts of 14
  `extraction_review_ready` and 4 `not_ready`, and no integrity issues.
- Policy-clean core field analysis shows stop-related required fields remain the
  largest true intake blocker group, but mostly as `no_candidate`, not as a
  mapping conflict. The next stop-focused block should inspect stop-span
  evidence/candidate generation and coverage before adding more deterministic
  date/time or mapping heuristics.
- Validation still gates readiness when fields are missing, low confidence, or conflicting.

## Next Recommended Block

Next safe block after policy-aware blocker cleanup:

```text
Audit stop-span evidence/candidate generation and coverage for required
pickup/delivery date and location fields, or use local human review if the
review workbook shows those gaps are expected document-specific omissions.
```

OCR and Vision remain deferred. Camelot/table-provider evaluation should happen
only if future diagnostics show pdfplumber cannot produce useful table evidence
or if resolver-ready table evidence remains structurally insufficient after
line/section and stop-group scoring are measured.
