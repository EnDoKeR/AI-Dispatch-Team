# RateCon Load Source-Line Detail Enrichment v1

This PR enriches local diagnostics only. It does not improve selected
`load_number` output, candidate generation, resolver ranking/scoring,
table-neighbor pairing, nearby-row pairing, source labels, confidence values,
schemas, evaluator statuses, extraction, private measurement behavior, PDF
processing, OCR, or model/cloud behavior.

## Scope

`app/document_ai/load_identifier_source_line_detail.py` normalizes already
available evaluation, audit, and diagnostic metadata into safe local-only detail
rows. `scripts/create_ratecon_load_source_line_detail_inventory.py` reads
existing local artifacts and writes a redacted detail inventory under
`.local_outputs/`.

The sidecar answers whether selected and candidate load-number rows have a
candidate id, source, page/line metadata, pairing method, label context, value
context, and neighboring context. It also reports where detail appears to be
missing between candidate/audit/evaluator/diagnostic surfaces.

Private selected, gold, and candidate values are redacted by default. They may
only be included with `--include-private-values-local-only` and
`--confirm-private-local-run`.

## Detail-Loss Buckets

The local-only detail-loss buckets include:

- `candidate_has_complete_source_detail`
- `candidate_missing_candidate_id`
- `candidate_missing_page_line`
- `candidate_missing_source`
- `candidate_missing_pairing_method`
- `candidate_missing_label_context`
- `candidate_missing_value_context`
- `candidate_detail_dropped_before_resolver`
- `candidate_detail_dropped_in_resolver_trace`
- `candidate_detail_dropped_before_audit`
- `candidate_detail_missing_from_evaluator`
- `diagnostic_detail_unavailable`
- `private_values_required_for_value_comparison`
- `detail_not_applicable_missing_candidate`
- `unknown`

These buckets explain diagnostic evidence availability. They do not classify
extraction correctness and do not feed back into resolver selection.

## Local Command

```powershell
python scripts/create_ratecon_load_source_line_detail_inventory.py `
  --eval-dir .local_outputs/private_ratecon_gold_eval `
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl `
  --diagnostics-dir .local_outputs/ratecon_load_source_line_diagnostics_current `
  --output-dir .local_outputs/ratecon_load_source_line_detail_inventory `
  --confirm-private-local-run
```

The script reads existing local eval/audit/diagnostic outputs only. It must not
run private measurement, process PDFs, run OCR, call Google/model/cloud
services, edit gold labels, or edit templates.

## Closeout Input

`scripts/summarize_ratecon_load_source_line_diagnostics_closeout.py` accepts an
optional `--detail-inventory-dir`. When present, the closeout includes complete
detail counts, missing page/line counts, missing source counts, dropped-detail
counts, unknown-caused-by-missing-detail counts, and a readiness recommendation.

The detail inventory can only make readiness stricter. If missing page/line,
missing source, or unknown-caused-by-missing-detail dominates, future
table-neighbor or nearby-row experiments remain blocked.

## Future Work

Future behavior experiments require:

1. selected-load regression harness;
2. private selected-load aggregate gate;
3. source-line diagnostics;
4. detail inventory;
5. closeout readiness.

If detail remains missing, the next task is audit/eval serialization repair,
not table-neighbor or nearby-row behavior changes.

## Serialization Sidecar

`app/document_ai/load_identifier_source_line_serialization.py` and
`scripts/create_ratecon_load_source_line_serialization.py` add an optional
local-only serialization sidecar for this detail inventory. When
`--serialization-dir` is supplied, the detail inventory can include
`serialization_loss_stage`, `serialization_loss_reason`, and
`source_detail_roundtrip_status` columns. The sidecar explains whether
candidate id, source, page/line, and pairing metadata roundtripped across
generation, resolver trace, shadow audit, and evaluator surfaces.

Serialization repair is diagnostic-only. It does not infer missing page/line
metadata and does not change selected load output or resolver behavior.

## Adapter Roundtrip Detail

When the serialization sidecar includes adapter provenance fields, the detail
inventory reports `adapter_roundtrip_status`, `adapter_loss_reason`,
`adapter_detail_preserved_count`, and `adapter_detail_lost_count`. These fields
show whether already-present load candidate metadata survived the adapter
boundary. They are local-only diagnostics and do not make closeout readiness
more permissive.

## Generated/Resolver Provenance Detail

When a generated/resolver provenance sidecar is supplied with
`--generated-resolver-provenance-dir`, the detail inventory can include
`generated_resolver_roundtrip_status`, `generated_resolver_loss_stage`, and
`generated_resolver_loss_reason`. It can also summarize generated candidate
detail availability and resolver-visible detail availability.

This input explains whether current artifacts are measurable or only
eval/audit-level and unmeasurable. It remains local-only and redacted by
default.

## Current-Run Generated Provenance

The generated-provenance current-run summarizer is the next evidence gate after
generated/resolver sidecars. It records whether generated rows are absent,
present but missing detail, or present with later loss. If later loss remains,
the next task is a boundary-specific serialization repair, not a table-neighbor
or nearby-row behavior change.

## Later-Boundary Compare

The detail inventory can consume boundary compare summaries through
`--boundary-compare-dir`. Boundary fields explain whether generated provenance
detail is still blocked after generation, adapter, dedupe, resolver, audit,
evaluator, or sidecar serialization. This input is local-only and can only keep
future behavior experiments blocked until complete roundtrip is proven.

## Adapter/Dedupe Stage Sidecars

Generated/resolver sidecars also expose adapter input/output and dedupe
input/output counts. The detail inventory reports these only as local evidence
for missing-detail attribution; it does not approve behavior experiments or
change selected load output.

## Adapter/Dedupe Current-Run Verification

The adapter/dedupe current-run closeout is an additional detail prerequisite.
Candidate-not-comparable, stage-unavailable, or missing complete roundtrip
evidence keeps table-neighbor and nearby-row experiments blocked.
