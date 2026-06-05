# RateCon Load Generated/Resolver Provenance Sidecars V1

## Scope

This PR adds local-only generated/resolver provenance sidecars for load-number
diagnostics. It does not improve selected load-number output, change extraction,
change candidate generation decisions, change resolver ranking/scoring, change
table-neighbor or nearby-row behavior, change source labels, change confidence
values, or change evaluator statuses.

The sidecars make adapter/provenance roundtrip measurable on explicit local
runs. They record only already-existing metadata from generated candidates,
adapter input/output rows, dedupe rows, resolver-visible rows, audit rows, and
serialization sidecars. They do not infer missing page/line/source detail and
do not fabricate candidate ids.

Private values remain redacted by default. Private value inclusion is local-only
and requires an explicit flag.

## Ownership

`app/document_ai/load_identifier_generated_resolver_provenance.py` owns the
redacted sidecar row contract for generated, adapted, deduped, and
resolver-visible load candidates.

`scripts/create_ratecon_load_generated_resolver_provenance_sidecars.py` owns
standalone local-only sidecar creation from existing local outputs. It reads
audit/sidecar artifacts only; it does not run private measurement, process PDFs,
run OCR, call Google/model/cloud services, edit gold labels, or edit templates.

`scripts/run_private_ratecon_measurement.py` exposes
`--write-load-generated-resolver-provenance-sidecars` as an explicit opt-in
local diagnostic flag. The flag is off by default and writes additive sidecars
under the existing local output directory.

## Stage-Loss Buckets

The sidecar stage-loss buckets are:

- `generated_detail_available`
- `generated_detail_missing`
- `adapter_input_available`
- `adapter_input_missing`
- `adapter_output_available`
- `adapter_output_missing`
- `lost_between_generation_and_adapter`
- `lost_between_adapter_and_dedupe`
- `lost_between_dedupe_and_resolver`
- `lost_between_resolver_and_audit`
- `lost_between_audit_and_evaluator`
- `resolver_trace_unavailable`
- `dedupe_lineage_unavailable`
- `private_values_not_requested`
- `not_applicable_candidate_missing`
- `unknown`

These buckets are additive and reporting-only. They can be mapped into earlier
detail-loss and serialization-loss summaries, but they do not rename PR #75 or
PR #76 buckets and do not change source-line diagnostic classifications.

## Outputs

The standalone sidecar script writes:

- `load_generated_resolver_provenance_summary.json`
- `load_generated_resolver_provenance_report.md`
- `load_generated_candidates.csv`
- `load_adapter_roundtrip_rows.csv`
- `load_resolver_visible_candidates.csv`
- `load_dedupe_lineage_rows.csv`
- `load_provenance_loss_by_stage.csv`
- `load_generated_resolver_review_items.csv`

All outputs are local-only. Safe fields include document alias, field, stage,
candidate id when already present, source, source family, parser name, pairing
method, page number, line index, bbox availability, candidate rank, stage
visibility flags, roundtrip status, loss stage, loss reason, and redaction
status.

## Local Commands

Standalone sidecar creation from existing local outputs:

```powershell
python scripts/create_ratecon_load_generated_resolver_provenance_sidecars.py `
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl `
  --legacy-output-dir .local_outputs/private_ratecon_measurement `
  --serialization-dir .local_outputs/ratecon_load_source_line_serialization_after_adapter_repair `
  --output-dir .local_outputs/ratecon_load_generated_resolver_provenance_sidecars `
  --confirm-private-local-run
```

Explicit private measurement opt-in, only when a private local measurement run
is already approved:

```powershell
python scripts/run_private_ratecon_measurement.py `
  --input-dir .local_outputs/private_ratecon_input `
  --output-dir .local_outputs/private_ratecon_measurement `
  --confirm-private-local-run `
  --write-load-generated-resolver-provenance-sidecars
```

The second command is documentation only for this PR. Do not run private
measurement automatically.

## Readiness Impact

Current eval/audit-only artifacts cannot prove adapter improvement without
generated/resolver rows. When the sidecar reports
`current_like_eval_audit_only_unmeasurable`, roundtrip improvement remains
unmeasured at corpus level.

Future load behavior experiments remain blocked until sidecars show actionable
source-line detail, the selected-load regression harness passes, and the
private selected-load aggregate gate passes. If generated candidates lack
detail, the next task is candidate provenance generation repair. If generated
candidates have detail but later rows lose it, the next task is exact boundary
repair at the reported stage.

## Current-Run Verification

`scripts/summarize_ratecon_load_generated_provenance_current_run.py` is the
local-only current-run evidence gate for these sidecars. It separates generated
rows being absent, generated rows being present but missing detail, and
generated rows being present with later provenance loss.

The current-run gate is reporting-only. It must not make readiness more
permissive unless generated rows, resolver-visible rows, a complete roundtrip,
and the existing selected-load gates are all present. When generated rows are
absent in an explicit sidecar-enabled measurement, the only allowed repair is
local-only generation-stage sidecar instrumentation.

## Later-Boundary Compare

`app/document_ai/load_identifier_generated_provenance_boundary.py` and
`scripts/compare_ratecon_load_generated_provenance_boundaries.py` compare the
stage rows produced by these sidecars with serialization/detail outputs. They
identify the first later boundary where already-existing generated provenance
stops being visible.

The generated/resolver sidecar writer accepts `--boundary-compare-dir` only as
an additive local summary input. It does not change sidecar row matching,
candidate generation, resolver behavior, selected output, or readiness gates.

## Adapter/Dedupe Stage Sidecars

The adapter/dedupe sidecar extension adds split outputs for
`load_adapter_input_candidates.csv`, `load_adapter_output_candidates.csv`,
`load_dedupe_input_candidates.csv`, `load_dedupe_output_candidates.csv`, and
`load_adapter_dedupe_loss_by_stage.csv`. The older combined
`load_adapter_roundtrip_rows.csv` and `load_dedupe_lineage_rows.csv` remain for
compatibility.

These rows are visibility only. They read or emit existing metadata, redact
values by default, and must not change generation, adapter, dedupe, resolver,
selected output, or evaluator metrics.
