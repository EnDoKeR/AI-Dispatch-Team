# Layout Evidence Fusion And Stop Association

This document defines the next hardening layer after the first `pdfplumber`
layout provider pilot. The goal is safer resolver input, not production
automation.

## Why This Follows The Provider Pilot

The provider block proved that digital-text PDFs can be converted into layout
artifacts and layout candidates behind explicit safe-measurement flags. The
safe private run showed:

- layout attempted on 6 normal-load documents;
- layout provider success on all 6 attempted documents;
- rate candidate coverage improved on 6 documents;
- weight improved on 1 document;
- commodity improved on 2 documents;
- stop, location, and date fields often worsened or stayed unresolved.

That result means the next blocker is not another provider. It is how layout
evidence is fused with existing text candidates and how stop-related evidence is
associated before the resolver makes conservative decisions.

The follow-up diagnostics and no-regression rerun changed the provider
assessment:

- layout attempted: 6;
- layout success: 6;
- provider quality: `rich_layout` on attempted documents;
- total tables: 22;
- total table cells: 710;
- stop label signals: pickup 37, delivery 44, stop 26, date 5, time 23;
- stop groups produced: 78;
- fusion worsened fields: none.

That means `pdfplumber` is producing enough structure for the next diagnostic
step. The blocker is now resolver/evaluation readiness: selecting from stop
groups and layout-backed field candidates without over-trusting ambiguous
evidence.

## Why Not Add Another Provider Now

Adding Camelot or another table provider before fusion would increase input
volume without fixing the decision problem. The current provider already
produces useful layout evidence. The measured weakness is candidate association:
which date belongs to which location, which section is pickup versus delivery,
and when layout evidence should override or merely supplement text evidence.

PyMuPDF and Camelot remain possible future provider decisions. They need a
separate dependency, licensing, and measurement checkpoint.

## Why OCR And Vision Remain Deferred

OCR is still needed for the 4 empty-text documents, but OCR does not address
digital-text association failures in the 6 normal-load documents. Vision remains
a later gated fallback only after deterministic layout, provider, and resolver
routes are measured and shown insufficient.

## Candidate Sources

Fusion should preserve candidate source identity:

- text regex candidates;
- text section candidates;
- layout table candidates;
- layout label-value candidates;
- layout section candidates;
- broker-template adjusted candidates;
- future OCR candidates;
- future Vision candidates;
- manual review feedback if that is introduced later.

The fusion layer must not hide source disagreements. It should carry evidence
forward so the resolver can select, conflict, or review explicitly.

## Desired Fusion Behavior

Fusion must be conservative:

- never blindly replace text candidates with layout candidates;
- merge candidates by field and evidence source;
- select stronger evidence only when confidence, section scope, and source type
  support it;
- prevent field status regression when baseline text extraction is stronger;
- preserve conflicting strong candidates as review-required evidence;
- keep multiple candidates when ambiguity remains;
- avoid creating any DispatchCase or business recommendation.

Layout evidence can improve a field when it has stronger scope and association,
for example a same-row table value in a `RATE_SUMMARY` section or a pickup date
inside a pickup section. Weak or contradictory layout evidence should not
downgrade a resolved baseline field.

## No-Regression Guard

Layout fusion protects critical baseline fields by default. Protected fields
include broker identity, load number, rate, pickup/delivery location/date/time,
equipment, weight, and commodity.

Default behavior:

- do not downgrade resolved fields to missing;
- do not downgrade resolved fields to low confidence because layout evidence is
  weaker;
- route strong source disagreement to conflict/review instead of hiding it;
- reject weak layout candidates that would worsen a protected baseline field;
- expose rejected field names and counts as safe diagnostics only.

The explicit debug path `--allow-layout-regression-for-debug` exists for local
diagnosis only. It must not be used to claim production readiness.

## Stop Association Model

Stops should be grouped before final resolution. A stop group should carry:

- stop group id;
- stop type: pickup, delivery, stop, or unknown;
- optional sequence;
- location candidates;
- date candidates;
- time candidates;
- reference candidates;
- notes candidates;
- table row, section, label-value, or text evidence;
- warnings when stop type or field association is ambiguous.

Table-row evidence should usually beat distant text order because row structure
preserves association. Section evidence should beat unscoped regex evidence.
The system must not collapse multi-stop documents into one pickup and one
delivery if the source provides more stops.

Missing dates or times must not be invented. Ambiguous stop type or conflicting
strong sources should route to review.

## Rate Behavior

The provider run showed useful rate coverage, so rate fusion should protect that
improvement:

- rate-summary, rate-breakdown, and payment-summary table evidence can improve
  the main rate;
- terms, legal, quick-pay, penalty, and deduction amounts must not become the
  main rate by default;
- matching text and layout rate evidence can reinforce confidence;
- conflicting strong totals route to review;
- TONU payment is not normal linehaul unless the document type is
  `TRUCK_ORDER_NOT_USED`.

## Operational Detail Behavior

Equipment, weight, commodity, and special requirements can improve from layout
sections:

- `EQUIPMENT_SUMMARY` and `COMMODITY_WEIGHT` evidence should boost operational
  details;
- `SPECIAL_INSTRUCTIONS` evidence should preserve requirements;
- legal terms can contribute lower-confidence requirement evidence only when
  clearly load-specific;
- no driver compatibility decision is made here.

## Provider Diagnostics

Safe measurement can add provider diagnostics with:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --write-json --write-csv --write-md
```

Optional table profile comparison:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-pdfplumber-table-profiles --compare-layout-to-text-baseline --write-json --write-csv --write-md
```

The supported `--pdfplumber-table-profile` values are `default`, `lines`,
`text`, `lines_strict`, and `text_strict`. Diagnostics report only counts,
status buckets, field names, evidence types, and aliases. They do not include
raw text, filenames, broker names, MC numbers, rates, addresses, dates/times,
references, or local paths.

Issue buckets:

- `provider_no_tables`: tables were not detected; continue line/section
  extraction or evaluate table-specific providers only after measurement.
- `provider_no_words`: provider output is too weak for deterministic layout
  extraction; review route/provider options.
- `provider_has_tables_but_no_stop_groups`: table conversion exists but
  association missed it.
- `provider_has_stop_labels_but_no_groups`: labels exist but grouping did not
  connect them.
- `scope_filter_excluded_pages`: classification scope excluded stop evidence.
- `association_logic_gap`: stop groups/candidates exist but resolver scoring
  still needs calibration.
- `candidate_fusion_regression`: fusion guardrails need review.

## Decision Gates

Use safe diagnostics to decide the next block:

- If tables and stop signals exist and stop groups improve, proceed to resolver
  readiness and a human review/evaluation corpus.
- If tables and stop signals exist but field statuses stay unresolved, harden
  resolver scoring and evaluation fixtures before adding Camelot.
- If no tables exist but words/lines are strong, extend line/section stop
  extraction and consider a Camelot design checkpoint only after that evidence.
- If provider output is weak, run an alternative layout provider review.
- If OCR-needed remains isolated to empty-text documents, keep OCR queued for a
  separate local OCR design checkpoint.
- Vision remains a later gated fallback.

## Non-Goals

This block does not:

- add OCR;
- add Vision;
- add Camelot;
- add PyMuPDF;
- add cloud APIs;
- add new dependencies;
- create DispatchCase records;
- call DecisionEngine;
- call Telegram;
- write Event Timeline events;
- claim production readiness.
