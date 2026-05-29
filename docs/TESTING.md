# Testing Plan

This document defines the testing strategy for AI Dispatch Team.

The project is moving from MVP scripts toward a stable Dispatch Operating Intelligence System.

Before adding more automation, core logic must be protected by repeatable tests.

---

## 1. Testing goals

Testing should protect:

- dispatch business rules
- equipment compatibility logic
- rate check logic
- broker memory logic
- driver memory logic
- driver lane memory logic
- DispatchCase timeline logic
- feedback status transitions
- SQLite memory rebuild
- Telegram feedback integration
- simulation events

The goal is not to test everything at once.

The goal is to protect the rules that can break dispatch decisions.

---

## 2. Current manual test commands

Run these commands from the project root:

```powershell
cd C:\Projects\AI-Dispatch-Team
````

Compile check:

```powershell
py -m compileall app scripts main.py
```

Build DispatchCases:

```powershell
py scripts/build_dispatch_cases.py
```

Build SQLite memory:

```powershell
py scripts/build_sqlite_memory.py
```

Case status report:

```powershell
py scripts/case_status_report.py --summary
```

SQLite memory report:

```powershell
py scripts/sqlite_memory_report.py --summary
```

Feedback learning report:

```powershell
py scripts/feedback_learning_report.py --summary
```

Broker memory rules report:

```powershell
py scripts/broker_memory_rules_report.py --broker-mc 222222
```

Driver preference rules report:

```powershell
py scripts/driver_preference_rules_report.py --driver TestCAFlatbed
```

Driver lane preference report:

```powershell
py scripts/driver_lane_preference_report.py --driver TestCAFlatbed --only-actionable
```

Learning recommendations report:

```powershell
py scripts/learning_recommendations_report.py --only-actionable
```

---

## 3. Simulation test flow

The timed load board simulator should be tested before live DAT/API integration.

### Step 1 — Load appeared

```powershell
py scripts/run_load_board_simulation.py --reset --clear-sent
py scripts/run_load_board_simulation.py --step 1 --clear-sent
py main.py
py scripts/build_dispatch_cases.py
py scripts/case_replay_report.py SIM-CLEAN-001 TestCAFlatbed --latest
```

Expected timeline:

```text
LOAD_APPEARED
AI_DECISION_CREATED
TELEGRAM_ALERT_SENT
```

Expected result:

```text
MATCH / LOAD OPPORTUNITY
```

---

### Step 2 — Rate check load appeared

```powershell
py scripts/run_load_board_simulation.py --reset --clear-sent
py scripts/run_load_board_simulation.py --step 2 --clear-sent
py main.py
py scripts/build_dispatch_cases.py
py scripts/case_replay_report.py SIM-RATECHECK-001 TestCAFlatbed --latest
```

Expected result:

```text
REVIEW_ONCE / RATE CHECK
Rate: $0
```

Expected timeline:

```text
LOAD_APPEARED
AI_DECISION_CREATED
TELEGRAM_ALERT_SENT
```

---

### Step 3 — Rate updated

```powershell
py scripts/run_load_board_simulation.py --step 3 --clear-sent
py main.py
py scripts/build_dispatch_cases.py
py scripts/case_replay_report.py SIM-RATECHECK-001 TestCAFlatbed --latest
```

Expected result:

```text
LOAD_UPDATED
AI_DECISION_CREATED
TELEGRAM_ALERT_SENT
Rate: $4300
```

Expected decision:

```text
MATCH / LOAD OPPORTUNITY
```

unless another review rule applies.

---

### Step 4 — Load removed / covered

```powershell
py scripts/run_load_board_simulation.py --step 4 --clear-sent
py main.py
py scripts/build_dispatch_cases.py
py scripts/case_replay_report.py SIM-CLEAN-001 TestCAFlatbed --latest
```

Expected timeline includes:

```text
LOAD_REMOVED
Reason: covered
```

Expected case:

```text
Status: COVERED
Final Outcome: COVERED
```

---

## 4. Business rule tests to add

Automated tests should be added for these rules.

### Conestoga tarp rule

Rule:

```text
Conestoga can take tarp-required loads because Conestoga covers the load.
```

Expected:

```text
Tarp-required note should not block Conestoga.
Tarp-required note should not create review only because driver cannot take tarps.
```

---

### No Conestoga blocker

Rule:

```text
Explicit No Conestoga / No Stogas / Flatbed only should block Conestoga.
```

Expected:

```text
Decision: BLOCK
```

---

### Flatbed / Step Deck posting for Conestoga

Rule:

```text
Flatbed or Step Deck posting should become CONESTOGA VERIFY, not automatic block.
```

Expected:

```text
Decision: REVIEW_ONCE
Category: CONESTOGA VERIFY
```

---

### Rate = 0

Rule:

```text
Rate = 0 should not auto-block if the load otherwise fits.
```

Expected:

```text
Decision: REVIEW_ONCE
Category: RATE CHECK
```

---

### Missing MC

Rule:

```text
Missing broker MC cannot show BUY.
```

Expected:

```text
Broker Status: NEEDS MC CHECK
or
Broker Status: UNKNOWN / MC REQUIRED
```

Not allowed:

```text
Broker Status: BUY
```

---

### Broker memory high risk

Rule:

```text
bad_broker feedback 2x should create BAD_BROKER_REVIEW / HIGH.
```

Expected:

```text
Broker Memory Status: BAD_BROKER_REVIEW / HIGH
```

If the load is otherwise clean:

```text
Decision may move to REVIEW_ONCE / BROKER REVIEW
```

If the load has a hard block:

```text
Decision remains BLOCK
```

---

### Final outcome protection

Rule:

```text
Final outcome must not be downgraded by later working feedback.
```

Example:

```text
RATECON_RECEIVED
then
sent_to_driver
```

Expected:

```text
Status remains RATECON_RECEIVED
Final Outcome remains RATECON_RECEIVED
```

---

### Driver sample protection

Rule:

```text
Driver memory under 50 signals should not automatically control decisions.
```

Expected:

```text
0-9 signals: INSUFFICIENT_SAMPLE
10-24 signals: EARLY_SIGNAL
25-49 signals: DEVELOPING_PATTERN
50+ signals: RELIABLE_PATTERN
```

---

### Driver lane sample protection

Rule:

```text
Lane memory under 50 signals should not automatically control decisions.
```

Expected:

```text
Lane memory can show signal.
Lane memory should not override hard logic.
Lane memory should not auto-block.
```

---

## 5. DispatchCase tests to add

Automated tests should cover:

* case id generation
* matching by driver + reference ID
* matching by load ID
* feedback matching
* Telegram outbox matching
* ratecon attachment matching
* duplicate event protection
* simulation event attachment
* LOAD_REMOVED -> COVERED
* LOAD_UPDATED appears in replay
* `--latest` replay window

---

## 6. SQLite memory tests to add

Automated tests should cover:

* database file creation
* table creation
* case insert
* event insert
* feedback insert
* Telegram alert insert
* ratecon insert
* rebuild from JSONL
* report filters:

  * driver
  * status
  * final outcome
  * broker MC
  * category
  * has feedback
  * has telegram

---

## 7. Telegram feedback tests to add

Automated or semi-automated tests should cover:

* callback parsing
* reference ID inside callback
* old callback fallback from message text
* missing reference ID handling
* feedback saved with source `telegram_button`
* button feedback appears in DispatchCase
* button feedback appears in SQLite
* button feedback changes status correctly

---

## 8. Report tests to add

Reports should run without crashing:

```powershell
py scripts/case_status_report.py --summary
py scripts/sqlite_memory_report.py --summary
py scripts/broker_memory_report.py
py scripts/broker_memory_rules_report.py
py scripts/broker_memory_decision_report.py --summary
py scripts/feedback_learning_report.py --summary
py scripts/learning_recommendations_report.py --only-actionable
py scripts/driver_learning_report.py --summary --show-recommendations
py scripts/driver_preference_rules_report.py --driver TestCAFlatbed
py scripts/driver_lane_preference_report.py --driver TestCAFlatbed --only-actionable
```

---

## 9. First automated testing milestone

The first automated test milestone should include tests for:

1. status transitions
2. broker MC safety
3. rate = 0 logic
4. Conestoga tarp logic
5. no Conestoga blocker
6. broker memory rules
7. sample size protection
8. DispatchCase event deduplication

---

## 10. Definition of done

Testing foundation is acceptable when:

* manual test commands are documented
* first automated tests exist
* core business rules are protected
* main reports run successfully
* simulation flow can be replayed
* future refactors can be done safely

