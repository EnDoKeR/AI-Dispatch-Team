# Development Rules

This document defines how AI Dispatch Team should be developed going forward.

The goal is to prevent the project from becoming difficult to maintain as more dispatch logic is added.

---

## 1. Main rule

Do not overload large files.

New logic should normally be added as:

~~~text
small focused module + matching test file
~~~

Example:

~~~text
app/market_intelligence/feature_core.py
tests/test_feature_core.py
~~~

---

## 2. Orchestrator rule

Orchestrator files should only coordinate workflow.

Good orchestrator responsibilities:

- normalize high-level inputs
- call focused helpers
- combine helper results
- return final decision/status/message
- preserve backward-compatible imports when needed

Bad orchestrator responsibilities:

- large business-rule blocks
- SQL query construction
- formatting logic
- grouping logic
- parsing logic
- memory classification logic
- unrelated helper functions

---

## 3. Test-first refactor rule

Before moving risky logic:

1. Add tests around current behavior.
2. Run focused tests.
3. Move the logic.
4. Update imports.
5. Run focused tests again.
6. Run full test discovery.
7. Commit only after the mini-block is stable.

Standard checks:

~~~powershell
py -m compileall app scripts main.py
py -m unittest discover -s tests -p "test_*.py"
git --no-pager diff --check
git status
~~~

---

## 4. Commit rule

Commit one logical mini-block at a time.

Good commit examples:

~~~text
Refactor notes parser payment helpers
Refactor driver lane preference groups
Connect driver lane preference queries
Update roadmap documentation
~~~

Avoid mixing business logic, refactor, docs, and unrelated cleanup unless it is a planned documentation-only block.

---

## 5. Business logic safety

Hard business logic wins over memory.

Memory may:

- add context
- add reasons
- suggest review
- improve confidence

Memory must not silently override:

- equipment mismatch
- explicit No Conestoga notes
- OD / permit hard rules
- overweight hard rules
- broker MC requirement
- date/time incompatibility
- dimensions that do not fit equipment

---

## 6. Sample-size protection

Driver, broker, and lane memory should not control decisions too early.

Signal levels:

~~~text
0-9 signals      -> INSUFFICIENT_SAMPLE
10-24 signals    -> EARLY_SIGNAL
25-49 signals    -> DEVELOPING_PATTERN
50+ signals      -> RELIABLE_PATTERN
~~~

Before reliable sample size, memory should remain informational or review context.

---

## 7. Documentation rule

When a major refactor or business rule changes:

- update README when product direction changes
- update BUSINESS_RULES when dispatch logic changes
- update ARCHITECTURE when module boundaries change
- update TESTING when test strategy changes
- update ROADMAP when phase progress changes
- update FOUNDATION_HARDENING when sprint priorities change

---

## 8. PowerShell workflow rule

The project is developed through controlled steps.

The assistant should provide:

- exact commands
- exact file paths
- exact functions/blocks to replace
- focused checks
- commit command only after verification

The user should not make independent code changes without a clear instruction in the current workflow.
---

## 9. Layer boundary rule

The project should follow strict architecture layers:

~~~text
Raw Intake -> Decision Engine -> DispatchCase Builder -> Memory Layer -> Interfaces
~~~

Layer rules:

- Raw Intake should not know Telegram or SQLite.
- Decision Engine should not send Telegram messages.
- Decision Engine should not write SQLite directly.
- DispatchCase Builder should connect decisions, events, feedback, and outcomes.
- Memory Layer should store and retrieve operational truth.
- Interfaces should display or collect information, not own business rules.

Avoid circular dependencies.

Avoid shortcuts where Telegram, reports, or memory modules make core dispatch decisions directly.

---

## 10. Replay-first intelligence rule

Before building autonomous agents, large dashboards, or live automation, the project should build replay and missed opportunity intelligence.

Priority order:

1. stable events
2. stable DispatchCase timeline
3. SQLite memory consistency
4. replay engine
5. missed opportunity engine
6. probabilistic memory
7. observer / interface expansion
8. live DAT/API integration

Do not build autonomous booking before replay can explain whether the AI was right or wrong.

---

## 11. Central storage split rule

Central storage files must not become large mixed-responsibility modules.

Default pattern for SQLite/local memory:

~~~text
*_io.py
*_connection.py
*_schema.py
*_repository.py
*_summary.py
*_rebuild.py
facade.py
~~~

The facade may keep backward-compatible imports and `__all__`, but it should not contain large local business logic.

Every storage helper module needs a matching test file.

Example:

~~~text
app/market_intelligence/sqlite_memory_repository.py
tests/test_sqlite_memory_repository.py
~~~
