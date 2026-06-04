# RateCon Model-Assisted Evaluation Plan V1

## Executive Summary

The validated manual/hybrid workflow is now the baseline for future
model-assisted filling experiments. This PR does not add a live model
integration. It adds only the local contracts, stub output generator, benchmark
wrapper, and tests needed to evaluate future model-assisted
`ratecon_hybrid_extraction_result_v1` JSON safely.

## What Manual/Hybrid Validation Proved

- Manual filling can produce contract-valid hybrid result JSON for the full
  private corpus.
- The benchmark can distinguish exact, review-required uncertain gold,
  non-RC/BOL-POD no-action, and unsafe outputs.
- Review-first stop policy is workable across the corpus.
- Scalar and stop evaluator cleanup can be handled without changing production
  extraction.

## What It Did Not Prove

- It did not prove production auto-extraction is ready.
- It did not prove stops can be auto-accepted.
- It did not prove any model can reproduce the manual result quality.
- It did not validate cloud processing of private documents.
- It did not remove the requirement for human review.

## Why Model-Assisted Filling Is Next

The manual baseline shows the target output shape is achievable. The next useful
question is whether a future local or approved model-assisted workflow can fill
the same contract with equal or better review-draft quality while preserving
evidence, review-required stops, and privacy. That must be evaluated with the
same benchmark before any production discussion.

## Production Extraction Must Not Change

This stage is evaluation-only. Production and legacy output remain unchanged.
Resolver thresholds, selected stop output, broker-specific parsing, OCR, and
cloud/model integrations are out of scope.

## Evaluation Architecture

1. Private documents remain local.
2. A future provider produces `ratecon_hybrid_extraction_result_v1`.
3. The result is wrapped in `ratecon_model_assisted_submission_v1` metadata.
4. The model-assisted benchmark validates the wrapper and embedded hybrid
   result.
5. The existing hybrid benchmark scores extracted hybrid results.
6. Results are compared to the manual full-corpus baseline.
7. Stops remain `requires_human_review=true`.
8. Stops remain `auto_accept=false`.

## Provider Categories

- `stub`: no model, used for harness testing.
- `manual_baseline`: already validated manual outputs.
- `local_model`: future local-only model provider, still disabled by default.
- `cloud_model`: future only, rejected in this phase unless a later explicit
  privacy-approved flag is added.

## Provider Adapter Registry

Provider experiments must go through the disabled-by-default adapter registry.
The current registry exposes:

- `stub_empty_v1`: the only runnable provider in this phase;
- `manual_baseline_reference_v1`: reference-only comparison metadata;
- `local_model_placeholder_v1`: blocked until a later explicit local-only PR;
- `cloud_model_placeholder_v1`: blocked until explicit privacy approval and a
  later PR.

Use `scripts/ratecon_model_provider_cli.py list-providers` to inspect provider
status and `validate-config` before any dry-run planning. The provider registry
does not execute models.

## Privacy Rules

- No private PDFs or raw extracted text are committed.
- No API keys are stored in the repo.
- Default logs and reports do not include private raw values.
- Model prompts and responses containing private values stay local-only.
- External calls must be false for this phase.

## Success Metrics

- `external_call_made=false` for every submission.
- `offline_only=true` for every provider.
- 0 schema errors.
- 0 missing evidence for filled values.
- 0 stop auto-accept violations.
- 0 unsafe wrong stops.
- Model output quality is compared against the manual baseline, not production
  output.

## Stop Conditions

Stop the evaluation if any submission:

- calls a model/API unexpectedly;
- processes private PDFs outside the approved local workflow;
- sets stop `auto_accept=true`;
- makes stops not review-required;
- includes filled values without evidence;
- produces unsafe wrong stops.

## Next 30-Day Pilot Plan

1. Use the stub provider to verify the harness and reports.
2. Prepare a small local-only model provider adapter in a later PR, disabled by
   default.
3. Run model-assisted outputs on a small private batch only after explicit
   approval.
4. Compare against the manual baseline after every run.
5. Keep all model outputs review-first and local-only.
6. Decide whether model-assisted filling reduces manual effort without
   increasing unsafe wrong or missing-evidence rates.

## Local Provider Readiness Gates

Any future local provider experiment must first pass the readiness-gate workflow
in `docs/ratecon_local_provider_readiness_gates_v1.md`. The readiness CLI and
fixture-only smoke test verify the approval checklist, provider config policy,
registry blockers, stub submissions, and benchmark comparison without calling a
model or processing PDFs. These gates do not approve implementation or private
execution; they define the evidence required for a later PR.

The review evidence should then be bundled with
`docs/ratecon_local_provider_evidence_pack_v1.md`. The evidence pack summarizes
whether the fixture-only scaffold is ready for a separate local-provider design
PR. It does not approve live model integration.

## Design Review Before Implementation

An accepted evidence pack leads only to the design-review packet and PR
checklist in `docs/ratecon_local_provider_design_pr_template_v1.md`. The design
review defines acceptance criteria for a possible future implementation PR; it
does not approve execution of OpenAI, Claude, Gemini, local VLMs, OCR, PDF
processing, or any real provider.

Actual local-provider implementation remains a separate PR with separate
approval and must satisfy
`docs/ratecon_local_provider_future_implementation_acceptance_criteria_v1.md`.
Production extraction, selected stop output, review-required stops, and
`auto_accept=false` remain unchanged by evidence or design review alone.
