import pytest
from src.bot.state import GridState, BotPhase, BotStateRole
from src.bot.decision import get_next_order_intent, transition_state_on_fill
from src.core.math import build_grid

def test_initial_long_order_intent():
    # Long mode: start in BUY
    state = GridState(phase=BotPhase.BUY, state=BotStateRole.IDLE)
    levels = build_grid(100.0, -0.10, 0.10, 4)  # 5 levels: [90.0, 94.86, 100.0, 105.4, 110.0]  (approx)
    
    intent = get_next_order_intent(state, current_price=101.0, levels=levels, mode="LONG", capital=100.0)
    
    assert intent is not None
    assert intent.side == BotPhase.BUY
    assert intent.grid_index == 2
    assert intent.price == pytest.approx(99.498, abs=0.01)

def test_state_transition_and_adjacent_intent():
    # Assume we placed BUY at level 2 (99.498) and it filled.
    state = GridState(phase=BotPhase.BUY, state=BotStateRole.WAITING_ORDER_FILL, last_filled_index=None)
    levels = build_grid(100.0, -0.10, 0.10, 4)
    
    # 1. Fill it -> phase becomes SELL, idx = 2
    state = transition_state_on_fill(state, filled_index=2, realized_pnl=0.0)
    assert state.phase == BotPhase.SELL
    assert state.last_filled_index == 2
    assert state.state == BotStateRole.IDLE
    
    # 2. Next intent -> Should be SELL at index 3
    intent = get_next_order_intent(state, current_price=101.0, levels=levels, mode="LONG", capital=100.0)
    
    assert intent is not None
    assert intent.side == BotPhase.SELL
    assert intent.grid_index == 3
    assert intent.price == pytest.approx(104.617, abs=0.01)

def test_out_of_bounds_blocks_intent():
    # Top of grid is level 4 (110.0). We just bought at level 4 -> sell at 5 (out of bounds).
    state = GridState(phase=BotPhase.BUY, state=BotStateRole.IDLE, last_filled_index=None)
    # Mock filled at N (level 4)
    state = transition_state_on_fill(state, filled_index=4)
    
    # We are SELL phase, last filled 4. Next intent is 5.
    levels = build_grid(100.0, -0.10, 0.10, 4)
    intent = get_next_order_intent(state, current_price=100.0, levels=levels, mode="LONG", capital=100.0)
    
    assert intent is None
    
    # Bottom of grid (level 0). We sold at level 0 -> buy at -1 (out of bounds).
    state2 = GridState(phase=BotPhase.SELL, state=BotStateRole.IDLE, last_filled_index=None)
    state2 = transition_state_on_fill(state2, filled_index=0)
    
    intent2 = get_next_order_intent(state2, current_price=100.0, levels=levels, mode="LONG", capital=100.0)
    assert intent2 is None
