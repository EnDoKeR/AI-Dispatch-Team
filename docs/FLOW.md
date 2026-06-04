# Dispatch Flow

This document describes the canonical operating flows for AI Dispatch Team. It is architecture guidance only. It does not add runtime behavior, live integrations, OCR, Google Sheets, Google Maps, DAT/API, Telegram upload handling, accounting/factoring actions, or DispatchCase writes.

## Core Flow

```text
Document/Load Source
-> Intake Record
-> DocumentRecord / LoadCandidate
-> parser/extractor
-> normalized domain object
-> DispatchCase
-> DecisionEngine
-> Event Timeline
-> Telegram/UI output
-> dispatcher feedback
-> memory/replay/accounting
```

Hard boundary:

- sources and parsers produce evidence;
- the domain core normalizes evidence;
- DecisionEngine produces recommendations;
- DispatchCase and Event Timeline preserve operational history;
- adapters present results and collect feedback.

## Simulated Load Flow

```text
Synthetic load board event
-> load source / simulation record
-> MarketLoad-like object
-> current decision behavior
-> DispatchCase builder where currently wired
-> case_event_builder current runtime events
-> Telegram/outbox where currently wired
-> dispatcher feedback
-> replay/reporting
```

Current status:

- simulation is used before live DAT/API work;
- existing runtime behavior remains protected by tests;
- future simulation improvements should keep current case/event behavior stable unless a specific migration block approves changes.

Event timeline append points:

- load appeared;
- load updated;
- load removed;
- AI evaluated;
- Telegram alert sent;
- dispatcher feedback added;
- case status changed;
- final outcome recorded later.

## RateCon PDF Intake Flow

Target future flow:

```text
RateCon document received
-> DocumentRecord
-> PDF triage
-> text extraction artifact
-> extraction candidates
-> RateConfirmationIntake
-> validation and confidence checks
-> review-required gate if fields are missing, low confidence, or conflicting
-> optional DispatchCase draft/link candidate after approval policy
-> DecisionEngine only after normalized evidence is safe enough
-> Event Timeline entries
```

Current status:

- local/private PDF extraction dry-run exists;
- redacted diagnostics and layout diagnostics exist;
- private value-review CSV is local-only and ignored;
- no raw extracted text should be committed;
- no production OCR/Vision path exists yet;
- optional local/shadow OCR diagnostics exist and are disabled by default;
- no RateCon intake should automatically create or link DispatchCases.

Event timeline append points later:

- document received;
- PDF triaged;
- text extracted;
- OCR fallback needed;
- RateCon parsed;
- review required;
- field corrected;
- document linked;
- case created from intake after approval.

## Future DAT/API Flow

Future intended flow:

```text
DAT/API or live load source adapter
-> LoadCandidate
-> source metadata and idempotency key
-> normalized domain object
-> DecisionEngine
-> DispatchCase where policy allows
-> Event Timeline
-> Telegram/UI output
-> dispatcher feedback
-> memory/replay
```

Rules:

- live source adapters must not own business rules;
- live source adapters must be read-only before any operational action;
- no autonomous booking;
- idempotency and duplicate/repost identity must be tested before live use;
- simulator coverage should prove core behavior first.

## Dispatcher Feedback Flow

```text
Telegram/CLI/future UI feedback
-> feedback adapter
-> normalized feedback event
-> DispatchCase update policy
-> Event Timeline
-> SQLite/memory reports
-> future replay and missed-opportunity analysis
```

Rules:

- feedback is evidence;
- feedback may train memory over time;
- feedback should not silently rewrite historical AI recommendations;
- final outcomes should not be downgraded by later working feedback without explicit status rules.

## Document / Accounting / Factoring Flow

Future intended flow:

```text
Document evidence
-> DocumentRecord
-> extraction artifact / human review
-> DispatchCase document link
-> missing document detection
-> factoring packet readiness report
-> explicit dispatcher approval before any external submission
```

Rules:

- factoring/accounting helpers may prepare internal readiness reports later;
- they must not submit packets, send emails, contact brokers, or create financial/legal commitments without explicit approval;
- document events belong on the Event Timeline only after event ownership policy is accepted.

## Output Flow

```text
DecisionResult / case summary / report data
-> formatter
-> Telegram/CLI/dashboard/sheet adapter
-> dispatcher-visible output
```

Rules:

- output formatters should not calculate decisions;
- REVIEW_REQUIRED output must show missing or low-confidence critical fields;
- adapters should not mutate the decision result or source evidence;
- no raw private RateCon text should be included in output.
