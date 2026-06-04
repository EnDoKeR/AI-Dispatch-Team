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
- `identifier_label_missing`: no load-identity label feature was found for the
  primary load identifier.
- `identifier_candidate_not_generated`: identifier label evidence exists, but
  no primary load identifier candidate was emitted.
- `only_non_primary_reference_found`: PO/BOL/pickup/delivery/customer/carrier
  references were found, but none should be promoted to `load_number`.

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
Production OCR is not implemented in this workflow. Optional local/shadow OCR
diagnostics exist elsewhere and remain disabled by default.

## Non-Goals

This workflow does not run Google sync, enable production OCR or Vision, add
cloud document AI, create DispatchCases, call DecisionEngine, call Telegram,
write Event Timeline events, or claim production readiness.

## Latest Local Result

The target selector confirmed `stop_span_date_candidate_generation` only after
coverage showed eight pickup/delivery date records at
`span_field_candidate/candidate_not_generated` across two aliases. The focused
fix added table-row date candidates for stop rows when line-based date
candidates are absent.

Safe delta after rerun:

- selected date `candidate_not_generated`: 8 -> 0;
- total `candidate_not_generated`: 22 -> 14;
- span date resolved/missing: 8 / 21 -> 10 / 19;
- true intake blockers: 53 -> 49;
- dispatch-decision blockers: 123 -> 119;
- readiness unchanged: `extraction_review_ready=14`, `not_ready=4`.

The third target was `load_identifier_candidate_generation`. The implementation
added typed load identifier contracts, label helpers, typed candidate
generation, load-number resolver mapping, load identifier coverage counters, and
review workbook columns. Synthetic fixtures now cover load/order/tender/PRO/
freight-bill/shipment labels and non-primary PO/BOL/stop references.

Safe private delta after rerun:

- primary identifier candidates observed: 3;
- typed references observed: 11;
- rejected non-primary references: 11;
- load-number candidate gap: 7 -> 8 under the more specific taxonomy;
- total candidate gap count stayed 14;
- load-number intake blockers: 7 -> 9;
- readiness unchanged: `extraction_review_ready=14`, `not_ready=4`;
- next selected target remains `load_identifier_candidate_generation`.

The load identifier block improved diagnostics, but not the private corpus. The
next load-identifier pass should audit section/label coverage for missing
identifier features before adding broader regexes.

The follow-up load identifier audit selected
`generic_header_reference_review_candidate` from the unknown/non-primary
reference bucket and added a constrained fix for generic header/load-context
reference labels. Synthetic coverage improved, but the private rerun stayed
flat: primary identifier candidates 3, typed references 11, rejected
non-primary references 11, core mappings 1, and readiness unchanged. The target
selector still returns `load_identifier_candidate_generation`; the next specific
work should inspect whether identifier-like source lines and load-identity
sections are present before extending label rules again.

That source-line inspection has now run. It found no shared code-fixable load
identifier root cause: 96 identifier-like source lines were counted, but only
11 were in header/load-identity sections, and root causes split across unknown,
OCR/weak text, absent source lines, only non-primary references, and correctly
non-primary labels. Because `fix_allowed=false`, the selector result should be
treated as a broad remaining blocker, not permission to add another generic
load-number rule.

The target disposition registry now records
`load_identifier_candidate_generation` as `no_shared_code_root_cause` for the
current evidence set. With deferred targets excluded, candidate coverage target
selection moves to `rate_candidate_generation_or_resolution`. The first rate
forensics block selected `rate_source_priority_guardrails`, improved typed
main-rate candidate visibility, and reduced the accessorial/main-rate root
cause, but readiness stayed unchanged. The next selectable rate target is
`multiple_strong_totals` / review routing, not another load-id or generic
datetime patch.

The deeper rate conflict audit then split that broad rate target. It found no
safe arbitration fix: equivalent same-amount groups were zero,
`multiple_different_strong_totals` affected only two aliases, and remaining
conflict reasons were split across accessorial residuals, TONU context, and
unknown cases. The target selector may still point at rate broadly, but the
current rate-specific decision gate says local human review is the next action
unless new safe evidence creates a shared code-fixable root cause.
