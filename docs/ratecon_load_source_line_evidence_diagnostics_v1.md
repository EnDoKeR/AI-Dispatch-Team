# RateCon Load Source-Line Evidence Diagnostics v1

This PR is diagnostics-only. It does not improve selected load-number output,
candidate generation, resolver ranking/scoring, source labels, confidence
values, schemas, evaluator statuses, private measurement behavior, extraction,
PDF processing, OCR, or model/cloud behavior.

## Scope

The source-line/evidence diagnostics classify current load-number evidence
quality failures. They answer whether selected `load_number` evidence appears
near the right label or row, whether a better candidate was present but not
selected, whether the gold value was absent from candidates, and whether
table-neighbor, nearby-row, footer/barcode, PO, PRO, BOL, or generic reference
noise competed with the real load number.

Diagnostics are local-only and reporting-only. They do not feed back into
resolver selection, scoring, thresholds, candidate generation, or evaluator
status strings.

## Ownership Boundaries

`app/document_ai/load_identifier_candidates.py` remains the intended canonical
owner for load identifier candidate taxonomy and policy.

`app/document_ai/field_candidate_resolver.py` and the legacy
`app/document_ai/ratecon_field_resolution.py` remain selected-value owners.

`app/document_ai/load_identifier_source_line_audit.py` owns safe source-line
count/category audit helpers. `scripts/create_ratecon_load_source_line_diagnostics.py`
consumes existing eval/audit artifacts and reports local-only diagnostic
buckets. It must not invent selected-value behavior or change production
outputs.

Table-neighbor and nearby-row behavior is pinned, not fixed.

## Diagnostic Buckets

The local-only diagnostic buckets include:

- `selected_table_neighbor_wrong_cell`
- `selected_nearby_row_wrong_pair`
- `selected_footer_or_barcode_noise`
- `selected_reference_number_noise`
- `selected_po_number_noise`
- `selected_pro_number_noise`
- `selected_bol_number_noise`
- `gold_not_in_candidates`
- `gold_in_candidates_not_selected`
- `candidate_source_line_unavailable`
- `candidate_page_line_unavailable`
- `ambiguous_multiple_load_ids`
- `duplicate_same_value_candidates`
- `layout_ordering_ambiguous`
- `text_extraction_ordering_ambiguous`
- `evaluator_detail_unavailable`
- `gold_uncertain_or_review_required`
- `unknown`

These buckets are additive diagnostics only. Existing evaluator error status
strings remain unchanged.

## Local Commands

Static source-line/evidence inventory:

```powershell
python scripts/audit_ratecon_load_source_line_evidence.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_load_source_line_evidence_audit `
  --confirm-local-audit-run
```

Local-only diagnostics over existing private outputs:

```powershell
python scripts/create_ratecon_load_source_line_diagnostics.py `
  --eval-dir .local_outputs/private_ratecon_gold_eval `
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl `
  --output-dir .local_outputs/ratecon_load_source_line_diagnostics `
  --confirm-private-local-run
```

The diagnostics command redacts selected and gold values by default. Private
values can only be included with `--include-private-values-local-only` and an
explicit private-local confirmation.

## Future Behavior Changes

Future behavior changes require:

1. the selected-load regression harness;
2. the private selected-load aggregate gate;
3. private full-corpus evaluation only when explicitly requested.

Known debt remains table-neighbor wrong cell, nearby-row wrong pair, noisy
references, footer/barcode noise, and ambiguous competing load identifiers.
This PR does not approve fixing those behaviors.
