# docs/test-plan.md

## Goals
- Deterministic verification of grid math and state transitions.
- Confidence that dry-run and persistence work before live integration.

## Test categories

### 1) Unit tests (pure functions)
- Grid generator:
  - endpoints match computed `P_bottom` and `P_top`
  - monotonic increasing levels
  - correct length N+1
- Sizing:
  - LONG: notional split and qty calculation
  - SHORT_INVERTED: BTC split across grids
- Sanity checks:
  - grid step percent calculation
  - warning thresholds vs fee assumptions

### 2) State machine tests (MockExchange)
Deterministic price sequences:
- Sideways within range: alternating buy/sell at adjacent levels.
- Trend up: sells happen when appropriate; out-of-range behavior “valid side only”.
- Trend down: buys happen when appropriate; “valid side only”.
- Jump across multiple levels between ticks: confirm only one order is issued per tick.
- Restart:
  - save state mid-run, reload, ensure no duplicate order placement.

### 3) Dry-run simulation tests
- Fill rules:
  - BUY fills when `P <= limit`
  - SELL fills when `P >= limit`
- Determinism:
  - same price feed → identical trades and final state.

### 4) Integration smoke tests (non-trading)
- Fetch price and symbol rules repeatedly for 30 minutes without exceptions.
- Validate rounding outputs against symbol constraints.

## DoD
- Core logic tests cover the main path and the listed scenarios.
- Dry-run stability test run is documented (command + expected output).
- Integration smoke test is documented.