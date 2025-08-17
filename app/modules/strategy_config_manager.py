import json
import logging
from pathlib import Path
from .optimization_config import OptimizationConfig

class StrategyConfigManager:
    """
    Manages the creation of strategy-specific configuration files.
    """

    def __init__(self, config: OptimizationConfig, logger: logging.Logger):
        """
        Initialize the config manager.

        Args:
            config: The main OptimizationConfig object.
            logger: The shared logger instance.
        """
        self.config = config
        self.logger = logger
        self.template_path = Path("resources/config_template.json")
        self.config_dir = Path("configs")

    def create_config(self, strategy_name: str) -> bool:
        """
        Create a strategy-specific configuration file based on a template.

        Args:
            strategy_name: Name of the strategy.

        Returns:
            bool: True if config was created successfully, False otherwise.
        """
        try:
            self.config_dir.mkdir(exist_ok=True)
            strategy_config_path = self.config_dir / f"{strategy_name}.json"

            # Load template or create a default one
            if self.template_path.exists():
                with open(self.template_path, 'r') as f:
                    config_data = json.load(f)
            else:
                self.logger.info("config_template.json not found, creating a default one.")
                config_data = {
                    "max_open_trades": 3,
                    "stake_currency": "BTC",
                    "stake_amount": 0.001,
                    "tradable_balance_ratio": 0.99,
                    "fiat_display_currency": "EUR",
                    "dry_run": True,
                    "cancel_open_orders_on_exit": False,
                    "exchange": {},
                    "dataformat_ohlcv": "json",
                    "strategy": "",
                    "datadir": f"user_data/data/{self.config.pair_data_exchange}",
                    "internals": {"process_throttle_secs": 5}
                }

            # Update strategy-specific settings
            config_data["strategy"] = strategy_name
            if "exchange" not in config_data:
                config_data["exchange"] = {}
            config_data["exchange"]["name"] = self.config.exchange
            config_data["exchange"]["pair_whitelist"] = self.config.pairs

            # Save the new strategy-specific config file
            with open(strategy_config_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            self.logger.debug(f"Created config file: {strategy_config_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create config for strategy {strategy_name}: {e}")
            return False