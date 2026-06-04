# RateCon Local Provider Design PR Template v1

Use this template for a future design-only PR after a fixture-only evidence pack
recommends `ready_for_separate_local_provider_design_pr`.

This template is not implementation approval. It does not approve model
execution, PDF processing, OCR, private document processing, external calls, or
model weight downloads. Implementation requires a separate PR and separate
approval.

## PR Title Template

```text
RateCon local provider design: <provider name> fixture-only contract review
```

## Summary

- Design review ID:
- Provider name:
- Evidence pack ID:
- Evidence pack recommendation:
- Design review recommendation:
- This PR is design-only:
- Implementation PR requested: no
- Runtime model execution allowed: no

## Scope

- Define provider contract, safety gates, fixture tests, benchmark reports, and
  review checklist only.
- Do not add a provider implementation.
- Do not change production or legacy output.
- Do not change selected stop output.
- Do not relax provider registry blockers.
- Do not lower resolver thresholds.
- Do not add broker-specific regexes.

## Forbidden Actions

- No OpenAI, Claude, Gemini, local VLM, OCR, or real model calls.
- No cloud calls or external service calls.
- No local model execution.
- No PDF processing.
- No OCR.
- No private PDF, private raw text, or private image input.
- No model weight downloads.
- No gold-label edits.
- No filled hybrid-template edits.
- No committed prompt or response logs containing private values.
- No committed provider configs containing secrets.
- No committed local model files, weights, embeddings, or vector stores.

## Required Gates

- Evidence pack recommendation is `ready_for_separate_local_provider_design_pr`.
- Design review recommendation is `design_pr_ready`.
- `design_only=true`.
- `implementation_pr_requested=false`.
- `runtime_execution_allowed=false`.
- `pdf_processing_allowed=false`.
- `ocr_allowed=false`.
- `external_calls_allowed=false`.
- `model_weight_download_allowed=false`.
- `fixture_only_inputs=true`.
- Stops remain review-required.
- `auto_accept` remains false.

## Required Fixture Tests

- Design-review contract tests cover ready, incomplete, rejected, and unsafe
  permission states.
- CLI tests prove `--confirm-private-local-run` is required.
- CLI tests prove output is restricted to `.local_outputs`.
- Fixture-only smoke tests remain required before implementation work.
- Provider registry tests still prove local and cloud placeholders are blocked.

## Required Benchmark Reports

- Model-assisted benchmark wrapper remains the benchmark path.
- Future implementation benchmark must compare to the manual baseline.
- Reports must include schema errors, missing evidence, auto-accept violations,
  unsafe wrong stops, and manual baseline deltas.
- Any safety failure blocks progression.

## Required Safety Proof

- Production extraction remains unchanged.
- Legacy output remains unchanged.
- Selected stop output remains unchanged.
- Stops remain `requires_human_review=true`.
- Stops remain `auto_accept=false`.
- Gold labels and filled hybrid templates are unchanged.
- Design review output cannot unblock providers.

## Required Privacy Proof

- No secrets are committed.
- No private values appear in prompts, response logs, fixtures, or reports.
- No private PDFs, raw extracted text, private images, or private local outputs
  are committed.
- No local model files, model weights, embeddings, or vector stores are
  committed.
- Default report redaction remains required.
- Generated design review files are written only under `.local_outputs`.

## Rollback Plan

- Revert the design-only docs, fixtures, and validation helpers.
- Leave production extraction untouched.
- Leave provider registry blockers in place.
- Remove any generated `.local_outputs` packets locally; they must not be in
  git.

## Review Signoff Checklist

- [ ] Evidence pack only led to a design review.
- [ ] Design review only led to this design PR.
- [ ] This PR does not approve implementation.
- [ ] This PR does not approve model execution.
- [ ] Implementation requires a separate approved PR.
- [ ] Provider registry blocks remain intact.
- [ ] Stub remains the only runnable provider.
- [ ] Stops remain review-required.
- [ ] `auto_accept` remains false.
- [ ] Production extraction remains unchanged.
