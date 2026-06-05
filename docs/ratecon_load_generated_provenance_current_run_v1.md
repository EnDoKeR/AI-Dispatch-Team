# RateCon Load Generated Provenance Current Run v1

## Scope

This PR verifies generated/resolver load provenance on an explicit local current
run and adds a local-only current-run evidence summarizer. It does not improve
selected `load_number` output, change extraction, change candidate generation
decisions, change resolver ranking/scoring, change table-neighbor or nearby-row
pairing, change source labels, change confidence values, or change evaluator
statuses.

Private values remain redacted by default. Local current-run outputs must stay
under `.local_outputs/` and must not be committed.

## Current-Run Statuses

The current-run summarizer reports one of these statuses:

- `current_run_full_roundtrip_measurable`
- `current_run_partial_roundtrip_measurable`
- `current_run_generated_rows_absent`
- `current_run_generated_rows_present_missing_detail`
- `current_run_generated_rows_present_detail_lost_later`
- `current_run_eval_audit_only_unmeasurable`
- `current_run_private_inputs_unavailable`
- `current_run_gate_failed`
- `current_run_unknown`

The status distinguishes absent generated rows from generated rows that lack
detail at generation and generated rows whose detail is lost later. It does not
classify extraction correctness and does not approve load-ranking behavior
changes.

## Generation-Stage Sidecar Instrumentation

If an explicit sidecar-enabled measurement still has no generated rows, the
allowed instrumentation is limited to local-only sidecar emission. Generated
records may copy only metadata already present on debug load candidates:
candidate id if present, source, parser, page/line, pairing method, bbox
availability, and candidate rank.

The instrumentation must not infer missing page/line/source detail, fabricate
candidate ids, include candidate values by default, change generated candidates,
change resolver inputs, or change selected output.

## Local Commands

Current-run evidence summarizer:

```powershell
python scripts/summarize_ratecon_load_generated_provenance_current_run.py `
  --generated-resolver-sidecar-dir .local_outputs/ratecon_load_generated_resolver_provenance_sidecars_current_run `
  --detail-inventory-dir .local_outputs/ratecon_load_source_line_detail_inventory_current `
  --closeout-dir .local_outputs/ratecon_load_source_line_diagnostics_closeout_current `
  --output-dir .local_outputs/ratecon_load_generated_provenance_current_run_summary `
  --confirm-local-audit-run
```

The summarizer reads existing sidecar/detail/closeout outputs only. It does not
run private measurement, process PDFs, run OCR, call Google/model/cloud
services, edit gold labels, or edit templates.

## Readiness Decision

Table-neighbor and nearby-row behavior experiments remain blocked unless the
current run is actionable and the selected-load regression harness and private
selected-load aggregate gate pass.

If generated rows are absent, the next task is generation-stage sidecar
emission. If generated rows lack source-line detail, the next task is candidate
provenance generation repair. If generated rows have detail but complete
roundtrip is still absent, the next task is the exact later-boundary repair
reported by the sidecar.

This closeout does not approve production migration and does not approve an
experimental ranking profile by itself.

## Later-Boundary Compare

`scripts/compare_ratecon_load_generated_provenance_boundaries.py` adds the
next local-only gate for current runs where generated rows exist but complete
roundtrip is still missing. It compares generated, adapter, dedupe, resolver,
audit, evaluator, and sidecar rows and reports the first unavailable boundary.

The current-run summarizer can consume `--boundary-compare-dir` additively. A
boundary compare result can only block readiness; it does not approve
table-neighbor or nearby-row behavior changes.
