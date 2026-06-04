# RateCon Candidate Model Ownership v1

This note defines ownership for RateCon candidate model contracts. It is an
audit and governance artifact only. It does not change extraction behavior,
resolver behavior, scoring, thresholds, output schemas, or selected output.

## Canonical Owner

`app/document_ai/field_candidate_provenance.py` is the canonical candidate
contract for new document AI extraction candidates. New candidate schema fields,
source metadata, confidence metadata, provenance metadata, and adapter behavior
must be coordinated there or in an explicitly documented support-policy module.

`app/document_ai/field_candidate_generators.py` is a generator and orchestration
layer. It may assemble candidates from text, layout, broker-template, OCR shadow,
or legacy adapters, but it should not become a new candidate schema owner.

`app/document_ai/field_candidate_resolver.py` consumes candidate records and
produces resolution/review states. It must not own new candidate schema fields
unless those fields are first coordinated with the canonical candidate contract.
Resolver threshold or selection changes require a separate behavior-change PR.

## Compatibility Surfaces

`app/document_ai/ratecon_candidates.py` is a legacy RateCon candidate compatibility surface
unless a later audit proves otherwise. It preserves older candidate shapes and
constants for existing fake/anonymized candidate extraction tests and
compatibility flows.

`app/document_ai/ratecon_candidate_generators.py` is a legacy compatibility
generator surface unless a later audit proves otherwise.

`app/document_ai/ratecon_candidate_extraction.py` and
`app/document_ai/ratecon_field_resolution.py` remain compatibility extraction
and resolution surfaces. Do not delete, rename, or consolidate these modules
until import graph evidence and behavior-pinning tests prove a separate cleanup
is safe.

Intake candidate builders, including
`app/market_intelligence/intake/rate_confirmation_intake.py` and
`app/document_ai/ratecon_intake_draft.py`, are boundary adapters. They are not
canonical candidate model owners.

## Change Rules

- Do not add new field/source/confidence constants in random modules.
- Do not change candidate shapes without evaluator and measurement tests.
- Do not change resolver thresholds in a candidate ownership cleanup.
- Do not change candidate confidence values or source names without a separate
  behavior review.
- Do not delete legacy candidate modules until import graph and tests prove
  they are unused or safely adapted.
- Keep private/local-only candidate values protected. Generated local outputs,
  private PDFs, raw extracted text, gold labels, benchmark outputs, and review
  packets must not be committed.

## Audit Command

Run the local-only static audit before planning any candidate cleanup:

```powershell
python scripts/audit_ratecon_candidate_model_ownership.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_candidate_model_ownership_audit `
  --confirm-local-audit-run
```

The audit uses static AST/text analysis only. It does not import project modules,
execute extraction or resolver code, process PDFs, run OCR, call Google, or call
model/cloud services.

## Required Tests Before Behavior Changes

Any future behavior-changing candidate PR must include tests that pin:

- candidate field/source/confidence metadata;
- candidate output shape and schema compatibility;
- resolver review/selection behavior;
- private/local output redaction behavior;
- architecture boundaries for document AI, intake, integrations, and model/OCR
  surfaces.
