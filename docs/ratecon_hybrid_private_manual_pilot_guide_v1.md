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

1. `document_type`: `rate_confirmation`, `bol_pod`,
   `non_rate_confirmation`, `bill_of_lading_or_delivery_receipt`, or
   `unknown`.
2. `fields.load_number.value`.
3. `fields.total_carrier_rate.value`.
4. `fields.pickup_stops`.
5. `fields.delivery_stops`.
6. `evidence`.

Leave unavailable components as `null`.

## Fill BOL/POD Or Non-RC Documents

If a selected document is a BOL, POD, delivery receipt, or otherwise not a
rate confirmation, set `document_type` to the closest non-RC type and leave
rate-con fields blank:

- `fields.load_number.value = null`;
- `fields.total_carrier_rate.value = null`;
- `fields.pickup_stops = []`;
- `fields.delivery_stops = []`.

Do not add stop evidence for blank non-RC rate-con fields. The benchmark marks
confirmed non-RC blank fields as `not_applicable_non_rc` and reports them as
filtered, not failed. If the classification is uncertain, use `unknown`, keep
the template review-required, and flag it for human review.

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

## Review Scalar Mismatches

For load number or total carrier rate mismatches, generate a local-only scalar
review packet:

```powershell
python scripts/create_ratecon_hybrid_scalar_discrepancy_review.py ^
  --hybrid-results-dir .local_outputs/private_ratecon_hybrid_manual_pilot/templates ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --benchmark-dir .local_outputs/private_ratecon_hybrid_manual_pilot_benchmark_uncertain_gold_v1 ^
  --output-dir .local_outputs/private_ratecon_hybrid_scalar_discrepancy_review ^
  --confirm-private-local-run
```

Open `scalar_discrepancy_summary.md` first, then
`scalar_discrepancy_items.csv`. The packet recommends whether to correct a
manual hybrid template, request gold-label review, inspect document/file-hash
matching, or investigate a benchmark bug. The patch template is dry-run-only
and leaves proposed values blank.

Do not edit gold labels automatically. Do not change a manually filled template
unless the source document evidence proves the template is wrong.

## Summarize Pilot Results

After benchmark and scalar review cleanup, create a concise pilot summary:

```powershell
python scripts/summarize_ratecon_hybrid_manual_pilot.py ^
  --benchmark-dir .local_outputs/private_ratecon_hybrid_manual_pilot_benchmark_after_scalar_fix ^
  --output-dir .local_outputs/private_ratecon_hybrid_manual_pilot_summary ^
  --confirm-private-local-run
```

The summary writes:

- `manual_pilot_summary.md`;
- `manual_pilot_summary.json`;
- `manual_pilot_success_criteria.csv`;
- `manual_pilot_next_actions.csv`.

Pilot status meanings:

- `pilot_passed`: no schema, safety, accuracy, or review-item blockers.
- `pilot_passed_with_review_items`: no failures, but review-required items
  remain, such as uncertain gold.
- `pilot_failed_schema`: schema errors must be fixed first.
- `pilot_failed_safety`: missing evidence or stop auto-accept violations exist.
- `pilot_failed_accuracy`: unsafe wrong stops or unresolved scalar wrongs remain.
- `pilot_inconclusive`: inputs were insufficient to classify.

Uncertain gold is not a failure when the benchmark classifies it as
review-required. Keep it in human review and do not convert it into
auto-accept.

## Plan The Next Batch

If audit and gold metadata are available, add `--write-next-batch-plan`:

```powershell
python scripts/summarize_ratecon_hybrid_manual_pilot.py ^
  --benchmark-dir .local_outputs/private_ratecon_hybrid_manual_pilot_benchmark_after_scalar_fix ^
  --output-dir .local_outputs/private_ratecon_hybrid_manual_pilot_summary ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --confirm-private-local-run ^
  --write-next-batch-plan
```

The planner writes `manual_pilot_next_batch_plan.csv` with suggested documents,
patterns, difficulty, why each document was selected, and what fields to fill.
Use it to expand the pilot to 5-10 more documents while preserving pattern
diversity:

- TQL compact rows;
- Express pickup/drop blocks;
- PU/SO scanned blocks;
- SPI/Fello/Landstar structured blocks;
- city-level-only/verbal agreement;
- non-RC/BOL/POD.

Stay in manual-pilot mode until multiple batches show stable safety:

- no schema errors;
- no missing evidence;
- no stop auto-accept violations;
- no unsafe wrong stops;
- scalar mismatches are resolved by review packets;
- uncertain-gold rows remain explicitly review-required.

Consider model-assisted filling only after the manual workflow proves the
contract, evidence rules, review policy, and benchmark reports are stable across
diverse document patterns. Do not introduce model integration from a single
successful 5-document pilot.

## Create The Next-Batch Packet

After `manual_pilot_next_batch_plan.csv` exists, create a local-only packet for
the next 5-10 documents:

```powershell
python scripts/create_ratecon_hybrid_next_batch_packet.py ^
  --next-batch-plan .local_outputs/private_ratecon_hybrid_manual_pilot_summary/manual_pilot_next_batch_plan.csv ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --output-dir .local_outputs/private_ratecon_hybrid_next_batch_packet ^
  --confirm-private-local-run ^
  --write-empty-templates ^
  --write-checklist ^
  --write-zip-instructions
```

The packet writes:

- `next_batch_summary.json`;
- `next_batch_readme.md`;
- `next_batch_document_index.csv`;
- `next_batch_checklist.csv`;
- blank templates under `templates/`;
- `how_to_fill_templates.md`;
- `how_to_run_benchmark.md`;
- `how_to_zip_for_review.md`.

Templates use `model_provider=manual`, `model_name=manual_next_batch_v1`,
`private_local_only=true`, and review reason `manual_next_batch_unfilled`.
Likely rate-confirmation documents get one blank pickup stop and one blank
delivery stop. Every stop remains `requires_human_review=true` and
`auto_accept=false`.

The checklist separates pickup and delivery rows and includes explicit evidence
page/source rows. Use it as the manual fill tracker.

## Zip Next-Batch Templates For Manual Filling

Use the generated `how_to_zip_for_review.md` instructions. The zip should only
include:

- `next_batch_document_index.csv`;
- `next_batch_checklist.csv`;
- `templates/*.hybrid_result.json`.

Do not zip PDFs unless explicitly requested. Do not commit the zip. Upload the
zip only for manual filling/review.

## Benchmark The Filled Next Batch

After the templates are filled, run:

```powershell
python scripts/run_ratecon_hybrid_benchmark.py ^
  --hybrid-results-dir .local_outputs/private_ratecon_hybrid_next_batch_packet/templates ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_next_batch_benchmark ^
  --confirm-private-local-run ^
  --allow-unfilled-manual-templates ^
  --write-review-packets
```

PowerShell array form:

```powershell
$benchmarkArgs = @(
  "--hybrid-results-dir", ".local_outputs/private_ratecon_hybrid_next_batch_packet/templates",
  "--gold-dir", ".local_outputs/private_ratecon_gold_labels",
  "--audit", ".local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl",
  "--output-dir", ".local_outputs/private_ratecon_hybrid_next_batch_benchmark",
  "--confirm-private-local-run",
  "--allow-unfilled-manual-templates",
  "--write-review-packets"
)
python scripts/run_ratecon_hybrid_benchmark.py @benchmarkArgs
```

Read `hybrid_benchmark_report.md` first, then inspect
`hybrid_error_cases.csv` and `hybrid_review_items.csv`. Treat uncertain gold as
review-required rather than failure when the benchmark classifies it that way.
Keep private benchmark outputs local.

## Summarize Multiple Manual Batches

After two or more manual benchmark folders exist, aggregate them:

```powershell
python scripts/summarize_ratecon_hybrid_batches.py ^
  --benchmark-dir .local_outputs/private_ratecon_hybrid_manual_pilot_benchmark_after_scalar_fix ^
  --benchmark-dir .local_outputs/private_ratecon_hybrid_next_batch_benchmark ^
  --output-dir .local_outputs/private_ratecon_hybrid_multi_batch_summary ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --confirm-private-local-run ^
  --write-remaining-plan ^
  --max-next-docs 10
```

The multi-batch summary writes:

- `multi_batch_summary.md`;
- `multi_batch_summary.json`;
- `multi_batch_document_coverage.csv`;
- `multi_batch_field_metrics.csv`;
- `multi_batch_review_items.csv`;
- `multi_batch_success_criteria.csv`;
- optionally `remaining_manual_batch_plan.csv`.

Document IDs are deduplicated across benchmark folders. Duplicate documents are
listed in `multi_batch_document_coverage.csv` but excluded from aggregate
metrics.

Aggregate statuses:

- `manual_hybrid_workflow_validated`: clean aggregate with no review blockers.
- `manual_hybrid_validated_with_review_items`: clean aggregate except expected
  review items, such as uncertain gold.
- `manual_hybrid_failed_schema`: at least one schema error exists.
- `manual_hybrid_failed_safety`: missing evidence or stop auto-accept exists.
- `manual_hybrid_failed_accuracy`: unsafe wrong stops or unresolved scalar
  wrongs remain.
- `manual_hybrid_inconclusive`: insufficient benchmark inputs.

The manual workflow is considered validated for the current stage when multiple
batches show no schema errors, no missing evidence, no stop auto-accept
violations, no unsafe wrong stops, and only explicit review-required uncertain
gold remains.

## Generate The Remaining Plan

When `--write-remaining-plan` is supplied, the summary script writes
`remaining_manual_batch_plan.csv`. It excludes document IDs already benchmarked
in prior manual batches and excludes non-RC/BOL/POD rows by default.

Use the plan to create a third-batch packet:

```powershell
python scripts/create_ratecon_hybrid_next_batch_packet.py ^
  --next-batch-plan .local_outputs/private_ratecon_hybrid_multi_batch_summary/remaining_manual_batch_plan.csv ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --output-dir .local_outputs/private_ratecon_hybrid_third_batch_packet ^
  --confirm-private-local-run ^
  --write-empty-templates ^
  --write-checklist ^
  --write-zip-instructions
```

Benchmark unfilled third-batch templates before manual filling:

```powershell
python scripts/run_ratecon_hybrid_benchmark.py ^
  --hybrid-results-dir .local_outputs/private_ratecon_hybrid_third_batch_packet/templates ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_third_batch_benchmark_unfilled ^
  --confirm-private-local-run ^
  --allow-unfilled-manual-templates ^
  --write-review-packets
```

Avoid duplicate documents by checking `multi_batch_document_coverage.csv` and
the `already_completed` column in `remaining_manual_batch_plan.csv`. Do not
move to model-assisted filling until the manual workflow remains stable across
multiple diverse batches.

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
