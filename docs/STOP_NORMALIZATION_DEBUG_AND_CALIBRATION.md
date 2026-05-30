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

