# docs/functional-spec.md

## 1. Overview
Build a Python Spot grid bot MVP (single user) that trades BTC/USDT using a geometric grid over a fixed percent range around the start price. The bot checks the market every X minutes and maintains at most one active limit order at any time.

## 2. Goals
- Support Long and Short-inverted modes (spot-only; no borrowing).
- Geometric grid with N intervals between bottom/top.
- Periodic loop, state persistence, dry-run, simplified PnL.
- Minimal exchange adapter (one exchange for MVP).

## 3. Non-goals (MVP)
- Security hardening, multi-user, web UI, stop-loss/take-profit engine.
- Multiple simultaneous open grid orders.
- Dynamic grid recentering.
- Advanced fill handling (partial fills treated as filled only when closed).

## 4. Terminology
- **Base asset:** BTC
- **Quote asset:** USDT
- **Price:** USDT per 1 BTC
- **Grid intervals (N):** number of intervals; grid has N+1 price levels.
- **Phase:** BUY or SELL (internal state of which leg is next)

## 5. Inputs (runtime configuration)
- `symbol`: default `BTCUSDT`
- `mode`: `LONG` or `SHORT_INVERTED`
- `initial_capital_amount`: numeric (e.g., 100)
- `initial_capital_asset`: `USDT` or `BTC` (chosen at start)
- `range_pct_bottom`: e.g., `-0.10`
- `range_pct_top`: e.g., `+0.10`
- `grid_intervals`: integer N (e.g., 20)
- `check_interval_minutes`: integer X (e.g., 5)
- `dry_run`: boolean
- `fee_rate`: numeric (default exchange baseline; configurable)
- `min_grid_step_guard`: optional computed sanity warning threshold

## 6. Grid construction (geometric)
At start:
- read `P0` = current price
- compute `P_bottom = P0 * (1 + range_pct_bottom)`
- compute `P_top    = P0 * (1 + range_pct_top)`
- ensure `P_bottom > 0` and `P_top > P_bottom`

Define:
- `r = (P_top / P_bottom) ** (1 / N)`
- `levels[i] = P_bottom * r**i` for `i in [0..N]`

## 7. Order sizing (fixed, capital split across grids)
- `notional_per_grid = initial_quote_capital / N` (for LONG)
- `qty_base = notional_per_grid / order_price`

For SHORT_INVERTED (spot-only):
- expected initial capital is in BTC
- `qty_base = initial_btc_capital / N` per SELL leg

Rounding/minimums:
- order price rounded to exchange tick size
- qty rounded to exchange step size
- if qty or notional is below exchange minimums: skip order and log reason

## 8. State machine (one active order)
Bot maintains:
- `phase`: BUY or SELL
- optional `active_order`
- `last_filled_level_index`
- balances (estimated for dry-run / simplified mode)

General rules:
- At most one active order at a time.
- Only one order can be placed per tick.

### 8.1 Initial phase
- LONG: start in BUY (assuming initial asset is USDT)
- SHORT_INVERTED: start in SELL (assuming initial asset is BTC)

### 8.2 Level selection logic
Let current price be `P`.

**LONG**
- choose a BUY level at or below current price:
  - `i = max index where levels[i] <= P` (clamped to [0..N])
  - place BUY at `levels[i]` if balances allow
- after BUY at `levels[i]` fills, next SELL is at `levels[i+1]` if exists

**SHORT_INVERTED**
- choose a SELL level at or above current price:
  - `i = min index where levels[i] >= P` (clamped to [0..N])
  - place SELL at `levels[i]` if balances allow
- after SELL at `levels[i]` fills, next BUY is at `levels[i-1]` if exists

### 8.3 Out-of-range behavior (“continue only on the valid side”)
- If `P > P_top`: bot may only consider SELL-side actions (if it has BTC)
- If `P < P_bottom`: bot may only consider BUY-side actions (if it has USDT)
- Otherwise: normal adjacent-level behavior

## 9. Order execution (limit orders, periodic checks)
On each tick:
1. fetch `P`
2. if there is an active order:
   - fetch status
   - if FILLED/CLOSED:
     - update state, update simplified balances, record trade
     - flip `phase` and schedule the adjacent-level order on next tick (or same tick only if it respects “1 order per tick”)
   - else do nothing
3. if no active order:
   - compute intended order (side, level index, price, qty)
   - place order (or simulate if dry-run)

Partial fills:
- treated as not filled until status is FILLED/CLOSED.

## 10. Simplified fees and PnL
- use constant `fee_rate`
- per completed round-trip:
  - `pnl_quote ≈ (sell_price - buy_price) * qty_base - fee_rate*(notional_buy + notional_sell)`
- record per-trade deltas and cumulative simplified PnL

Sanity check:
- compute approximate grid step percent; warn if step <= ~2*fee_rate (+ buffer)

## 11. Dry-run mode
- No API order placement.
- Simulated fill:
  - BUY fills if `P <= limit_price`
  - SELL fills if `P >= limit_price`
- Writes the same state updates and trade records as live mode.

## 12. Persistence
- State stored in `state.json`
- Atomic writes (temp + rename)
- On startup:
  - load state if present; validate version
  - otherwise initialize new state from config and current price

## 13. Acceptance criteria (high-level)
- Bot can run dry-run for 2 hours without crashing.
- State survives restart without duplicating orders.
- For deterministic price series, bot produces deterministic order intents.
- Logs show tick-by-tick status and every state transition.

## 14. Future enhancements (documented, not implemented)
- Reinvestment mode
- Dynamic grid recentering
- Multiple simultaneous open orders (classic grid)
- BTC/ETH pair support