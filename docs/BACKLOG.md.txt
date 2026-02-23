## Product context

You are building a **single-user Python MVP grid bot** for **Spot** trading, starting with **BTC/USDT**, with:

* geometric grid over a **fixed % range** around the start price
* **periodic checks** every X minutes
* **at most 1 active limit order** at a time
* modes: **Long** and **“Short-inverted”** (spot-only logic inversion; no borrowing)
* **dry-run** mode and **state persistence** (JSON file)
* simplified PnL, basic logs
* non-goals for MVP: security hardening, multi-user, stop-loss, complex risk engine, multiple simultaneous orders, dynamic grid recentering
* python

---

## Global Definition of Done (applies to all backlog items)

* Code is formatted/linted (e.g., `ruff` or `black` + `ruff`) and passes CI checks (local is acceptable for MVP).
* Unit tests exist for core logic (grid math, order decision) with deterministic fixtures.
* No secrets committed; API keys loaded from environment variables (minimal hygiene, not “security focus”).
* Logs are readable and include key fields (timestamp, symbol, mode, state transition, order intent/outcome).
* Documentation updated (README + config examples).
* Feature works end-to-end in **dry-run** without exceptions for at least a 2-hour run.

---

# Backlog (Epics → User Stories)

## Epic A — Requirements & Operating Model (P0)

### A1 — Write MVP Functional Spec

**Context:** Capture the precise behavior to prevent scope drift.
**Tasks:**

* Define inputs (capital, asset, range %, N intervals, check interval, mode).
* Define geometric grid formulas and rounding rules.
* Define “1 active order” state machine (phases, transitions).
* Define out-of-range behavior (“continue only on the valid side”).
* Define simplified PnL accounting and fee assumptions.
* Define non-goals and next-step roadmap (dynamic grid, reinvest, multi-order grid).
  **DoD:**
* Spec is written in English, versioned with the repo, and includes at least 2 worked examples (Long and Short-inverted) with numbers.

### A2 — Exchange Selection Decision Record

**Context:** Choose one exchange for MVP to avoid dual integration overhead.
**Tasks:**

* Document selection criteria: test environment availability, API maturity, fees, rate limits, symbol availability.
* Decide MVP exchange; document rationale and constraints.
  **DoD:**
* One-page decision record committed (ADR format is fine).

---

## Epic B — Repo Setup & Developer Workflow (P0)

### B1 — Initialize Project Skeleton

**Context:** Keep structure minimal but scalable.
**Tasks:**

* Create repo structure:

  * `src/` (core)
  * `src/exchange/` (adapter)
  * `src/bot/` (loop + state machine)
  * `src/core/` (grid, sizing, PnL)
  * `tests/`
* Add `pyproject.toml` with dependencies and scripts.
* Add formatting/linting (`ruff` and optionally `black`).
* Add a basic `Makefile` or `task` scripts for run/lint/test.
  **DoD:**
* `python -m src.main --help` runs and prints CLI help.
* `ruff check .` and `pytest` run without errors (even if tests are placeholders).

### B2 — Configuration & Secrets Handling (Minimal)

**Context:** MVP hygiene without security overbuild.
**Tasks:**

* Load config from a `.yaml` or `.json` file (plus CLI overrides).
* Load API keys from environment variables (support `.env` file optionally).
* Add config validation with clear error messages.
  **DoD:**
* Running without keys defaults to dry-run and prints a clear warning.
* Misconfigured ranges or grid counts fail fast with actionable errors.

---

## Epic C — Core Trading Math & Decision Engine (P0)

### C1 — Implement Geometric Grid Generator

**Context:** Deterministic and testable grid levels.
**Tasks:**

* Implement function: `build_grid(P0, bottom_pct, top_pct, N) -> levels[]`.
* Ensure N intervals yields N+1 levels.
* Add rounding hooks (tick size applied later by exchange adapter).
* Add unit tests for level monotonicity, correct endpoints, and ratio behavior.
  **DoD:**
* For known inputs, grid levels match expected values within tolerance.
* Tests cover edge cases (N=1, narrow range, invalid pct order).

### C2 — Implement Order Sizing (Fixed, Capital Split Across Grids)

**Context:** Keep size stable per your decision.
**Tasks:**

* Long: `notional_per_grid = quote_capital / N`, `qty = notional/price`.
* Short-inverted: `qty = base_capital / N` for sell legs (spot-only).
* Add “insufficient balance” behavior (skip order + log reason).
* Unit tests for sizing under typical inputs.
  **DoD:**
* For both modes, sizing outputs are deterministic and respect min order constraints after rounding (when provided).

### C3 — Implement State Machine (1 Active Limit Order)

**Context:** This is the core MVP behavior.
**Tasks:**

* Define states: `IDLE`, `WAITING_ORDER_FILL` and phases `BUY`/`SELL`.
* Define transition rules:

  * if active order FILLED → flip phase → create next order at adjacent level
  * if no active order → place initial order based on current price and mode
  * if price outside range → “valid side only” logic
* Implement “only 1 order per tick” (no catch-up multiple orders).
* Unit tests with simulated price sequences for both modes.
  **DoD:**
* Given a scripted price series, bot emits the expected sequence of order intents (side/level index).

---

## Epic D — Exchange Adapter Layer (P0)

> MVP recommendation: implement **one** adapter first. If you later want both, add the second adapter behind the same interface.

### D1 — Define Exchange Interface

**Context:** Avoid coupling bot logic to a specific API.
**Tasks:**

* Interface methods:

  * `get_price(symbol)`
  * `get_symbol_rules(symbol)` (tick size, step size, min qty/notional)
  * `place_limit_order(symbol, side, price, qty)`
  * `get_order_status(order_id)`
  * `cancel_order(order_id)` (optional P1)
  * `get_balances()` (optional for “real mode”)
* Implement a `MockExchange` for unit/integration tests.
  **DoD:**
* Bot loop can run entirely against `MockExchange` in tests.

### D2 — Implement Spot Adapter for Binance (or choose Pionex)

**Context:** Real connectivity for non-dry-run.
**Tasks:**

* Implement signing/auth, REST calls, and error handling (retry only for clear transient failures).
* Implement symbol rules fetching + local caching.
* Implement order placement and status polling.
* Map exchange statuses to internal statuses (`NEW`, `OPEN`, `FILLED`, `CANCELED`, `REJECTED`).
* Add integration test in “dry-run + live price only” mode (no order placement) to validate connectivity.
  **DoD:**
* In live mode with order placement disabled, price and symbol rules are fetched reliably for 30 minutes.
* With order placement enabled, a small notional order can be placed and observed (manual runbook step documented).

---

## Epic E — Bot Runtime (Loop, Persistence, Logging) (P0)

### E1 — Implement Persistent State (JSON)

**Context:** Resume after restart without complex infra.
**Tasks:**

* Define `state.json` schema (versioned).
* Save state atomically (write temp + rename).
* On startup:

  * if state exists → load and validate schema version
  * if missing → initialize from config and current price
* Add unit tests for load/save and schema validation.
  **DoD:**
* Restarting the bot continues from previous state without duplicating an order intent.

### E2 — Implement Bot Loop (Periodic Checks)

**Context:** Stable runtime behavior for hours.
**Tasks:**

* Implement scheduler loop (sleep until next tick; handle drift).
* Each tick:

  * fetch price
  * if active order: poll status and transition if filled
  * else: compute next order intent and place (or simulate in dry-run)
* Handle exceptions: log and continue (unless configuration/validation error).
  **DoD:**
* A 2-hour dry-run completes with no crashes; logs show consistent state transitions.

### E3 — Structured Logging + Run Summary

**Context:** Debuggability for a single user.
**Tasks:**

* Log on each tick: price, phase/state, active order summary.
* Log on transitions: filled order, next order, PnL delta.
* End-of-run summary on SIGINT (Ctrl+C).
  **DoD:**
* Logs are sufficiently detailed to reconstruct decisions post-run.

---

## Epic F — Dry-Run & Backtesting-lite (P1)

### F1 — Deterministic Dry-Run Fill Simulation

**Context:** Validate logic without touching the exchange.
**Tasks:**

* Fill rules:

  * BUY fills if `current_price <= limit_price`
  * SELL fills if `current_price >= limit_price`
* Optional: simple slippage toggle (off by default).
* Store simulated fills in state for audit.
  **DoD:**
* Same price series produces identical results across runs.

### F2 — CSV Replay Runner (Optional)

**Context:** Quick sanity checks with historical candles/prices.
**Tasks:**

* Read CSV with timestamp, price.
* Run state machine against the series, output final balances and trade list.
  **DoD:**
* Produces a summary report (PnL, trade count, max drawdown approximation optional).

---

## Epic G — Documentation & Runbooks (P0)

### G1 — README + Quickstart

**Context:** Single-user usability.
**Tasks:**

* Explain modes (Long vs Short-inverted in spot).
* Explain configuration with examples (100 USDT example).
* Explain risk notes and non-goals.
* Provide dry-run instructions and “first live run” checklist.
  **DoD:**
* A new user can run dry-run within 10 minutes using the README.

### G2 — Troubleshooting Guide

**Context:** Reduce debugging time.
**Tasks:**

* Common API errors (precision, min notional, insufficient balance).
* Clock/time drift note and fix.
* Rate-limit handling note.
  **DoD:**
* At least 8 common issues documented with resolutions.

---

## Epic H — Quality Gates (Minimal) (P0)

### H1 — Unit Tests for Core Logic

**Context:** Prevent regressions in math/decisions.
**Tasks:**

* Tests for grid generation, sizing, state transitions.
* Add fixtures for typical configs (N=20, ±10% range).
  **DoD:**
* Core logic coverage is “reasonable” (target 60%+ for `src/core` and `src/bot/decision`).

### H2 — Basic CI (Optional but recommended)

**Context:** Best practice with minimal effort.
**Tasks:**

* Add GitHub Actions workflow (lint + tests) or local-only checklist if you prefer.
  **DoD:**
* On each push, lint + tests run automatically (or documented local alternative).

---