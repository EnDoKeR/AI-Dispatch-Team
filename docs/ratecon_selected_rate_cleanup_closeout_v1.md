# RateCon Selected-Rate Cleanup Closeout v1

This note closes out the current RateCon rate/money cleanup series at the
behavior-preserving reporting layer. It does not change selected-rate output,
resolver scoring, resolver penalties, thresholds, trace schemas, diagnosis
strings, evaluator statuses, aggregate gate semantics, extraction behavior, or
candidate generation behavior.

## Series Status

The cleanup series established ownership and guardrails for selected
`total_carrier_rate` behavior without claiming extraction or accuracy
improvement. The series now has documentation, static audits, behavior-pinning
tests, sanitized regression fixtures, and a local-only aggregate gate.

## Ownership Map

- `app/document_ai/ratecon_rate_money_safety.py` owns total-pay/main-rate label
  taxonomy.
- `app/document_ai/ratecon_rate_money_safety.py` owns
  accessorial/noise/fee/penalty label taxonomy.
- `app/document_ai/ratecon_rate_money_safety.py` owns money-context classifier
  helpers and rate-safety taxonomy inputs.
- `app/document_ai/field_candidate_resolver.py` owns selected-rate ranking
  penalties, scoring behavior, demotion/abstention decisions, selected output,
  and score trace construction.
- `docs/ratecon_rate_score_trace_explanation_v1.md` documents score trace
  ownership. Trace output explains current decisions and must not define
  scoring behavior independently.
- `app/document_ai/rate_candidate_forensics.py` owns selected-rate forensics
  diagnosis mapping documentation and safe forensic category contracts.
- `scripts/compare_ratecon_private_selected_rate_aggregates.py` owns the
  local-only private aggregate selected-rate comparison gate.
- `scripts/summarize_ratecon_selected_rate_closeout.py` owns local-only
  selected-rate closeout evidence summarization.

## Pinned Behavior

Pinned behavior includes:

- selected `total_carrier_rate` outputs across sanitized total-pay,
  accessorial/noise, fee/penalty, line-item, per-unit, and missing-total
  candidate combinations;
- current money-context labels and rate-safety status values;
- current resolver score adjustments, penalties, ranking profile behavior,
  demotion/abstention decisions, selected candidate trace fields, and
  not-selected reason strings;
- current forensics diagnosis strings, diagnosis counts, wrong reason counts,
  and aggregate gate diagnosis deltas;
- current local-only output filenames and redaction behavior for selected-rate
  gates and closeout reports.

Known-debt fixture behavior remains pinned, not fixed. Changing expected
fixture output requires explicit review and metric-delta justification.

## Required Gates Before Behavior Changes

Before any future selected-rate behavior, ranking, scoring, penalty, threshold,
trace schema, money-context classifier, or diagnosis mapping change, run:

1. `tests/test_ratecon_selected_rate_regression_harness.py`;
2. `scripts/run_ratecon_selected_rate_regression_snapshot.py`;
3. `scripts/compare_ratecon_selected_rate_regression_snapshots.py`;
4. `scripts/compare_ratecon_private_selected_rate_aggregates.py`;
5. `scripts/summarize_ratecon_selected_rate_closeout.py`;
6. full private gold evaluation only when explicitly requested.

The closeout and aggregate gates block accidental regressions. They do not
certify correctness and do not approve production migration or an experimental
ranking profile by themselves.

## Running The Closeout

```powershell
python scripts/summarize_ratecon_selected_rate_closeout.py `
  --selected-rate-snapshot-dir .local_outputs/ratecon_selected_rate_regression_snapshot `
  --aggregate-gate-dir .local_outputs/ratecon_private_selected_rate_aggregate_compare `
  --rate-money-audit-dir .local_outputs/ratecon_rate_money_safety_ownership_audit `
  --output-dir .local_outputs/ratecon_selected_rate_closeout `
  --confirm-local-audit-run
```

The script reads existing local-only outputs if present, tolerates missing
optional audit/private baseline directories, and writes only under
`.local_outputs/`.

## Optional Private Full-Corpus Baseline

When explicitly requested, a local private full-corpus baseline may be captured
with this safe sequence:

1. run private measurement under `.local_outputs/`;
2. run gold evaluation under `.local_outputs/`;
3. run the selected-rate aggregate gate comparing baseline to itself or to a
   previous local baseline;
4. run the closeout summarizer.

Do not run private measurement, process private PDFs, call OCR, sync Google
Sheets, call model/cloud services, edit gold labels, or edit filled hybrid
templates as part of this closeout PR.

Private values remain local-only and redacted by default. Raw selected values
must only appear behind explicit local-only flags and must never be committed.

## Remaining Known Debt

Known debt includes evaluator-side diagnosis assignment that remains pinned as
compatibility behavior, known-debt selected-rate regression fixtures, and any
future private full-corpus baseline if local private evaluation directories are
not available during closeout.

Future options after closeout are:

- capture the private full-corpus baseline if it was skipped;
- design an explicit shadow-only experimental ranking profile;
- continue with load identifier ownership cleanup;
- continue with stop extraction architecture closeout.

Do not lower thresholds, change resolver ranking behavior, auto-accept shadow
rates, or use private gold labels as runtime truth as part of closeout work.
