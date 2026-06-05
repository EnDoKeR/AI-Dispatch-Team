# RateCon Load Adapter/Dedupe Current-Run Verification v1

## Scope

This PR verifies adapter/dedupe provenance sidecars on a fresh explicit local
current run. It does not improve selected `load_number` output, change
extraction, change candidate generation, change resolver ranking/scoring,
change dedupe decisions, change table-neighbor or nearby-row pairing, change
source labels, change confidence values, or change evaluator statuses.

The closeout distinguishes true boundary loss from missing diagnostic stage
visibility. It reads existing local sidecar and boundary outputs only. It does
not run private measurement, process PDFs, run OCR, call Google/model/cloud
services, edit gold labels, or edit templates.

## Local Commands

Fresh explicit diagnostic measurement, when private inputs are present:

```powershell
python scripts/run_private_ratecon_measurement.py `
  --input-dir data\private_ratecons\originals `
  --confirm-private-local-run `
  --ratecon-shadow-document-pipeline `
  --write-ratecon-shadow-audit `
  --ratecon-shadow-layout-provider pdfplumber `
  --ratecon-shadow-table-profile default `
  --include-filenames-local-only `
  --include-file-hash-prefix-local-only `
  --include-document-ai-debug `
  --write-load-generated-resolver-provenance-sidecars `
  --output-dir .local_outputs\private_ratecon_measurement_adapter_dedupe_current_run `
  --allow-custom-output-dir
```

Sidecar rebuild and boundary compare:

```powershell
python scripts/create_ratecon_load_generated_resolver_provenance_sidecars.py `
  --audit .local_outputs\private_ratecon_measurement_adapter_dedupe_current_run\ratecon_shadow_document_pipeline_audit.jsonl `
  --legacy-output-dir .local_outputs\private_ratecon_measurement_adapter_dedupe_current_run `
  --output-dir .local_outputs\ratecon_load_generated_resolver_provenance_sidecars_adapter_dedupe_current_run `
  --confirm-private-local-run

python scripts/compare_ratecon_load_generated_provenance_boundaries.py `
  --generated-resolver-sidecar-dir .local_outputs\ratecon_load_generated_resolver_provenance_sidecars_adapter_dedupe_current_run `
  --output-dir .local_outputs\ratecon_load_generated_provenance_boundary_compare_adapter_dedupe_current_run `
  --confirm-local-audit-run
```

Current-run closeout:

```powershell
python scripts/summarize_ratecon_load_adapter_dedupe_current_run.py `
  --generated-resolver-sidecar-dir .local_outputs\ratecon_load_generated_resolver_provenance_sidecars_adapter_dedupe_current_run `
  --boundary-compare-dir .local_outputs\ratecon_load_generated_provenance_boundary_compare_adapter_dedupe_current_run `
  --output-dir .local_outputs\ratecon_load_adapter_dedupe_current_run_summary `
  --confirm-local-audit-run
```

All outputs remain local-only and ignored.

## Statuses

The closeout reports one stable status:

- `adapter_dedupe_current_run_full_roundtrip_measurable`
- `adapter_dedupe_current_run_generation_to_adapter_loss`
- `adapter_dedupe_current_run_adapter_to_dedupe_loss`
- `adapter_dedupe_current_run_dedupe_to_resolver_loss`
- `adapter_dedupe_current_run_resolver_to_audit_loss`
- `adapter_dedupe_current_run_audit_to_evaluator_loss`
- `adapter_dedupe_current_run_candidate_not_comparable`
- `adapter_dedupe_current_run_stage_unavailable`
- `adapter_dedupe_current_run_private_inputs_unavailable`
- `adapter_dedupe_current_run_unknown`

Full roundtrip requires generated rows, adapter input/output rows, dedupe
input/output rows, resolver-visible rows, and at least one complete roundtrip.
Candidate-not-comparable or stage-unavailable evidence blocks behavior
experiments.

## Current Decision

If the fresh current run proves adapter and dedupe rows exist but complete
roundtrip is still missing, the next cleanup must target the exact first proven
loss boundary. It must remain diagnostic-only unless a separately approved
shadow-only behavior experiment is created and gated.

Private values remain redacted by default. Table-neighbor and nearby-row
experiments remain blocked unless complete roundtrip and selected-load gates are
actionable.
