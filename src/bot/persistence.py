import os
import json
import logging
from dataclasses import asdict
from typing import Optional
from src.bot.state import GridState, BotPhase, BotStateRole, ActiveOrder

logger = logging.getLogger(__name__)

def save_state(state: GridState, filepath: str):
    """
    Saves the GridState to a JSON file atomically.
    Writes to a .tmp file first, then renames to avoid corruption on crash.
    """
    tmp_path = f"{filepath}.tmp"
    
    # Custom encoder for enums or just convert to dict
    state_dict = asdict(state)
    
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=4)
        
        # Atomic replace
        os.replace(tmp_path, filepath)
    except Exception as e:
        logger.error(f"Failed to save state to {filepath}: {e}")
        raise

def load_state(filepath: str) -> Optional[GridState]:
    """
    Loads GridState from a JSON file.
    Returns None if file does not exist.
    """
    if not os.path.exists(filepath):
        return None
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Reconstruct ActiveOrder if present
        active_order = None
        if data.get("active_order"):
            ao_data = data["active_order"]
            active_order = ActiveOrder(
                order_id=ao_data["order_id"],
                side=BotPhase(ao_data["side"]),
                price=float(ao_data["price"]),
                qty=float(ao_data["qty"]),
                grid_index=int(ao_data["grid_index"]),
                status=ao_data.get("status", "NEW")
            )
            
        state = GridState(
            phase=BotPhase(data["phase"]),
            state=BotStateRole(data["state"]),
            p0_reference_price=float(data.get("p0_reference_price", 0.0)),
            active_order=active_order,
            last_filled_index=data.get("last_filled_index"),
            realized_pnl=float(data.get("realized_pnl", 0.0)),
            estimated_balances=data.get("estimated_balances", {})
        )
        return state
        
    except Exception as e:
        logger.error(f"Failed to load state from {filepath}: {e}")
        raise
