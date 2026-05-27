# AI Dispatch Team

AI Dispatch Team is an internal dispatch assistant project designed to help truck dispatchers evaluate loads, match them to drivers, monitor markets, reduce manual work, and send actionable alerts through Telegram.

The current focus is on flatbed / conestoga dispatch operations in the U.S. freight market.

---

## Current Project Goal

Build an AI-powered dispatch assistant that can:

- analyze available loads;
- match loads to driver profiles;
- calculate total miles and RPM;
- evaluate pickup feasibility;
- detect good, weak, and risky opportunities;
- send only actionable Telegram alerts;
- avoid duplicate alerts;
- support multiple drivers at the same time;
- prepare the system for DAT API / CSV / external load sources.

---

## Current MVP Flow

```text
data/mock_loads.json
↓
load_source.py
↓
MarketLoad normalization
↓
Driver Profile JSON
↓
Search Request JSON
↓
Market Snapshot
↓
Driver-specific matching
↓
Telegram Alerts

Да, обязательно. `README.md` нужно обновлять регулярно, потому что проект уже растет быстро, и без документации через пару недель будет сложно помнить:

что уже сделано, какая логика есть, какие файлы за что отвечают, что планируется дальше.

Я предлагаю правило:

**после каждого крупного спринта обновляем `README.md`**.

Сейчас как раз хороший момент, потому что мы завершили большой блок:

```text
Multi-driver search
Driver profiles
Search requests
Telegram alerts
Duplicate protection
Equipment compatibility
Mock load source layer
```

## Sprint 4.1 — README + DAT Load Normalizer

Сначала сделаем `README.md`, потом пойдем к DAT normalizer.

---

Создай или полностью замени файл:

```text
README.md
```

на это:

````markdown
# AI Dispatch Team

AI Dispatch Team is an internal dispatch assistant project designed to help truck dispatchers evaluate loads, match them to drivers, monitor markets, reduce manual work, and send actionable alerts through Telegram.

The current focus is on flatbed / conestoga dispatch operations in the U.S. freight market.

---

## Current Project Goal

Build an AI-powered dispatch assistant that can:

- analyze available loads;
- match loads to driver profiles;
- calculate total miles and RPM;
- evaluate pickup feasibility;
- detect good, weak, and risky opportunities;
- send only actionable Telegram alerts;
- avoid duplicate alerts;
- support multiple drivers at the same time;
- prepare the system for DAT API / CSV / external load sources.

---

## Current MVP Flow

```text
data/mock_loads.json
↓
load_source.py
↓
MarketLoad normalization
↓
Driver Profile JSON
↓
Search Request JSON
↓
Market Snapshot
↓
Driver-specific matching
↓
Telegram Alerts
````

---

## Main Features Implemented

### 1. Market Snapshot

The system groups loads into distance buckets:

```text
0–450 miles
450–700 miles
700–1300 miles
1300+ miles
```

For each bucket, it calculates:

* total loads;
* qualified loads;
* good loads;
* average total RPM;
* average rate;
* average opportunity score;
* average qualified score;
* average good score.

---

### 2. Opportunity Score

Each load receives an opportunity score based on:

* total RPM;
* gross rate;
* empty miles;
* distance bucket;
* execution simplicity;
* stops;
* weight;
* pickup feasibility;
* driver match status.

The score is used to rank top opportunities.

---

### 3. Driver Profiles

Driver profiles are stored as JSON files:

```text
data/drivers/sergey.json
data/drivers/alex.json
```

Example fields:

```json
{
  "driver_name": "Sergey",
  "equipment": "Conestoga",
  "max_weight": 40000,
  "accept_coils": true,
  "accept_tarps": false,
  "blocked_states": [],
  "preferred_directions": ["Midwest", "Southeast", "Texas"],
  "avg_daily_miles": 650,
  "home_city": "",
  "home_state": "",
  "notes": "Conestoga driver. Prefer legal full loads, reasonable weight, and simple 1P/1D loads."
}
```

Driver profiles store stable driver preferences and limitations.

---

### 4. Search Requests

Active search requests are stored as JSON files:

```text
data/search_requests/sergey_active.json
data/search_requests/alex_active.json
```

Example:

```json
{
  "driver_name": "Sergey",
  "current_location": "Dade City, FL",
  "available_time": "12 PM",
  "pickup_date": "today",
  "search_radius": 150,
  "target_direction": "Midwest",
  "min_total_rpm": 2.5,
  "notes": "Driver available around noon. Send only feasible loads or loads that need pickup confirmation."
}
```

Search requests store temporary search conditions for a specific driver.

---

### 5. Pickup Feasibility Logic

The system estimates whether a driver can make pickup based on:

* driver available time;
* empty miles;
* default driving speed: 50 miles per hour;
* safety buffer: 1 hour;
* pickup appointment or pickup closing time.

Possible pickup statuses:

```text
OK
NEEDS_CONFIRMATION
IMPOSSIBLE
TOO_FAR
```

If pickup time is missing, the system does not immediately reject the load. It marks it as:

```text
NEEDS_CONFIRMATION
```

and recommends verifying pickup time.

---

### 6. Driver Match Logic

Each load is matched against the driver profile and search request.

Driver match statuses:

```text
MATCH
REVIEW_ONCE
BLOCK
```

#### MATCH

The load fits the driver and request.

#### REVIEW_ONCE

The load is not perfect but may still be worth one review.

Examples:

* weight slightly above driver preference;
* flatbed posting for a conestoga driver;
* pickup time must be confirmed;
* RPM slightly below request minimum;
* tarp requirement needs clarification.

#### BLOCK

The load should not be sent as an opportunity.

Examples:

* NO BUY broker;
* OD load;
* overweight load;
* pickup impossible;
* empty miles too far;
* blocked state;
* driver does not accept the required commodity type.

---

### 7. Equipment Compatibility Logic

The system currently supports:

```text
Conestoga
Flatbed
```

Important logic:

* Conestoga can review Flatbed-posted loads if Conestoga may be accepted.
* Tarp-required notes do not automatically block Conestoga loads.
* For Conestoga, the main hard blocks are OD, overweight, too heavy, or physically incompatible loads.
* Flatbed drivers can accept tarp-required loads if their profile allows tarps.
* OD and overweight loads are blocked for now.

---

### 8. Telegram Alerts

The bot sends actionable alerts to a Telegram group.

Current Telegram message types:

```text
Market Summary
High Priority Load
Review Once Load
Search Health Check
```

### Market Summary

Sent only when the market state changes or has not been sent before for that search state.

Includes:

* driver name;
* search area;
* market status;
* best bucket;
* good loads;
* qualified loads;
* best match;
* recommendation.

### High Priority Load

Sent for strong matching loads.

Includes:

* driver name;
* pickup and delivery;
* rate;
* loaded miles;
* empty miles;
* total miles;
* total RPM;
* weight;
* trailer type;
* pickup time;
* delivery time;
* notes;
* delivery zone outlook;
* action;
* reason.

### Review Once Load

Sent only once per driver/load combination.

Used for strong loads that are outside driver settings but may be worth checking.

### Search Health Check

If no strong matches are found after monitoring, the bot can suggest relaxing filters.

Examples:

* expand empty radius;
* allow slightly higher weight;
* allow pickup-time verification;
* lower RPM target slightly;
* check review-once options.

---

## Duplicate Protection

Duplicate protection currently exists for:

```text
High Priority Loads
Review Once Loads
Market Summaries
Search Health Checks
```

Sent history files:

```text
data/sent_telegram_loads.txt
data/sent_review_once_loads.txt
data/sent_market_summaries.txt
data/sent_search_health_alerts.txt
```

Duplicate keys now include driver name, so the same load can be sent separately for different drivers if it is relevant to each driver.

---

## Delivery Zone Outlook

Telegram load cards include a basic delivery zone outlook:

```text
GOOD / STRONG RELOAD AREA
WORKABLE / CHECK RELOADS
RISKY / EXIT PLAN NEEDED
UNKNOWN / NEEDS MARKET CHECK
```

Current version uses simple state-based logic.

Future version should use dynamic market analysis based on:

* reload count around destination;
* average RPM from destination;
* average rate for 500-mile loads;
* average rate for 1000-mile loads;
* number of good loads;
* number of qualified loads;
* recent market changes.

---

## Current Data Source

Loads are currently stored in:

```text
data/mock_loads.json
```

They are loaded through:

```text
app/market_intelligence/load_source.py
```

This prepares the system for future load sources:

```text
DAT API
CSV export
Google Sheet
manual upload
scraper/parser
```

The core logic should not depend on where the loads come from.

---

## Current Folder Structure

```text
app/
  market_intelligence/
    load_source.py
    market_models.py
    market_snapshot.py
    search_request.py
    telegram_notifier.py

data/
  drivers/
    sergey.json
    alex.json

  search_requests/
    sergey_active.json
    alex_active.json

  mock_loads.json

  sent_telegram_loads.txt
  sent_review_once_loads.txt
  sent_market_summaries.txt
  sent_search_health_alerts.txt

main.py
README.md
.env
```

---

## Current Run Command

```bash
py main.py
```

The system will:

1. read all active search requests from `data/search_requests/`;
2. load the matching driver profile;
3. load current loads from `data/mock_loads.json`;
4. analyze loads for each driver separately;
5. send Telegram alerts if needed.

---

## Important Product Principles

### 1. Telegram should not be noisy

Telegram should receive only actionable alerts.

The bot should not spam:

* every load;
* weak loads;
* bad-zone loads without exit plan;
* repeated summaries;
* repeated review-once loads.

### 2. Agent thinks silently

The system may analyze many options internally, but the dispatcher should only receive messages that require action.

### 3. Bad-zone loads should not be sent unless exit plan exists

A load going into a weak zone should not be sent to Telegram just because the rate is good.

It should only be sent if:

* the destination market is actually workable; or
* the agent finds a good exit/reload option.

### 4. Driver-specific logic is critical

The same load can be:

```text
MATCH for one driver
REVIEW_ONCE for another driver
BLOCK for another driver
```

The system must always evaluate loads under the correct driver profile and active search request.

---

## Planned Next Steps

### Sprint 4.1 — DAT Load Normalizer

Create a normalization layer that converts raw DAT-style load data into the internal `MarketLoad` format.

Target output fields:

```text
pickup
delivery
rate
loaded_miles
empty_miles
weight
stops
commodity
pickup_time
delivery_time
posted_trailer_type
notes
requires_tarp
is_od
is_overweight
has_email
has_phone
broker_status
```

### Sprint 4.2 — Dynamic Delivery Zone Analysis

Replace simple state-based delivery zone outlook with dynamic market analysis.

The agent should evaluate the delivery market based on:

* available reloads;
* average RPM;
* average gross;
* good loads count;
* qualified loads count;
* empty miles required to find reloads;
* final zone quality.

### Sprint 4.3 — Silent Bad-Zone Watch

If a good load goes to a weak zone:

* do not alert Telegram immediately;
* silently watch the destination reload market;
* alert only if a good exit load appears;
* stop watching if the original inbound load disappears.

### Sprint 4.4 — Telegram Search Request Creation

Allow dispatchers to create active searches through Telegram.

Possible future flow:

```text
/start_search
→ choose driver
→ enter current location
→ enter available time
→ choose target direction
→ confirm search
```

### Sprint 4.5 — Rate Confirmation Upload

Future Telegram menu:

```text
Upload Rate Con
→ choose driver
→ booked by dispatcher / bot
→ upload PDF
→ parse rate con
→ save load history
```

This will allow the system to connect recommendations with actual booked loads.

---

## Current Status

The project currently has a working MVP backend with:

* multi-driver search;
* driver profiles;
* active search requests;
* market scoring;
* pickup feasibility;
* driver match logic;
* equipment compatibility;
* Telegram alerts;
* duplicate protection;
* review-once logic;
* basic delivery zone outlook;
* external mock load source.

The next important backend step is the DAT Load Normalizer.

```

---

После этого продолжаем к **Sprint 4.1 — DAT Load Normalizer**.

И да, я буду периодически предлагать обновить `README.md`, особенно после больших изменений.
```
