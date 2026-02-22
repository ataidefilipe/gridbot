# Agent Roles and Workflow Document (Grid Bot MVP)

## Purpose

Define the **agent roster**, **responsibilities**, and **end-to-end workflow** for building a **single-user Python Spot grid bot MVP** (starting with BTC/USDT, evolving later), using agentic development while keeping the solution **clean, simple, and non-overengineered** (no security hardening focus).

---

## Guiding principles (non-negotiables)

1. **MVP first:** deliver a working dry-run loop + persistent state + core decision engine before any “nice-to-haves”.
2. **No overengineering:** one exchange adapter initially; one active order at a time; JSON state file; minimal abstractions.
3. **Clean code > clever code:** explicit state machine, deterministic pure functions for grid math and sizing, straightforward logging.
4. **Single source of truth:** written spec/backlog governs behavior; code implements the spec; tests validate it.
5. **Human-in-the-loop approvals:** a human approves scope changes, exchange choice, and any live-trading enablement.
6. **No security focus (MVP):** API keys via env vars; basic hygiene only; no secrets committed.

---

## Deliverables (shared artifacts)

All agents collaborate through a small set of versioned documents:

* **Functional Spec (FS):** exact behavior, inputs, state transitions, out-of-range behavior, simplified PnL assumptions.
* **Backlog:** epics/stories/tasks + DoD.
* **Architecture Notes:** minimal module boundaries and data model (state schema).
* **ADR (Decision Records):** e.g., choose Binance vs Pionex, choose geometric grid, one-order-per-tick.
* **Runbook:** how to run dry-run, how to enable live trading, troubleshooting.
* **Test Plan:** unit tests + deterministic dry-run scenarios.

---

## Agent roster (roles, responsabilities, outputs)

### 1) Orchestrator Agent (Coordinator)

**Goal:** keep the project aligned with MVP constraints and manage handoffs.
**Responsibilities:**

* Break work into tasks; route tasks to the right agents.
* Maintain the “single source of truth” documents.
* Enforce scope discipline and resolve conflicts between agent proposals.
  **Outputs:**
* Updated backlog, weekly/daily plan, consolidated decisions, integration checklist.

### 2) Product/Spec Agent (MVP Product Owner)

**Goal:** define the correct behavior in plain English.
**Responsibilities:**

* Write/maintain Functional Spec and acceptance criteria.
* Clarify ambiguous behavior (e.g., short-inverted semantics in spot).
* Ensure spec matches user constraints: 1 order per tick, periodic checks, fixed range, geometric grid.
  **Outputs:**
* Functional Spec, acceptance tests (Given/When/Then), non-goals, future roadmap section.

### 3) Quant/Strategy Agent (Trading Logic Specialist)

**Goal:** ensure the grid logic is coherent, consistent, and implementable.
**Responsibilities:**

* Specify geometric grid calculation, level selection rules, out-of-range rules.
* Specify order sizing logic (capital split) and rounding strategy requirements.
* Provide simplified fee/PnL model and sanity checks (grid step vs fees).
  **Outputs:**
* Strategy appendix: formulas, examples, invariants, “edge-case table”.

### 4) Software Lead Agent (Senior Engineer / Code Quality)

**Goal:** keep implementation minimal, testable, and readable.
**Responsibilities:**

* Define module boundaries (core math, bot loop, exchange adapter, state persistence).
* Define state machine model (states, transitions, event handling).
* Review PRs for simplicity, naming, error handling, and avoiding abstraction creep.
  **Outputs:**
* Minimal architecture notes, coding standards, review checklists, refactor guidance.

### 5) Exchange Integration Agent (API Adapter Specialist)

**Goal:** implement one clean adapter behind a tiny interface.
**Responsibilities:**

* Implement exchange interface: get price, symbol rules, place limit order, poll status.
* Handle rounding/min-notional constraints using symbol rules.
* Keep error handling pragmatic (clear logs, minimal retries).
  **Outputs:**
* `ExchangeAdapter` implementation + docs on required permissions/keys + connectivity check steps.

### 6) Persistence & Runtime Agent (State + Loop)

**Goal:** reliable long-running loop with state resume.
**Responsibilities:**

* Define `state.json` schema (versioned).
* Implement atomic save/load, startup resume logic, and tick scheduling.
* Ensure idempotency (no duplicate order creation after restart).
  **Outputs:**
* State schema, persistence module, runtime loop module, crash/restart behavior notes.

### 7) QA/Test Agent (Deterministic Verification)

**Goal:** validate core logic without needing live trading.
**Responsibilities:**

* Build MockExchange and deterministic dry-run price feeds.
* Unit tests for grid math, sizing, and state transitions.
* Scenario tests: trending up, trending down, range breakout, restart mid-order.
  **Outputs:**
* Test suite + test plan + minimal CI checklist (or local scripts).

### 8) Documentation/Runbook Agent

**Goal:** make the MVP runnable and understandable for one user.
**Responsibilities:**

* Maintain README + quickstart + troubleshooting.
* Document config examples (100 USDT, +/- % ranges, N grids, X minutes).
* Document safe “enable live” steps (without security hardening).
  **Outputs:**
* README, runbook, troubleshooting guide, example configs.

---

## Tooling assumptions (lightweight)

* Version control in Git (single repo).
* One issue tracker (GitHub Issues or a simple Markdown backlog).
* One communication channel (single shared doc or repo wiki).
* Optional: minimal CI for lint/test (not required, but recommended).

---

## Working agreements (best practices for agentic development)

1. **Every change must trace to a story** (or a spec line). No “drive-by” improvements.
2. **Small diffs:** agents produce incremental PRs aligned to a backlog item.
3. **No speculative abstractions:** adapters and interfaces only when required by current scope.
4. **Deterministic core:** grid math + decision logic are pure functions with tests.
5. **Runtime is explicit:** state transitions logged; state saved after meaningful events.
6. **Disagreement resolution:** Orchestrator defers to Functional Spec; unresolved ambiguity goes to the human decision.

---

## End-to-end workflow (phases and handoffs)

### Phase 0 — Project initialization (1–2 short iterations)

**Owner:** Orchestrator + Software Lead
**Steps:**

1. Create skeleton repo + lint/test tooling.
2. Create initial docs: Functional Spec (draft), Backlog, ADR template.
3. Choose the first exchange adapter target (one only).
   **Exit criteria:**

* Repo runs a placeholder CLI; docs exist; backlog ready.

### Phase 1 — Define behavior precisely (spec-first)

**Owner:** Product/Spec + Quant/Strategy
**Steps:**

1. Freeze MVP scope and non-goals.
2. Define formulas and state machine transitions in writing.
3. Add acceptance criteria and 2 worked examples (Long and Short-inverted).
   **Exit criteria:**

* Functional Spec approved by Orchestrator/human; backlog stories unblocked.

### Phase 2 — Implement core engine against MockExchange (no real API)

**Owner:** Software Lead + QA/Test + Persistence/Runtime
**Steps:**

1. Implement grid generator + sizing (pure).
2. Implement state machine (one active order).
3. Implement state persistence (JSON) and periodic loop.
4. Add deterministic tests and dry-run simulation.
   **Exit criteria:**

* Dry-run runs 2 hours without crash; tests pass; logs readable.

### Phase 3 — Integrate real exchange adapter (still cautious)

**Owner:** Exchange Integration + Software Lead
**Steps:**

1. Implement adapter behind small interface.
2. Connectivity-only run: fetch price + symbol rules.
3. Enable order placement behind a feature flag (`--live`), default off.
   **Exit criteria:**

* Adapter stable; a tiny order can be placed manually when enabled; runbook updated.

### Phase 4 — Stabilize and document

**Owner:** Documentation + QA/Test
**Steps:**

1. Add troubleshooting for common precision/min-notional failures.
2. Add restart scenario test; verify no duplicate orders after restart.
3. Finalize README + config templates.
   **Exit criteria:**

* MVP release tag with known limitations and next steps.

---

## Quality gates (MVP-appropriate)

* **Gate 1 (Spec):** acceptance criteria defined for each story.
* **Gate 2 (Core logic):** unit tests exist for grid + sizing + transitions.
* **Gate 3 (Runtime):** dry-run long run without exceptions; state file consistent.
* **Gate 4 (Integration):** real adapter can fetch symbol rules; live trading is opt-in.

---

## Minimal prompts / instructions per agent (operational)

Use these as the “role headers” when running agents:

* **Orchestrator:** “Keep MVP scope; route tasks; consolidate docs; reject overengineering.”
* **Product/Spec:** “Convert requirements into exact behaviors + acceptance criteria; no code.”
* **Quant/Strategy:** “Define formulas, invariants, edge cases; keep it implementable; no complex quant features.”
* **Software Lead:** “Design minimal modules; prioritize clarity; prevent premature abstractions.”
* **Exchange Integration:** “Implement only required endpoints; handle rounding/min rules; minimal retries; clear logs.”
* **Persistence/Runtime:** “Atomic state saves; deterministic loop behavior; idempotent restarts.”
* **QA/Test:** “Deterministic tests; mock exchange; scenario coverage; stop when scope creep appears.”
* **Documentation:** “Make it runnable in 10 minutes; document limitations and next steps.”

---
