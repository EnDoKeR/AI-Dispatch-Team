# Layout Provider Decision: pdfplumber Pilot

This document records the decision to pilot `pdfplumber` as the first real
digital-text layout provider after the dependency-free layout-aware extraction
scaffold.

## Measurement Basis

The calibrated safe private measurement currently shows:

- 18 total documents measured;
- 10 extraction-relevant documents;
- 6 normal load-movement documents;
- 4 TONU/payment confirmation documents;
- 4 OCR-needed / empty-text documents;
- normal-load blockers still include broker identity, rate, stops, dates, and
  weight.

The dominant blocker is not scanned-document OCR. The dominant blocker is
extracting better structured evidence from digital-text transportation
confirmation documents whose fields appear in tables, route-detail sections,
PU/SO sections, payment summaries, continuation pages, and broker-specific
layouts.

## Decision

Use `pdfplumber` as the first layout provider candidate, behind an explicit
provider boundary that returns normalized `LayoutExtractionArtifact` objects.

This decision does not make layout extraction production-ready. It only allows
safe local measurement of whether digital-text layout evidence improves
candidate coverage and field status.

## Why Layout Provider Is Next

The project already has:

- document/page/section classification;
- extraction scope filtering;
- dependency-free layout contracts;
- synthetic layout fixtures;
- layout indexing and label-value proximity helpers;
- layout-aware candidate generators;
- resolver readiness tests.

The next measurable step is to populate those contracts from real digital-text
PDF pages and compare status-only deltas against the text-only baseline.

## Why OCR Is Deferred

OCR-needed documents are present, but they are not the majority blocker in the
current calibrated measurement. OCR requires a separate design checkpoint for:

- OCR artifact contracts;
- privacy and raw text handling;
- dependency review;
- Windows install behavior;
- scanned fixture strategy;
- measurement and validation rules.

No OCR tool is added in this block.

## Why Vision Is Deferred

Vision fallback remains a later gated design topic. It should only be
considered after deterministic digital-text routes and local OCR options are
measured and shown insufficient. This block does not add Vision AI, cloud APIs,
or remote extraction.

## Why pdfplumber First

`pdfplumber` is selected as the first candidate because it is aimed at
digital-text PDF inspection and can expose page geometry, words, and table-like
structures that map naturally to the existing `LayoutExtractionArtifact`
contracts.

It is a better first pilot than OCR or Vision for this measured blocker because
the current problem is structured digital text, not primarily image-only pages.

## Deferred Candidates

PyMuPDF is deferred pending a separate dependency and licensing/legal review,
including future SaaS or commercial-use implications.

Camelot is deferred as a table-specific provider candidate. It may be useful
if `pdfplumber` table extraction is not sufficient, but it has its own install,
system dependency, table-quality, and supportability questions.

No OCR, ML, cloud, or table-extraction extras are added with this decision.

## Provider Selection Criteria

Provider candidates must be evaluated for:

- Windows install behavior;
- license and future SaaS/commercial implications;
- coordinate support;
- word, line, block, and table extraction quality;
- page object support;
- behavior on scanned or empty-text PDFs;
- compatibility with the current safe measurement harness;
- no raw text logging;
- no raw text saved to shareable outputs;
- deterministic testability with fake/synthetic fixtures.

If exact license or operational details are not verified locally, they remain
`needs verification before adding dependency`.

## pdfplumber Acceptance Criteria

The provider pilot is acceptable only if it:

- converts digital PDF pages into `LayoutExtractionArtifact`;
- records page count, page geometry, words, lines, blocks, and tables where
  available;
- sets `raw_text_included` to false for safe artifacts by default;
- keeps raw text in memory only;
- does not print filenames or private values by default;
- supports safe status-only measurement deltas;
- returns safe failure or empty-text statuses for scanned/empty/broken PDFs;
- does not run candidates, resolver, intake, DispatchCase creation,
  DecisionEngine, Telegram, or Event Timeline writes inside the provider.

## Safety Boundary

The provider boundary may read local PDFs only when explicitly invoked by a
local CLI or measurement flow. It must not copy private PDFs into the repo, and
generated private measurement outputs must remain ignored local files.

Safe shared output remains limited to aliases, statuses, counts, field names,
warning codes, blocker categories, and provider status counts.
