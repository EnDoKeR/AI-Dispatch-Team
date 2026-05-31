# Target Deferral And Rate Forensics

Google Sheets sync remains paused until a valid local service account
credential exists. This workflow stays local-first and uses ignored local
measurement outputs, review CSVs, and safe analysis artifacts.

## Why Load Identifier Is Deferred

`load_identifier_candidate_generation` remains a real intake-core blocker, but
the latest source-line audit did not prove a shared code-fixable root cause.
Safe result:

- source-line audit ran on 18 documents;
- primary candidates stayed low;
- rejected non-primary references remained useful review evidence;
- root causes split across unknown, OCR/weak text, absent source lines, only
  non-primary references, and correctly non-primary labels;
- no code-fixable bucket reached the required three-alias threshold.

Continuing to add generic load-number rules would risk promoting PO, BOL,
pickup, delivery, appointment, customer, or carrier references into
`load_number`. That would hide an honest missing identifier behind weak
evidence. The target is therefore deferred until local human review or new
source-line evidence changes the root-cause distribution.

## Why Deferral Is Needed

Target selection loops are dangerous when a broad blocker stays high after a
negative audit. Without a disposition registry, the selector can keep returning
the same target even after the measured evidence says no further code change is
justified.

Deferral is a control mechanism, not a suppression mechanism. It records why a
target is paused and lets the selector move to the next actionable blocker.

## Target Disposition States

- `active`: selectable for the next hardening block.
- `completed`: already handled for the current evidence set.
- `deferred_until_review`: blocked until local human review adds new evidence.
- `no_shared_code_root_cause`: audited, but no shared code-fixable reason was
  found.
- `blocked_by_missing_credential`: blocked by missing local service account
  credential or local config.
- `blocked_by_ocr`: blocked by non-digital or weak text that belongs in a future
  OCR design block.
- `needs_human_review`: not enough safe deterministic evidence to proceed.

Deferred or blocked targets are skipped by default. An explicit override may
allow rerunning a deferred target when new evidence exists, but the default
selector must not loop.

The local registry is written only under ignored measurement output paths, for
example `target_disposition_registry.json`. The registry stores target names,
statuses, safe reasons, and supporting counts only.

## Next Measured Area

The next measured area is rate conflict and main-rate resolution. Rate is a true
intake-core field. Unlike `no_candidate`, rate conflicts usually mean money-like
candidates exist but disagree, come from the wrong section, or are ranked with
the wrong source priority.

Rate forensics should determine whether conflicts come from:

- `accessorial_as_main_rate`;
- `quickpay_discount_as_main_rate`;
- `deduction_or_penalty_as_main_rate`;
- `terms_page_money_noise`;
- `billing_page_money_noise`;
- `linehaul_vs_total_conflict`;
- `multiple_strong_totals_conflict`;
- `TONU_payment_non_normal_load`;
- `candidate_generated_but_not_resolved`;
- `normalized_rate_not_core_mapped`;
- `no_shared_root_cause`.

A rate fix is allowed only if a shared, code-fixable root cause is proven. If
the root causes split across aliases or require private judgment, the correct
outcome is local human review for rate fields.

## Current Rate Forensics Result

After deferring `load_identifier_candidate_generation`, target selection skips
that target by default and selected `rate_candidate_generation_or_resolution`.

The first rate forensics pass found a shared source-priority issue:

- selected root cause: `accessorial_confused_with_main_rate`;
- fix allowed: yes;
- selected fix: `rate_source_priority_guardrails`;
- supporting aliases: 10;
- conflict-present records: 7.

The targeted fix preserved typed money candidate categories in generic text
candidate generation so main pay labels, accessorials, quickpay, deductions,
and TONU payment amounts can be separated downstream.

Post-fix safe delta:

- main rate candidates: 0 -> 9;
- `accessorial_confused_with_main_rate`: 10 -> 3;
- rate conflict count: 7 -> 7;
- true intake blockers: 51 -> 51;
- readiness: unchanged;
- next rate root cause: `multiple_strong_totals`.

This means the source-priority fix improved diagnostics and candidate typing,
but did not improve readiness. The next rate block should focus on conflict
review routing only if measured evidence still supports it. Do not stack more
source-priority patches without a new shared root cause.

## Rate Conflict Audit

The follow-up conflict audit is stricter than the broad rate candidate
forensics report. It separates equivalent candidates, different strong totals,
linehaul/total conflicts, revised/original conflicts, TONU payment context,
and selected-rate mapping gaps.

Safe latest result:

- rate conflict records: 10;
- equivalent same-amount groups: 0;
- different strong total groups: 6;
- conflict-present records: 7;
- selected/core-mapped records: 2 / 2;
- conflict reasons: `accessorial_noise_remaining=4`,
  `multiple_different_strong_totals=2`, `tonu_non_normal_load=1`,
  `unknown=3`;
- fix allowed: false;
- recommended next action: local human review for rate fields.

The broad forensics report still flags `multiple_strong_totals`, but the deeper
audit shows that this bucket splits below the three-alias code-fix threshold.
No resolver/arbitration fix should be applied from this evidence set.

Local review exports now include safe rate conflict columns such as conflict
reason, main candidate count, equivalent group count, different strong total
count, selected-rate status, core-mapped status, and component category counts.
Money values remain local-only and must not be printed or committed.

## Local Commands

Create/update rate forensics artifacts during a private run by adding:

```powershell
--write-rate-forensics
```

Analyze existing local artifacts with:

```powershell
python scripts/analyze_rate_candidate_forensics.py --write-md --write-json --include-local-document-names-local-only
```

Create/update rate conflict audit artifacts during a private run by adding:

```powershell
--write-rate-conflict-audit
```

Analyze existing conflict audit artifacts with:

```powershell
python scripts/analyze_rate_conflicts.py --write-md --write-json --include-local-document-names-local-only
```

Console and Markdown output contain aliases, counts, categories, and conflict
reasons only. They do not contain money values.

## Safe Sharing Rules

Safe to share:

- aliases;
- counts;
- statuses;
- field names;
- issue categories;
- rate candidate categories;
- source section categories;
- selected target names.

Do not share:

- money values;
- private predicted or expected values;
- raw text or line text;
- private filenames or local paths;
- broker/customer identifiers;
- service account keys.

## Non-Goals

This workflow does not run Google sync, add OCR/Vision/cloud document AI, add
Camelot/PyMuPDF/Tesseract/PaddleOCR, create DispatchCases, call DecisionEngine,
call Telegram, write Event Timeline events, or make production automation
claims.
