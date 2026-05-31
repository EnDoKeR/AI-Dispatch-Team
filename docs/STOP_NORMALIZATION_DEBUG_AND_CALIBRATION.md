# Stop Normalization Debug And Calibration

This document defines the safe debug block after normalized stop extraction. It
is a measurement and calibration block, not a production automation block.

## Why This Block Follows Normalized Stops

The normalized stop block proved that `pdfplumber` can produce useful layout
evidence and that the pipeline can convert raw stop groups into normalized stop
records. The latest safe private rerun also showed that the normalized output is
not yet correctness-ready:

- raw stop groups: 78;
- normalized stops: 78;
- duplicate / noise removed: 0 / 0;
- stop review required: 78;
- date missing: 78 / 78;
- time resolved: 2 / 78.

The blocker is no longer provider visibility. The blocker is stop normalization
correctness.

## Suspicious Signals

`raw_stop_groups == normalized_stops` is suspicious because normalization should
usually merge or discard at least some repeated table fragments, headers,
footers, section labels, or duplicate stop-like records.

`duplicate_removed == 0` and `noise_removed == 0` are suspicious because real
Rate Confirmation packets often contain repeated headers, footers, terms,
billing sections, and signature sections that can look stop-like but should not
be treated as core pickup or delivery stops.

`date missing 78/78` is critical because a location-only stop set cannot
reliably resolve pickup/delivery timing. The issue may be date candidates not
being generated, date candidates being filtered out, or date candidates being
generated but not attached to the right row or section.

`stop_review_required == 78` means the normalized stop output is still a review
artifact, not a resolver-ready stop set.

## Local-Only Private Review Packets

The stop review packet exists to support local correctness review without
turning private documents into tracked fixtures or chat content.

Codex may inspect ignored local-only stop review packets when the user has
explicitly requested a local-private calibration run. That inspection may use
selected private stop values only to classify generic error patterns.

Codex must not print, copy into docs, copy into tests, commit, or paste private
values from the packet. Console and final reports must use only aliases, counts,
statuses, field names, warning codes, and pattern categories.

## Failure Categories

The calibration pass should classify safe error patterns into these categories:

- `over_grouping`: too many stop groups are produced from one logical stop.
- `duplicate_not_merged`: repeated groups survive normalization.
- `header_footer_noise`: headers or footers create stop-like groups.
- `terms_billing_noise`: terms, billing, quick-pay, or remittance text creates
  core stop-like groups.
- `date_candidate_not_generated`: date-like evidence is absent from stop
  candidates.
- `date_candidate_not_attached`: date-like evidence exists but remains separate
  from the stop.
- `time_candidate_not_attached`: time-like evidence exists but remains separate
  from the stop.
- `table_row_association_gap`: table cells are not merged into one stop row.
- `section_association_gap`: section lines are not merged into one stop block.
- `scope_filter_gap`: classification or extraction scope excludes relevant stop
  evidence.
- `pickup_delivery_type_overclassification`: generic stop-like signals are
  labeled pickup or delivery too aggressively.

## Calibration Approach

1. Run the safe private measurement CLI with `--write-stop-review-packet` and
   explicit `--include-private-stop-values-local-only`.
2. Inspect the ignored local packet internally.
3. Print only safe pattern counts and affected aliases.
4. Add fake/synthetic fixtures that mimic generic failure shapes only.
5. Harden table row merge, duplicate/noise filtering, date/time attachment, and
   stop type confidence.
6. Re-run safe private measurement without printing private values.
7. Decide the next block from safe aggregate/status deltas only.

## Calibration Rerun Result

After adding the first debug pass, table/section date-time attachment, generic
stop type calibration, and expanded safe diagnostics, the shareable private
rerun reported:

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
- stop pattern counts:
  - `LOCATION_DATE_SPLIT`: 6;
  - `TABLE_CELL_OVER_GROUPING`: 2;
  - `TABLE_ROW_NOT_MERGED`: 1;
  - `TIME_CANDIDATE_NOT_ATTACHED`: 3;
  - `PICKUP_DELIVERY_OVERCLASSIFIED`: 2;
- fusion worsened fields: none;
- OCR-needed unchanged: 4.

This is a partial improvement only. Date/time candidates now reach normalized
stop diagnostics, and generic stop ambiguity is visible, but raw/normalized stop
counts increased and merge/noise counts remain zero. The next block should
harden grouping/merge logic using the newly exposed pattern counts before a
local value correctness corpus is useful.

## Current Decision Gate

The provenance audit and first grouping-stage refactor confirmed the next block
is still deeper stop grouping and merge hardening. The latest safe rerun showed
no reduction across stage counts:

- raw stop signals/groups: 112 / 112;
- premerge groups: 112;
- post row merge groups: 112;
- post section merge groups: 112;
- post noise filter groups: 112;
- post dedupe groups: 112;
- normalized stops: 112.

The current grouping logic is still effectively passthrough on private
provider artifacts. The next block should:

- merge provider-created section/line/table fragments into one logical stop
  when evidence points to the same row or stop context;
- reduce one-stop-per-line and split location/date/time patterns;
- tighten provider table-row stop classification so non-stop rows do not become
  stops;
- make duplicate/noise counters nonzero when repeated headers, terms, or
  footer-like groups are safely identified;
- keep no-regression fusion active;
- keep all private value review local-only and ignored.

Camelot is still not the default next step because `pdfplumber` sees tables,
cells, words, and stop labels. OCR remains queued only for empty-text documents.
Vision remains deferred.

## Wiring Audit Result

The wiring audit added synthetic invariant tests and a stage trace. Those tests
prove the normalized pipeline can reduce mergeable synthetic single-line
fixtures. The private safe rerun remains `NOT FIXED`:

- raw stop groups: 112;
- post single-line cluster groups: 112;
- normalized stops: 112;
- duplicate / noise removed: 0 / 0;
- first changed stage counts: none;
- passthrough aliases: 6.

The next debug target is not another generic heuristic. It is a direct
provider-line clustering rewrite that builds stop clusters from adjacent line
order, bbox proximity, page/section context, and field context.

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
