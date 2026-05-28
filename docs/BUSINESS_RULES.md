# Business Rules

This document defines the core dispatch business rules used by AI Dispatch Team.

These rules are the foundation for:

- AI decision logic
- DispatchCase status logic
- broker memory
- driver memory
- lane memory
- Telegram alerts
- replay reports
- future tests

The goal is to keep business logic explicit and stable before adding more automation.

---

## 1. Decision categories

The system should classify loads into clear categories.

Main AI decisions:

- `MATCH`
- `REVIEW_ONCE`
- `BLOCK`
- `UNKNOWN`

Main AI categories:

- `LOAD OPPORTUNITY`
- `RATE CHECK`
- `CONESTOGA VERIFY`
- `OD / PERMIT`
- `ALONG ROUTE`
- `SEARCH HEALTH CHECK`
- `BLOCK`
- `BROKER REVIEW`

---

## 2. Hard block rules

A load should be blocked when there is a clear incompatibility.

Hard block examples:

- equipment mismatch
- explicit "No Conestoga"
- explicit "No Stogas"
- explicit "Conestoga would not work"
- explicit "flatbed only" or "flat only" when driver is Conestoga
- overweight above driver capacity when no review exception is allowed
- oversize / OD / permit requirement if the driver cannot take it
- pickup or delivery does not match the intended search constraints
- dates or times do not fit driver availability
- dimensions do not fit the equipment
- explicit broker/load note showing the load cannot fit the driver

Hard blocks should not be overridden by broker memory, driver memory, or lane memory.

---

## 3. Conestoga rules

Conestoga can accept loads with tarp requirements.

Reason:

- Conestoga itself covers the load.
- Tarp-required notes should not block Conestoga by default.
- Tarp-required notes should not create review-once only because the driver profile says `can_take_tarps = false`.

Conestoga should be blocked only when notes explicitly say:

- No Conestoga
- No Stogas
- Conestoga would not work
- Flatbed only
- Flat only
- OD / oversize / permit / wide load
- overweight above allowed capacity
- dimensions do not fit Conestoga

---

## 4. Flatbed / Step Deck postings for Conestoga

If the posted equipment is:

- Flatbed
- Flat
- Step Deck
- Flat or Step
- Flatbed or Step Deck

and the driver has Conestoga, the load should usually become:

```text
REVIEW_ONCE / CONESTOGA VERIFY
````

The system should not automatically block only because the posting says Flatbed or Step Deck.

Block only if notes explicitly exclude Conestoga or show clear incompatibility.

---

## 5. Rate = 0 rule

A load with rate `0` or missing rate should not be automatically blocked.

If the load otherwise fits:

```text
REVIEW_ONCE / RATE CHECK
```

Reason:

* Brokers often post rates as $0.
* Dispatcher may need to call or email for rate.
* Good lanes should not be missed only because rate is missing.

Rate = 0 can be blocked only if another hard-block reason exists.

Examples of separate hard-block reasons:

* wrong equipment
* overweight
* wrong pickup/delivery
* timing conflict
* dimensions do not fit
* explicit note showing the load is not suitable

---

## 6. RPM logic

RPM should be used as a quality signal, not always as a hard block.

If RPM is below preferred minimum:

* add reason
* lower priority
* possibly mark as review once
* do not automatically block if the gross, lane, and reload potential are strong

Rate sensitivity can be learned over time, but only with enough data.

---

## 7. Broker MC and broker status

Broker MC is required for reliable broker/factoring status.

If broker MC is missing, empty, or `NEEDS CHECK`:

```text
Broker Status: UNKNOWN / MC REQUIRED / NEEDS CHECK
```

It must not show:

```text
Broker Status: BUY
```

Reason:

* Factoring status cannot be trusted without a valid MC.
* Broker memory should not pretend that the broker is verified.

---

## 8. Broker contact and reference ID

Every real DAT load should try to show:

* broker name
* broker MC
* phone or email
* reference ID

Reference ID should be searched in:

* structured fields
* notes
* broker text
* Telegram alert text
* known reference patterns

If no reference ID is found, Telegram should show:

```text
Reference ID: NO ID
```

The field should not be hidden.

---

## 9. ISO tank rule

ISO tanks in commodity or notes are a document-related warning.

If notes mention:

* ISO tank
* ISO tanks

Then the system should treat this as:

```text
REVIEW_ONCE / DOCUMENT WARNING
```

unless clearer rules are added later.

Reason:

* ISO tank loads may require documents, certifications, or special handling.
* This should not be silently treated as a clean load.

---

## 10. Overweight logic

Flatbed overweight above driver max weight should usually be blocked.

However, for good loads, the system may send one dispatcher review if:

* the load is otherwise strong
* driver profile does not already have a hard block setting
* there is no confirmed rule that this driver cannot take the weight

If dispatcher rejects because the driver cannot take that weight, update driver memory/profile later so similar loads are blocked in the future.

---

## 11. Telegram flow

The Telegram flow should send information in this order:

1. market / zone analysis
2. top load opportunities with posted rates
3. rate = 0 matching loads separately as `REVIEW_ONCE / RATE CHECK`
4. search health checks when needed

The system should eventually send all matching loads that fit filters, not only a few.

The minimum RPM filter should not be used too aggressively per-driver, because it may hide possible options.

---

## 12. DispatchCase concept

A DispatchCase represents one operational load opportunity or decision.

A case should connect:

```text
market data
AI decision
Telegram alert
dispatcher feedback
ratecon evidence
final outcome
event timeline
```

A DispatchCase should contain:

* case ID
* driver
* load ID
* reference ID
* pickup
* delivery
* rate
* miles
* RPM
* weight
* trailer
* broker
* broker MC
* broker contact
* AI decision
* AI category
* status
* final outcome
* reasons
* Telegram alerts
* dispatcher feedback
* ratecons
* events

---

## 13. Case status rules

Current case status and final outcome must be separate.

Current status examples:

* `OPEN`
* `CALLED`
* `SENT_TO_DRIVER`
* `BOOKED`
* `RATECON_RECEIVED`
* `REJECTED`
* `SKIPPED`
* `COVERED`
* `REMOVED`
* `DUPLICATE`

Final outcome examples:

* `BOOKED`
* `RATECON_RECEIVED`
* `REJECTED`
* `SKIPPED`
* `COVERED`
* `REMOVED`
* `DUPLICATE`

If there is no final outcome:

```text
final_outcome = None
```

---

## 14. Feedback status transition rules

Dispatcher feedback should update case status carefully.

Working feedback:

```text
called_broker -> CALLED
sent_to_driver -> SENT_TO_DRIVER
```

Final feedback:

```text
booked -> BOOKED
ratecon_received -> RATECON_RECEIVED
bad_broker -> REJECTED
rate_too_low -> REJECTED
driver_rejected -> REJECTED
covered -> COVERED
skipped -> SKIPPED
duplicate -> DUPLICATE
```

Final outcome must not be downgraded by later working feedback.

Example:

If case is:

```text
status = RATECON_RECEIVED
final_outcome = RATECON_RECEIVED
```

then later `sent_to_driver` must not change status back to `SENT_TO_DRIVER`.

---

## 15. Event timeline rules

Every important action should be recorded as an event.

Main event types:

* `AI_DECISION_CREATED`
* `TELEGRAM_ALERT_SENT`
* `DISPATCHER_FEEDBACK_ADDED`
* `RATECON_RECEIVED`
* `LOAD_APPEARED`
* `LOAD_UPDATED`
* `LOAD_REMOVED`

Events should support:

* replay reports
* debugging
* backtesting
* Shadow Dispatcher workflow
* future simulation

---

## 16. Broker memory rules

Broker memory should learn from dispatcher feedback.

Examples:

```text
bad_broker 2x -> BAD_BROKER_REVIEW / HIGH
booked 2x + ratecon_received 1x -> GOOD / LOW
rate_too_low repeated -> RATE_NEGOTIATION_WARNING
```

Broker memory can affect decisions carefully.

Rules:

* high-risk broker memory can move a clean load to review
* broker memory should not override hard blocks
* positive broker memory can add confidence
* missing MC prevents reliable broker status
* bad broker feedback is broker memory, not driver preference

---

## 17. Driver memory rules

Driver memory should not be trusted from a small sample.

Sample quality:

* 0-9 signals: `INSUFFICIENT_SAMPLE`
* 10-24 signals: `EARLY_SIGNAL`
* 25-49 signals: `DEVELOPING_PATTERN`
* 50+ signals: `RELIABLE_PATTERN`

Before 50+ signals, driver memory should be informational only.

Driver preference memory should not automatically block loads.

---

## 18. Driver lane memory rules

Lane memory should be separate from general driver memory.

Example:

```text
Stockton, CA -> Dallas, TX
positive feedback 4x
rate feedback 1x
```

This may become:

```text
POSITIVE_LANE_WITH_RATE_SENSITIVITY
```

But if sample size is low:

```text
INSUFFICIENT_SAMPLE
```

Then it should not affect decision automatically.

Lane memory should distinguish:

* positive driver/lane signal
* rate sensitivity
* broker issue
* market timing issue
* unclear dispatcher/driver negative signal

---

## 19. Memory vs decision rules

Memory can add context.

Memory can add reasons.

Memory can suggest review.

Memory should not silently override:

* hard block logic
* equipment logic
* date/time logic
* weight/dimension logic
* broker MC requirement
* explicit notes from the load

Before reliable sample size, memory should be visible but not controlling.

---

## 20. Search health rules

If no loads are found or very few loads are available, the system can suggest:

* increasing radius
* checking nearby markets
* relaxing target destination
* reviewing equipment constraints
* checking if RPM filter is too strict
* checking if too many loads are hidden by filters

Search health should be sent separately from load opportunities.

---

## 21. Simulation rules

Before live DAT/API integration, simulation should test:

* load appeared
* load updated
* load removed
* duplicate alerts
* rate changes
* DispatchCase creation
* event timeline
* rate check flow
* broker repost logic
* covered logic
* feedback transitions
* ratecon received

Simulation should stay safe and predictable.

