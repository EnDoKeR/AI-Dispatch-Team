# RateCon Load Source-Line Serialization Repair v1

This PR repairs local-only diagnostic serialization only. It does not improve
selected `load_number` output, candidate generation, resolver ranking/scoring,
table-neighbor pairing, nearby-row pairing, source labels, confidence values,
schemas, evaluator statuses, extraction behavior, private measurement behavior,
PDF processing, OCR, or model/cloud behavior.

## Scope

`app/document_ai/load_identifier_source_line_serialization.py` converts already
existing generated-candidate, resolver-trace, audit, and evaluator metadata into
safe diagnostic sidecar rows. It preserves candidate id, source, page/line, and
pairing method when those fields already exist. It does not infer missing
page/line data, invent pairing methods, or feed any signal back into selection.

`scripts/create_ratecon_load_source_line_serialization.py` reads existing local
artifacts and writes redacted sidecar outputs under `.local_outputs/`. Private
candidate/selected/gold values are redacted by default and can only be included
with `--include-private-values-local-only` plus `--confirm-private-local-run`.

`scripts/audit_ratecon_load_source_line_serialization.py` statically inventories
serialization boundaries. It uses AST/text analysis only and does not import or
execute project modules.

## Serialization-Loss Buckets

The local-only serialization-loss buckets are:

- `complete_detail_serialized`
- `missing_candidate_id_at_generation`
- `missing_page_line_at_generation`
- `missing_source_at_generation`
- `missing_pairing_method_at_generation`
- `lost_in_candidate_adapter`
- `lost_in_dedupe`
- `lost_in_resolver_trace`
- `lost_in_shadow_audit`
- `lost_in_gold_evaluator`
- `lost_in_detail_inventory_reader`
- `private_values_not_requested`
- `not_applicable_candidate_missing`
- `unknown`

These buckets explain where diagnostic detail is missing. They do not classify
extraction correctness and do not change PR #73 diagnostic classifications or
PR #75 detail-loss bucket names.

## Sidecar Outputs

The serialization command writes:

- `load_source_line_serialization_summary.json`
- `load_source_line_serialization_report.md`
- `load_source_line_serialization_rows.csv`

The rows are additive local-only diagnostics. They include fields such as
`candidate_id`, `source`, `pairing_method`, `page_number`, `line_index`,
`resolver_seen`, `audit_serialized`, `evaluator_serialized`,
`serialization_loss_bucket`, `detail_loss_stage`, and
`source_detail_roundtrip_status`.

## Local Commands

Static serialization audit:

```powershell
python scripts/audit_ratecon_load_source_line_serialization.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_load_source_line_serialization_audit `
  --confirm-local-audit-run
```

Local-only serialization sidecar:

```powershell
python scripts/create_ratecon_load_source_line_serialization.py `
  --generated-candidates .local_outputs/ratecon_load_source_line_generated_candidates.csv `
  --resolver-trace .local_outputs/ratecon_load_source_line_resolver_trace.csv `
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl `
  --eval-dir .local_outputs/private_ratecon_gold_eval `
  --output-dir .local_outputs/ratecon_load_source_line_serialization `
  --confirm-private-local-run
```

Detail inventory with serialization sidecar:

```powershell
python scripts/create_ratecon_load_source_line_detail_inventory.py `
  --eval-dir .local_outputs/private_ratecon_gold_eval `
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl `
  --diagnostics-dir .local_outputs/ratecon_load_source_line_diagnostics_current `
  --serialization-dir .local_outputs/ratecon_load_source_line_serialization `
  --output-dir .local_outputs/ratecon_load_source_line_detail_inventory `
  --confirm-private-local-run
```

These commands read existing local outputs only. They must not run private
measurement, process PDFs, run OCR, call Google/model/cloud services, edit gold
labels, or edit filled hybrid templates.

## Readiness Impact

The detail inventory and closeout summarizer now consume serialization sidecar
metadata when it is present. Serialization detail can only make readiness
stricter. If the sidecar shows detail is missing at generation, the next task is
candidate provenance repair. If detail is present at generation but lost later,
the next task is repairing the specific serialization boundary. Table-neighbor
or nearby-row behavior experiments remain blocked until source-line detail
roundtrip is actionable.

## Adapter Provenance Repair

`app/document_ai/load_identifier_candidate_adapter_provenance.py` and
`scripts/audit_ratecon_load_candidate_adapter_provenance.py` narrow the next
serialization repair target to the candidate adapter boundary. They preserve and
audit already-existing candidate id, source, page/line, bbox, and pairing
metadata across adaptation without inferring missing detail or changing
resolver behavior. Serialization sidecar rows may report adapter roundtrip
status, but those fields remain local-only diagnostics.

## Generated/Resolver Sidecar Integration

`scripts/create_ratecon_load_source_line_serialization.py` can consume an
optional `--generated-resolver-provenance-dir`. When present, serialization
reports include generated/resolver roundtrip status, loss stage, loss reason,
generated candidate detail availability, and resolver-visible detail
availability.

This sidecar input is additive. It can improve loss-stage attribution, but it
does not make readiness more permissive, change diagnostic classifications, or
change selected load behavior.

## Current-Run Generated Provenance

`scripts/summarize_ratecon_load_generated_provenance_current_run.py` consumes
generated/resolver sidecar summaries after an explicit local run. If generated
rows are present but complete roundtrip is absent, the next repair must target
the exact later boundary reported by `generated_resolver_loss_stage`. This
continues to be diagnostic-only and does not approve load selection changes.
