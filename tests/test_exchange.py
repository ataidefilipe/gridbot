from src.exchange.mock import MockExchange

def test_mock_exchange_price():
    ex = MockExchange(current_price=50000.0)
    assert ex.get_price("BTCUSDT") == 50000.0
    
    ex.set_price(51000.0)
    assert ex.get_price("BTCUSDT") == 51000.0

def test_mock_exchange_order_lifecycle():
    ex = MockExchange(current_price=100.0)
    
    # Place BUY order at 90.0
    order_id = ex.place_limit_order("BTCUSDT", "BUY", price=90.0, qty=1.0)
    assert ex.get_order_status("BTCUSDT", order_id) == "OPEN"
    
    # Price drops to 95.0. Order shouldn't fill.
    ex.set_price(95.0)
    assert ex.get_order_status("BTCUSDT", order_id) == "OPEN"
    
    # Price drops to 90.0. Order should fill.
    ex.set_price(90.0)
    assert ex.get_order_status("BTCUSDT", order_id) == "FILLED"
    
def test_mock_exchange_sell_order_lifecycle():
    ex = MockExchange(current_price=100.0)
    
    # Place SELL order at 110.0
    order_id = ex.place_limit_order("BTCUSDT", "SELL", price=110.0, qty=1.0)
    assert ex.get_order_status("BTCUSDT", order_id) == "OPEN"
    
    # Price goes up to 105.0. Order shouldn't fill.
    ex.set_price(105.0)
    assert ex.get_order_status("BTCUSDT", order_id) == "OPEN"
    
    # Price goes up to 110.0. Order should fill.
    ex.set_price(110.0)
    assert ex.get_order_status("BTCUSDT", order_id) == "FILLED"

def test_mock_exchange_balances():
    ex = MockExchange(current_price=100.0)
    # default mock is 1 BTC and 1000 USDT
    balances_start = ex.get_balances()
    assert balances_start["USDT"] == 1000.0
    
    # Buy 1 BTC at 90
    order_id = ex.place_limit_order("BTCUSDT", "BUY", price=90.0, qty=1.0)
    ex.set_price(90.0)
    ex.get_order_status("BTCUSDT", order_id)  # Trigger fill evaluation
    
    balances_end = ex.get_balances()
    assert balances_end["USDT"] == 910.0
    assert balances_end["BTC"] == 2.0
