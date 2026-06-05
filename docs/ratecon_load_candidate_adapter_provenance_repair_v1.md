# RateCon Load Candidate Adapter Provenance Repair v1

This PR repairs local-only metadata preservation across load candidate adapter
boundaries. It does not improve selected `load_number` output, candidate
generation, resolver ranking/scoring, table-neighbor pairing, nearby-row
pairing, source labels, confidence values, evaluator statuses, extraction,
private measurement behavior, PDF processing, OCR, or model/cloud behavior.

## Scope

The observed local diagnostic baseline after the serialization repair showed
source-line detail present before diagnostics but dropped after generation:

- `complete_detail_serialized_count=0`
- `lost_after_generation_count=32`
- `lost_in_candidate_adapter=32`

This cleanup focuses on that adapter boundary only. It preserves already
existing candidate id, source, source family, parser name, page/line, bbox,
pairing method, and label/value/context availability metadata when those fields
are present on the incoming load candidate. It does not infer missing metadata,
fabricate candidate ids, derive page/line detail from private text, or feed any
new signal back into resolver selection.

`app/document_ai/field_candidate_provenance.py` remains the candidate adapter
boundary. `app/document_ai/load_identifier_candidate_adapter_provenance.py`
provides local-only helper functions for preserving and summarizing load
candidate provenance metadata. Resolver traces and serialization sidecars may
report that metadata for diagnostics, but resolver scoring and selected output
remain unchanged.

## Adapter Roundtrip Status

The local-only adapter roundtrip statuses are:

- `adapter_roundtrip_complete`
- `adapter_roundtrip_missing_input_detail`
- `adapter_roundtrip_preserved_partial_detail`
- `adapter_roundtrip_lost_candidate_id`
- `adapter_roundtrip_lost_page_line`
- `adapter_roundtrip_lost_source`
- `adapter_roundtrip_lost_pairing_method`
- `adapter_roundtrip_not_applicable`
- `adapter_roundtrip_unknown`

These statuses explain whether already-present metadata survived the adapter
boundary. They do not classify extraction correctness and do not change
diagnostic classifications from the source-line diagnostics, detail inventory,
or serialization repair phases.

## Local Commands

Static adapter provenance audit:

```powershell
python scripts/audit_ratecon_load_candidate_adapter_provenance.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_load_candidate_adapter_provenance_audit `
  --confirm-local-audit-run
```

Serialization sidecar after adapter repair:

```powershell
python scripts/create_ratecon_load_source_line_serialization.py `
  --eval-dir .local_outputs/private_ratecon_gold_eval `
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl `
  --output-dir .local_outputs/ratecon_load_source_line_serialization_after_adapter_repair `
  --confirm-private-local-run
```

Detail inventory with serialization sidecar:

```powershell
python scripts/create_ratecon_load_source_line_detail_inventory.py `
  --eval-dir .local_outputs/private_ratecon_gold_eval `
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl `
  --diagnostics-dir .local_outputs/ratecon_load_source_line_diagnostics_current `
  --serialization-dir .local_outputs/ratecon_load_source_line_serialization_after_adapter_repair `
  --output-dir .local_outputs/ratecon_load_source_line_detail_inventory_after_adapter_repair `
  --confirm-private-local-run
```

These commands read existing local outputs only. They must not run private
measurement, process PDFs, run OCR, call Google/model/cloud services, edit gold
labels, or edit filled hybrid templates. Private values remain redacted by
default.

## Readiness Impact

Future table-neighbor or nearby-row experiments remain blocked until metadata
roundtrip is actionable and the selected-load regression harness and private
selected-load aggregate gate pass.

If metadata is still missing at adapter input, the next task is candidate
provenance generation repair. If metadata survives the adapter but is lost
later, the next task is the exact later-boundary serialization repair. This PR
does not approve behavior-changing load-number experiments or production
migration.

## Generated/Resolver Provenance Sidecars

`app/document_ai/load_identifier_generated_resolver_provenance.py` and
`scripts/create_ratecon_load_generated_resolver_provenance_sidecars.py` add the
next local-only measurement surface for this phase. They make generated,
adapter, dedupe, and resolver-visible provenance rows explicit so adapter
roundtrip can be measured during future opt-in local runs.

These sidecars do not infer missing metadata, fabricate candidate ids, change
resolver behavior, or change selected load output. Current eval/audit-only
artifacts can still be reported as unmeasurable when generated/resolver rows
are absent.

## Current-Run Verification

`docs/ratecon_load_generated_provenance_current_run_v1.md` adds the next
current-run evidence gate. It verifies whether an explicit sidecar-enabled
private measurement emits generated rows before deciding on later boundary
repair. If generated rows are present but complete roundtrip is still absent,
the next task must target the exact later loss boundary and must not change
selection, scoring, source labels, or candidate generation.
