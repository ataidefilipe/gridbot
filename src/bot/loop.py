import time
import logging
from typing import Optional

from src.core.config import AppConfig
from src.exchange.base import ExchangeInterface, SymbolRules
from src.bot.state import GridState, BotPhase, BotStateRole, ActiveOrder
from src.core.math import build_grid, round_tick_size, round_step_size
from src.bot.persistence import save_state, load_state
from src.bot.decision import get_next_order_intent, transition_state_on_fill

logger = logging.getLogger(__name__)

class GridBotOrchestrator:
    def __init__(self, config: AppConfig, exchange: ExchangeInterface, state_file: str = "state.json"):
        self.config = config
        self.exchange = exchange
        self.state_file = state_file
        
        self.symbol = config.grid.symbol
        self.mode = config.grid.mode
        
        self.state: Optional[GridState] = None
        self.levels: list[float] = []
        self.rules: Optional[SymbolRules] = None
        
        self.running = False

    def initialize(self):
        """Loads state or initializes a new one based on current market."""
        logger.info(f"Initializing GridBot for {self.symbol} in {self.mode} mode")
        
        try:
            # Fetch rules needed for everything
            self.rules = self.exchange.get_symbol_rules(self.symbol)
            logger.info(f"Rules: tick={self.rules.tick_size}, step={self.rules.step_size}")
            
            # Load persistence
            loaded_state = load_state(self.state_file)
            if loaded_state:
                logger.info(f"Resuming existing state from {self.state_file}")
                self.state = loaded_state
            else:
                logger.info("Creating new state. Fetching market price...")
                p0 = self.exchange.get_price(self.symbol)
                logger.info(f"Current price P0: {p0}")
                
                initial_phase = BotPhase.BUY if self.mode == "LONG" else BotPhase.SELL
                self.state = GridState(
                    phase=initial_phase, 
                    state=BotStateRole.IDLE,
                    p0_reference_price=p0
                )
                
            # Build grid mathematically based on P0
            if self.state.p0_reference_price <= 0:
                raise ValueError("GridState loaded without a valid p0_reference_price.")
                
            self.levels = build_grid(
                self.state.p0_reference_price, 
                self.config.grid.range_pct_bottom, 
                self.config.grid.range_pct_top, 
                self.config.grid.grid_intervals
            )
            logger.info(f"Built grid with {len(self.levels)} levels. Bottom: {self.levels[0]}, Top: {self.levels[-1]}")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    def execute_tick(self):
        """Single tick iteration: fetch price, poll orders, make decisions."""
        current_price = self.exchange.get_price(self.symbol)
        logger.debug(f"[TICK] {self.symbol} price: {current_price}")
        
        # 1. State: check existing order status
        if self.state.active_order:
            status = self.exchange.get_order_status(self.symbol, self.state.active_order.order_id)
            logger.debug(f"Active order {self.state.active_order.order_id} status: {status}")
            
            if status == "FILLED":
                logger.info(f"Order FIlled! {self.state.active_order.side} at {self.state.active_order.price}")
                # We do simple PnL locally in memory
                # But wait, transition state handles phase flips.
                self.state = transition_state_on_fill(self.state, self.state.active_order.grid_index)
                save_state(self.state, self.state_file)
            elif status in ("CANCELED", "REJECTED"):
                logger.warning("Order Canceled/Rejected. Reverting to IDLE.")
                self.state.active_order = None
                self.state.state = BotStateRole.IDLE
                save_state(self.state, self.state_file)
            else:
                # Still OPEN
                return
                
        # 2. State: place new order if IDLE
        if not self.state.active_order:
            intent = get_next_order_intent(
                state=self.state,
                current_price=current_price,
                levels=self.levels,
                mode=self.mode,
                capital=self.config.grid.initial_capital_amount
            )
            
            if intent:
                # Round to exchange tick sizes
                p = round_tick_size(intent.price, self.rules.tick_size)
                q = round_step_size(intent.qty, self.rules.step_size)
                
                notional = p * q
                if notional < self.rules.min_notional or q < self.rules.min_qty:
                    logger.warning(f"Calculated intent below minimums. p={p}, q={q}, not={notional}. Skipping.")
                    return
                    
                # We are safe to place.
                logger.info(f"Placing new {intent.side} order at {p} (qty: {q})")
                
                if self.config.dry_run:
                    # Fake order id
                    oid = f"dry_run_{int(time.time()*1000)}"
                    logger.info("[DRY RUN] Order logic passed perfectly. Skipped exchange submission.")
                else:
                    oid = self.exchange.place_limit_order(self.symbol, intent.side.value, p, q)
                
                # Update local DB state
                self.state.active_order = ActiveOrder(
                    order_id=oid,
                    side=intent.side,
                    price=p,
                    qty=q,
                    grid_index=intent.grid_index,
                    status="OPEN"
                )
                self.state.state = BotStateRole.WAITING_ORDER_FILL
                save_state(self.state, self.state_file)
            else:
                logger.debug("No viable target intent evaluated. Waiting for price movement or range recovery.")

    def run_loop(self):
        """Infinite loop wrapper for production use."""
        self.running = True
        logger.info(f"Starting GridBot loop every {self.config.grid.check_interval_minutes} minutes.")
        interval_seconds = self.config.grid.check_interval_minutes * 60
        
        while self.running:
            try:
                self.execute_tick()
            except Exception as e:
                logger.error(f"Error during tick: {e}", exc_info=True)
                
            time.sleep(interval_seconds)
