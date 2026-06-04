# RateCon Rate-Ranking Penalty Ownership v1

This note documents current ownership for RateCon `total_carrier_rate`
resolver ranking, penalty, demotion, abstention, and not-selected trace
behavior. It is behavior-preserving only. It does not change selected rate
output, resolver scoring, thresholds, penalty values, candidate generation,
money-context labels, source names, confidence values, schemas, taxonomy, or
forensics mappings.

## Canonical Owner

`app/document_ai/field_candidate_resolver.py` currently owns selected-rate
ranking behavior. That includes the rate ranking profile name, score
calculation, source boost application, label adjustment, profile adjustment
values, demotion/abstention penalties, and resolver not-selected trace fields.

`app/document_ai/ratecon_rate_money_safety.py` owns money-context taxonomy,
accessorial/noise taxonomy, total-pay taxonomy, money-context classification,
and abstention metadata inputs. It does not own selected-rate ranking
decisions.

`app/document_ai/rate_candidate_forensics.py` and
`app/document_ai/rate_conflict_audit.py` report selected-rate outcomes,
diagnoses, and audit labels. They must not become owners for resolver ranking
penalties.

## Behavior Pinning

Current behavior is pinned by:

- `tests/test_ratecon_rate_ranking_penalty_pinning.py`
- `tests/test_ratecon_rate_ranking_penalty_ownership.py`
- `tests/test_ratecon_rate_ranking_penalty_guardrails.py`
- `tests/test_ratecon_selected_rate_regression_harness.py`
- `tests/test_compare_ratecon_private_selected_rate_aggregates.py`

Pinned behavior includes current boost/penalty values for total-carrier-pay,
total-rate, carrier-freight-pay, linehaul-total, line-item, deduction/fee,
payment-terms, per-unit, accessorial, abstained, weak-only, and
instructions/footer contexts. Known-debt selected-rate fixtures remain pinned,
not fixed.

No compatibility aliases were added in this phase. The current ranking
adjustment literals remain inside `field_candidate_resolver.py`; moving them
into a separate policy module should be a future narrow cleanup only after this
pinning remains green.

## Required Gates

Before any future ranking penalty, scoring, selected-rate behavior, or resolver
profile change, run:

1. sanitized selected-rate regression harness;
2. private aggregate selected-rate comparison gate;
3. full private gold evaluation only when explicitly requested.

The local private aggregate gate is a regression gate, not a correctness
certification. It must remain redacted by default and must not process PDFs,
run OCR, call Google, call model/cloud services, or create private evaluation
outputs.

## Future Cleanup Targets

Future behavior-preserving targets can include:

- centralize named penalty constants inside `field_candidate_resolver.py` or a
  dedicated `ratecon_rate_ranking_policy.py` module;
- isolate score explanation traces;
- improve forensics diagnosis ownership;
- capture private aggregate baselines before any experimental ranking profile;
- only later consider behavior-changing ranking experiments under an explicit
  experiment profile.

Do not lower thresholds, change score calculations, change selected output,
auto-accept shadow rates, or use private gold labels as runtime truth as part
of ownership cleanup.
