from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict

class BotPhase(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class BotStateRole(str, Enum):
    IDLE = "IDLE"
    WAITING_ORDER_FILL = "WAITING_ORDER_FILL"

@dataclass
class OrderIntent:
    side: BotPhase
    price: float
    qty: float
    grid_index: int

@dataclass
class ActiveOrder:
    order_id: str
    side: BotPhase
    price: float
    qty: float
    grid_index: int
    status: str = "NEW"

@dataclass
class GridState:
    phase: BotPhase
    state: BotStateRole
    p0_reference_price: float = 0.0
    active_order: Optional[ActiveOrder] = None
    last_filled_index: Optional[int] = None
    realized_pnl: float = 0.0
    estimated_balances: Dict[str, float] = field(default_factory=dict)
