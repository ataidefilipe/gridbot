from abc import ABC, abstractmethod
from typing import Dict
from dataclasses import dataclass

@dataclass
class SymbolRules:
    tick_size: float
    step_size: float
    min_notional: float
    min_qty: float

class ExchangeError(Exception):
    """Base exception for all exchange-related errors."""
    pass

class ExchangeInterface(ABC):
    """
    Minimal interface for the Spot Grid Bot MVP.
    """
    
    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """Fetch the current market price for the symbol."""
        pass
        
    @abstractmethod
    def get_symbol_rules(self, symbol: str) -> SymbolRules:
        """Fetch trading rules like tick size, step size, and minimums."""
        pass
        
    @abstractmethod
    def place_limit_order(self, symbol: str, side: str, price: float, qty: float) -> str:
        """
        Place a limit order.
        side is typically 'BUY' or 'SELL'.
        Returns the exchange order_id as a string.
        """
        pass
        
    @abstractmethod
    def get_order_status(self, symbol: str, order_id: str) -> str:
        """
        Fetch order status.
        Should normalize to: 'NEW', 'OPEN', 'FILLED', 'CANCELED', 'REJECTED'.
        """
        pass
        
    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Optional: cancel a specific order."""
        pass

    @abstractmethod
    def get_balances(self) -> Dict[str, float]:
        """Optional: fetch asset balances for real mode."""
        pass
