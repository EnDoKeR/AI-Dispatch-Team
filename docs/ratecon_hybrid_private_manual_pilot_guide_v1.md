# RateCon Hybrid Private Manual Pilot Guide v1

Date: 2026-06-03

Scope: local-only workflow for creating a small manual pilot packet from private
RateCon audit/gold metadata. This workflow does not call AI, cloud services,
OCR, local models, or PDF processing.

## What This Produces

The pilot generator creates:

- a small document index;
- blank hybrid result JSON templates;
- an Excel-friendly checklist;
- a readme;
- benchmark instructions.

All outputs are written under `.local_outputs/` and must not be committed.

## Generate The Pilot Packet

```powershell
python scripts/create_ratecon_hybrid_private_manual_pilot.py ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --output-dir .local_outputs/private_ratecon_hybrid_manual_pilot ^
  --confirm-private-local-run
```

Optional flags:

- `--max-docs 5`
- `--pilot-profile representative_v1`
- `--document-id DOC_ID`
- `--include-private-values-local-only`

The generator refuses to write outside `.local_outputs/`.

## Where To Find Templates

Templates are written to:

```text
.local_outputs/private_ratecon_hybrid_manual_pilot/templates/
```

Each template is a `.hybrid_result.json` file. Open it in a text editor and
fill only values visible in the document.

## Which Fields To Fill First

Fill in this order:

1. `document_type`: `rate_confirmation`, `bol_pod`, or `unknown`.
2. `fields.load_number.value`.
3. `fields.total_carrier_rate.value`.
4. `fields.pickup_stops`.
5. `fields.delivery_stops`.
6. `evidence`.

Leave unavailable components as `null`.

## Required Stop Policy

Every stop must stay:

```json
{
  "requires_human_review": true,
  "auto_accept": false
}
```

Stops are review drafts only. Do not auto-accept stops in this pilot.

## Add Evidence

Every filled value needs evidence. Add evidence rows like:

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

Then reference the evidence ID from the field or stop:

```json
{
  "evidence_ids": ["ev_pickup_001"]
}
```

Use redacted excerpts in any shareable output. Private raw text belongs only in
ignored local files.

## Run Benchmark After Editing Templates

```powershell
python scripts/run_ratecon_hybrid_benchmark.py ^
  --hybrid-results-dir .local_outputs/private_ratecon_hybrid_manual_pilot/templates ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_manual_pilot_benchmark ^
  --confirm-private-local-run ^
  --allow-unfilled-manual-templates ^
  --write-review-packets
```

The `--allow-unfilled-manual-templates` flag lets blank templates benchmark as
missing/unfilled rows while still enforcing:

- no `auto_accept=true`;
- every stop must be review-required;
- filled values must have evidence.

## Read Benchmark Reports

Start with:

- `hybrid_benchmark_report.md`
- `hybrid_error_cases.csv`
- `hybrid_review_items.csv`

Fix in this order:

1. Schema errors.
2. Auto-accept violations.
3. Missing evidence.
4. Unsafe wrong stops.
5. Remaining missing/unfilled fields.

If a stop gold label is marked uncertain, the benchmark keeps that row in
human review instead of treating a stable-component match as `unsafe_wrong`.
Review the source document and gold note before changing a manually preserved
odd date or appointment window.

For wrong rate rows, inspect `hybrid_money_diagnostics.csv`. The default file
redacts raw private values but shows the source field path, comparison reason,
and whether decimal-cent normalization matched.

## Files That Must Never Be Committed

Do not commit:

- `.local_outputs/`;
- private PDFs;
- private gold labels;
- private audit/eval/review outputs;
- private hybrid templates;
- manually filled hybrid results with private values;
- raw extracted text;
- model outputs containing private data.

## Important Limits

This is a manual pilot scaffold. It does not improve production extraction,
does not change selected stop output, and does not introduce AI/model
integration.
