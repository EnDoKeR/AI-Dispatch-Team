# Layout Stop Normalization And Evaluation

This document defines the next RateCon extraction hardening layer after
pdfplumber diagnostics and no-regression fusion. It is a measurement and review
readiness block, not a production automation block.

## Why This Follows Diagnostics

The latest safe private diagnostics rerun showed that the provider can see
layout structure:

- tables / cells: 22 / 710;
- stop signals: pickup 37, delivery 44, stop 26, date 5, time 23;
- stop groups: 78;
- fusion worsened fields: none.

That result means the current blocker is not that pdfplumber cannot see layout.
The risk is that raw stop evidence is too noisy and too numerous to trust
directly. The pipeline needs to normalize, deduplicate, sequence, and review
stop evidence before using it to resolve pickup and delivery fields.

## Why Stop Groups Need Normalization

`stop_groups = 78` is useful because it proves the provider and association
layer are finding stop-like evidence. It is risky because raw groups can include:

- duplicate headers across pages;
- repeated table fragments;
- footer or signature noise;
- terms or billing dates that are not stop dates;
- ambiguous stop-like labels without location/date context;
- multi-stop rows that should stay distinct.

The resolver should not consume this raw set as if every group were a final
stop. It should consume a normalized stop set with explicit status, evidence,
warnings, and review flags.

## Terms

Raw stop signal:

Generic layout evidence such as a pickup label, delivery label, stop label,
date label, time label, table row, or section marker. It is not a candidate
stop by itself.

Stop group candidate:

A grouped set of stop-like field candidates from table rows, sections, or text
ordering. It may still be duplicate, noisy, ambiguous, or incomplete.

Normalized stop:

A reviewable stop record with a conservative stop type, optional sequence,
deduplicated source group ids, page/section/table evidence, and field statuses
for location, date, time, reference, notes, and related fields.

Stop set:

The document-level collection of normalized stops, including pickup/delivery
counts, unknown counts, unresolved fields, conflict fields, and warning codes.

Final RateConfirmationIntake stops:

The intake-facing fields produced only after conservative resolver validation.
If the current intake schema is flat, the first safe pickup and delivery may map
to flat fields while extra stops remain review metadata.

## Normalization Goals

The stop normalization layer should:

- deduplicate duplicate stop groups;
- remove header, footer, signature, terms, and billing noise conservatively;
- associate location, date, time, reference, and notes with the correct stop
  when layout evidence is strong;
- preserve multi-stop sequences instead of collapsing them into one pickup and
  one delivery;
- avoid inventing missing dates, times, or locations;
- keep ambiguous stop type or conflicting fields as review-required;
- preserve evidence references and warning codes;
- keep outputs value-free by default.

## Evaluation Goal

Status improvement alone is not enough. A field can move from missing to
resolved while still being wrong. The project needs local-only review artifacts
that let a human compare normalized stop status and, only with an explicit local
private flag, selected values. Shareable outputs must remain aliases, counts,
statuses, field names, confidence buckets, warnings, and blocker categories.

The default review packet is redacted/status-only. Any local-private value
packet must be ignored, clearly marked local-only, never printed to console, and
never pasted into chat or committed.

## Safe Rerun Result

The first safe private rerun with normalized stops reported:

- documents measured: 18;
- layout attempted: 6;
- fusion attempted: 6;
- raw stop groups: 78;
- normalized stops: 78;
- pickup / delivery / unknown stops: 43 / 32 / 0;
- stop review required: 78;
- duplicate / noise removed: 0 / 0;
- stop field statuses: location resolved 78, date missing 78, time missing 76
  and resolved 2, reference resolved 11;
- fusion worsened fields: none;
- OCR-needed unchanged: 4.

This result is useful because it proves that normalized stop records can be
created from provider artifacts. It is not correctness-ready because every
normalized stop still requires review, date fields are still missing, and
deduplication/noise filtering did not reduce the raw group count. The next
default block should harden stop field association and dedupe/noise filtering
before adding Camelot, OCR, Vision, or another provider.

## Calibration Rerun Result

The stop calibration rerun added safe pattern diagnostics and broadened
date/time signal attachment. It reported:

- documents measured: 18;
- layout attempted: 6;
- raw stop groups: 112;
- normalized stops: 112;
- pickup / delivery / unknown stops: 45 / 37 / 30;
- duplicate / noise removed: 0 / 0;
- table row / section context merges: 0 / 0;
- stop review required: 112;
- date candidates generated / attached: 10 / 10;
- time candidates generated / attached: 9 / 9;
- missing date / time fields: 102 / 103;
- pattern counts: `LOCATION_DATE_SPLIT`, `TABLE_CELL_OVER_GROUPING`,
  `TABLE_ROW_NOT_MERGED`, `TIME_CANDIDATE_NOT_ATTACHED`, and
  `PICKUP_DELIVERY_OVERCLASSIFIED`;
- fusion worsened fields: none;
- OCR-needed unchanged: 4.

The result confirms that the next problem is not provider visibility. It is
fragment normalization: provider artifacts are producing more stop-like evidence
than the current normalizer can merge into logical pickup/delivery/stop rows.
The next block should target row/section fragment merging and duplicate/noise
reduction before moving to local value correctness evaluation.

## Review Packet

Private measurement can write a local-only stop review packet:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --write-json --write-csv --write-md --write-stop-review-packet
```

Default packet mode is shareable/status-only. It includes aliases, stop ids,
stop type, sequence, field name, status, confidence bucket, evidence type, page
number, and warning codes. It does not include stop values.

`--include-private-stop-values-local-only` may be used only with
`--write-stop-review-packet`. That mode is for local review only, is ignored by
Git, is marked `LOCAL PRIVATE REVIEW ONLY - DO NOT COMMIT - DO NOT PASTE INTO
CHAT`, and never prints values to console.

## Non-Goals

This block does not add:

- OCR;
- Vision AI;
- Camelot;
- PyMuPDF;
- cloud APIs;
- new dependencies;
- real broker templates;
- DispatchCase creation;
- DecisionEngine calls;
- Telegram calls;
- Event Timeline writes;
- production automation claims.

## Decision Gates

After normalized stop measurement:

- If normalized stops are produced and stop/location/date conflicts decrease,
  move to local evaluation corpus and correctness review.
- If raw stop groups remain high but normalized stops are low, harden stop
  normalization.
- If normalized stops are high but many fields remain review-required, harden
  stop field association.
- If normalized stops match raw stop groups and no duplicates/noise are removed,
  harden stop deduplication and noise filtering.
- If raw and normalized stop counts both increase after date/time calibration,
  harden row/section fragment merging before reviewing private values.
- If provider tables/cells exist but stop groups are poor, revisit provider
  table calibration or design a table-specific provider checkpoint.
- If layout candidates are strong but correctness is unknown, build a local
  private value-review evaluation workflow.
- OCR remains queued only for OCR-needed documents.
- Vision remains deferred.
