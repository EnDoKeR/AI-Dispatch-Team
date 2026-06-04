# Project Structure Cleanup Strategy v1

This cleanup track is visibility-first and behavior-preserving. Each PR should
move one ownership boundary at a time, keep public entrypoints stable, and avoid
production extraction changes.

## Private RateCon Measurement CLI Split

`scripts/run_private_ratecon_measurement.py` remains the public private
measurement CLI. Phase 1 extracts only the command surface:

- argument definitions and help text;
- parsed command configuration;
- local/private preflight safety validation.

The extracted modules live under `app/document_ai/measurement_cli/` and must not
own measurement business logic. They must not process PDFs, invoke OCR, call
models or cloud services, write reports, sync Google Sheets, or read private
document content.

Phase 2 extracts only output path and filename construction. It centralizes
stable local artifact names and local-only output path validation so later
cleanup can move writers without accidentally changing filenames, directories,
or schemas. The output path module must not create directories, write files,
process PDFs, invoke OCR, call models or cloud services, sync Google Sheets, or
own report/audit generation.

Phase 3A extracts only safe report/export writer ownership for the local-only
private measurement summaries. The writer module owns safe JSON, CSV, Markdown,
and value-review template output generation while preserving existing filenames,
schemas, and local-only/private-redaction metadata. It must use the centralized
output path helpers and must not run measurement, process PDFs, invoke OCR, call
models or cloud services, sync Google Sheets, generate review workbooks, or own
full audit orchestration.

Phase 3B extracts only simple review/export artifact ownership for local-only
review packets and related labels. It must preserve existing filenames, schemas,
and local-only/private-redaction metadata, and it must not run measurement,
process PDFs, invoke OCR, call models or cloud services, sync Google Sheets,
generate review workbooks, or own full audit orchestration.

Phase 3C extracts only optional audit/diagnostic orchestration wrappers. The
orchestration module may decide which existing audit writer functions to call
from already-parsed flags, but it must not own metric definitions, audit
algorithms, filenames, schemas, measurement execution, review workbook
generation, or Google sync wiring.

Phase 3D extracts only review workbook generation ownership. The wrapper module
may decide whether to call the existing workbook artifact writer based on
already-parsed flags and may prepare console-safe result labels, but it must not
rewrite workbook internals, change sheet names, columns, styles, row semantics,
filenames, schemas, measurement execution, audit metrics, or Google sync wiring.

Phase 3E extracts only Google Sheets sync wiring. The wrapper module may plan
whether sync should run, apply the existing config override precedence, delegate
to the existing Google Sheets adapter, and prepare console-safe labels. It must
not change credential discovery, API scopes, worksheet semantics, sync modes,
output schemas, workbook layout, measurement execution, or audit metrics. Tests
must use fake clients and must not call Google.

Phase 3F is a responsibility audit, not another behavior split. Use
`scripts/audit_private_ratecon_measurement_cli_responsibilities.py` and
`docs/private_ratecon_measurement_cli_responsibility_audit_v1.md` to measure the
remaining responsibilities in `scripts/run_private_ratecon_measurement.py`
before deciding whether any further split is justified. The audit must remain
static/local-only and must not import project modules, run measurement, process
PDFs, invoke OCR, call Google, or call model/cloud services.

Future work should pause after the audit and make an explicit decision. Each
phase must preserve CLI flag names, output schemas, output filenames, workbook
layout, metric definitions, safety gates, credential behavior, sync semantics,
and measurement behavior unless a separate behavior-change PR explicitly
approves and tests that change.

Private outputs remain local-only. Generated reports, audits, review workbooks,
OCR artifacts, model outputs, raw extracted text, gold labels, Google
credentials, token files, sync logs with private values, and local audit outputs
must stay out of git.

## RateCon Field Policy Ownership

`app/document_ai/ratecon_core_field_policy.py` is the single owner for RateCon
readiness and critical-field policy. New readiness, dispatch-critical,
intake-core, or extraction-review policy logic must be added there, with tests
that pin the affected field set and readiness behavior.

Legacy `CRITICAL_FIELDS` in
`app/market_intelligence/intake/rate_confirmation_intake.py` is a compatibility
surface only. It should stay available for old imports, but it must not become a
second owner for field policy. See
`docs/ratecon_field_policy_ownership_v1.md` before changing any field set.

Do not add new critical/readiness policy lists in scripts, review exporters,
local audit tooling, provider governance scaffolding, or tests except as
expected-value assertions for the canonical policy.

## RateCon OCR Ownership Status

OCR cleanup starts with an ownership/status audit, not deletion or
productionization. Use `scripts/audit_ratecon_ocr_ownership_status.py` and
`docs/ratecon_ocr_ownership_status_v1.md` before changing OCR modules.

Current status:

- OCR production path is not implemented.
- Optional local/shadow OCR diagnostics exist.
- OCR remains disabled by default and behind explicit local/private flags.
- OCR dependencies remain optional and must not become mandatory in a cleanup
  PR.
- OCR stop assembly, geometry, and table reconstruction are experimental
  shadow diagnostics, not production stop selection.

Do not delete OCR modules until the ownership/status audit is reviewed. Do not
productionize OCR without a separate approved PR with fixture tests, safety
proof, default-off behavior, and review-required output. Generated OCR temp
text, images, TSV, local outputs, raw extracted text, PDFs, and private audit
artifacts must stay out of git.

## RateCon Candidate Model Ownership

Candidate model cleanup starts with an ownership/status audit, not refactoring or
deletion. Use `scripts/audit_ratecon_candidate_model_ownership.py` and
`docs/ratecon_candidate_model_ownership_v1.md` before changing candidate
contracts, generators, resolver inputs, or compatibility modules.

Current ownership policy:

- `app/document_ai/field_candidate_provenance.py` is the canonical candidate
  contract for new document AI extraction candidates.
- `app/document_ai/field_candidate_generators.py` is a generator/orchestration
  layer and should not own canonical schema fields.
- `app/document_ai/field_candidate_resolver.py` consumes the candidate contract
  and owns resolution/review gating, not new candidate schema ownership.
- Legacy RateCon candidate modules remain compatibility surfaces until import
  graph evidence and behavior-pinning tests support a separate cleanup.
- Intake candidate builders are boundary adapters, not candidate contract
  owners.

Do not delete candidate modules until the candidate ownership audit is reviewed.
Do not change candidate shapes, source names, confidence values, resolver
thresholds, scoring, selected output, or extraction behavior in an ownership
cleanup. Future cleanup may add compatibility adapters or consolidate constants
only after behavior-pinning tests prove the existing output contract.

## RateCon Candidate Compatibility Pinning

Candidate compatibility pinning locks current legacy and canonical candidate
surfaces before any migration work. Use
`tests/test_ratecon_candidate_compatibility_pinning.py` to verify that legacy
field/source/confidence constants, candidate dict shapes, canonical candidate
shape, existing adapters, and intake boundary candidate builders have not
changed.

Use `tests/test_ratecon_candidate_constant_guardrails.py` to keep new random
candidate/source/confidence/field/status constants from spreading outside
documented canonical, support-policy, or compatibility modules.
Current duplicate constants are compatibility debt and are pinned by audit count; they are not
approval to add more duplicates.

Future candidate cleanup should start with one narrow target:

- confidence/source constants;
- candidate adapter behavior;
- load identifier candidate generation;
- rate money candidate context;
- stop component candidate shape.

Do not consolidate duplicates without behavior-pinning tests. Do not migrate
consumers, refactor candidate generation, delete candidate modules, change
resolver thresholds, or change selected output in the same PR as guardrail work.

## RateCon Rate/Money Safety Ownership

Rate/money safety cleanup starts with ownership documentation, behavior pinning,
and guardrails. Use `scripts/audit_ratecon_rate_money_safety_ownership.py` and
`docs/ratecon_rate_money_safety_ownership_v1.md` before changing total-rate,
money-context, accessorial/noise, or rate-forensics logic.

Current ownership policy:

- `app/document_ai/ratecon_rate_money_safety.py` is the intended canonical owner
  for money-context safety taxonomy.
- Candidate generators may emit rate/money candidates but should not own an
  independent total-pay/accessorial taxonomy.
- `app/document_ai/field_candidate_resolver.py` consumes rate/money safety
  metadata and owns current ranking behavior, but it should not grow a separate
  rate label taxonomy.
- Rate forensics and conflict-audit modules report diagnoses and safe aggregate
  counts; they should not define competing total-vs-accessorial safety rules.
- Existing duplicate labels/constants are compatibility debt and are pinned by
  tests until a future narrow consolidation PR.

Do not consolidate duplicate rate/money constants without behavior-pinning
tests. The first narrow consolidation target centralizes total-pay/main-rate
label taxonomy in `app/document_ai/ratecon_rate_money_safety.py` while keeping
legacy resolver and generator constants as compatibility aliases. It does not
change selected rate output, resolver scoring, thresholds, candidate source
names, confidence values, field names, schemas, or money-context labels.

Accessorial/noise taxonomy remains intentionally out of scope for the total-pay
label phase.

The next narrow consolidation target centralizes accessorial/noise/fee/penalty
label taxonomy in `app/document_ai/ratecon_rate_money_safety.py` while keeping
legacy resolver, generator, context-feature, layout, and OCR policy constants as
compatibility aliases. It does not change total-pay taxonomy semantics, selected
rate output, resolver scoring, thresholds, candidate source names, confidence
values, field names, schemas, or money-context labels.

After total-pay and accessorial/noise taxonomy centralization, the selected-rate
regression harness pins current sanitized `total_carrier_rate` resolver behavior.
Use `tests/test_ratecon_selected_rate_regression_harness.py` and the optional
`scripts/run_ratecon_selected_rate_regression_snapshot.py` local snapshot before
touching money-context classification, resolver penalties, forensics diagnosis
mapping, or selected-rate ranking profiles. The harness is a behavior pin, not a
correctness claim; known-debt cases require explicit review before expected
outputs change.

The next narrow consolidation target centralizes money-context classifier
helpers in `app/document_ai/ratecon_rate_money_safety.py` while keeping legacy
context-feature wrapper names and return values. It must run the selected-rate
snapshot before and after, compare snapshots locally, and leave resolver
ranking penalties, selected rate output, money-context labels, total-pay
taxonomy, and accessorial/noise taxonomy unchanged.

After classifier ownership, add a local-only private aggregate selected-rate
comparison gate before touching behavior-sensitive resolver ranking or scoring.
`scripts/compare_ratecon_private_selected_rate_aggregates.py` compares existing
private evaluation outputs for `total_carrier_rate`, redacts selected private
values by default, writes only under `.local_outputs/`, and must not run
measurement, process PDFs, run OCR, call Google/model/cloud services, or edit
gold labels/templates.

Future resolver penalty, ranking, scoring, selected-rate behavior, or private
aggregate comparison work must run both the sanitized selected-rate regression
harness and the private aggregate selected-rate gate. The private gate blocks
unintentional increases in wrong counts, high-confidence wrong counts, selected
wrong money-context counts, missing counts, selected-value changes when locally
available, or incompatible evaluated document counts. It is a regression gate,
not a correctness certification.

The next behavior-preserving phase documents and pins resolver rate-ranking
penalty ownership. `app/document_ai/field_candidate_resolver.py` owns
selected-rate ranking behavior for now, including score adjustments, profile
handling, demotion/abstention penalties, and not-selected traces.
`app/document_ai/ratecon_rate_money_safety.py` remains the owner for
money-context taxonomy/classification inputs, not ranking penalties. This phase
must not change penalty values, score calculations, thresholds, demotion or
abstention decisions, selected rate output, or selected-rate regression
expectations.

The next behavior-preserving phase documents selected-rate score
trace/explanation ownership. `app/document_ai/field_candidate_resolver.py`
continues to own score calculation and trace construction. Score traces explain
current decisions; they do not define scoring behavior independently.
Forensics, conflict-audit, shadow-audit, and root-cause modules may summarize
resolver traces but should not invent competing explanation schemas. This phase
must run the selected-rate snapshot before and after, compare snapshots
locally, and leave score calculations, penalty values, thresholds, reason
strings, metrics, and selected rate output unchanged.

The next behavior-preserving phase documents selected-rate forensics diagnosis
mapping ownership. `app/document_ai/rate_candidate_forensics.py` owns diagnosis
mapping documentation and safe forensic category contracts.
`app/document_ai/ratecon_gold_labels.py` currently assigns residual selected-rate
diagnosis strings during local evaluation; that implementation path remains
pinned compatibility debt until a separate narrow move proves unchanged
diagnosis strings, counts, evaluator statuses, aggregate gate results, and
selected-rate snapshots. This phase must not change resolver scoring,
penalties, thresholds, trace schemas, diagnosis strings, diagnosis counts,
evaluator statuses, aggregate gate behavior, or selected rate output.

The next reporting-only phase closes out the selected-rate rate/money cleanup
series with `scripts/summarize_ratecon_selected_rate_closeout.py` and
`docs/ratecon_selected_rate_cleanup_closeout_v1.md`. The closeout summarizes
existing sanitized selected-rate snapshots, aggregate gate output, optional
static audit output, known debt, required gates, and next actions. It tolerates
missing optional private full-corpus baseline inputs and must not run private
measurement, process PDFs, run OCR, call Google/model/cloud services, edit gold
labels, or change resolver behavior.

The next behavior-preserving architecture phase establishes load identifier
ownership and baseline gates. `app/document_ai/load_identifier_candidates.py`
is documented as the intended canonical owner for load identifier candidate
taxonomy/policy, while generators emit candidates, resolvers choose selected
values, and forensics/audit modules report diagnostics. This phase adds a
sanitized selected-load regression harness and a local-only private aggregate
`load_number` gate before any future load-ranking, table/layout pairing, or
candidate-generation behavior changes.

Future rate/money consolidation should continue with one narrow target:

- private full-corpus baseline if the closeout skipped it;
- private aggregate baseline before experimental ranking profile;
- optional shadow-only experimental ranking profile under explicit gates;
- candidate source/ranking normalization.
- load identifier ownership cleanup;
- stop extraction architecture closeout.

Do not lower thresholds, change scoring, change selected rate output, auto-accept
shadow rates, or use private gold labels as runtime truth as part of ownership
cleanup.
