# RateCon Load Identifier Ownership v1

This document clarifies ownership for RateCon `load_number` candidate
generation, selected-value resolution, source taxonomy, and diagnostics. This
PR changes no selected load-number behavior, candidate generation behavior,
resolver scoring, thresholds, source names, confidence values, schemas,
private measurement behavior, or evaluator metrics.

## Ownership

`app/document_ai/load_identifier_candidates.py` is the intended canonical owner
for load identifier candidate taxonomy and policy when current imports allow
it. It owns typed identifier categories such as broker load number, order
number, tender ID, PRO number, freight bill number, primary reference, and
non-primary references.

`app/document_ai/field_candidate_generators.py` may generate load identifier
candidates, but it should not grow independent load identifier taxonomy long
term. Generator-visible labels, source names, confidence values, and candidate
shape remain pinned compatibility behavior.

`app/document_ai/field_candidate_resolver.py` and the legacy
`app/document_ai/ratecon_field_resolution.py` consume load identifier
candidates and own selected value choice, resolver status, conflict routing,
and review flags. They do not own candidate taxonomy.

`app/document_ai/load_identity_forensics.py`,
`app/document_ai/load_identifier_coverage_audit.py`, and
`app/document_ai/load_identifier_source_line_audit.py` report diagnostics,
coverage stages, source-line categories, and safe aggregate counts. They do
not own canonical candidate taxonomy or selected-value behavior.

Evaluator and private-measurement scripts report load-number outcomes and must
not own load identifier extraction rules or ranking changes.

## Pinned Behavior

Current behavior is pinned by sanitized regression fixtures and compatibility
tests. The pinned surface includes:

- primary load/order/tender/PRO/freight-bill style identifiers mapping to
  `load_number`;
- PO, BOL, customer, pickup, delivery, appointment, and carrier references
  remaining non-primary by default;
- generic references requiring review when selected as primary references;
- duplicate same-value primary candidates resolving without conflict;
- conflicting strong primary identifiers requiring review;
- current source labels, confidence values, status strings, warning codes, and
  diagnostic labels.

Known-debt fixtures remain pinned, not fixed. Current wrong/missing and
high-confidence behavior is intentionally preserved.

## Safety Gates

Future load-number behavior changes must run:

1. `tests/test_ratecon_selected_load_regression_harness.py`;
2. `scripts/compare_ratecon_private_selected_load_aggregates.py` against
   sanitized fixtures and local private aggregate outputs when explicitly
   available;
3. full private gold evaluation only when explicitly requested.

Table/layout pairing improvements must be shadow-only or separately approved.
Do not change selected load output, source names, confidence values, evaluator
statuses, or private measurement schemas as part of ownership cleanup.

## Source-Line Evidence Diagnostics

`scripts/audit_ratecon_load_source_line_evidence.py` and
`scripts/create_ratecon_load_source_line_diagnostics.py` provide local-only
source-line/evidence diagnostics after the ownership baseline. They classify
current failure modes such as table-neighbor wrong cell, nearby-row wrong pair,
footer/barcode noise, PO/PRO/BOL/reference noise, gold absent from candidates,
and gold present but not selected.

Those diagnostics are reporting-only. They do not change selected load output,
candidate generation, resolver ranking/scoring, source labels, confidence
values, schemas, evaluator statuses, extraction, or private measurement
behavior.

`scripts/summarize_ratecon_load_source_line_diagnostics_closeout.py` is the
local-only closeout/readiness gate for this diagnostics phase. Run it before
any source-line evidence-quality behavior experiment. If the closeout reports
mostly unavailable detail or unknown buckets, table-neighbor and nearby-row
experiments remain blocked until audit/eval evidence is improved.

`app/document_ai/load_identifier_source_line_detail.py` and
`scripts/create_ratecon_load_source_line_detail_inventory.py` add local-only
detail inventory sidecars for existing eval/audit/diagnostic metadata. They
explain whether unknown or source-line-unavailable diagnostics are caused by
missing candidate id, source, page/line, pairing, label, value, or evaluator
detail. They do not change selected load output, candidate generation, resolver
ranking, source labels, confidence values, schemas, or evaluator statuses.

`app/document_ai/load_identifier_source_line_serialization.py` and
`scripts/create_ratecon_load_source_line_serialization.py` own local-only
serialization sidecars for load source-line diagnostic detail. They preserve
existing candidate id, source, page/line, and pairing metadata when available
and classify where it is lost. They do not own candidate taxonomy, resolver
selection, source labels, confidence values, schemas, or evaluator status
semantics.

`app/document_ai/load_identifier_candidate_adapter_provenance.py` and
`scripts/audit_ratecon_load_candidate_adapter_provenance.py` focus specifically
on preserving already-existing load candidate provenance metadata across the
candidate adapter boundary. They do not infer missing metadata, change candidate
generation, change selected-value resolution, or approve table/nearby-row
behavior changes.

## Local-Only Audit

`scripts/audit_ratecon_load_identifier_ownership.py` provides static AST/text
inventory only. It refuses to run without `--confirm-local-audit-run`, writes
only under `.local_outputs/`, and must not import project modules dynamically,
execute resolver or extraction code, process PDFs, run OCR, call Google/model
services, or read private/local output directories.

```powershell
python scripts/audit_ratecon_load_identifier_ownership.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_load_identifier_ownership_audit `
  --confirm-local-audit-run
```

This ownership baseline is not a load-number improvement PR and does not claim
accuracy gains.
