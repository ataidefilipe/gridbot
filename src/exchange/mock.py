import logging
from typing import Dict
from src.exchange.base import ExchangeInterface, SymbolRules, ExchangeError

logger = logging.getLogger(__name__)

class MockExchange(ExchangeInterface):
    """
    A purely deterministic Mock Exchange for unit tests and deterministic dry-runs.
    """
    def __init__(self, current_price: float = 100.0):
        self._current_price = current_price
        self._rules: Dict[str, SymbolRules] = {}
        # Stores orders by id: dict of {id: {symbol, side, price, qty, status}}
        self._orders: Dict[str, dict] = {}
        self._order_counter = 0
        self._balances: Dict[str, float] = {"BTC": 1.0, "USDT": 1000.0}

    def set_price(self, price: float):
        """Helper to advance simulated price."""
        self._current_price = price

    def add_symbol_rules(self, symbol: str, rules: SymbolRules):
        """Helper to inject rules for testing rounding."""
        self._rules[symbol] = rules

    def get_price(self, symbol: str) -> float:
        return self._current_price
        
    def get_symbol_rules(self, symbol: str) -> SymbolRules:
        if symbol not in self._rules:
            # Default zero-constraint rules
            return SymbolRules(tick_size=0.0, step_size=0.0, min_notional=0.0, min_qty=0.0)
        return self._rules[symbol]
        
    def place_limit_order(self, symbol: str, side: str, price: float, qty: float) -> str:
        self._order_counter += 1
        order_id = f"mock_{self._order_counter}"
        self._orders[order_id] = {
            "symbol": symbol,
            "side": side,
            "price": price,
            "qty": qty,
            "status": "OPEN"
        }
        logger.debug(f"MockExchange placed limit order {order_id}: {side} {qty} at {price}")
        return order_id
        
    def get_order_status(self, symbol: str, order_id: str) -> str:
        if order_id not in self._orders:
            raise ExchangeError(f"Order {order_id} not found.")
        
        order = self._orders[order_id]
        
        # Simulate fills deterministically based on price
        if order["status"] == "OPEN":
            if order["side"] == "BUY" and self._current_price <= order["price"]:
                order["status"] = "FILLED"
                # Update mock balances
                notional = order["price"] * order["qty"]
                self._balances["USDT"] -= notional
                self._balances["BTC"] += order["qty"]
            elif order["side"] == "SELL" and self._current_price >= order["price"]:
                order["status"] = "FILLED"
                notional = order["price"] * order["qty"]
                self._balances["BTC"] -= order["qty"]
                self._balances["USDT"] += notional
                
        return order["status"]
        
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        if order_id in self._orders and self._orders[order_id]["status"] == "OPEN":
            self._orders[order_id]["status"] = "CANCELED"
            return True
        return False

    def get_balances(self) -> Dict[str, float]:
        return self._balances
