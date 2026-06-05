# RateCon Load Resolver-to-Audit Provenance Repair v1

## Scope

This PR targets the proven resolver-to-audit provenance loss boundary. It does
not improve selected `load_number` output, change extraction, change adapter
behavior, change dedupe decisions, change resolver ranking/scoring, change
resolver thresholds, change source labels, change confidence values, or change
evaluator statuses.

The repair preserves only already-existing resolver-visible metadata into
local-only audit diagnostic sidecars. It does not infer missing metadata,
fabricate candidate IDs, process PDFs, run OCR, call Google/model/cloud
services, edit gold labels, or run private measurement by default.

## Current Evidence

PR #82 made generated, adapter, dedupe, and resolver rows visible on a fresh
explicit local diagnostic run. The first proven boundary remained:

- `boundary_resolver_to_audit_loss`

The resolver-to-audit sidecar compares resolver-visible candidates with audit
diagnostic rows and reports whether candidate ID, source, page/line,
pairing-method, bbox, and selected-flag detail survived into local audit
diagnostics.

## Local Commands

Static ownership audit:

```powershell
python scripts/audit_ratecon_load_resolver_to_audit_provenance.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_load_resolver_to_audit_provenance_audit `
  --confirm-local-audit-run
```

Resolver-to-audit sidecar:

```powershell
python scripts/create_ratecon_load_resolver_to_audit_provenance_sidecar.py `
  --generated-resolver-sidecar-dir .local_outputs\ratecon_load_generated_resolver_provenance_sidecars_adapter_dedupe_current_run `
  --audit .local_outputs\private_ratecon_measurement_adapter_dedupe_current_run\ratecon_shadow_document_pipeline_audit.jsonl `
  --output-dir .local_outputs\ratecon_load_resolver_to_audit_provenance_sidecar `
  --confirm-private-local-run
```

Boundary compare with resolver-to-audit sidecar:

```powershell
python scripts/compare_ratecon_load_generated_provenance_boundaries.py `
  --generated-resolver-sidecar-dir .local_outputs\ratecon_load_generated_resolver_provenance_sidecars_adapter_dedupe_current_run `
  --resolver-to-audit-sidecar-dir .local_outputs\ratecon_load_resolver_to_audit_provenance_sidecar `
  --output-dir .local_outputs\ratecon_load_generated_provenance_boundary_compare_resolver_to_audit `
  --confirm-local-audit-run
```

All outputs remain local-only and ignored. Private values are redacted by
default.

## Statuses

The sidecar reports stable statuses:

- `resolver_to_audit_preserved`
- `resolver_to_audit_missing_audit_row`
- `resolver_to_audit_candidate_id_lost`
- `resolver_to_audit_source_lost`
- `resolver_to_audit_page_line_lost`
- `resolver_to_audit_pairing_method_lost`
- `resolver_to_audit_bbox_lost`
- `resolver_to_audit_selected_flag_lost`
- `resolver_to_audit_stage_unavailable`
- `resolver_to_audit_candidate_not_comparable`
- `resolver_to_audit_private_values_not_requested`
- `resolver_to_audit_unknown`

Only rows classified as preserved may count as audit-stage rows in the boundary
comparator. Missing audit rows, field-loss rows, stage-unavailable rows, and
candidate-not-comparable rows remain blocking evidence.

## Next Decision

If resolver-to-audit preservation is proven but complete roundtrip is still
absent, the next task is audit-to-evaluator diagnostic preservation. If
resolver-visible rows lack the needed detail, the next task is resolver trace
sidecar preservation.

Future table-neighbor or nearby-row behavior experiments remain blocked until
complete roundtrip and selected-load gates are actionable.
