# RateCon Hybrid Benchmark Design v1

Date: 2026-06-03

Scope: benchmark group design for evaluating future hybrid document
understanding approaches on the current private RateCon set. This document
contains no private values, filenames, PDFs, raw extracted text, OCR output, or
gold labels.

## Benchmark Principles

The benchmark should test document patterns, not individual private documents.
Each group represents a visual/semantic shape that the current deterministic
stop parser struggles to prove safely.

Evaluation rules:

- no private values in committed artifacts;
- use aliases or pattern groups only;
- keep stops review-required during phase 1;
- compare hybrid drafts separately from selected deterministic output;
- require page/source evidence for every proposed field;
- keep BOL/POD/non-RC documents out of RateCon failure denominators.

## Current Baseline

| Area | Baseline |
|---|---:|
| Load number | 25 correct / 1 wrong / 5 missing |
| Total carrier rate | 26 correct / 3 wrong / 2 missing |
| Pickup selected stops | 0 exact / 17 partial / 5 wrong / 3 missing |
| Delivery selected stops | 0 exact / 12 partial / 5 wrong / 4 missing |
| Stop gold/evaluator issues | 0 |
| Patch template rows | 0 |

## Benchmark Groups

### 1. TQL Compact Table Rows

Why current parser fails:

- location, date, and time are visually aligned but can be fragmented in linear
  text;
- current row/block proof remains weak;
- duplicate fragments can look like competing locations.

Hybrid model should extract:

- pickup/delivery role;
- city/state or full location;
- date;
- time or appointment window;
- page/source evidence for the compact row.

Required validation:

- role-specific row association;
- no cross-role date/time mixing;
- evidence row or table proof.

Expected review behavior:

- review-required stop drafts;
- human confirms row-level association.

Success criteria:

- draft has one coherent stop object per role when source evidence supports it;
- no payment/instruction text enters stop location.

### 2. Express Pickup/Drop Table Blocks

Why current parser fails:

- pickup/drop blocks can separate date, time, location, and contact columns;
- contact/reference text may contaminate location candidates;
- multiple locations can be generated from one visual block.

Hybrid model should extract:

- pickup/drop role;
- stop index;
- location components;
- date/time components;
- contact/reference excluded from location.

Required validation:

- contact/reference exclusion;
- block-level evidence;
- no role inversion.

Expected review behavior:

- review-required drafts with block evidence.

Success criteria:

- one structured stop draft per pickup/drop block;
- contact/reference fields do not become addresses.

### 3. Wilson / Beemac / Ryan PU/SO Rows

Why current parser fails:

- PU/SO labels, date columns, and address/name/city rows require visual
  grouping;
- line ordering can split the row into fragments;
- payment or terms boundaries can be nearby.

Hybrid model should extract:

- PU/SO role;
- facility/name when visible;
- address/city/state/ZIP when visible;
- date/time/window when visible.

Required validation:

- PU/SO role separation;
- row/section boundary proof;
- payment/terms exclusion.

Expected review behavior:

- review-required drafts;
- unclear rows remain manual review.

Success criteria:

- no fused stop without row/section proof;
- no broad fusion from nearby unrelated components.

### 4. Axle / ADICA Scanned McLeod-Like Pages

Why current parser fails:

- scanned or image-heavy pages depend on OCR quality;
- OCR line order and TSV geometry can split stop blocks;
- source confidence and bounding boxes may be incomplete.

Hybrid model should extract:

- role label;
- stop index;
- location/date/time components;
- image evidence region.

Required validation:

- OCR/image evidence available;
- role and stop index not inferred from gold;
- uncertain OCR output goes to review.

Expected review behavior:

- review-required drafts with image/page evidence;
- low OCR quality triggers manual-only fallback.

Success criteria:

- draft coverage improves without unsafe role/location swaps.

### 5. SPI / Fello / Landstar Structured Blocks

Why current parser fails:

- shipper/consignee blocks may contain expected date, target window, shipping
  hours, and location lines in section form;
- date/time labels are not always table columns;
- multiple date-like values can appear in nearby instructions.

Hybrid model should extract:

- shipper pickup / consignee delivery role;
- city/state/address/facility when visible;
- expected date;
- target window or shipping/receiving hours when visible.

Required validation:

- section boundary proof;
- instruction/footer date exclusion;
- no contact/reference-only location.

Expected review behavior:

- review-required draft;
- missing time/window is allowed when absent from source.

Success criteria:

- known-absent values remain no-action;
- visible date/time stays inside the correct section.

### 6. IEL / TMC Route Sections

Why current parser fails:

- route sections can look like prose rather than tables;
- pickup/delivery blocks may have partial location or city-level data;
- stop order may rely on headings and visual grouping.

Hybrid model should extract:

- route role;
- city/state/date where visible;
- address/facility only when present;
- review reasons for city-level-only stops.

Required validation:

- source supports city-level-only classification;
- no invented facility/address;
- review-required output.

Expected review behavior:

- human confirms city-level stop if full address is absent.

Success criteria:

- no false gold-review rows for known-absent values;
- no fabricated address.

### 7. Verbal Agreement / City-Level Only

Why current parser fails:

- source may not contain full address or time/window;
- exact stop scoring is impossible;
- partial/city-level data must not become unsafe by evaluator confusion.

Hybrid model should extract:

- city/state/date if visible;
- missing components as null;
- explicit review reason for source-limited stop.

Required validation:

- missing time/window is not a gold defect when source lacks it;
- no fabricated values.

Expected review behavior:

- review-required city-level draft;
- no patch template row unless source visibly contains a missing value.

Success criteria:

- source-limited stops are classified as review-required/no-action rather than
  code/evaluator errors.

### 8. Non-RC BOL/POD

Why current parser fails:

- supplemental documents can contain locations, dates, signatures, and charges
  that resemble RateCon fields;
- they should not count as failed RateCon extraction.

Hybrid model should extract:

- document type classification only;
- no RateCon stop draft unless explicitly classified as RateCon.

Required validation:

- BOL/POD/non-RC gate;
- no RateCon denominator pollution.

Expected review behavior:

- supplemental/manual review if classification is uncertain.

Success criteria:

- non-RC documents filtered before extraction scoring.

## Evaluation Matrix

| Group | Current parser failure | Hybrid target | Required validator |
|---|---|---|---|
| TQL compact table rows | Row proof and duplicate fragments | Row-backed stop draft | Same-row evidence gate |
| Express pickup/drop blocks | Contact/reference contamination | Block-backed stop draft | Contact/reference exclusion |
| PU/SO rows | Role/date/location association | Role-row stop object | Role boundary gate |
| Scanned McLeod-like pages | OCR and geometry fragmentation | Image/OCR-backed draft | OCR evidence gate |
| Structured blocks | Section/date leakage | Section-backed draft | Instruction/footer exclusion |
| Route sections | Prose-like partials | City-level review draft | Source-limited stop gate |
| City-level only | Missing source values | Known-absent review draft | No fabrication gate |
| Non-RC BOL/POD | Denominator pollution | Classification only | Document classification gate |

## Reporting Requirements

The benchmark should report:

- document classification accuracy;
- stop draft coverage;
- unsafe wrong stop draft count;
- exact and dispatch-usable draft counts;
- evidence completeness;
- review-required count;
- selected deterministic metrics unchanged;
- load/rate unchanged;
- private output path only;
- zero committed private data.

## Next Benchmark Artifact

The next implementation branch should add a local-only benchmark runner that can
load hybrid result JSON files, validate the contract, compare draft groups
against gold/eval summaries, and produce aggregate metrics under
`.local_outputs/`.
