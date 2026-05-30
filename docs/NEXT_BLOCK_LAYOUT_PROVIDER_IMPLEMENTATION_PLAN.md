# Layout Provider Implementation Plan

This plan recorded the provider implementation checkpoint after the
dependency-free layout-aware extraction scaffold. The first provider pilot is
now implemented with `pdfplumber==0.11.9`; this document remains as the
acceptance checklist and follow-up guide.

## Current Implementation Result

- provider boundary: `app/document_ai/layout_provider.py`
- provider: `app/document_ai/pdfplumber_layout_provider.py`
- provider-to-candidate pipeline: `app/document_ai/layout_pipeline.py`
- safe comparison helper: `app/document_ai/layout_provider_comparison.py`
- CLI flags:
  `--layout-provider pdfplumber --enable-layout-candidates --compare-layout-to-text-baseline`
- safe private rerun: 18 docs measured, 6 layout attempts, 6 successes, 12
  skips, 0 provider failures, 4 OCR-needed unchanged.

## Objective

Implemented one local digital-text layout provider that returns normalized
`LayoutExtractionArtifact` records for safe private measurement. The provider
must preserve the current privacy model:

- no raw text printed;
- no raw text saved to shareable outputs;
- no private values in committed fixtures;
- no private PDFs committed;
- no production automation claim.

## Why This Comes Next

The current scaffold defines:

- layout artifact contracts;
- synthetic layout fixtures;
- layout indexing helpers;
- label-value proximity helpers;
- layout-aware rate, stop, and operational candidate generators;
- resolver readiness tests;
- fake-only layout CLI validation.

The next useful measurement needs real digital-text layout artifacts from local
PDFs. That requires choosing and implementing a provider behind the normalized
artifact interface.

## Providers To Evaluate Later

Evaluate these candidates before adding any additional dependency:

- current `pypdf` text path;
- PyMuPDF;
- Camelot or another table provider.

OCR tools are not part of this provider block. Tesseract, PaddleOCR, and Vision
fallbacks require separate design checkpoints.

## Required Verification Before Dependency Adoption

Before adding a provider dependency, verify:

- license;
- Windows install behavior;
- output quality on fake and local private measurement samples;
- table extraction capability;
- word/line/block coordinate support;
- coordinate consistency across pages;
- compatibility with current unit tests;
- whether the provider handles scanned PDFs or only digital text;
- raw-text handling and local-only privacy risks;
- future SaaS/commercial-use implications.

If any item cannot be verified locally, record it as `needs verification before
adding dependency`.

## Provider Interface

The implementation should return:

```text
LayoutExtractionArtifact
```

The provider-specific code should normalize its output into:

- page width and height;
- words;
- lines;
- blocks;
- tables;
- table cells;
- reading order, if available;
- page and section role hints when safely derivable;
- warning codes.

The downstream layout candidate code should not depend on provider-specific
objects.

## Safe Private Measurement Plan

After a provider is implemented or tuned:

1. Run it locally only on an explicitly provided private directory.
2. Keep raw text in memory.
3. Write only ignored local outputs.
4. Compare status-only deltas against the current safe measurement:
   - candidate counts by field;
   - resolved/missing/unresolved/conflict field statuses;
   - normal-load denominator;
   - TONU denominator;
   - blocker categories;
   - review-required count.
5. Share only safe aggregates, aliases, statuses, field names, warning codes,
   and blocker categories.

Do not share filenames, broker names, MC numbers, rates, addresses, dates/times,
load/reference numbers, raw text, local paths, or private notes.

## Non-Goals

The next provider block should not add:

- OCR;
- Vision AI;
- cloud extraction APIs;
- DispatchCase creation;
- DecisionEngine calls;
- Telegram calls;
- Event Timeline writes;
- production readiness claims.

## Exit Criteria

The provider block is complete only when:

- dependency review is updated with verified facts;
- the provider returns `LayoutExtractionArtifact`;
- fake/synthetic tests still pass;
- safe private measurement can compare status-only deltas;
- no private outputs or templates are staged;
- no raw private text is printed or committed.

Current status: criteria satisfied for the initial `pdfplumber` pilot. Further
provider work should be driven by safe candidate/status deltas rather than by
adding more dependencies speculatively.
