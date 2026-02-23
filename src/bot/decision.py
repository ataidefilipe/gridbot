import logging
from typing import List, Optional
from src.bot.state import GridState, BotPhase, BotStateRole, OrderIntent
from src.core.math import calculate_base_qty_for_long, calculate_base_qty_for_short_inverted

logger = logging.getLogger(__name__)

def determine_initial_grid_index(current_price: float, levels: List[float], phase: BotPhase) -> int:
    """Finds the best starting level index based on the initial price."""
    n = len(levels) - 1
    
    # Range check
    if current_price < levels[0]:
        return 0
    if current_price > levels[-1]:
        return n

    if phase == BotPhase.BUY:
        # Find max index i where levels[i] <= P
        for i in range(n, -1, -1):
            if levels[i] <= current_price:
                return i
        return 0
    else:
        # SELL phase: find min index i where levels[i] >= P
        for i in range(n + 1):
            if levels[i] >= current_price:
                return i
        return n

def get_next_order_intent(
    state: GridState, 
    current_price: float, 
    levels: List[float], 
    mode: str, 
    capital: float,
    tick_size: float = 0.0,
    step_size: float = 0.0
) -> Optional[OrderIntent]:
    """
    Pure function to determine the next order to be placed based on current state.
    Returns None if an order is already active, or if out-of-range constraints block it.
    """
    if state.state == BotStateRole.WAITING_ORDER_FILL or state.active_order is not None:
        return None

    n_intervals = len(levels) - 1

    # Determine next grid index
    if state.last_filled_index is None:
        target_index = determine_initial_grid_index(current_price, levels, state.phase)
    else:
        # Adjacent behavior
        if state.phase == BotPhase.BUY:
            # We just finished a SELL, or we are returning from out of range
            target_index = state.last_filled_index - 1
        else:
            # We just finished a BUY
            target_index = state.last_filled_index + 1

    # Clamp bounds and check out-of-range logic
    if target_index < 0:
        # Means we sold at level 0. Cannot drop further. Waiting for price to recover.
        logger.info("Price dropped out of grid bottom. Bot needs USDT to buy, or must wait.")
        return None
    elif target_index > n_intervals:
        # Means we bought at level N. Cannot exceed top.
        logger.info("Price exceeded grid top. Bot must wait for drop to buy, or sell if trailing.")
        return None

    order_price = levels[target_index]
    
    # Optional constraint: 
    # If P > P_top and mode is LONG (where phase would be BUY), should skip?
    # Actually, if we use target_index clamps, an out of range price just waits unless we hit the ceiling limit order.
    
    # Calculate order quantities
    if mode == "LONG":
        # Quote capital split
        raw_qty = calculate_base_qty_for_long(capital, n_intervals, order_price)
    elif mode == "SHORT_INVERTED":
        # Base capital split
        raw_qty = calculate_base_qty_for_short_inverted(capital, n_intervals)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # For now, we return un-rounded qty depending on where tick/step rounding goes.
    # Typically, the Exchange layer will apply round_tick_size and round_step_size.
    # We pass raw values here for intent.
    
    return OrderIntent(
        side=state.phase,
        price=order_price,
        qty=raw_qty,
        grid_index=target_index
    )

def transition_state_on_fill(state: GridState, filled_index: int, realized_pnl: float = 0.0) -> GridState:
    """Returns a newly mutated state after an order fills."""
    # Flip phase
    next_phase = BotPhase.SELL if state.phase == BotPhase.BUY else BotPhase.BUY
    
    state.active_order = None
    state.state = BotStateRole.IDLE
    state.last_filled_index = filled_index
    state.phase = next_phase
    state.realized_pnl += realized_pnl
    
    return state
