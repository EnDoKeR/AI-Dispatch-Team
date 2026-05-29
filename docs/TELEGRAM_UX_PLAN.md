# Telegram UX Future Interface Plan

Telegram is an adapter/interface for the Dispatch Operating Intelligence System. It is not the business core.

This plan captures future UX direction only. It does not change current Telegram runtime behavior, message text, commands, buttons, DispatchCase behavior, DecisionEngine behavior, or load alerts.

## Product Position

Telegram should eventually feel like a dispatcher cockpit:

- quick status
- short ranked options
- clear review queues
- muted routine updates
- critical alerts when action is needed
- easy access to intake and settings

The core system should remain interface-independent. Telegram should display and route structured information that comes from core modules such as DispatchCase, DecisionEngine, intake records, market context, and reload-watch state.

## UX Phases

### Phase 1: Private Chat With Commands And Cards

Start with one private dispatcher chat.

Future scope:

- menu command
- short command list
- compact cards
- digest-style views
- manual dispatcher actions after backend policies exist

Not in this phase:

- Telegram buttons
- group/forum topic mode
- Telegram Web App
- live scheduler expansion
- new DispatchCase writes without accepted policy

### Phase 2: Notification Settings And Digest Logic

Future scope:

- choose when normal updates appear
- mute non-critical reload-watch status
- keep critical alerts enabled
- choose clean-match digest size
- separate review-once digest from clean matches

This phase should happen only after backend event ownership and alert policies are stable.

### Phase 3: Team / Supergroup / Topic Mode Audit

Future audit only.

Possible use:

- one topic per driver
- one topic for intake/review
- one topic for operations summary
- one topic for accounting/documents later

Risks:

- noisy threads
- privacy exposure
- accidental cross-driver confusion
- harder message-to-case linking

Do not implement before a separate group/topic mode audit.

### Phase 4: Telegram Web App / Dashboard Audit

Future audit only.

Possible use:

- richer load cards
- filters
- driver/search setup
- document intake status
- case timeline view

Do not implement before backend repositories, case timeline policies, and approval rules are stable.

## Future Commands

Recommended command set:

```text
/menu
/search
/top
/review
/market
/watch
/intake
/settings
/help
```

### `/menu`

Home entry point.

Should show:

- active searches
- top options shortcut
- review queue shortcut
- market summary shortcut
- reload watch shortcut
- intake shortcut
- settings shortcut

### `/search`

Search setup and active driver/search state.

Should show:

- driver name
- equipment
- current location/search area
- available time
- target direction
- status

Future actions should require a separate accepted design before they mutate search state.

### `/top`

Best options view.

Should show ranked clean matches only. Keep it short and scannable.

### `/review`

Review Once / Needs Check queue.

Should show:

- rate checks
- Conestoga verify
- document requirements
- timing checks
- broker/payment checks
- other review reasons

Review queue should stay separate from clean matches.

### `/market`

Market summary view.

Should show:

- market activity
- clean matches
- review once
- blocked count
- best bucket
- recommendation

Market summary should not be mixed into individual load alerts.

### `/watch`

Reload watch status.

Should show:

- active watches
- muted watches
- clean exits found
- strong chain found
- parent load removed/updated alerts

Muted watch should suppress normal status updates but still allow critical alerts.

### `/intake`

RateCon/intake review.

Should show:

- intake records waiting for review
- missing fields
- needs-check fields
- source type
- linked case status later

Do not treat Telegram as the parser or as storage. Intake data should come from structured intake records.

### `/settings`

Notification and display preferences.

Future examples:

- digest size
- normal status frequency
- mute routine reload-watch updates
- show/hide review-once queue
- driver/search shortcuts

### `/help`

Short help and safety notes.

Should explain:

- Telegram is an interface only
- the system does not auto-book
- critical actions require dispatcher approval
- private documents/data must be handled carefully

## Future Card Types

### Strong Match Card

Purpose:

- show a ranked clean option

Should include:

- driver
- pickup/delivery
- rate
- miles/RPM
- broker
- reason
- reference ID
- recommended next action

### Review Once Card

Purpose:

- show one reviewable exception

Should include:

- review category
- reason
- missing/needs-check fields if available
- key load details
- clear review action

### Market Summary Card

Purpose:

- summarize one active search

Should include:

- search area
- equipment
- target direction
- activity
- clean/review/blocked counts
- best bucket
- recommendation

### Reload Watch Card

Purpose:

- show reload-watch status or critical event

Should include:

- watched parent load
- delivery market
- clean/review/rate-check exit counts
- best exit if available
- chain status if available
- whether normal updates are muted

### Intake / Missing Fields Card

Purpose:

- show one intake record that needs dispatcher review

Should include:

- intake ID
- source type
- broker/rate/lane summary
- missing fields
- needs-check fields
- field confidence summary

### Settings Card

Purpose:

- show current notification/display preferences

Should include:

- normal update mode
- critical alert mode
- digest size
- active driver/search shortcuts

## Anti-spam Rules

Telegram should stay useful and calm.

Rules:

- Do not send every load as a separate noisy alert.
- Best options should be short and ranked.
- Review once should be separate from clean matches.
- Market summary should not mix with load alerts.
- Reload-watch normal status can be muted later, but critical alerts still go through.
- Repeated alerts need duplicate protection.
- Summaries should explain why the dispatcher is seeing them.
- Telegram should not be used as the database.
- Telegram should not be the source of business truth.
- Telegram should not hide structured backend state behind unparseable text.

## Core Boundary Rules

Telegram may:

- display structured decisions and summaries
- route dispatcher commands
- preview future actions
- collect dispatcher feedback after accepted design

Telegram must not:

- own business rules
- decide `MATCH` / `REVIEW_ONCE` / `BLOCK`
- parse RateCons
- write DispatchCase events without accepted policy
- send financial/legal/accounting commitments
- auto-book loads
- become the only audit trail

## Not Now

Do not implement in the current foundation phase:

- new Telegram runtime commands
- Telegram buttons
- Telegram group/forum topics
- Telegram Web App
- dashboard UI
- live reload-watch sending
- scheduler/background loops
- DAT/API or Google Maps
- Gmail/email or Google Sheets
- PDF/OCR parser behavior
- accounting/factoring submission

The next backend priority remains DispatchCase/Event Timeline policy before any new live Telegram UX is wired.
