# RateCon OCR Ownership Status v1

This document records the current RateCon OCR ownership and status. It is an
architecture and governance note only. It does not approve OCR execution, PDF
processing, extraction behavior changes, or production output changes.

## Current Status

1. OCR production path is not implemented.
2. Optional OCR shadow-local diagnostics exist for private/local review.
3. OCR is disabled by default.
4. OCR dependencies are not mandatory project dependencies.
5. Local Tesseract and `pytesseract` support is diagnostic-only.
6. OCR output must never be auto-accepted into production output.
7. OCR stop assembly, geometry, and table reconstruction are experimental
   shadow profiles.
8. OCR must remain behind explicit local/private flags.
9. OCR must not call cloud OCR, AI/model services, Google, or other external
   services.
10. OCR temp text, images, TSV, raw extracted text, and local OCR outputs must
    never be committed.
11. Any future production OCR path requires separate approval and tests.

## Ownership

The OCR ownership surfaces are:

- `app/document_ai/ocr_provider_contract.py`: optional local/shadow OCR provider
  contract and safe summary helpers.
- `app/document_ai/tesseract_ocr_provider.py`: optional local Tesseract provider
  implementation for explicitly requested shadow diagnostics.
- `app/document_ai/ocr_stop_block_assembler.py`: experimental OCR stop block
  diagnostic candidate assembly.
- `app/document_ai/ocr_stop_geometry_assembler.py`: experimental OCR geometry
  stop diagnostic candidate assembly.
- `app/document_ai/ocr_stop_table_reconstructor.py`: experimental OCR table
  reconstruction diagnostics.
- `app/document_ai/ratecon_ocr_candidate_policy.py`: OCR candidate policy
  constants for shadow/local candidate handling.

The private measurement CLI may expose OCR flags only as explicit local/shadow
diagnostic controls. Those flags do not make OCR production behavior.

## Required Guardrails

Any future OCR provider or production OCR proposal must prove:

- no production output changes by default;
- no private output commits;
- no raw OCR text, temp images, TSV, or PDF artifacts committed;
- no model, cloud OCR, Google, or external service calls;
- no auto-accept stops;
- review-required by default;
- dependencies remain optional unless a separately approved dependency PR says
  otherwise;
- fixture-only tests pass before any private/local pilot command is considered.

## How To Audit

Run the local-only static audit:

```powershell
python scripts/audit_ratecon_ocr_ownership_status.py `
  --repo-root . `
  --output-dir .local_outputs/ratecon_ocr_ownership_status_audit `
  --confirm-local-audit-run
```

The audit uses AST/text parsing only. It does not import project modules, run
OCR, check Tesseract, process PDFs, read `.local_outputs/`, read
`data/private_ratecons/`, call Google, or call AI/model/cloud services.

Generated audit outputs are local-only and must not be committed.

## Future Decision Points

Do not delete OCR modules until the static ownership/status audit is reviewed.
Do not productionize OCR in a cleanup PR. A future OCR implementation proposal
must be a separate PR with explicit scope, safety proof, fixture tests, private
data handling rules, and review-required output behavior.

This document does not claim OCR accuracy improvement.
