# docs/state-schema.md

## Purpose
Define the minimum persistent state needed to resume reliably and avoid duplicate orders.

## Versioning
- `schema_version`: integer starting at 1.
- Any breaking change increments version and includes migration notes.

## Minimal `state.json` fields

### Required top-level fields
- `schema_version`
- `created_at`, `updated_at`
- `config_snapshot` (key config used to start)
- `symbol`, `mode`

### Grid
- `grid`:
  - `P0`
  - `P_bottom`
  - `P_top`
  - `N`
  - `levels[]`

### Bot state
- `phase`: `BUY` or `SELL`
- `active_order`: nullable object:
  - `order_id` (string, or null in dry-run)
  - `side` (BUY/SELL)
  - `price`, `qty`
  - `level_index`
  - `status` (NEW/OPEN/FILLED/CANCELED/REJECTED)
  - `created_at`
- `last_filled_level_index`: nullable int

### Balances and accounting (simplified)
- `balances_estimated`:
  - `base` (BTC)
  - `quote` (USDT)
- `trades` (append-only list; may be bounded later):
  - `timestamp`, `side`, `price`, `qty`, `fee_est`, `pnl_delta_quote_est`
  - `order_id` (if live)
- `pnl_simplified`:
  - `cum_quote`
  - `trade_count`

## Atomic write requirement
Write `state.json.tmp` then rename to `state.json`.

## Restart rule (idempotency)
On startup:
- Load state; if `active_order` exists and is live:
  - poll its status and update before placing anything new
- Never place a new order in the same tick before reconciling the active order.

## Note
This document describes the intended persisted fields for MVP. The exact JSON schema can be formalized later if needed.