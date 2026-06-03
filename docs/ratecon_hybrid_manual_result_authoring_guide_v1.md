# RateCon Hybrid Manual Result Authoring Guide v1

Date: 2026-06-03

Scope: how to manually create, fill, validate, and benchmark RateCon hybrid
result JSON files. This workflow is local-only and does not call AI, cloud
services, OCR, local models, or PDF processing.

## Purpose

Hybrid result JSON files are review-first extraction drafts. They let a human
or future opt-in model pipeline submit auditable load, rate, pickup, and
delivery fields for benchmark scoring against local gold labels.

Stops remain review-required. Do not use this workflow to auto-accept stops or
replace production output.

## Create Blank Templates

Create one blank hybrid result JSON template per audited document:

```powershell
python scripts/create_ratecon_hybrid_result_templates.py ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_result_templates ^
  --confirm-private-local-run
```

The template generator:

- writes only under `.local_outputs`;
- does not read PDFs;
- does not call AI/model services;
- does not fill private values by default;
- sets every stop to `requires_human_review=true`;
- sets every stop to `auto_accept=false`.

## Fill Hybrid Result JSON Manually

For each template, fill:

- `document_type`: `rate_confirmation`, `bol_pod`, or `unknown`;
- `fields.load_number.value`;
- `fields.total_carrier_rate.value`;
- `fields.pickup_stops`;
- `fields.delivery_stops`;
- `evidence`;
- `confidence`;
- `review_reasons`;
- `validator_results`.

Use `null` for missing components. Do not use placeholders such as `"unknown"`
or `"n/a"` as extracted values.

## Required Stop Fields

Each stop object must include:

```json
{
  "role": "pickup",
  "stop_index": 1,
  "facility": null,
  "address": null,
  "city": null,
  "state": null,
  "zip": null,
  "date": null,
  "time": null,
  "appointment_window": null,
  "raw_text_local_only": null,
  "evidence_page": null,
  "evidence_bbox": null,
  "confidence": 0.0,
  "requires_human_review": true,
  "auto_accept": false,
  "evidence_ids": []
}
```

`role`, `stop_index`, `requires_human_review`, and `auto_accept` are policy
critical. Stops with values must include evidence.

## Add Evidence

Every extracted value should point to evidence:

```json
{
  "evidence_id": "ev_pickup_001",
  "field": "pickup_stops[0]",
  "page": 1,
  "bbox": null,
  "text_excerpt_redacted": "<redacted>",
  "source": "model"
}
```

Use redacted excerpts in committed or shared artifacts. Private raw text can
exist only in ignored local outputs and only when explicitly requested by a
local/private flag.

## Why Stops Require Review

Current stop extraction has poor exact/dispatch-usable selected-stop accuracy.
Hybrid stops may be better drafts, but phase 1 policy requires human review
for every stop because wrong location, role, date, or time can affect dispatch.

## Why `auto_accept` Must Stay False

`auto_accept=true` is a policy violation in phase 1. The benchmark runner
reports it as an error even if the extracted value matches gold. Stop
auto-accept requires a separate approved architecture decision and materially
better measured performance.

## Run Benchmark

Run benchmark on manually filled results:

```powershell
python scripts/run_ratecon_hybrid_benchmark.py ^
  --hybrid-results-dir .local_outputs/private_ratecon_hybrid_results ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_benchmark ^
  --confirm-private-local-run ^
  --write-review-packets
```

Run the committed sanitized fixture demo:

```powershell
python scripts/run_ratecon_hybrid_fixture_demo.py
```

The demo reads only `tests/fixtures/ratecon_hybrid/` and writes:

```text
.local_outputs/ratecon_hybrid_fixture_demo/
```

## Read Reports

Key outputs:

- `hybrid_benchmark_report.md`: one-screen summary, safety section, baseline
  comparison, error examples, and next action.
- `hybrid_benchmark_summary.json`: aggregate metrics and safety flags.
- `hybrid_field_metrics.csv`: scalar and stop comparison rows.
- `hybrid_error_cases.csv`: schema, evidence, unsafe, and policy failures.
- `hybrid_review_items.csv`: review-oriented stop rows when
  `--write-review-packets` is used.

Start with schema errors and auto-accept violations, then missing evidence, then
unsafe wrong stops.

Uncertain gold labels are review cases. When stable stop components match but
the gold stop is marked uncertain, the benchmark reports the row as
review-required instead of `unsafe_wrong` or `reject_wrong`. This keeps manual
preservation of visibly odd source values from being treated as an automatic
failure.

Wrong money rows also write `hybrid_money_diagnostics.csv`. By default this
file redacts raw values and reports the source field path, comparison reason,
and decimal-cent normalization status. Use `--include-private-values-local-only`
only for ignored local debugging.

## Review Scalar Discrepancies

When load number or total carrier rate mismatches remain, create a local-only
scalar discrepancy packet before changing anything:

```powershell
python scripts/create_ratecon_hybrid_scalar_discrepancy_review.py ^
  --hybrid-results-dir .local_outputs/private_ratecon_hybrid_manual_pilot/templates ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --benchmark-dir .local_outputs/private_ratecon_hybrid_manual_pilot_benchmark_uncertain_gold_v1 ^
  --output-dir .local_outputs/private_ratecon_hybrid_scalar_discrepancy_review ^
  --confirm-private-local-run
```

The packet classifies each scalar mismatch as a likely template issue, gold
review issue, match-key issue, benchmark lookup issue, normalization issue, or
uncertain-gold review case. It writes a dry-run patch template with blank
proposed values only. Do not edit gold labels or hybrid templates until a human
has checked the document evidence and decided which side is wrong.

## Keep Private Data Local

Do not commit:

- `.local_outputs/`;
- private PDFs;
- private gold labels;
- private audit/eval/review outputs;
- raw extracted document text;
- hybrid model outputs containing private values.

Committed fixtures must remain synthetic. Use generic document IDs, fake values,
redacted evidence text, and sanitized labels only.
