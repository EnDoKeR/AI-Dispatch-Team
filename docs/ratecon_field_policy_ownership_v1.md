# RateCon Field Policy Ownership v1

`app/document_ai/ratecon_core_field_policy.py` is the canonical owner for
RateCon readiness and critical-field policy.

This ownership note is behavior-preserving. It does not change readiness
decisions, validation semantics, resolver thresholds, selected stop output,
private measurement schemas, or extraction behavior.

## Canonical Owner

Use `app/document_ai/ratecon_core_field_policy.py` for:

- extraction-review field policy;
- intake-core readiness field policy;
- dispatch-critical field policy;
- legacy intake `CRITICAL_FIELDS` compatibility values.

The module exposes compatibility helpers:

- `get_readiness_required_fields()`
- `get_dispatch_critical_fields()`
- `get_intake_core_fields()`
- `get_extraction_review_fields()`
- `get_legacy_critical_fields()`

Use `get_required_fields_for_readiness()` and
`get_review_fields_for_readiness()` when a caller needs an explicit readiness
role or document context.

## Legacy Compatibility Surfaces

`app/market_intelligence/intake/rate_confirmation_intake.py` still exposes
`CRITICAL_FIELDS` for legacy imports. That symbol is compatibility only and
must not become a new owner for RateCon readiness policy.

Legacy callers may keep importing `CRITICAL_FIELDS`, but new RateCon readiness
or critical-field logic should use `ratecon_core_field_policy.py`.

## Dependency Rules

- Document AI readiness/review/audit modules may import
  `ratecon_core_field_policy.py`.
- Legacy intake modules may keep thin compatibility aliases when needed.
- Do not add new readiness or critical-field lists in scripts, tests, review
  exporters, model-provider scaffolding, or local audit tooling.
- Do not introduce circular imports. If a dependency direction becomes unsafe,
  leave the legacy surface unchanged and add a tested comparison instead.

## Adding Or Changing A Field

Any field-policy behavior change must be a separate reviewed PR. Before
changing a field set or role:

1. Update `ratecon_core_field_policy.py` only.
2. Explain whether the change affects extraction-review, intake-core,
   dispatch-critical, or legacy compatibility behavior.
3. Update tests that pin the affected field set.
4. Run architecture boundary tests.
5. Prove readiness and validation outcomes changed only as intended.

## Required Tests

Before changing field policy, run:

```powershell
python -m unittest tests.test_ratecon_core_field_policy_owner
python -m unittest tests.architecture.test_architecture_boundaries
python -m unittest discover -s tests -p "test_*.py"
python scripts/run_tests.py
python -m compileall app scripts tests
git diff --check
git diff --cached --check
```

## Private Data Safety

Field policy tests and docs must use sanitized field names only. Do not commit
`.local_outputs`, private PDFs, raw extracted document text, gold labels,
benchmark outputs, audit JSONL with private values, Google credentials, tokens,
model outputs, OCR artifacts, or private local debug files.
