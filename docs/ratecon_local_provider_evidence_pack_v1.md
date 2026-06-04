# RateCon Local Provider Evidence Pack v1

## Purpose

The local provider evidence pack bundles the facts needed to approve or reject a
future local-provider design PR. It is fixture-only scaffolding. It does not
approve implementation, execute a model, process PDFs, run OCR, or change
production extraction.

## Evidence Bundled

The pack summarizes:

- readiness validation status;
- provider config validation status;
- provider registry blockers;
- fixture smoke-test status;
- model-assisted fixture benchmark status when available;
- safety gates;
- blockers and warnings;
- required next actions;
- local artifact index.

## Run Fixture Smoke First

```powershell
python scripts/run_ratecon_local_provider_fixture_smoke_test.py ^
  --output-dir .local_outputs/ratecon_local_provider_fixture_smoke_test ^
  --confirm-private-local-run
```

This uses sanitized fixtures only. It lists providers, validates the safe stub
config, validates readiness gates, creates stub submissions, and runs the
model-assisted benchmark wrapper. It does not call a model, process PDFs, run
OCR, edit gold labels, or edit hybrid templates.

## Run Readiness Dry Run

```powershell
python scripts/ratecon_local_provider_readiness_cli.py dry-run-report ^
  --readiness-file tests/fixtures/ratecon_local_provider_readiness/valid_fixture_only_readiness.json ^
  --provider-config tests/fixtures/ratecon_model_provider/valid_stub_provider_config.json ^
  --output-dir .local_outputs/ratecon_local_provider_readiness_dry_run ^
  --confirm-private-local-run
```

## Generate Evidence Pack

```powershell
python scripts/create_ratecon_local_provider_evidence_pack.py ^
  --readiness-file tests/fixtures/ratecon_local_provider_readiness/valid_fixture_only_readiness.json ^
  --provider-config tests/fixtures/ratecon_model_provider/valid_stub_provider_config.json ^
  --smoke-dir .local_outputs/ratecon_local_provider_fixture_smoke_test ^
  --readiness-report-dir .local_outputs/ratecon_local_provider_readiness_dry_run ^
  --output-dir .local_outputs/ratecon_local_provider_evidence_pack ^
  --confirm-private-local-run
```

The command writes:

- `local_provider_evidence_pack_summary.json`;
- `local_provider_evidence_pack_report.md`;
- `local_provider_evidence_gate_results.csv`;
- `local_provider_evidence_blockers.csv`;
- `local_provider_evidence_next_actions.csv`;
- `local_provider_evidence_artifact_index.csv`.

## Recommendations

Possible recommendations:

- `reject`;
- `fixture_only_continue`;
- `ready_for_separate_local_provider_design_pr`.

`ready_for_separate_local_provider_design_pr` means the fixture-only evidence is
good enough to propose a separate design PR. It is not approval to implement a
model provider, run a model, process private PDFs, or use private data.

## Design Review Handoff

The evidence pack leads only to the design-review packet described in
`docs/ratecon_local_provider_design_pr_template_v1.md`. Generate that packet
with:

```powershell
python scripts/create_ratecon_local_provider_design_review.py ^
  --evidence-pack-summary .local_outputs/ratecon_local_provider_evidence_pack/local_provider_evidence_pack_summary.json ^
  --output-dir .local_outputs/ratecon_local_provider_design_review ^
  --confirm-private-local-run
```

The design review can only recommend `design_pr_ready` for a future design PR.
It cannot approve runtime model execution, private PDF processing, OCR,
external calls, private execution, provider-registry unblocking, model weight
downloads, or a provider implementation. A future actual implementation PR
still requires separate approval and must satisfy
`docs/ratecon_local_provider_future_implementation_acceptance_criteria_v1.md`.

## Blocking Conditions

The pack recommends `reject` if any artifact indicates:

- model execution;
- PDF processing;
- OCR;
- external calls;
- private data use;
- auto-accept safety failure;
- stop review-required failure;
- unsafe provider config;
- secret-like provider config keys;
- local private execution approval;
- cloud approval.

Missing smoke output recommends `fixture_only_continue`, not approval.

## Artifact Index

The artifact index records:

- artifact name and type;
- path;
- whether the file exists;
- whether it is safe to commit;
- whether the path indicates private-value risk;
- whether it was generated from fixtures only;
- whether it is required for review.

Anything under `.local_outputs` is marked `safe_to_commit=false`. Paths that
look private, such as `.local_outputs/private_...`, are marked as private-value
risk.

## Files That Must Never Be Committed

Do not commit:

- `.local_outputs/`;
- private PDFs;
- private gold labels;
- private audit/evaluation/review outputs;
- private hybrid templates;
- model outputs containing private data;
- raw extracted text;
- API keys;
- provider configs containing secrets;
- local model files or weights;
- embeddings or vector stores containing private content;
- readiness/evidence/design review packs containing private values.

## Future Design PR Requirements

A future local-provider design PR must include:

- validated readiness file;
- safe provider config;
- fixture smoke output;
- evidence pack with no blockers;
- explicit statement that implementation is not approved by the evidence pack;
- unchanged production extraction behavior;
- review-required stops and `auto_accept=false`.

## Production and Stop Policy

Production extraction remains unchanged. Stops remain review-required. A future
model result cannot be production auto-accepted in this evaluation phase.
