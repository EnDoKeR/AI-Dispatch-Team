# RateCon Local Provider Readiness Gates v1

## Purpose

The local provider readiness gates define the privacy, safety, and benchmark
conditions required before any local model provider implementation can be
considered. This document is an approval scaffold only. It does not authorize
model execution.

## What Must Be True First

A future local provider PR must prove all of the following before private local
experiments are considered:

- private data stays local;
- no external calls are made;
- no model weights are downloaded inside the task;
- no private prompts or responses are logged by default;
- output redaction is enabled by default;
- production and legacy extraction output remain unchanged;
- gold labels and filled hybrid templates are not edited automatically;
- all stops remain `requires_human_review=true`;
- all stops remain `auto_accept=false`;
- model outputs validate as `ratecon_model_assisted_submission_v1`;
- embedded results validate as `ratecon_hybrid_extraction_result_v1`;
- fixture smoke tests pass before private pilot work starts;
- manual baseline comparison remains part of every benchmark.

## Forbidden Now

The current phase forbids:

- live OpenAI, Claude, Gemini, local VLM, or other model calls;
- cloud provider execution;
- local model provider execution;
- OCR;
- PDF/image/raw-text input to a provider;
- private value copying;
- model weight downloads;
- API keys or secret-bearing provider configs;
- vector stores or embeddings containing private content;
- production extraction changes.

## Privacy Review Checklist

Every readiness file must assert:

- `private_data_stays_local=true`;
- `no_external_calls=true`;
- `no_model_weight_download_in_task=true`;
- `no_private_prompt_logging=true`;
- `no_private_response_logging=true`;
- `output_redaction_default=true`.

Any failed item blocks readiness.

## Safety Review Checklist

Every readiness file must assert:

- `auto_accept_disabled=true`;
- `stops_review_required=true`;
- `production_output_unchanged=true`;
- `gold_labels_unchanged=true`;
- `filled_templates_unchanged=true`.

Any failed item blocks readiness.

## Benchmark Requirements

The benchmark plan must require:

- manual baseline comparison;
- fixture-only smoke testing;
- explicit confirmation for any private local pilot;
- reports for schema errors, missing evidence, auto-accept violations, unsafe
  wrong stops, and manual baseline deltas.

## Stop Conditions

Stop the experiment review if any readiness artifact requests:

- external calls;
- PDF input;
- image input;
- raw text input;
- OCR input;
- private value copying;
- private local execution approval;
- cloud approval.

These conditions require a separate scoped approval path and must not be
approved by this scaffolding.

## Readiness CLI

Create a local template:

```powershell
python scripts/ratecon_local_provider_readiness_cli.py create-template ^
  --output .local_outputs/ratecon_local_provider_readiness_template.json ^
  --confirm-private-local-run
```

Validate a readiness file:

```powershell
python scripts/ratecon_local_provider_readiness_cli.py validate ^
  --readiness-file tests/fixtures/ratecon_local_provider_readiness/valid_fixture_only_readiness.json ^
  --confirm-private-local-run
```

Write a dry-run report:

```powershell
python scripts/ratecon_local_provider_readiness_cli.py dry-run-report ^
  --readiness-file tests/fixtures/ratecon_local_provider_readiness/valid_fixture_only_readiness.json ^
  --provider-config tests/fixtures/ratecon_model_provider/valid_stub_provider_config.json ^
  --output-dir .local_outputs/ratecon_local_provider_readiness_dry_run ^
  --confirm-private-local-run
```

The dry-run report writes:

- `readiness_report.md`;
- `readiness_summary.json`;
- `readiness_gate_results.csv`;
- `readiness_next_actions.csv`.

## Fixture-Only Smoke Test

Run the fixture-only smoke workflow:

```powershell
python scripts/run_ratecon_local_provider_fixture_smoke_test.py ^
  --output-dir .local_outputs/ratecon_local_provider_fixture_smoke_test ^
  --confirm-private-local-run
```

The smoke test uses sanitized fixtures only and runs:

- provider registry listing;
- safe provider config validation;
- readiness template validation;
- readiness dry-run report generation;
- stub submission generation;
- model-assisted benchmark wrapper against fixture data.

It reports `fixture_smoke_passed_no_model_execution` when the scaffold works
without model execution.

## Files That Must Never Be Committed

Do not commit:

- `.local_outputs/`;
- private PDFs;
- private gold labels;
- private audit/evaluation/review outputs;
- private hybrid templates;
- model prompts or responses containing private values;
- API keys;
- provider configs containing secrets;
- local model files or downloaded weights;
- embeddings or vector stores containing private content.

## Future Local Provider PR Requirements

A future local provider implementation must be a separate PR and must prove:

- the readiness file still validates;
- provider registry blocks are intentionally changed and reviewed;
- fixture smoke tests pass;
- no production extraction behavior changes;
- private pilot execution requires explicit user confirmation;
- all output remains review-first and benchmarked against the manual baseline.

## Cloud Provider Approval

Cloud providers require a separate privacy and business approval path. This
readiness scaffold cannot approve cloud execution, external calls, API keys, or
private document transfer.
