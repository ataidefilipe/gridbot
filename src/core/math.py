import math
from typing import List

class MathError(Exception):
    """Exception for core math and sizing errors."""
    pass

def build_grid(p0: float, range_pct_bottom: float, range_pct_top: float, num_intervals: int) -> List[float]:
    """
    Builds a geometric grid of N intervals (N+1 price levels).
    """
    if num_intervals < 1:
        raise MathError("Number of intervals must be at least 1.")
    
    if p0 <= 0:
        raise MathError("Reference price P0 must be > 0.")
        
    if range_pct_bottom >= range_pct_top:
        raise MathError(f"Bottom range ({range_pct_bottom}) must be less than top range ({range_pct_top}).")
        
    p_bottom = p0 * (1 + range_pct_bottom)
    p_top = p0 * (1 + range_pct_top)
    
    if p_bottom <= 0:
        raise MathError("Resulting bottom price must be > 0.")
        
    ratio = (p_top / p_bottom) ** (1.0 / num_intervals)
    
    levels = []
    for i in range(num_intervals + 1):
        level_price = p_bottom * (ratio ** i)
        levels.append(level_price)
        
    # Ensure exact bounds (prevent tiny floating point precision overflow at the top)
    levels[0] = p_bottom
    levels[-1] = p_top
    
    return levels

def calculate_notional_per_grid(initial_capital: float, num_intervals: int) -> float:
    """Calculates exactly how much capital to allocate per grid interval."""
    if initial_capital <= 0:
        raise MathError("Capital must be > 0.")
    if num_intervals < 1:
        raise MathError("Intervals must be > 0.")
    return initial_capital / num_intervals

def calculate_base_qty_for_long(quote_capital: float, num_intervals: int, order_price: float) -> float:
    """LONG: buys using USDT to get BTC. Qty = (USDT_allocated) / price."""
    notional = calculate_notional_per_grid(quote_capital, num_intervals)
    if order_price <= 0:
        raise MathError("Order price must be > 0.")
    return notional / order_price
    
def calculate_base_qty_for_short_inverted(base_capital: float, num_intervals: int) -> float:
    """SHORT_INVERTED (Spot): uses BTC capital to sell. Qty = BTC_allocated."""
    return calculate_notional_per_grid(base_capital, num_intervals)

def round_step_size(quantity: float, step_size: float) -> float:
    """
    Rounds down a quantity to the nearest multiple of step_size.
    E.g., round_step_size(1.2345, 0.01) -> 1.23
    """
    if step_size <= 0:
        return quantity
    # Use decimal or math.floor handling avoids precision issues
    precision = max(0, -int(math.floor(math.log10(step_size))))
    # Math floor division
    rounded = math.floor(quantity / step_size) * step_size
    return round(rounded, precision)

def round_tick_size(price: float, tick_size: float) -> float:
    """
    Rounds price to the nearest multiple of tick_size.
    Exchange typically requires limit orders to align with tick size.
    """
    if tick_size <= 0:
        return price
    precision = max(0, -int(math.floor(math.log10(tick_size))))
    rounded = round(price / tick_size) * tick_size
    return round(rounded, precision)
