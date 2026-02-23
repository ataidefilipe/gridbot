import yaml
import pytest
from src.core.config import load_config, ConfigError

def test_load_default_config():
    config = load_config(None, cli_dry_run=True)
    assert config.dry_run is True
    assert config.grid.symbol == "BTCUSDT"

def test_missing_api_keys_forces_dry_run(monkeypatch):
    monkeypatch.delenv("EXCHANGE_API_KEY", raising=False)
    monkeypatch.delenv("EXCHANGE_API_SECRET", raising=False)
    config = load_config(None, cli_dry_run=False)
    assert config.dry_run is True

def test_load_yaml_config(tmp_path):
    config_file = tmp_path / "test_conf.yaml"
    config_data = {
        "grid": {
            "symbol": "BTCETH",
            "mode": "SHORT_INVERTED"
        },
        "dry_run": False
    }
    config_file.write_text(yaml.dump(config_data))
    
    config = load_config(str(config_file), cli_dry_run=True)
    assert config.grid.symbol == "BTCETH"
    assert config.grid.mode == "SHORT_INVERTED"
    # CLI arg overrides YAML
    assert config.dry_run is True

def test_invalid_mode():
    with pytest.raises(ConfigError):
        # We monkeypatch the loaded config or test via YAML
        from src.core.config import AppConfig, GridConfig, validate_config
        cfg = AppConfig(grid=GridConfig(mode="INVALID_MODE"))
        validate_config(cfg)

def test_invalid_range():
    with pytest.raises(ConfigError, match="must be <"):
        from src.core.config import AppConfig, GridConfig, validate_config
        cfg = AppConfig(grid=GridConfig(range_pct_bottom=0.20, range_pct_top=0.10))
        validate_config(cfg)
