# RateCon Rate/Money Safety Ownership v1

This note defines ownership for RateCon total-carrier-rate and money-context
safety logic. It is a behavior-preserving audit and guardrail artifact only. It
does not change extraction behavior, resolver scoring, resolver thresholds,
selected rate output, candidate schemas, source names, confidence values, field
names, money context labels, or rate ranking behavior.

## Canonical Owner

`app/document_ai/ratecon_rate_money_safety.py` is the intended canonical owner
for RateCon money-context safety taxonomy. New total-carrier-pay,
accessorial/noise, deduction, quick-pay, fuel-advance, payment-terms,
line-item, and total-vs-line-item safety policy must be coordinated there or in
an explicitly documented support-policy module.

The total-pay/main-rate label taxonomy is centralized in
`app/document_ai/ratecon_rate_money_safety.py`. Compatibility aliases preserve
the existing resolver and legacy generator constant names and values. This does
not change selected rate output, resolver ranking behavior, candidate source
names, confidence values, field names, or output schemas.

The accessorial/noise/fee/penalty label taxonomy is also centralized in
`app/document_ai/ratecon_rate_money_safety.py`. Compatibility aliases preserve
existing resolver, generator, context-feature, layout, and OCR policy constant
names and values. The total-pay taxonomy remains unchanged from the total-pay
label consolidation phase, and this accessorial/noise consolidation does not
change selected rate output, ranking, penalties, diagnostic labels, source
names, confidence values, field names, money-context labels, or output schemas.

Money-context classifier ownership is centralized in
`app/document_ai/ratecon_rate_money_safety.py`. Compatibility wrappers preserve
old function names and return values where context-feature enrichment still
depends on legacy behavior. This does not change selected rate output, resolver
ranking behavior, resolver penalty values, money-context labels, diagnostic
labels, source names, confidence values, field names, or output schemas.
Known-debt classifier behavior is pinned rather than fixed here.

Candidate generators may emit money candidates, but they should not own
independent total-pay or accessorial safety taxonomy. Generator-side labels that
exist today are compatibility debt and must remain pinned until a future
consolidation PR proves behavior is unchanged.

`app/document_ai/field_candidate_resolver.py` may consume rate/money safety
metadata and apply current ranking policy, but it should not grow independent
rate label taxonomies. Resolver threshold, scoring, penalty, or selected-output
changes require a separate behavior-change PR.

Forensics and audit modules may report diagnoses, conflict reasons, categories,
and safe aggregate counts. They should not define competing total-vs-accessorial
safety rules.

## Compatibility Debt

Existing duplicate labels/constants are compatibility debt, not approval to add
more. Current duplicates are pinned by tests and static audit count so future
cleanup has a stable baseline.

Compatibility surfaces include:

- `app/document_ai/ratecon_candidate_generators.py`
- `app/document_ai/ratecon_candidate_context_features.py`
- `app/document_ai/field_candidate_resolver.py`
- `app/document_ai/rate_candidate_forensics.py`
- `app/document_ai/rate_conflict_audit.py`
- `app/document_ai/rate_candidate_equivalence.py`

Do not delete or consolidate these surfaces without a separate narrow PR and
behavior-pinning evidence.

Some duplicate constants remain intentionally allowlisted compatibility debt,
including diagnostic status/root-cause constants and support-policy markers that
are not pure label-taxonomy owners. Do not consolidate those remaining surfaces
without a separate narrow PR and behavior-pinning evidence.

## Behavior Pinning Status

Current rate/money behavior is pinned by:

- `tests/test_ratecon_selected_rate_regression_harness.py`
- `tests/test_ratecon_total_pay_label_taxonomy.py`
- `tests/test_ratecon_accessorial_noise_label_taxonomy.py`
- `tests/test_ratecon_money_context_classifier.py`
- `tests/test_ratecon_rate_money_compatibility_pinning.py`
- `tests/test_ratecon_rate_money_constant_guardrails.py`
- `tests/test_ratecon_rate_money_safety_ownership.py`

Pinned behavior includes:

- money-context labels for total carrier pay, line items, accessorials,
  quick-pay, fuel advances, and unknown totals;
- current shadow-only abstention/demotion behavior;
- selected-safe, weak-only, and abstain status values;
- rate candidate equivalence amount normalization and fingerprints;
- forensics category and source-section classifications;
- conflict-audit diagnosis and recommended-fix labels;
- compatibility imports and duplicate constant count.
- total-pay/main-rate labels, context markers, compatibility aliases, and
  sanitized selected-rate behavior.
- accessorial/noise/fee/penalty labels, compatibility aliases, current
  sanitizer/context classifications, and sanitized selected-rate behavior.
- money-context classifier labels/statuses, compatibility wrapper behavior, and
  known-debt classifier outcomes.
- selected `total_carrier_rate` behavior across sanitized total-pay,
  accessorial/noise, fee/penalty, line-item, per-unit, and missing-total
  candidate combinations.

The selected-rate regression harness pins current behavior; it does not certify
that every selected output is semantically correct. Some cases are explicitly
marked as known debt so future cleanup can distinguish intentional behavior
changes from accidental regressions.

## Future Consolidation Requirements

Any future rate/money consolidation requires tests proving:

- same selected rate outputs;
- same wrong and missing counts;
- same high-confidence wrong counts;
- same candidate labels and source names;
- same diagnostic classifications unless intentionally changed in a
  behavior-change PR;
- same output schemas and filenames;
- no production output changes by default.

Future total-pay label changes must include selected-rate regression tests and
measurement/evaluation evidence before changing ranking, safety classification,
or candidate metadata behavior.

Future accessorial/noise label changes must include selected-rate regression
tests and measurement/evaluation evidence before changing ranking, safety
classification, money-context labels, or candidate metadata behavior.

Run `tests/test_ratecon_selected_rate_regression_harness.py` before changing
money context classification, resolver ranking penalties, forensics diagnosis
mapping, or selected-rate ranking profiles. Any change to the committed expected
fixture outputs requires explicit review and a clear explanation.

For classifier ownership cleanup, capture a before/after local snapshot with
`scripts/run_ratecon_selected_rate_regression_snapshot.py` and compare it with
`scripts/compare_ratecon_selected_rate_regression_snapshots.py`. The compare
must show unchanged selected values, selected sources, confidence/status fields,
review flags, and selected money-context metadata before proceeding.

The private aggregate selected-rate comparison gate is
`scripts/compare_ratecon_private_selected_rate_aggregates.py`. It compares
existing local private evaluation outputs for `total_carrier_rate` without
running measurement, processing PDFs, OCR, Google sync, or model/cloud calls.
Reports redact selected private values by default; raw selected values are only
included behind the explicit `--include-private-values-local-only` flag and
still write only to `.local_outputs/`.

Before any future resolver penalty, ranking, scoring, or selected-rate behavior
change, run:

1. the sanitized selected-rate regression harness;
2. the private aggregate selected-rate comparison gate;
3. a full private gold evaluation only when explicitly requested.

The private aggregate gate blocks unintentional regressions in wrong counts,
high-confidence wrong counts, selected wrong money-context counts, missing
counts, selected-value changes when locally available, and incompatible
evaluated document counts. It does not certify correctness or approve behavior
changes by itself.

Resolver rate-ranking penalties are intentionally separate from money-context
classifier ownership. `app/document_ai/field_candidate_resolver.py` owns current
selected-rate score adjustments, profile handling, demotion/abstention
penalties, and not-selected traces. `app/document_ai/ratecon_rate_money_safety.py`
owns taxonomy/classifier inputs and abstention metadata only. The ownership
pinning phase documents this split and pins current penalty behavior without
changing selected rate output.

Do not lower resolver thresholds as part of rate/money cleanup. Do not
auto-accept rates from shadow output. Do not use private gold labels as runtime
truth.

## Audit Commands

Run the local-only static audit before planning any rate/money cleanup:

```powershell
python scripts/audit_ratecon_rate_money_safety_ownership.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_rate_money_safety_ownership_audit `
  --confirm-local-audit-run
```

The audit uses static AST/text analysis only. It does not import project
modules, execute extraction or resolver code, process PDFs, run OCR, call
Google, or call model/cloud services.

Run the optional local-only selected-rate snapshot when planning resolver or
money-context cleanup:

```powershell
python scripts/run_ratecon_selected_rate_regression_snapshot.py `
  --output-dir .local_outputs/ratecon_selected_rate_regression_snapshot `
  --confirm-local-audit-run
```

The snapshot uses sanitized fixture candidates only. It does not process PDFs,
run OCR, call Google, or call model/cloud services. Generated snapshot outputs
must stay under `.local_outputs/` and must not be committed.

Run the local-only private aggregate gate when comparing two existing private
evaluation directories:

```powershell
python scripts/compare_ratecon_private_selected_rate_aggregates.py `
  --baseline-eval-dir .local_outputs/private_ratecon_gold_eval_before `
  --experiment-eval-dir .local_outputs/private_ratecon_gold_eval_after `
  --output-dir .local_outputs/ratecon_private_selected_rate_aggregate_compare `
  --confirm-private-local-run `
  --fail-on-selected-rate-regression
```

The gate reads existing summaries and optional selected-rate rows only. It must
not be used to create private evaluation outputs, process PDFs, run OCR, sync
Google Sheets, call model/cloud services, or edit gold labels/templates.

Generated audit outputs, private PDFs, raw extracted text, gold labels,
benchmark outputs, local review packets, Google credentials, OCR artifacts, and
other private/local outputs must never be committed.
