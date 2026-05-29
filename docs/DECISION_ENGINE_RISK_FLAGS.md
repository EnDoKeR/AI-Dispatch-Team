# DecisionEngine Risk Flag Taxonomy

This document defines a first stable vocabulary for future DecisionEngine risk flags. It does not implement code or change runtime behavior.

Risk flags are machine-readable labels. They should complement, not replace, human-readable `review_reasons`, `block_reasons`, and explanations.

## Typical Action Levels

- `BLOCK`: usually a hard incompatibility.
- `REVIEW`: usually requires dispatcher verification.
- `INFO`: context only; should not change the decision by itself.

Action levels are defaults, not permanent truth. Final behavior must still follow accepted business rules and tests.

## Missing Data

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `MISSING_RATE` | Rate is absent or posted as zero. | load facts, intake record | `REVIEW` |
| `MISSING_WEIGHT` | Weight is missing. | load facts, intake record, parser output | `REVIEW` |
| `MISSING_DIMENSIONS` | Dimensions are missing when load language suggests OD/oversize or dimension-sensitive freight. | notes parser, intake parser | `REVIEW` |
| `MISSING_COMMODITY` | Commodity is missing. | load facts, intake record | `REVIEW` |
| `MISSING_REFERENCE_ID` | Broker/reference/load number is missing. | load facts, intake record | `REVIEW` |
| `MISSING_PICKUP_DATE` | Pickup date is missing. | load facts, intake record | `REVIEW` |
| `MISSING_DELIVERY_DATE` | Delivery date is missing. | load facts, intake record | `REVIEW` |
| `BROKER_MC_MISSING` | Broker MC is missing or invalid. | load facts, intake record, broker block | `REVIEW` |
| `BROKER_NAME_MISSING` | Broker name is missing. | load facts, intake record | `REVIEW` |

Policy notes:

- Missing rate should not automatically block a load.
- Missing broker MC must not display BUY.
- Missing fields should flow from intake/parser evidence into DecisionEngine output without being inferred from Telegram text.

## Equipment Mismatch

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `UNCLEAR_EQUIPMENT` | Equipment type is missing or ambiguous. | load facts, parser output, notes | `REVIEW` |
| `EQUIPMENT_MISMATCH` | Posted equipment clearly does not match driver equipment/capability. | load facts, driver profile | `BLOCK` or `REVIEW` |
| `FLATBED_VERIFY` | Flatbed-style posting may be workable but needs verification. | load facts, notes parser | `REVIEW` |
| `STEPDECK_VERIFY` | Step Deck posting may be workable but needs verification. | load facts, notes parser | `REVIEW` |
| `NO_BOX_TRUCK` | Notes exclude box truck. | notes parser | `INFO` unless relevant |

## Conestoga Compatibility

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `NO_CONESTOGA` | Notes explicitly reject Conestoga/Stoga or require flatbed only. | notes parser, conestoga rules | `BLOCK` |
| `CONESTOGA_VERIFY` | Load is flatbed/stepdeck-style or prefers flatbed; Conestoga may work but must be verified. | load facts, notes parser | `REVIEW` |
| `CONESTOGA_COVERS_TARP` | Tarp requirement is covered by Conestoga. | tarp rules, driver profile | `INFO` |
| `CONESTOGA_OD_BLOCK` | OD/permit/wide load is not acceptable for Conestoga. | OD/permit rules | `BLOCK` |

Policy notes:

- Tarp-required loads should not block Conestoga by default.
- Conestoga should be blocked only by explicit no-Conestoga/flatbed-only language, OD/oversize/overweight/dimension conflicts, or other hard incompatibilities.

## Weight And Dimensions

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `OVERWEIGHT` | Weight exceeds driver max weight. | load facts, driver profile | `BLOCK` or `REVIEW` |
| `WEIGHT_REVIEW` | Weight is close/uncertain or policy says ask dispatcher. | load facts, driver profile | `REVIEW` |
| `OD_PERMIT_LOAD` | OD/permit/wide load detected. | notes parser, OD rules | `REVIEW` or `BLOCK` |
| `DIMENSIONS_NEED_CHECK` | Dimensions are incomplete or suspicious. | notes parser, parser confidence | `REVIEW` |
| `MULTISTOP_REVIEW` | Multiple stops or extra pickup/delivery clues require review. | notes parser, parser output | `REVIEW` |

## Appointment And Timing

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `PICKUP_TIME_NEEDS_CHECK` | Pickup time is missing, unclear, or marked needs check. | load facts, notes parser, intake parser | `REVIEW` |
| `DELIVERY_TIME_NEEDS_CHECK` | Delivery time is missing, unclear, or marked needs check. | load facts, notes parser, intake parser | `REVIEW` |
| `APPOINTMENT_REQUIRED` | Appointment/window required. | notes parser, intake parser | `REVIEW` |
| `ACTUAL_PICKUP_CHANGED` | Notes indicate actual pickup differs from posted pickup. | notes parser | `REVIEW` |
| `TIMING_RISK` | Timing may not support pickup/reload feasibility. | search request, load facts, future route timing | `REVIEW` |

## Rate / RPM / Market Weakness

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `RATE_MISSING` | Rate is missing or zero. | load facts | `REVIEW` |
| `RATE_CHECK_REQUIRED` | Dispatcher should confirm rate with broker. | quality rules, review category | `REVIEW` |
| `RATE_BELOW_MARKET` | Rate/RPM is below current market context. | market baseline | `REVIEW` or `INFO` |
| `LOW_RPM` | RPM is below preferred threshold. | quality rules | `INFO` or `REVIEW` |
| `STRONG_GROSS` | Gross pay is strong. | scoring | `INFO` |
| `STRONG_RPM` | RPM is strong for the relevant mileage bucket. | scoring, market baseline | `INFO` |
| `LOW_DATA_MARKET` | Market data is too limited for confident classification. | market baseline | `INFO` |

Policy notes:

- Static RPM thresholds should not be the only market logic.
- Rate/RPM context must respect mileage buckets.
- Low market confidence is not the same as a bad market.

## Bad Zone / Reload Risk

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `LOW_EXIT_CONFIDENCE` | Delivery market has too little exit data. | zone snapshot, exit classifier | `REVIEW` or `INFO` |
| `WEAK_EXIT_MARKET` | Delivery market has weak current exit context. | zone snapshot, exit classifier | `REVIEW` |
| `RISKY_EXIT_MARKET` | Delivery market has few/no clean exits and mostly review/rate-check options. | zone snapshot, exit classifier | `REVIEW` |
| `CLEAN_EXIT_AVAILABLE` | Clean exit options are visible. | zone snapshot, exit classifier | `INFO` |
| `RATE_CHECK_EXITS_AVAILABLE` | Exit options exist but need rate check. | zone snapshot, exit classifier | `REVIEW` |
| `RELOAD_WATCH_RECOMMENDED` | Inbound load may be worth watching for reload options. | exit classifier | `REVIEW` |
| `SECONDARY_EXIT_RISK` | The second leg in a two-load chain delivers into weak/risky context. | chain scoring | `REVIEW` |

Policy notes:

- A strong load into a weak exit market should not be hidden automatically.
- The expected context is `STRONG PAY / RELOAD WATCH ACTIVE` or equivalent later, not hard block.

## Broker / Payment Risk

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `BROKER_RISK` | Broker memory or notes indicate broker risk. | broker memory, notes parser | `REVIEW` |
| `BROKER_WATCHLIST` | Broker has watchlist-type history. | broker memory | `REVIEW` |
| `BROKER_RATE_NEGOTIATION_RISK` | Broker history suggests rate negotiation issues. | broker memory | `REVIEW` |
| `BROKER_POSITIVE_MEMORY` | Broker history is positive. | broker memory | `INFO` |
| `PAYMENT_RISK` | Notes indicate payment, cash/Zelle, quickpay, factoring, or no-buy concerns. | notes parser, broker block | `REVIEW` |
| `FACTORING_NEEDS_CHECK` | Factoring status is unclear. | broker block, future accounting model | `REVIEW` |

Policy notes:

- Broker memory can add review warnings or positive context.
- Broker memory should not override hard blocks.

## Document Requirements

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `HAZMAT_REQUIRED` | Hazmat required. | notes parser, document rules | `BLOCK` or `REVIEW` |
| `TWIC_REQUIRED` | TWIC required. | notes parser, document rules | `BLOCK` or `REVIEW` |
| `TANKER_REQUIRED` | Tanker endorsement required. | notes parser, document rules | `BLOCK` or `REVIEW` |
| `RAMPS_REQUIRED` | Ramps required. | notes parser, document rules | `BLOCK` or `REVIEW` |
| `DUNNAGE_REQUIRED` | Dunnage/wood/blocking/bracing required. | notes parser, document rules | `BLOCK` or `REVIEW` |
| `LEGAL_STATUS_REQUIRED` | US citizen/green card/work permit requirement. | notes parser, document rules | `BLOCK` or `REVIEW` |
| `DOCUMENTS_NEED_CHECK` | Required document status is unknown. | driver profile, document rules | `REVIEW` |

Policy notes:

- Known driver document absence may block.
- Unknown driver document status should usually be review and profile update.

## Tracking / Driver Requirements

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `TRACKING_REQUIRED` | Tracking is required. | notes parser, tracking rules | `BLOCK` or `REVIEW` |
| `DRIVER_PROFILE_UNKNOWN` | Driver profile lacks a needed capability answer. | driver profile, search request | `REVIEW` |
| `TARGET_DIRECTION_MISMATCH` | Load does not fit target direction/city policy. | target helpers, direction matcher | `BLOCK` or `REVIEW` |
| `PICKUP_TOO_FAR` | Pickup appears too far from driver location. | target helpers, region conflict | `BLOCK` or `REVIEW` |
| `LOCAL_LOAD` | Local/same-city or too-short load context. | local load rules | `BLOCK` or `REVIEW` |

## Notes Ambiguity

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `NOTES_AMBIGUOUS` | Notes contain unclear language affecting compatibility. | notes parser, parser confidence | `REVIEW` |
| `LOW_CONFIDENCE_PARSER_FIELD` | Parser extracted a field with low confidence. | parser confidence | `REVIEW` |
| `CONFLICTING_DOCUMENT_FIELDS` | Source document has conflicting values. | future parser/intake evidence | `REVIEW` |
| `CONTACT_NEEDS_CHECK` | Broker/contact data is unclear or has override conflict. | notes parser, contact parser | `REVIEW` |

## Factoring / Accounting Later

These flags are future context only. Do not implement factoring/accounting behavior yet.

| Flag | Meaning | Typical source | Usual action |
| --- | --- | --- | --- |
| `FACTORING_PACKET_INCOMPLETE` | Required packet fields/documents are missing. | future accounting model | `REVIEW` |
| `BROKER_FACTORING_NOT_APPROVED` | Broker/factoring eligibility is not approved. | future accounting model | `REVIEW` or `BLOCK` |
| `POD_MISSING` | Proof of delivery missing. | future document model | `REVIEW` |
| `RATECON_MISSING` | Rate confirmation missing. | future document model | `REVIEW` |
| `INVOICE_DATA_MISSING` | Invoice fields missing. | future accounting model | `REVIEW` |

Policy notes:

- Accounting/factoring flags must not submit packets or create financial/legal commitments.
- Any real factoring action requires dispatcher approval and a separate accepted design.

## First Implementation Recommendation

Start with constants or a small helper only after this taxonomy is accepted.

Recommended first code target:

```text
app/market_intelligence/decision_engine/risk_flags.py
```

or, before package migration:

```text
app/market_intelligence/decision_risk_flags.py
```

The first helper should expose stable names and metadata only. It should not change current load decisions.
