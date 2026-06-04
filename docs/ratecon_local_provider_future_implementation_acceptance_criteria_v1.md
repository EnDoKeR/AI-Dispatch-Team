# RateCon Local Provider Future Implementation Acceptance Criteria v1

This document defines what a future actual local-provider implementation PR
must prove. It does not implement a provider and does not approve model
execution.

## Required Implementation Posture

- The provider must remain disabled by default.
- The provider must require explicit opt-in configuration.
- No private run may occur without explicit user confirmation.
- No private PDF processing may occur until the readiness gate allows it.
- Private pilot execution must use a separate manual command.
- Private pilot execution requires separate approval after the design PR.
- The implementation must write generated files only under `.local_outputs`.

## Required Privacy Criteria

- No secrets may be committed.
- No provider config containing secrets may be committed.
- No raw prompt logs containing private values may be committed.
- No raw response logs containing private values may be committed.
- No private PDFs, private raw extracted text, or private images may be
  committed.
- No local model files or downloaded model weights may be committed.
- No embeddings or vector stores containing private content may be committed.
- The provider must support full redaction by default.

## Required Output Criteria

- Generated submissions must validate `ratecon_model_assisted_submission_v1`.
- Embedded hybrid results must validate
  `ratecon_hybrid_extraction_result_v1`.
- Model output must not auto-accept stops.
- Stops must remain review-required.
- Raw model responses must be private-local-only by default.
- Default reports must not include private values.

## Required Benchmark Criteria

- Fixture-only tests must pass first.
- Fixture smoke must pass before private implementation testing.
- The model-assisted benchmark wrapper must run on generated submissions.
- Benchmark output must compare against the manual baseline.
- Benchmark reports must include schema errors, missing evidence,
  auto-accept violations, unsafe wrong stops, and manual baseline deltas.
- Any safety failure blocks progression.
- Any unsafe wrong stop blocks progression.
- Any missing evidence for filled values blocks progression.

## Required Provider Registry Criteria

- Local and cloud placeholders must remain blocked until the implementation PR
  explicitly changes registry behavior.
- Any registry change must be reviewed in the implementation PR.
- Design review output cannot unblock providers.
- The stub must remain the only runnable provider until implementation approval
  explicitly changes that state.

## Required Private Pilot Criteria

- Private pilot requires a separate manual command.
- Private pilot requires explicit confirmation.
- Private pilot must write only under `.local_outputs`.
- Private pilot must not commit generated outputs.
- Private pilot must not run if readiness gates fail.
- Private pilot must stop on any unsafe wrong stop or auto-accept violation.

## Required Non-Goals

- Do not claim production extraction improvement from implementation fixtures.
- Do not change production extraction unless a separate production PR is
  approved.
- Do not change selected stop output.
- Do not lower resolver thresholds.
- Do not add broker-specific regexes as part of provider implementation.
