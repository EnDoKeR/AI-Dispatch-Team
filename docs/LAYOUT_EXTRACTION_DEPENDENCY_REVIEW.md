# Layout Extraction Dependency Review

This document records the dependency review criteria for a future layout
provider. No dependency is added in the current layout-aware extraction scaffold.

## Current Position

The current RateCon pipeline can triage PDFs and extract text locally through
existing optional `pypdf` paths. `pypdf` is not a project-wide requirement in
`requirements.txt`; the file explicitly keeps optional/manual PDF and external
integrations out of core requirements until accepted as active integrations.

The current layout-aware block defines normalized contracts and synthetic tests
only. Real PDF layout extraction remains a future provider implementation block.

## Provider Interface

A future provider should return a normalized `LayoutExtractionArtifact`:

```text
provider-specific PDF read
-> words / lines / blocks / tables / coordinates
-> normalized LayoutExtractionArtifact
-> layout-aware candidate generators
-> conservative resolver
```

The provider boundary must keep raw text in memory unless a future local-only
artifact explicitly allows redacted storage. Shareable summaries must contain
only aliases, statuses, counts, roles, scopes, field names, warning codes, and
blocker categories.

## Review Criteria

Every provider candidate must be reviewed for:

- license;
- install complexity;
- Windows compatibility;
- table extraction quality;
- word and line coordinate support;
- page rendering support;
- behavior on scanned PDFs or lack of scanned-PDF support;
- interaction with the existing safe measurement harness;
- future SaaS or commercial-use implications;
- testability with fake/synthetic fixtures;
- ability to avoid printing or saving raw private text.

If exact details are not verified locally, the decision must say `needs
verification before adding dependency`.

## Current Extractor Path

The existing `pypdf` path is useful for text-layer extraction and PDF triage.
It does not provide a complete normalized table/word/block layout artifact in
the current project. It can remain the safe text path while layout provider
contracts are developed.

Decision status: keep existing optional/manual role. Do not add a new
dependency in this block.

## pypdf Candidate Role

Possible future role:

- continue text-layer extraction;
- provide basic page text for classification;
- possibly provide limited layout hints if available through the installed
  version and verified locally.

Known decision gap:

- coordinate, table, and reading-order quality must be verified before treating
  it as a layout provider.

License and operational details: needs verification before expanding use.

## pdfplumber Candidate Role

Possible future role:

- word-level coordinates;
- line/block reconstruction;
- table-like extraction;
- PDF page geometry.

Review needed before adoption:

- license;
- Windows install behavior;
- dependency chain;
- table quality on synthetic and local private measurement samples;
- whether it can run without rendering scanned pages into OCR;
- safe handling of raw text and coordinates.

Decision status: not added in this block. Needs verification before adding
dependency.

## PyMuPDF Candidate Role

Possible future role:

- fast page parsing;
- word/block coordinates;
- page geometry;
- optional rendering support for a later non-OCR visual QA path.

Review needed before adoption:

- license and commercial/SaaS implications;
- Windows install behavior;
- output stability across versions;
- coordinate and block quality;
- safe local-only operation;
- whether rendering support creates any new privacy or artifact-storage risk.

Decision status: not added in this block. Needs verification before adding
dependency.

## Camelot/Table Extraction Candidate Role

Possible future role:

- table extraction for table-heavy confirmations;
- stop and rate-table structure when text-layer table geometry is reliable.

Review needed before adoption:

- license;
- install complexity on Windows;
- external system dependencies, if any;
- quality on freight/tender table structures;
- whether table extraction works without OCR;
- whether output can be normalized into `LayoutTable` and `LayoutTableCell`.

Decision status: not added in this block. Needs verification before adding
dependency.

## OCR Tools Are Out Of Scope

OCR tools are not part of this layout-provider block. Tesseract, PaddleOCR, and
other OCR engines belong to a separate local OCR design checkpoint with its own
privacy policy, artifact contract, dependency review, fixtures, and measurement
plan.

## Explicit Decision

No dependency is added in this block.

The current block will:

- define layout contracts;
- create synthetic layout fixtures;
- build dependency-free layout indexes and proximity helpers;
- generate layout-aware candidates from synthetic artifacts;
- prove resolver readiness with fake data;
- document the next provider implementation plan.

Provider selection and implementation are deferred until the next block, after
the normalized artifact contract and fake tests are in place.
