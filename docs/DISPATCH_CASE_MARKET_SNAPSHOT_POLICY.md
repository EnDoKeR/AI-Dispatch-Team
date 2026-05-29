# DispatchCase MARKET_SNAPSHOT Policy

Date: 2026-05-29

Status:

```text
Implemented for load-level DispatchCase flow.
```

Scope:

- no Telegram formatter/sender/notifier changes
- no outbox JSONL schema changes
- no reload-watch live wiring
- no scheduler, buttons, DAT/API, Google Maps, or RateCon work

## Previous Behavior

Successful Telegram outbox records are processed by:

```text
dispatch_case.build_cases_and_events(...)
```

Previously allowed outbox message types were:

```text
LOAD_OPPORTUNITY
REVIEW_ONCE
MARKET_SNAPSHOT
SEARCH_HEALTH_CHECK
```

For every successful allowed outbox record, DispatchCase previously:

1. Tries to match an existing case with `outbox_matches_case(...)`.
2. If no case matches, creates a new case with `build_case_from_outbox(...)`.
3. Applies the outbox alert to the case with `apply_outbox_to_case(...)`.
4. Emits a `TELEGRAM_ALERT_SENT` event.

This meant `MARKET_SNAPSHOT` was treated as a load-level outbox candidate even though it is a market/search summary.

## Implemented Behavior

`MARKET_SNAPSHOT` is now excluded from load-level DispatchCase outbox handling.

Current case-eligible outbox message types:

```text
LOAD_OPPORTUNITY
REVIEW_ONCE
SEARCH_HEALTH_CHECK
```

Practical result:

- successful `MARKET_SNAPSHOT` outbox records do not create load-level DispatchCases
- successful `MARKET_SNAPSHOT` outbox records do not attach to existing load-level DispatchCases through parsed best-load lane fields
- successful `MARKET_SNAPSHOT` outbox records with empty metadata fields do not create generic outbox-only load cases
- `LOAD_OPPORTUNITY` and `REVIEW_ONCE` remain load-level case events
- `SEARCH_HEALTH_CHECK` behavior was intentionally left unchanged in this mini-block

## How MARKET_SNAPSHOT Can Match A Load Case Today

`telegram_outbox_logger.py` currently infers `MARKET_SNAPSHOT` from message text.

The current market summary formatter can include a `Best Clean Match` section with a lane and rate. The outbox parser can therefore extract:

```text
pickup
delivery
rate
```

`outbox_matches_case(...)` can match an outbox record to an existing load case when:

- driver matches
- pickup matches
- delivery matches
- broker MC is missing on one side, or broker MC matches

Because market summary outbox records usually have no broker MC, a summary can attach to a load case by driver + parsed best-match lane.

## How MARKET_SNAPSHOT Can Create An Outbox-Only Case Today

If a successful `MARKET_SNAPSHOT` outbox record does not match an existing case, `build_case_from_outbox(...)` can create a case anyway.

For a metadata-based market summary with intentionally empty load-specific fields:

```text
pickup=""
delivery=""
rate=""
broker=""
broker_mc=""
reference_id=""
```

the resulting case would still be a load-shaped DispatchCase with no real load identity.

Because `build_case_id(...)` falls back to driver + broker MC when there is no load ID or reference ID, multiple market snapshots for the same driver with empty broker MC can collapse into the same generic case.

## Is Current Behavior Desired?

Current behavior is not ideal for the project direction.

`LOAD_OPPORTUNITY` and `REVIEW_ONCE` are load-level alerts and should remain load-level DispatchCase events.

`MARKET_SNAPSHOT` is not a single load. It describes the search/market state for a driver at a point in time.

Treating market summaries as load cases can create two problems:

1. A market summary with a best clean match can attach to a load case even though the alert itself was a market summary.
2. A market summary with empty load fields can create a low-quality outbox-only load case.

## Implemented Policy

Implemented current policy:

```text
MARKET_SNAPSHOT is outbox/reporting-only in DispatchCase flow until a search-level entity exists.
```

Practical meaning:

- `MARKET_SNAPSHOT` is still written to `telegram_outbox.jsonl`.
- `MARKET_SNAPSHOT` remains available for outbox reports, replay, and SQLite/reporting work.
- `MARKET_SNAPSHOT` does not create a load-level DispatchCase.
- `MARKET_SNAPSHOT` does not attach to a load-level DispatchCase through parsed best-load lane fields.
- `MARKET_SNAPSHOT` does not create a generic outbox-only case with empty load identity.

Future policy after a search-level model exists:

```text
MARKET_SNAPSHOT can become a driver/search-level event attached to DispatchSearchSession.
```

Possible future entity:

```text
DispatchSearchSession
```

Possible future event:

```text
MARKET_SNAPSHOT_SENT
```

That future model should be separate from load-level DispatchCase.

## Interaction With Market Summary Metadata

`telegram_summary_metadata.py` now builds market summary metadata with intentionally empty load-specific core fields.

That helper is not wired into `send_market_summary_to_telegram(...)` yet.

Because load-level DispatchCase exclusion is now protected, market summary metadata wiring can be considered in a later mini-block.

## Behavior Tests

The behavior change is protected by focused tests covering:

1. A successful `MARKET_SNAPSHOT` with no decision records does not create a load case.
2. A successful `MARKET_SNAPSHOT` with parsed best-load pickup/delivery does not attach to an existing load case.
3. A successful `MARKET_SNAPSHOT` with empty metadata fields does not create a generic outbox-only case.
4. `LOAD_OPPORTUNITY` still creates or updates load-level DispatchCases.
5. `REVIEW_ONCE` still creates or updates load-level DispatchCases.
6. Failed outbox records are still ignored.
7. Existing `TELEGRAM_ALERT_SENT` behavior for load-level alerts remains unchanged.

## Do Not Change Yet

Do not change yet:

- Telegram message text
- market summary formatter
- Telegram sender/notifier behavior
- outbox JSONL schema
- outbox logger fallback parser
- market summary metadata wiring
- `SEARCH_HEALTH_CHECK` policy
- reload-chain DispatchCase policy
- reload-watch live wiring
- SQLite schema

## Recommended Next Mini-Block

Recommended next mini-block:

```text
Telegram market summary metadata wiring
```

Scope should be:

- test-first
- wire `build_market_summary_metadata(...)` into `send_market_summary_to_telegram(...)` only
- keep formatter text unchanged
- do not change Telegram/outbox schema

Do not wire search health, reload-chain, or reload-watch metadata in the same block.
