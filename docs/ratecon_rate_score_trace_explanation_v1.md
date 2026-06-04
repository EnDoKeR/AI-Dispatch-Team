# RateCon Rate Score Trace Explanation v1

This note documents current ownership for RateCon selected-rate score trace and
explanation output. It is behavior-preserving only. It does not change selected
rate output, resolver scoring, thresholds, penalty values, reason strings,
metrics, candidate generation, extraction, money-context labels, source names,
confidence values, schemas, or rate/money taxonomy.

## Canonical Owner

`app/document_ai/field_candidate_resolver.py` currently owns selected-rate
scoring and trace construction. That includes score calculation,
`ranking_adjustment_total`, `ranking_adjustments`, selected candidate trace
serialization, not-selected reason assignment, resolver decision status, and
review-gate trace construction.

Score traces explain current resolver decisions. They do not define scoring
behavior independently and must not become a second place for score
calculation, penalty values, demotion rules, or abstention decisions.

`app/document_ai/ratecon_rate_money_safety.py` owns taxonomy and classifier
inputs used by the resolver, including total-pay labels, accessorial/noise
labels, money-context classification, and rate-safety metadata. It does not own
score trace semantics.

`app/document_ai/rate_candidate_forensics.py`,
`app/document_ai/rate_conflict_audit.py`,
`app/document_ai/ratecon_shadow_audit.py`, and
`app/document_ai/ratecon_shadow_root_cause_analysis.py` may consume resolver
trace output and summarize it. They should not invent competing score
explanations or selected-rate reason schemas.

Score traces explain resolver decisions. Selected-rate forensics diagnosis
mapping summarizes error categories separately. Diagnosis mapping may consume
trace, scoring, selected candidate, and money-context metadata, but it must not
change trace schemas, reason strings, selected-rate output, scoring, penalties,
thresholds, or money-context labels.

## Behavior Pinning

Current trace behavior is pinned by:

- `tests/test_ratecon_rate_score_trace_explanation.py`
- `tests/test_ratecon_rate_score_trace_guardrails.py`
- `tests/test_audit_ratecon_rate_score_trace_explanation.py`
- `tests/test_ratecon_rate_ranking_penalty_pinning.py`
- `tests/test_ratecon_selected_rate_regression_harness.py`
- `tests/test_compare_ratecon_private_selected_rate_aggregates.py`

Pinned behavior includes current ranking adjustment reason strings, adjustment
amount serialization, selected candidate trace fields, conflict not-selected
reason output, selected-rate fixture output, and local-only static audit
outputs. Known-debt selected-rate fixture behavior remains pinned, not fixed.

## Required Gates

Any future trace field, trace schema, explanation, ranking, scoring, or
selected-rate behavior change must run:

1. sanitized selected-rate regression harness;
2. sanitized selected-rate before/after snapshot comparison;
3. private aggregate selected-rate comparison gate;
4. full private gold evaluation only when explicitly requested.

Trace cleanup is not approval to change selected-rate behavior. Changes to
expected fixture output require explicit review and must not be hidden inside
ownership cleanup.

## Future Cleanup

A future behavior-preserving cleanup may create a dedicated trace serializer
only after behavior pinning stays green. That serializer may normalize or
redact existing trace dictionaries, but it must not move score calculations,
change reason strings, change penalty values, change selected output, or change
resolver thresholds.
