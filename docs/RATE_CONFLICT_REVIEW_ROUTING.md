# Rate Conflict Review Routing

Google Sheets sync remains paused until the full service account credential exists. This workflow is local-only and uses ignored measurement/review artifacts.

## Why This Exists

The previous rate forensics block improved candidate classification: accessorials, quickpay discounts, deductions, and TONU payments are no longer treated as generic main-rate money candidates. That moved the main-rate candidate signal from absent to present, but it did not reduce rate conflicts.

That result is expected. Once stronger candidates are visible, the resolver must decide whether they are equivalent duplicates, compatible reinforcing evidence, or true conflicting totals. The goal is not to suppress conflicts. The goal is to route them honestly.

The current selected rate root cause is `multiple_strong_totals`.

## Conflict Types

Duplicate or equivalent candidate:
- Same normalized amount and compatible currency.
- Often appears from text, layout, and table extraction for the same line.
- Should be grouped and treated as reinforcing evidence, not as a conflict.

Same amount from multiple sources:
- Same amount appears under compatible main-rate labels from separate extraction paths.
- Should increase confidence when labels and sections are compatible.

True different totals conflict:
- Different amounts have strong main-rate labels.
- Should remain `review_required` with a safe conflict reason.

Linehaul vs total:
- `total carrier pay`, `agreed amount`, or equivalent total labels outrank `linehaul`.
- Linehaul should be preserved as a component, not silently selected over an explicit total.

Total carrier pay vs agreed amount:
- Compatible labels may reinforce each other when equivalent.
- Different amounts should route to review unless revised/current evidence clearly resolves the difference.

Revised/current vs original/previous:
- Strong revised/current labels can outrank original/previous labels.
- Weak revised evidence should remain review-required.

Accessorial, quickpay, deduction, penalty noise:
- These are not main-rate candidates unless explicitly labeled as total carrier pay or agreed amount.
- They should remain typed payment/component candidates.

TONU/payment confirmation:
- TONU payment amounts are not normal load linehaul totals.
- They should be treated as payment confirmation context and reviewed separately from normal load rate readiness.

## Desired Behavior

- Equivalent same-amount candidates are deduped into groups.
- Same amount from multiple compatible sources reinforces confidence.
- Total carrier pay and agreed amount outrank linehaul/accessorial components.
- Revised/current totals outrank original/previous totals only when evidence is strong.
- Accessorials, quickpay, deductions, penalties, and terms/billing money cannot become main rate by default.
- Multiple different strong totals route explicitly to `review_required`.
- The resolver must not hide true ambiguity just to reduce conflict counts.

## Review Workbook Fields

Useful safe fields for local review output:
- Rate candidate count
- Main rate candidate count
- Equivalent rate group count
- Different strong total count
- Rate conflict reason
- Selected rate status
- Rate review required reason
- Rate core mapped status

Private values and money amounts are included only in explicit local-only workbook modes and must not be printed or committed.

## Current Local Decision

The current deeper conflict audit did not allow a rate resolver fix:

- `accessorial_noise_remaining`: 4;
- `multiple_different_strong_totals`: 2;
- `tonu_non_normal_load`: 1;
- `unknown`: 3.

Because no allowed arbitration root cause reached the three-alias threshold,
the correct next action is local human review for rate fields or a separate
future block with new evidence. This prevents blindly picking one money amount
or suppressing true conflicts.

## Non-goals

- No OCR or Vision work.
- No Google Sheets sync.
- No DispatchCase creation.
- No DecisionEngine calls.
- No production automation claim.
