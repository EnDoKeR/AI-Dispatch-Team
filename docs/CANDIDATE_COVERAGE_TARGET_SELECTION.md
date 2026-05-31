# Candidate Coverage Target Selection

This workflow chooses the next RateCon extraction hardening target from safe
candidate coverage counts. It is local-first and does not require Google sync
or credentials.

## Why This Exists

The first candidate coverage pass selected broker identity candidate generation.
That fix reduced broker-name candidate gaps, but the measured improvement was
modest. The correct response is not to switch strategies or stack unrelated
heuristics. The next target must come from the coverage stage data.

The previous datetime hardening block improved synthetic fixtures but did not
move the private corpus: span date resolved/missing stayed 8 / 21 and span time
resolved/missing stayed 10 / 19. That means broad datetime regex expansion is
not a valid default. Date work is selected only when the coverage records prove
that date evidence reaches the span pipeline but does not become a span field
candidate.

## Stage Meanings

- `line_feature_missing`: layout evidence did not become a useful line feature.
- `anchor_missing`: line features exist, but no stop anchor was detected.
- `span_missing`: anchors exist, but no stop span was built.
- `span_boundary_excluded_line`: the relevant line is outside the span bounds.
- `candidate_not_generated`: the audited stage exists, but no field candidate
  was emitted.
- `candidate_generated_but_not_normalized`: a span candidate exists, but no
  normalized stop field was created.
- `normalized_but_not_core_mapped`: normalized stop field exists, but top-level
  core field mapping did not receive it.
- `scope_filtered`: scope rules filtered the field or document.
- `policy_excluded`: policy correctly excluded optional, review-only, or
  dispatch-only fields from intake-core blockers.

## Target Rules

Default candidate target is `stop_span_date_candidate_generation`, but only when
pickup or delivery date gaps have `candidate_not_generated` records at the
`span_field_candidate` stage. That proves layout/anchor/span evidence exists and
the loss happens when span field candidates are generated.

Fallback targets:

- `load_identifier_candidate_generation` when load/order/pro/tender identifiers
  dominate candidate gaps.
- `stop_span_location_candidate_generation` when pickup/delivery location gaps
  reach spans but location candidates are missing.
- `normalized_stop_field_mapping` when candidates exist but normalized fields do
  not.
- `normalized_to_core_field_mapping` when normalized fields exist but core field
  rows do not.
- `rate_candidate_generation_or_resolution` when rate candidate or conflict
  counts dominate.
- `broker_identity_candidate_generation` follow-up only when broker-name gaps
  remain the strongest concrete count after prior guardrails.

If OCR-needed documents dominate, the selected outcome is `ocr_design_later`.
OCR is not implemented in this workflow.

## Non-Goals

This workflow does not run Google sync, add OCR or Vision, add cloud document AI,
create DispatchCases, call DecisionEngine, call Telegram, write Event Timeline
events, or claim production readiness.
