# RateCon Load Adapter/Dedupe Stage Sidecars v1

## Scope

This PR adds local-only adapter and dedupe diagnostic sidecar visibility for
load-number provenance. It does not improve selected `load_number` output,
change extraction, change candidate generation decisions, change resolver
ranking/scoring, change table-neighbor or nearby-row pairing, change source
labels, change confidence values, change dedupe decisions, or change evaluator
statuses.

The sidecars exist because the generated-provenance later-boundary compare
reported `boundary_generation_to_adapter_loss` while adapter/dedupe diagnostic
stage rows were not visible. The new rows make that boundary measurable. They
do not infer missing page/line/source detail, fabricate new candidate ids, or
feed diagnostics back into resolver behavior.

## Local-Only Rows

The generated/resolver provenance sidecar now writes separate files for:

- `load_adapter_input_candidates.csv`
- `load_adapter_output_candidates.csv`
- `load_dedupe_input_candidates.csv`
- `load_dedupe_output_candidates.csv`
- `load_adapter_dedupe_loss_by_stage.csv`

The legacy combined outputs remain:

- `load_adapter_roundtrip_rows.csv`
- `load_dedupe_lineage_rows.csv`

Private values are redacted by default. The files are written only by explicit
local sidecar commands or the existing explicit private measurement sidecar
flag.

## Stage Statuses

Adapter/dedupe stage summaries report:

- `adapter_stage_complete`
- `adapter_stage_unavailable`
- `adapter_input_detail_available`
- `adapter_input_detail_missing`
- `adapter_output_detail_preserved`
- `adapter_output_detail_lost`
- `dedupe_stage_complete`
- `dedupe_stage_unavailable`
- `dedupe_input_detail_available`
- `dedupe_output_detail_preserved`
- `dedupe_output_detail_lost`
- `dedupe_merged_detail_preserved`
- `dedupe_dropped_detail_preserved`
- `dedupe_lineage_unavailable`
- `not_applicable_candidate_missing`
- `unknown`

These are additive diagnostics. They do not rename prior source-line,
serialization, generated/resolver, current-run, or boundary classifications.

## Boundary Use

When adapter/dedupe rows are available, the boundary comparator can distinguish:

- missing adapter stage visibility;
- adapter output detail loss;
- missing dedupe stage visibility;
- dedupe output detail loss;
- later dedupe-to-resolver loss.

When those rows are missing, the comparator preserves the prior unresolved
classification rather than inventing adapter or dedupe evidence.

## Readiness

Table-neighbor and nearby-row behavior experiments remain blocked until:

- generated rows are present;
- adapter input/output rows are present;
- dedupe input/output rows are present;
- resolver-visible rows are present;
- complete generated-to-sidecar roundtrip is actionable;
- selected-load regression harness passes;
- private selected-load aggregate gate passes;
- no private outputs are tracked.

The next cleanup should target the exact first loss boundary proven after
adapter/dedupe stage visibility exists. If adapter and dedupe rows are complete
but resolver rows lose detail, the next task is a dedupe-to-resolver diagnostic
boundary repair. If adapter input is still absent, the next task is adapter
stage emission repair, not extraction or resolver changes.

## Current-Run Verification

The follow-up current-run verification phase runs an explicit local private
diagnostic measurement with adapter/dedupe sidecars, then summarizes the
boundary result with
`scripts/summarize_ratecon_load_adapter_dedupe_current_run.py`. Diagnostics are
not experiment approval: if complete roundtrip remains missing, the next cleanup
must target the exact first proven loss boundary and must not change selected
load output.
