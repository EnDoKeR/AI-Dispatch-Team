# RateCon Load Generated Provenance Later-Boundary Repair v1

## Scope

This PR identifies the exact later boundary where generated load provenance
detail stops being visible in local-only diagnostics. It does not improve
selected `load_number` output, change extraction, change candidate generation
decisions, change resolver ranking/scoring, change table-neighbor or nearby-row
pairing, change source labels, change confidence values, or change evaluator
statuses.

The boundary compare is reporting-only. It preserves and compares only
already-existing generated candidate detail. It must not infer missing
page/line/source detail, fabricate candidate ids, or feed diagnostic results
back into resolver selection.

## Boundary Statuses

The local-only boundary compare reports one of these statuses:

- `boundary_generation_to_adapter_loss`
- `boundary_adapter_to_dedupe_loss`
- `boundary_dedupe_to_resolver_loss`
- `boundary_resolver_to_audit_loss`
- `boundary_audit_to_evaluator_loss`
- `boundary_evaluator_to_sidecar_loss`
- `boundary_no_loss_complete_roundtrip`
- `boundary_input_detail_missing`
- `boundary_candidate_not_comparable`
- `boundary_stage_unavailable`
- `boundary_private_values_not_requested`
- `boundary_unknown`

These statuses are additive diagnostics. They do not rename earlier detail-loss,
serialization-loss, adapter-roundtrip, or generated/resolver classifications.

## Local Commands

Static audit:

```powershell
python scripts/audit_ratecon_load_generated_provenance_later_boundary.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_load_generated_provenance_later_boundary_audit `
  --confirm-local-audit-run
```

Boundary comparison:

```powershell
python scripts/compare_ratecon_load_generated_provenance_boundaries.py `
  --generated-resolver-sidecar-dir .local_outputs/ratecon_load_generated_resolver_provenance_sidecars_current_run `
  --serialization-dir .local_outputs/ratecon_load_source_line_serialization_after_current_run `
  --detail-inventory-dir .local_outputs/ratecon_load_source_line_detail_inventory_current `
  --output-dir .local_outputs/ratecon_load_generated_provenance_boundary_compare `
  --confirm-local-audit-run
```

Both tools write only under `.local_outputs/`. They do not run private
measurement, process PDFs, run OCR, call Google/model/cloud services, edit gold
labels, or edit templates.

## Current Decision

Current evidence after the generated-provenance current-run phase showed
generated rows present but complete generated/resolver roundtrip missing. The
later-boundary compare narrows that to the first missing diagnostic stage rather
than changing generation, adapter, dedupe, resolver, audit, or evaluator
behavior.

This PR implements the boundary comparator and audit only. It does not repair a
runtime candidate/resolver boundary because the available local current-run
artifacts show missing adapter/dedupe diagnostic stage rows, and synthesizing
those rows would overstate evidence. The next repair must target that exact
diagnostic stage emission boundary without changing selected output.

If a safe exact repair is available, it may preserve only already-existing
metadata across that one boundary. If the missing stage cannot be repaired
without changing resolver traces, selected output, candidate generation, or
primary schemas, the repair must be deferred and documented.

## Readiness

Future table-neighbor or nearby-row behavior experiments remain blocked until:

- generated rows are present;
- resolver-visible rows are present;
- complete generated-to-sidecar roundtrip is actionable;
- selected-load regression harness passes;
- private selected-load aggregate gate passes;
- no private outputs are tracked.

This PR does not approve production migration, load ranking changes, or
table/nearby-row behavior changes.
