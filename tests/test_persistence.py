import os
from src.bot.state import GridState, BotPhase, BotStateRole, ActiveOrder
from src.bot.persistence import save_state, load_state

def test_save_and_load_state_empty(tmp_path):
    filepath = tmp_path / "state.json"
    
    # Base minimal state
    state = GridState(phase=BotPhase.BUY, state=BotStateRole.IDLE, p0_reference_price=50000.0)
    
    save_state(state, str(filepath))
    assert os.path.exists(filepath)
    
    loaded = load_state(str(filepath))
    assert loaded is not None
    assert loaded.phase == BotPhase.BUY
    assert loaded.state == BotStateRole.IDLE
    assert loaded.active_order is None

def test_save_and_load_state_full(tmp_path):
    filepath = tmp_path / "state.json"
    
    order = ActiveOrder(
        order_id="12345",
        side=BotPhase.SELL,
        price=50000.0,
        qty=1.5,
        grid_index=4,
        status="OPEN"
    )
    
    state = GridState(
        phase=BotPhase.SELL,
        state=BotStateRole.WAITING_ORDER_FILL,
        active_order=order,
        last_filled_index=3,
        realized_pnl=15.5,
        estimated_balances={"BTC": 0.5, "USDT": 1000.0}
    )
    
    save_state(state, str(filepath))
    
    loaded = load_state(str(filepath))
    assert loaded is not None
    assert loaded.phase == BotPhase.SELL
    assert loaded.state == BotStateRole.WAITING_ORDER_FILL
    assert loaded.last_filled_index == 3
    assert loaded.realized_pnl == 15.5
    assert loaded.estimated_balances["BTC"] == 0.5
    
    assert loaded.active_order is not None
    assert loaded.active_order.order_id == "12345"
    assert loaded.active_order.side == BotPhase.SELL
    assert loaded.active_order.grid_index == 4

def test_load_nonexistent_state():
    loaded = load_state("does_not_exist.json")
    assert loaded is None
