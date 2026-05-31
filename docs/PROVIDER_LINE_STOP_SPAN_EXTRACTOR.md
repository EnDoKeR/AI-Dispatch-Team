# Provider-Line Stop Span Extractor

This document defines the direct provider-line stop span extraction block. It
is a correctness/debugging block for digital-text RateCon stop extraction.

## Why This Block Exists

The latest safe private rerun showed that the old stop group pipeline is still
a passthrough:

- raw stop groups: 112;
- premerge groups: 112;
- post single-line cluster groups: 112;
- post row merge groups: 112;
- post section cluster groups: 112;
- post noise filter groups: 112;
- post dedupe groups: 112;
- normalized stops: 112;
- duplicate / noise removed: 0 / 0;
- first changed stage: none;
- passthrough detected: 6 aliases.

Those unchanged stage counts prove that the current raw-stop-group abstraction
is not reducing fragmented provider evidence on real pdfplumber artifacts. The
synthetic wiring tests protect the intended behavior, but the real provider path
still does not give the merge stages enough useful structure to reduce counts.

The next extractor should operate before raw stop group explosion. It should
consume provider layout lines and tables directly, detect stop anchors, build
bounded stop spans, extract fields inside each span, and then create normalized
stops from those spans.

## Old Flow

The old flow is:

1. layout evidence;
2. many raw stop groups;
3. attempted merge/dedupe/noise filtering;
4. normalized stops.

That flow has not reduced the real provider groups. It remains useful for
comparison and regression coverage, but it is not the default path to fix in
this block.

## New Flow

The new flow is:

1. layout lines and tables;
2. stop anchor detection;
3. stop span boundary detection;
4. field extraction inside each span;
5. normalized stop creation;
6. old/new count comparison in safe measurement.

This path is added behind explicit flags. The old stop group pipeline remains
available and is compared side by side with the span extractor.

## Stop Span Concept

A stop span is a bounded section of provider layout evidence centered on a stop
anchor. It includes:

- an anchor line or table row;
- section bounds;
- included line ids and table row ids;
- inferred stop type and sequence;
- field candidates found inside the span;
- warning codes and review reasons.

One span generally becomes one normalized stop. A span may still be ambiguous,
review required, or missing fields. The extractor must preserve those statuses
instead of inventing stop details.

## Supported Layout Families

The synthetic fixtures should cover generic layout families without broker
templates or private values:

- blue-table confirmations with pickup and delivery rows;
- Jay-style `Load At` and `Deliver To` blocks;
- Ryan, Beemac, and McLeod-style `PU` / `SO` sections;
- carrier tender route details;
- SPI/Integrity-style boxed shipper and consignee sections;
- Landstar-style `Stop # Pickup` / `Stop # Drop` route blocks.

These names describe layout shapes only. The committed fixtures must use fake
values and must not include real broker names, MC numbers, rates, addresses,
dates, references, screenshots, PDFs, or private text.

## Decision Gates

Safe measurement must compare old and new stop paths:

- old raw stop groups;
- old normalized stops;
- span anchor count;
- stop span count;
- span normalized stop count;
- span pickup, delivery, and unknown counts;
- span date/time resolved and missing counts;
- span review-required count;
- span passthrough detection.

If the span path still produces one stop per line or does not reduce counts on
provider-like fixtures, the block must be reported as `NOT FIXED`.

If span counts become plausible but date/time fields remain weak, the next block
is span field extraction hardening. If span extraction works on line layouts but
fails on table-heavy layouts, the next block is table-specific extraction or a
Camelot design checkpoint. OCR remains queued only for OCR-needed documents.
Vision remains deferred.

## Implemented Safe Measurement Result

The stop span extractor is available behind:

```text
--enable-stop-span-extractor
--compare-stop-span-to-stop-group-pipeline
```

The latest safe private rerun compared both paths:

- old raw stop groups: 112;
- old normalized stops: 112;
- stop span anchors: 29;
- stop spans: 29;
- span normalized stops: 29;
- span pickup / delivery / unknown: 13 / 14 / 0;
- span date resolved / missing: 8 / 21;
- span time resolved / missing: 10 / 19;
- span review required: 29;
- span passthrough count: 0.

This is not production-ready extraction. It does prove that the new
provider-line path avoids the old passthrough behavior and creates fewer
reviewable stop records. The remaining blocker is value correctness and span
field extraction: all span stops still require review, and many dates/times
remain missing.

## Review Export

The local-only Google Sheets-compatible export includes old/new stop columns:

- `Old Raw Stop Groups`;
- `Old Normalized Stops`;
- `Stop Span Anchors`;
- `Stop Spans`;
- `Span Normalized Stops`;
- `Span Pickup Count`;
- `Span Delivery Count`;
- `Span Unknown Count`;
- `Span Date Resolved`;
- `Span Date Missing`;
- `Span Time Resolved`;
- `Span Time Missing`;
- `Span Review Required Count`;
- `Stop Span Passthrough Detected`;
- `Old vs Span Delta`;
- `Recommended Review Priority`.

These files are local-only ignored outputs. They are intended for local review
or Google Sheets import. Do not commit or paste local-private review values.

## Non-Goals

This block does not add OCR, Vision AI, Camelot, PyMuPDF, broker templates,
cloud APIs, DispatchCase creation, DecisionEngine calls, Telegram calls, Event
Timeline events, or production automation claims.
