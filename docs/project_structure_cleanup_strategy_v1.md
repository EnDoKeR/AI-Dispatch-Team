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
