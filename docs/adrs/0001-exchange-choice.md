# docs/adrs/0001-exchange-choice.md

## Title
Exchange choice for MVP spot grid bot

## Status
Proposed

## Context
We need one exchange for the MVP to avoid dual integration overhead. Criteria:
- Spot trading support
- Clear REST API for price, symbol rules, limit orders, order status
- Practical testing path (preferably test environment)
- Fees and rate limits acceptable for periodic checks

## Alternatives considered

### Option A: Binance
**Pros**
- Broad Spot API coverage and widely used ecosystem
- Practical testing options (including test environments) and extensive community examples
- Strong symbol metadata support (tick/step/min constraints)

**Cons**
- Baseline fees can be higher than some competitors (depends on tier/discounts)

### Option B: Pionex
**Pros**
- Lower spot fee baseline in many cases
- Straightforward REST endpoints for orders

**Cons**
- Testing story may be less convenient depending on available environments
- Smaller ecosystem and fewer common reference implementations

## Decision (proposed)
Start MVP with Option A (Binance) to reduce integration and testing risk. Re-evaluate after MVP stabilization if fees become a priority.

## Consequences
- Implement exactly one adapter first.
- Backlog removes dual-exchange work until MVP is stable.
- Add a follow-up ADR if/when a second adapter is justified.

## Follow-up actions
- Confirm exchange account availability and API key setup.
- Implement adapter behind `ExchangeAdapter` interface.
- Add “connectivity-only” smoke test mode.