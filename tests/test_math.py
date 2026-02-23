import pytest
from src.core.math import (
    build_grid, 
    calculate_notional_per_grid,
    calculate_base_qty_for_long,
    calculate_base_qty_for_short_inverted,
    round_step_size,
    round_tick_size,
    MathError
)

def test_build_grid_standard():
    p0 = 100.0
    bottom_pct = -0.10
    top_pct = 0.10
    n = 2
    
    # Bottom = 90
    # Top = 110
    # ratio = (110 / 90) ^ (1/2) = 1.10554159...
    # levels: 90, 99.4987..., 110
    levels = build_grid(p0, bottom_pct, top_pct, n)
    assert len(levels) == 3
    assert levels[0] == pytest.approx(90.0)
    assert levels[-1] == pytest.approx(110.0)
    assert levels[0] < levels[1] < levels[2]
    
    # Check geometric ratio manually
    ratio1 = levels[1] / levels[0]
    ratio2 = levels[2] / levels[1]
    assert pytest.approx(ratio1) == ratio2

def test_build_grid_validation():
    with pytest.raises(MathError, match="must be at least 1"):
        build_grid(100.0, -0.1, 0.1, 0)
        
    with pytest.raises(MathError, match="P0 must be > 0"):
        build_grid(0, -0.1, 0.1, 10)
        
    with pytest.raises(MathError, match="must be less than top"):
        build_grid(100.0, 0.1, -0.1, 10)
        
    with pytest.raises(MathError, match="Resulting bottom price must be > 0"):
        build_grid(100.0, -1.1, 0.1, 10) # bottom = -10.0

def test_sizing_long():
    capital = 1000.0
    n = 10
    notional = calculate_notional_per_grid(capital, n)
    assert notional == 100.0
    
    qty = calculate_base_qty_for_long(capital, n, order_price=50000.0)
    assert qty == (100.0 / 50000.0)

def test_sizing_short_inverted():
    btc_capital = 1.0
    n = 10
    # For short inverted, qty is just capital / N
    qty = calculate_base_qty_for_short_inverted(btc_capital, n)
    assert qty == 0.1

def test_rounding_step_size():
    assert round_step_size(1.23456, 0.01) == 1.23
    assert round_step_size(1.23999, 0.01) == 1.23
    assert round_step_size(1.23456, 0.001) == 1.234
    assert round_step_size(0.5, 1.0) == 0.0
    assert round_step_size(1.5, 1.0) == 1.0
    assert round_step_size(1.23456, 0.0) == 1.23456

def test_rounding_tick_size():
    assert round_tick_size(100.123, 0.01) == 100.12
    assert round_tick_size(100.126, 0.01) == 100.13
    assert round_tick_size(100.999, 0.1) == 101.0
    assert round_tick_size(100.0, 0.0) == 100.0
