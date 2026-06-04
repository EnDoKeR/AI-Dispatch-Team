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

## Behavior Pinning Status

Current rate/money behavior is pinned by:

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

Do not lower resolver thresholds as part of rate/money cleanup. Do not
auto-accept rates from shadow output. Do not use private gold labels as runtime
truth.

## Audit Command

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

Generated audit outputs, private PDFs, raw extracted text, gold labels,
benchmark outputs, local review packets, Google credentials, OCR artifacts, and
other private/local outputs must never be committed.
