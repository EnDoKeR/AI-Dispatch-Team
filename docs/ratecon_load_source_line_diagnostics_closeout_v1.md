# RateCon Load Source-Line Diagnostics Closeout v1

This closeout is reporting-only. It does not improve `load_number` extraction,
candidate generation, resolver ranking/scoring, table-neighbor pairing,
nearby-row pairing, source labels, confidence values, schemas, evaluator
statuses, private measurement behavior, PDF processing, OCR, or model/cloud
behavior.

## Purpose

The closeout decides whether the local source-line diagnostics are actionable
enough for a future load evidence experiment. It summarizes diagnostic bucket
coverage, required gates, known debt, missing evidence, and readiness status.

It does not approve production migration. It does not approve a behavior
change. It does not approve table-neighbor or nearby-row ranking changes.

## Readiness Statuses

The closeout script reports one of these statuses:

- `load_source_line_diagnostics_closed_actionable`
- `load_source_line_diagnostics_closed_with_known_debt`
- `load_source_line_diagnostics_incomplete_detail_unavailable`
- `load_source_line_diagnostics_failed_required_gate`
- `load_source_line_diagnostics_private_baseline_skipped`
- `load_source_line_diagnostics_not_ready_for_experiment`

When source-line details are mostly unavailable, or the `unknown` bucket
dominates, the closeout must mark the phase not ready for a behavior
experiment. That result is expected and should not be hidden.

## Required Gates

Before any table-neighbor or nearby-row evidence-quality experiment, run:

1. the selected-load regression harness;
2. the private selected-load aggregate gate;
3. load source-line diagnostics over existing local outputs;
4. the load source-line detail inventory when available;
5. the closeout summarizer.

Expected-failure aggregate fixtures must still fail. Same-output aggregate
fixtures must still pass. Private values remain local-only and redacted by
default.

## Local Command

```powershell
python scripts/summarize_ratecon_load_source_line_diagnostics_closeout.py `
  --diagnostics-dir .local_outputs/ratecon_load_source_line_diagnostics_current `
  --ownership-audit-dir .local_outputs/ratecon_load_identifier_ownership_audit `
  --source-line-audit-dir .local_outputs/ratecon_load_source_line_evidence_audit `
  --aggregate-gate-dir .local_outputs/ratecon_private_selected_load_aggregate_compare `
  --detail-inventory-dir .local_outputs/ratecon_load_source_line_detail_inventory_current `
  --output-dir .local_outputs/ratecon_load_source_line_diagnostics_closeout `
  --confirm-local-audit-run
```

The script reads existing local-only outputs if present, tolerates missing
optional audit inputs, writes only under `.local_outputs/`, and reports skipped
inputs. It must not run private measurement, process PDFs, run OCR, call
Google/model/cloud services, edit gold labels, or edit templates.

When `--detail-inventory-dir` is supplied, the closeout includes complete
detail, missing page/line, missing source, dropped-detail, and
unknown-caused-by-missing-detail counts. This optional input can only make
readiness stricter; it does not approve a behavior experiment.

If the detail inventory includes serialization sidecar data, the closeout also
reports serialization complete-detail counts and whether serialization loss
dominates. High serialization loss keeps experiment readiness blocked.

If the detail inventory includes adapter provenance roundtrip data, the
closeout also reports adapter-preserved and adapter-lost counts. Adapter loss is
a blocker for behavior experiments until the boundary is repaired and the
selected-load regression harness plus private selected-load aggregate gate pass.

If a generated/resolver provenance sidecar is supplied, the closeout also
reports generated candidate detail availability, resolver-visible detail
availability, generated/resolver loss stage, and whether current artifacts are
measurable. Eval/audit-only unmeasurable artifacts keep behavior experiments
blocked.

## Known Debt

Known debt remains pinned:

- table-neighbor wrong cell;
- nearby-row wrong pair;
- footer/barcode noise;
- PO, PRO, BOL, and reference-number competition;
- ambiguous multiple load identifiers;
- missing source-line or page-line evidence;
- unknown/detail-unavailable local diagnostics.
- missing source-line detail between candidate/audit/evaluator/diagnostic
  surfaces.
- missing or dropped serialization of candidate id, source, page/line, and
  pairing metadata across local diagnostic surfaces.
- adapter-boundary loss of already-existing load candidate provenance metadata.
- missing generated/resolver provenance sidecars, which leaves corpus-level
  adapter improvement unmeasurable from eval/audit-only outputs.
- generated rows present without complete generated/resolver roundtrip, which
  blocks table-neighbor and nearby-row behavior experiments until the later
  loss boundary is repaired.

Future behavior changes must be shadow-only first and require explicit review
of selected-load regression output, private aggregate gate output, diagnostic
coverage, and metric deltas.
