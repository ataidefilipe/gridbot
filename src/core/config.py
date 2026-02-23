import os
import yaml
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

class ConfigError(Exception):
    pass

@dataclass
class GridConfig:
    symbol: str = "BTCUSDT"
    mode: str = "LONG"
    initial_capital_amount: float = 100.0
    initial_capital_asset: str = "USDT"
    range_pct_bottom: float = -0.10
    range_pct_top: float = 0.10
    grid_intervals: int = 20
    check_interval_minutes: int = 5
    fee_rate: float = 0.001

@dataclass
class AppConfig:
    grid: GridConfig
    dry_run: bool = True
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

def load_config(config_path: Optional[str], cli_dry_run: bool) -> AppConfig:
    # 1. Load env vars
    load_dotenv()
    
    # 2. Load yaml config if provided
    raw_yaml = {}
    if config_path:
        with open(config_path, "r", encoding="utf-8") as file:
            raw_yaml = yaml.safe_load(file) or {}
    
    grid_data = raw_yaml.get("grid", {})
    grid_config = GridConfig(
        symbol=grid_data.get("symbol", "BTCUSDT"),
        mode=grid_data.get("mode", "LONG"),
        initial_capital_amount=float(grid_data.get("initial_capital_amount", 100.0)),
        initial_capital_asset=grid_data.get("initial_capital_asset", "USDT"),
        range_pct_bottom=float(grid_data.get("range_pct_bottom", -0.10)),
        range_pct_top=float(grid_data.get("range_pct_top", 0.10)),
        grid_intervals=int(grid_data.get("grid_intervals", 20)),
        check_interval_minutes=int(grid_data.get("check_interval_minutes", 5)),
        fee_rate=float(grid_data.get("fee_rate", 0.001))
    )
    
    app_config = AppConfig(grid=grid_config)
    
    # 3. CLI dry_run overrides default and config
    # We default dry_run to true for safety, but check env/cli
    app_config.dry_run = True
    if not cli_dry_run:
        # If the user didn't explicitly pass --dry-run, check yaml/env
        if "dry_run" in raw_yaml:
            app_config.dry_run = raw_yaml["dry_run"]
    # (By default or if cli_dry_run is true, dry_run stays True)
    
    # 4. Load Secrets from ENV overrides
    app_config.api_key = os.environ.get("EXCHANGE_API_KEY", raw_yaml.get("api_key"))
    app_config.api_secret = os.environ.get("EXCHANGE_API_SECRET", raw_yaml.get("api_secret"))
    
    # Validation logic
    validate_config(app_config)
    
    return app_config

def validate_config(config: AppConfig):
    # Missing secrets logic
    if not config.dry_run and (not config.api_key or not config.api_secret):
        print("WARNING: API keys missing. Yielding safely to dry-run mode.")
        config.dry_run = True

    # Mode validation
    valid_modes = ["LONG", "SHORT_INVERTED"]
    if config.grid.mode not in valid_modes:
        raise ConfigError(f"Mode must be one of {valid_modes}, got {config.grid.mode}")

    # Capital validation
    if config.grid.initial_capital_amount <= 0:
        raise ConfigError("Initial capital amount must be completely > 0.")
        
    # Grid intervals validation
    if config.grid.grid_intervals < 2:
        raise ConfigError("Grid intervals must be >= 2.")

    # Range validation
    if config.grid.range_pct_bottom >= config.grid.range_pct_top:
        raise ConfigError(f"range_pct_bottom ({config.grid.range_pct_bottom}) must be < range_pct_top ({config.grid.range_pct_top})")
