# Driver Profile Source Of Truth

AI Dispatch Team currently has two driver profile sources:

```text
data/driver_profiles.json
data/drivers/*.json
```

This document defines how they should be treated during Foundation Hardening.

---

## Current Decision

`data/driver_profiles.json` is the primary source of truth for driver business rules.

Reason:

- It contains the current dispatch safety fields.
- It supports equipment, weight, tarp, OD, permit, document, and tracking rules.
- It is used by `driver_profile_loader.py` to enrich `SearchRequest` before market matching.

`data/drivers/*.json` remains a legacy compatibility source for now.

Reason:

- `SearchRequest` currently loads these files at initialization through `driver_profile.py`.
- These files still provide startup fields such as equipment and max weight.
- Removing or changing this path should be a separate compatibility refactor.

---

## Current Code Paths

Primary profile loader:

```text
app/market_intelligence/driver_profile_loader.py
data/driver_profiles.json
```

Known callers:

```text
app/market_intelligence/market_snapshot.py
scripts/log_decisions_snapshot.py
```

Legacy compatibility loader:

```text
app/market_intelligence/driver_profile.py
data/drivers/*.json
```

Known caller:

```text
app/market_intelligence/search_request.py
```

---

## Required Primary Fields

Every primary driver profile should include:

```text
driver_name
equipment
max_weight
can_take_tarps
max_tarp_size
can_take_od
can_take_permit_loads
hazmat
tanker_endorsement
twic
us_citizen
green_card_holder
work_permit
ramps
dunnage
tracking_ok
```

Document fields may be `true`, `false`, or `null`.

---

## Compatibility Rule

If a matching legacy profile exists, core fields must not conflict:

```text
driver_name
equipment
max_weight
accept_tarps / can_take_tarps
```

The old `accept_tarps` field maps to primary `can_take_tarps`.

Current audited drivers:

```text
Alex
Sergey
TestCA
TestCAFlatbed
```

At the time of this audit, all current legacy profiles have matching primary profiles and aligned core fields.

---

## Do Not Do Yet

- Do not delete `data/drivers/*.json`.
- Do not change `SearchRequest` profile-loading behavior without focused tests.
- Do not split new business fields between both sources.
- Do not add DAT/API, dashboard, Observer, or live automation as part of this cleanup.

---

## Safe Next Steps

1. Keep new driver business fields in `data/driver_profiles.json`.
2. Keep legacy files aligned until `SearchRequest` is migrated.
3. Add a compatibility adapter only in a separate mini-block.
4. Add tests proving `SearchRequest` and `apply_driver_profile_to_search_request()` agree before changing loader behavior.
