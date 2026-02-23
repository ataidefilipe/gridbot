import pytest
from unittest.mock import patch, MagicMock
from src.exchange.binance import BinanceSpotAdapter
from src.exchange.base import ExchangeError

@patch("src.exchange.binance.requests.get")
def test_binance_get_price(mock_get):
    adapter = BinanceSpotAdapter()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"symbol": "BTCUSDT", "price": "50000.10"}
    mock_get.return_value = mock_response
    
    price = adapter.get_price("BTCUSDT")
    assert price == 50000.10
    
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "ticker/price" in args[0]
    assert kwargs["params"]["symbol"] == "BTCUSDT"

@patch("src.exchange.binance.requests.get")
def test_binance_get_symbol_rules(mock_get):
    adapter = BinanceSpotAdapter()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "symbols": [{
            "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                {"filterType": "LOT_SIZE", "stepSize": "0.00001", "minQty": "0.00001"},
                {"filterType": "NOTIONAL", "minNotional": "10.0"}
            ]
        }]
    }
    mock_get.return_value = mock_response
    
    rules = adapter.get_symbol_rules("BTCUSDT")
    assert rules.tick_size == 0.01
    assert rules.step_size == 0.00001
    assert rules.min_notional == 10.0
    
    # Should cache it, calling again shouldn't hit network
    adapter.get_symbol_rules("BTCUSDT")
    assert mock_get.call_count == 1

@patch("src.exchange.binance.requests.post")
def test_binance_place_limit_order(mock_post):
    adapter = BinanceSpotAdapter(api_key="key", api_secret="secret")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"orderId": 12345}
    mock_post.return_value = mock_response
    
    order_id = adapter.place_limit_order("BTCUSDT", "BUY", price=45000.0, qty=1.0)
    assert order_id == "12345"
    
    args, kwargs = mock_post.call_args
    params = kwargs["params"]
    assert params["symbol"] == "BTCUSDT"
    assert params["side"] == "BUY"
    assert "signature" in params
    assert "timestamp" in params

@patch("src.exchange.binance.requests.get")
def test_binance_get_order_status(mock_get):
    adapter = BinanceSpotAdapter(api_key="key", api_secret="secret")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "FILLED"}
    mock_get.return_value = mock_response
    
    status = adapter.get_order_status("BTCUSDT", "123")
    assert status == "FILLED"

def test_binance_unsigned_post_raises():
    adapter = BinanceSpotAdapter()
    # No keys provided
    with pytest.raises(ExchangeError, match="API keys required"):
        adapter.place_limit_order("BTC", "BUY", 10, 1)
