# RateCon Rate Forensics Diagnosis Mapping v1

This note documents current ownership for RateCon selected-rate forensics
diagnosis mappings. It is behavior-preserving only. It does not change selected
rate output, resolver scoring, thresholds, penalty values, trace schemas,
diagnosis strings, diagnosis counts, evaluator statuses, aggregate gate
behavior, candidate generation, extraction, money-context labels, source names,
confidence values, schemas, or rate/money taxonomy.

## Canonical Owner

`app/document_ai/rate_candidate_forensics.py` owns selected-rate forensics
diagnosis mapping documentation and the rate forensic category/source/conflict
reason contracts used by safe local summaries.

`app/document_ai/rate_conflict_audit.py` owns audit summaries and conflict rows.
It must not become the canonical selected-rate diagnosis taxonomy owner.

`app/document_ai/ratecon_gold_labels.py` currently assigns residual selected
rate diagnosis strings during local evaluation. That is pinned current
implementation behavior and compatibility debt, not approval to add new
diagnosis categories there casually.

`scripts/evaluate_ratecon_against_gold.py` reports and writes diagnosis
outcomes. It should not own new diagnosis categories.

`scripts/compare_ratecon_private_selected_rate_aggregates.py` gates aggregate
selected-rate deltas. It should not invent new diagnosis categories.

`app/document_ai/field_candidate_resolver.py` owns selected-rate selection,
scoring, penalties, thresholds, and score trace output. It does not own
forensics diagnosis taxonomy.

`app/document_ai/ratecon_rate_money_safety.py` owns money taxonomy and
classifier inputs. It does not own forensics diagnosis taxonomy.

## Behavior Pinning

This PR changes no diagnosis strings or counts. Current diagnosis behavior is
pinned by:

- `tests/test_ratecon_rate_forensics_diagnosis_mapping.py`
- `tests/test_ratecon_rate_forensics_diagnosis_guardrails.py`
- `tests/test_audit_ratecon_rate_forensics_diagnosis_mapping.py`
- `tests/test_compare_ratecon_private_selected_rate_aggregates.py`
- `tests/test_ratecon_selected_rate_regression_harness.py`

Pinned behavior includes current selected-rate wrong reason counts, residual
wrong-rate diagnosis counts, high-confidence wrong counts, forensics category
labels, conflict-audit labels, aggregate gate diagnosis deltas, and redacted
safe summaries. Known-debt diagnoses remain pinned, not fixed.

## Required Gates

Any future diagnosis mapping, evaluator status, aggregate-delta, ranking,
scoring, trace, or selected-rate behavior change must run:

1. sanitized selected-rate regression harness;
2. sanitized selected-rate before/after snapshot comparison;
3. private aggregate selected-rate comparison gate;
4. explicit metric-delta review;
5. full private gold evaluation only when explicitly requested.

Changes to expected selected-rate fixture output, diagnosis strings, diagnosis
counts, evaluator statuses, or aggregate gate pass/fail semantics require
explicit compatibility review and must not be hidden inside ownership cleanup.

## Future Cleanup

A future behavior-preserving cleanup may move evaluator-side residual diagnosis
assignment behind a dedicated forensics-owned accessor after the existing
diagnosis strings and counts stay pinned. That cleanup must preserve existing
strings, grouping, output schemas, selected-rate behavior, metrics, and
redaction behavior exactly.
