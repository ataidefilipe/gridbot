import pytest
from src.core.config import AppConfig, GridConfig
from src.exchange.mock import MockExchange
from src.exchange.base import SymbolRules
from src.bot.loop import GridBotOrchestrator

def test_orchestrator_initialization(tmp_path):
    state_file = str(tmp_path / "state.json")
    
    config = AppConfig(grid=GridConfig(
        symbol="BTCUSDT",
        mode="LONG",
        initial_capital_amount=100.0,
        range_pct_bottom=-0.10,
        range_pct_top=0.10,
        grid_intervals=4
    ), dry_run=True)
    
    exchange = MockExchange(current_price=100.0)
    exchange.add_symbol_rules("BTCUSDT", SymbolRules(0.01, 0.0001, 10.0, 0.0001))
    
    bot = GridBotOrchestrator(config, exchange, state_file=state_file)
    bot.initialize()
    
    # Check levels
    assert len(bot.levels) == 5
    assert bot.levels[0] == pytest.approx(90.0)
    assert bot.levels[-1] == pytest.approx(110.0)
    
    # State has been seeded
    assert bot.state is not None
    assert bot.state.p0_reference_price == 100.0
    assert bot.state.active_order is None

def test_orchestrator_execute_tick_dry_run(tmp_path):
    state_file = str(tmp_path / "state.json")
    
    config = AppConfig(grid=GridConfig(
        symbol="BTCUSDT",
        mode="LONG",
        initial_capital_amount=100.0,
        range_pct_bottom=-0.10,
        range_pct_top=0.10,
        grid_intervals=4
    ), dry_run=True)
    
    exchange = MockExchange(current_price=100.0)
    # Zero minimums to avoid skipping
    exchange.add_symbol_rules("BTCUSDT", SymbolRules(0.01, 0.00001, 0.0, 0.0))
    
    bot = GridBotOrchestrator(config, exchange, state_file=state_file)
    bot.initialize()
    
    # 1st Tick: Starts IDLE -> Evaluates price -> Should place BUY order
    bot.execute_tick()
    
    assert bot.state.active_order is not None
    assert "dry_run_" in bot.state.active_order.order_id
    assert bot.state.active_order.side == "BUY"
    assert bot.state.active_order.price == pytest.approx(99.50)
    assert bot.state.state.value == "WAITING_ORDER_FILL"

def test_orchestrator_execute_tick_live_mock(tmp_path):
    state_file = str(tmp_path / "state.json")
    
    config = AppConfig(grid=GridConfig(
        symbol="BTCUSDT",
        mode="LONG",
        initial_capital_amount=100.0,
        range_pct_bottom=-0.10,
        range_pct_top=0.10,
        grid_intervals=4
    ), dry_run=False) # Fake live
    
    exchange = MockExchange(current_price=100.0)
    exchange.add_symbol_rules("BTCUSDT", SymbolRules(0.01, 0.00001, 0.0, 0.0))
    
    bot = GridBotOrchestrator(config, exchange, state_file=state_file)
    bot.initialize()
    
    # 1. Tick one -> Places order
    bot.execute_tick()
    
    order_id = bot.state.active_order.order_id
    assert "mock_" in order_id
    
    # 2. Tick two -> Price drops to 90, Mock exchange should fill the BUY order
    exchange.set_price(90.0)
    bot.execute_tick()
    
    # After tick, the state should flip back to IDLE in phase SELL, last filled is 2.
    # It hasn't placed the next order yet, because state transition happens at the end of the tick check, next tick places it
    # BUT wait, the execute_tick places order only when self.state.active_order is None at the START
    # Look at loop.py:
    # `if not self.state.active_order:` comes directly after.
    # Actually, transition_state triggers `active_order = None`. So in the SAME TICK it will proceed to place!
    
    assert bot.state.active_order is not None
    new_order_id = bot.state.active_order.order_id
    assert new_order_id != order_id
    assert bot.state.active_order.side == "SELL"
    # Buy filled at index 2 (100.0). Sell should be index 3 (approx 104.88)
    assert bot.state.active_order.grid_index == 3
