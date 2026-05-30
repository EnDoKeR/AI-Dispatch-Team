# RateCon Hard-Layout Fixture Design

This document defines fake/anonymized hard-layout Rate Confirmation fixtures for
template-aware resolver hardening.

These fixtures are not private RateCons, not real broker templates, and not a
production accuracy benchmark. They exist to test whether the deterministic
candidate/template/resolver layer handles difficult layouts without inventing
fields, hiding conflicts, or bypassing validation.

## Safety Rules

- Use fake/anonymized text only.
- Do not use private RateCon text or private-derived snippets.
- Do not use real broker, customer, carrier, driver, phone, email, address, MC,
  reference, appointment, or load data.
- Do not add OCR, Vision AI, cloud APIs, Google Sheets, DAT/API, or new PDF
  dependencies.
- Do not create DispatchCases, write events, call DecisionEngine, or call
  Telegram from this layer.
- BrokerTemplate remains document-layout vocabulary only. BrokerProfile and
  broker memory remain business-history concepts.

Allowed fake values include:

- `Alpha Freight Mock`
- `Northstar Logistics Mock`
- `Tablelane Transport Mock`
- `Unknown Mock Brokerage`
- `MC 111111`
- `MC 222222`
- `MC 333333`
- `MC 999999`
- `FAKE-LOAD-001`
- `FAKE-PO-001`
- `Fake City, ST 00000`
- `$0000.00`

## Fixture Scenarios

### 1. `repeated_headers_terms_ratecon.txt`

Purpose:

- repeated broker/load headers across pages;
- a terms page contains detention, layover, late fee, and penalty amounts;
- the resolver must not treat terms/accessorial/penalty amounts as the main
  carrier rate.

Expected candidate behavior:

- multiple rate-like money candidates may exist;
- terms/accessorial candidates should carry accessorial or negative-label
  warnings;
- repeated header candidates should not create false field conflicts when values
  are identical.

Expected template behavior:

- likely matches `alpha_freight_mock_v1` if Alpha-specific labels are present;
- template scoring can boost the true carrier-pay label;
- template scoring must penalize terms/accessorial labels.

Expected resolver behavior:

- resolve the main rate only if the carrier-pay candidate is strong;
- otherwise mark `rate` as `needs_review` or `conflict`;
- reject or downgrade detention/layover/fee/penalty candidates as final rate.

Expected missing/needs-check/conflict fields:

- `rate` may be resolved or needs-check depending evidence strength;
- no conflict should be created solely by identical repeated header values;
- accessorial-like candidates should not become resolved `rate`.

### 2. `multi_page_rate_terms_ratecon.txt`

Purpose:

- page 1 has actual carrier pay;
- later page has detention, layover, TONU, quick pay, and lumper amounts;
- resolver must select actual carrier pay or mark conflict.

Expected candidate behavior:

- true rate appears near a strong positive label;
- later terms amounts appear near negative/accessorial labels;
- all money candidates remain visible.

Expected template behavior:

- may match Alpha or Northstar depending fixture vocabulary;
- positive rate labels receive boosts;
- accessorial labels receive penalties.

Expected resolver behavior:

- select actual carrier pay if one strong positive rate exists;
- mark `rate` `missing` or `needs_review` if only terms amounts are found;
- mark `rate` `conflict` if two strong positive rates disagree.

Expected missing/needs-check/conflict fields:

- accessorial amounts must not populate `rate`;
- conflicting strong rate candidates should add `rate` to conflict fields.

### 3. `table_like_stops_ratecon.txt`

Purpose:

- pickup/delivery appear in stop-table-like lines;
- stop labels are `Stop 1` and `Stop 2`;
- dates, times, and locations need association with the correct stop.

Expected candidate behavior:

- stop-related candidates are generated for pickup/delivery location, date, and
  time;
- `Stop 1` and `Stop 2` context is preserved in labels/context or evidence;
- ambiguous stop candidates remain lower-confidence.

Expected template behavior:

- likely matches `tablelane_transport_mock_v1`;
- tablelane stop labels can boost correct stop candidates;
- generic stop labels must not overboost ambiguous fields.

Expected resolver behavior:

- associate pickup with `Stop 1` only when pickup/PU/origin context is strong;
- associate delivery with `Stop 2` only when delivery/DEL/destination context is
  strong;
- mark ambiguous stop/date/time association as needs-review rather than guessing.

Expected missing/needs-check/conflict fields:

- missing date/time fields remain missing;
- conflicting stop appointment values add the relevant field to
  `needs_check_fields` or `conflict_fields`.

### 4. `missing_broker_mc_header_only_ratecon.txt`

Purpose:

- broker name appears only in a header;
- broker MC is missing;
- broker name may resolve;
- broker MC must remain missing/review-visible.

Expected candidate behavior:

- one broker-name candidate appears from header/template identity;
- no broker MC candidate is invented.

Expected template behavior:

- likely matches the broker template from header keywords;
- template match can support broker-name confidence;
- template match must not invent MC.

Expected resolver behavior:

- `broker_name` may resolve if evidence is strong;
- `broker_mc` remains `missing` or review-visible;
- missing broker MC does not create fake data.

Expected missing/needs-check/conflict fields:

- `broker_mc` is missing at resolver level;
- current RateCon validation may treat broker MC as optional, but the missing
  optional field should remain visible.

### 5. `carrier_vs_broker_confusion_ratecon.txt`

Purpose:

- text contains both broker name and carrier name;
- resolver must not select carrier as broker.

Expected candidate behavior:

- broker-name and carrier-name candidates are both visible where labels support
  them;
- carrier-labeled company candidates should not be treated as broker_name;
- carrier labels add warnings or confidence penalties if considered for broker.

Expected template behavior:

- template match should rely on broker/template keywords, not carrier identity;
- carrier labels do not create broker template truth.

Expected resolver behavior:

- select broker name only from broker-positive labels/header/template evidence;
- mark broker identity needs-review/conflict if broker and carrier evidence is
  ambiguous;
- never silently resolve carrier name as broker.

Expected missing/needs-check/conflict fields:

- `broker_name` should not equal a carrier-labeled value;
- ambiguity can put `broker_name` in `needs_check_fields`.

### 6. `references_near_wrong_stop_ratecon.txt`

Purpose:

- PO, BOL, pickup, delivery, and appointment references appear near different
  stops;
- typed references must be preserved and not collapsed into one generic
  reference.

Expected candidate behavior:

- typed reference candidates include PO, BOL, pickup number, delivery number,
  customer reference, appointment number, pickup confirmation, and delivery
  confirmation where labels are present;
- context or value type preserves stop association when possible.

Expected template behavior:

- template reference rules boost typed references;
- unknown/ambiguous references stay lower-confidence or unknown type.

Expected resolver behavior:

- do not collapse typed references into one final generic reference;
- do not confidently assign a reference to the wrong stop;
- ambiguous references remain `unknown_reference` or needs-review.

Expected missing/needs-check/conflict fields:

- reference ambiguity should be visible in warnings or needs-check fields;
- load number remains separate from PO/BOL/pickup/delivery references.

### 7. `conflicting_appointment_times_ratecon.txt`

Purpose:

- pickup/delivery appointment candidates conflict;
- resolver must mark conflict/needs-review, not silently choose one.

Expected candidate behavior:

- multiple appointment time candidates are generated for the same stop/date
  field;
- conflicting values remain visible.

Expected template behavior:

- template appointment labels can boost candidates;
- boost must not override disagreement.

Expected resolver behavior:

- conflicting pickup time or delivery time values produce `conflict` or
  `needs_review`;
- no appointment time is selected silently when strong candidates disagree.

Expected missing/needs-check/conflict fields:

- `pickup_time` or `delivery_time` should appear in `conflict_fields` or
  `needs_check_fields` where disagreement exists.

### 8. `buried_special_requirements_ratecon.txt`

Purpose:

- tarp, straps, chains, driver assist, no-touch, and check-in instructions appear
  in notes;
- candidate generator may find them;
- resolver must preserve special requirements without making driver
  compatibility decisions.

Expected candidate behavior:

- special requirement candidates are generated from notes;
- accessorial terms can be generated separately if present;
- no dispatch recommendation is emitted.

Expected template behavior:

- template-specific special requirement labels can boost extraction candidates;
- templates do not decide equipment compatibility.

Expected resolver behavior:

- preserve special requirements as evidence or resolved/supporting fields if the
  current contract supports them;
- contradictory requirements become needs-review/conflict if supported;
- do not reject, accept, or dispatch the load.

Expected missing/needs-check/conflict fields:

- special requirements should remain visible;
- no driver compatibility field is produced by extraction.

### 9. `revised_rate_conflict_ratecon.txt`

Purpose:

- original rate and revised rate both appear;
- resolver must prefer explicit revised/current marker only if strong;
- otherwise mark rate conflict.

Expected candidate behavior:

- original/prior rate candidates carry original/prior context;
- revised/current/updated candidates carry revised/current context;
- both candidates remain visible.

Expected template behavior:

- template scoring can boost revised/current labels;
- original/prior labels should not win when a strong current rate exists.

Expected resolver behavior:

- prefer revised/current rate only when the label/context is strong;
- mark conflict or needs-review when revised/current evidence is weak;
- never silently choose the first or last dollar amount.

Expected missing/needs-check/conflict fields:

- `rate` resolved only with strong revised/current evidence;
- otherwise `rate` appears in `conflict_fields` or `needs_check_fields`.

### 10. `unknown_hard_layout_ratecon.txt`

Purpose:

- no matching broker template;
- generic fallback only;
- no over-resolution.

Expected candidate behavior:

- generic candidates may be produced;
- weak labels stay low or medium confidence.

Expected template behavior:

- template status is `unknown`;
- no template-specific boost is applied.

Expected resolver behavior:

- resolve only fields with strong generic evidence;
- missing/low-confidence fields remain explicit;
- no template confidence is invented.

Expected missing/needs-check/conflict fields:

- `template_match` may appear in warnings, not as a dispatch decision;
- core field gaps remain missing/needs-review.

## Baseline Matrix Expectations

The first regression matrix should be conservative:

- no fixture should crash extraction, template matching, resolution, or intake
  draft building;
- hard cases may initially resolve few fields;
- accessorial-only rate candidates must not become final rate;
- carrier name must not become broker name;
- typed references should remain typed where labels are clear;
- unknown template fixtures must not over-resolve due to template scoring;
- all outputs must serialize;
- no fixture or report should contain private data.

## Future Measurement Use

After resolver hardening passes fake/anonymized tests, a separate safe private
measurement block may compare local private documents using safe summaries only:

- triage route;
- candidate counts by field;
- template status;
- resolved/missing/needs-check/conflict field names;
- warnings;
- result categories.

That future block must not commit private PDFs, extracted text, private values,
or local private CSVs.
