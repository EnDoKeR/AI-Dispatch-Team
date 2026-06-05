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
