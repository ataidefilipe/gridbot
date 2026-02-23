import time
import hmac
import hashlib
import logging
from typing import Dict, Any
import requests

from src.exchange.base import ExchangeInterface, SymbolRules, ExchangeError

logger = logging.getLogger(__name__)

class BinanceSpotAdapter(ExchangeInterface):
    """
    Minimal adapter for Binance Spot API (V3).
    """
    
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        if testnet:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = "https://api.binance.com"
            
        self._rules_cache: Dict[str, SymbolRules] = {}
        
    def _get_timestamp(self) -> int:
        return int(time.time() * 1000)
        
    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, endpoint: str, params: Dict[str, Any] = None, signed: bool = False) -> Dict[str, Any]:
        params = params or {}
        
        if signed:
            if not self.api_key or not self.api_secret:
                raise ExchangeError("API keys required for signed requests.")
            params['timestamp'] = self._get_timestamp()
            # Sort params and build query string
            query_string = "&".join([f"{k}={params[k]}" for k in sorted(params.keys())])
            signature = self._sign(query_string)
            params['signature'] = signature
            
        headers = {}
        if self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key
            
        url = self.base_url + endpoint
        
        try:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                # For POST, Binance typically expects query params for data, OR application/x-www-form-urlencoded
                # The requests 'params' sends them as query limits which works for V3
                response = requests.post(url, params=params, headers=headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, params=params, headers=headers, timeout=10)
            else:
                raise ExchangeError(f"Unsupported method {method}")
                
            data = response.json()
            
            if response.status_code != 200:
                msg = data.get("msg", "Unknown error")
                code = data.get("code", response.status_code)
                logger.error(f"Binance API Error [{code}]: {msg}")
                raise ExchangeError(f"Binance API Error: {msg} (Code: {code})")
                
            return data
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise ExchangeError(f"Network error communicating with Binance: {e}")

    def get_price(self, symbol: str) -> float:
        res = self._request("GET", "/api/v3/ticker/price", params={"symbol": symbol})
        return float(res["price"])

    def get_symbol_rules(self, symbol: str) -> SymbolRules:
        if symbol in self._rules_cache:
            return self._rules_cache[symbol]
            
        res = self._request("GET", "/api/v3/exchangeInfo", params={"symbol": symbol})
        
        symbols = res.get("symbols", [])
        if not symbols:
            raise ExchangeError(f"Symbol {symbol} not found on Binance exchangeInfo.")
            
        symbol_data = symbols[0]
        filters = symbol_data.get("filters", [])
        
        tick_size = 0.0
        step_size = 0.0
        min_notional = 0.0
        min_qty = 0.0
        
        for f in filters:
            if f["filterType"] == "PRICE_FILTER":
                tick_size = float(f["tickSize"])
            elif f["filterType"] == "LOT_SIZE":
                step_size = float(f["stepSize"])
                min_qty = float(f["minQty"])
            elif f["filterType"] == "NOTIONAL":
                min_notional = float(f["minNotional"])
                
        rules = SymbolRules(
            tick_size=tick_size,
            step_size=step_size,
            min_notional=min_notional,
            min_qty=min_qty
        )
        self._rules_cache[symbol] = rules
        return rules

    def place_limit_order(self, symbol: str, side: str, price: float, qty: float) -> str:
        """Places a single limit order."""
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": f"{qty:.8f}", # Will be stripped to step_size later, simple pass here
            "price": f"{price:.8f}"
        }
        res = self._request("POST", "/api/v3/order", params=params, signed=True)
        return str(res["orderId"])

    def get_order_status(self, symbol: str, order_id: str) -> str:
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        res = self._request("GET", "/api/v3/order", params=params, signed=True)
        
        raw_status = res.get("status")
        # Binance statuses: NEW, PARTIALLY_FILLED, FILLED, CANCELED, PENDING_CANCEL, REJECTED, EXPIRED
        # Let's map to our internal ones:
        if raw_status in ("NEW", "PARTIALLY_FILLED"):
            return "OPEN"
        elif raw_status == "FILLED":
            return "FILLED"
        elif raw_status in ("CANCELED", "EXPIRED", "PENDING_CANCEL"):
            return "CANCELED"
        elif raw_status == "REJECTED":
            return "REJECTED"
        else:
            return "OPEN" # Unknown fallback

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        try:
            self._request("DELETE", "/api/v3/order", params=params, signed=True)
            return True
        except ExchangeError as e:
            logger.warning(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_balances(self) -> Dict[str, float]:
        res = self._request("GET", "/api/v3/account", signed=True)
        balances = {}
        for b in res.get("balances", []):
            free = float(b["free"])
            locked = float(b["locked"])
            if free > 0 or locked > 0:
                balances[b["asset"]] = free + locked
        return balances
