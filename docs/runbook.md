# docs/runbook.md

## Quickstart (Dry-run)
1. Create config file (example below).
2. Run: `python -m src.main --config config.yaml --dry-run`
3. Confirm:
   - logs show ticks
   - state file updates
   - simulated fills occur when price crosses limits

## Example config (100 USDT)
- `symbol: BTCUSDT`
- `mode: LONG`
- `initial_capital_amount: 100`
- `initial_capital_asset: USDT`
- `range_pct_bottom: -0.10`
- `range_pct_top: 0.10`
- `grid_intervals: 20`
- `check_interval_minutes: 5`
- `fee_rate: 0.001`
- `state_path: ./state.json`

## Enabling live trading (opt-in)
1. Set environment variables:
   - `EXCHANGE_API_KEY`
   - `EXCHANGE_API_SECRET`
2. Run connectivity-only (no orders):
   - `python -m src.main --config config.yaml --live=false`
   - should fetch price and symbol rules only
3. Enable live (orders allowed):
   - `python -m src.main --config config.yaml --live`
4. Start with very small notional and monitor logs.

## Operational notes
- The bot places at most one order per tick.
- Restart-safe behavior: bot reconciles active order before placing a new one.

## Troubleshooting (common)
- Precision / LOT_SIZE errors → rounding/step size mismatch.
- MIN_NOTIONAL → per-grid notional too small; reduce N or increase capital.
- Insufficient balance → wrong initial asset for the chosen mode.
- Rate limits → increase check interval or reduce API calls per tick.