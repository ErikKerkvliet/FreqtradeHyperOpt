#!/usr/bin/env python3
"""
FreqTrade Hyperparameter Optimization Automation - CLI Version
Uses the unified FreqTradeExecutor for command execution and database integration.
"""

import os
import sys
import logging
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .optimization_config import OptimizationConfig
from .freqtrade_executor import FreqTradeExecutor
from dotenv import load_dotenv


class FreqTradeOptimizer:
    """
    CLI optimizer that uses FreqTradeExecutor for command execution.
    """

    def __init__(self):
        """Initialize the optimizer with logging and configuration setup."""
        self.logger = None
        self.setup_logging()
        self.config: Optional[OptimizationConfig] = None
        self.executor: Optional[FreqTradeExecutor] = None

        # Statistics
        self.strategies_processed = 0
        self.strategies_successful = 0
        self.strategies_failed = 0

        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, self._signal_handler)

    def setup_logging(self) -> None:
        """Set up comprehensive logging to both console and file."""
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"freqtrade_optimizer_{timestamp}.log"

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info("FreqTrade Optimizer initialized")

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        self.logger.warning("Received interrupt signal. Cleaning up...")
        if self.executor:
            self.executor.stop_execution()
        self.print_enhanced_summary()
        sys.exit(0)

    def load_configuration(self) -> bool:
        """Load configuration from .env file and validate all required parameters."""
        try:
            # Load environment variables
            load_dotenv()

            current_date = datetime.now()
            days = os.getenv('HISTORICAL_DATA_IN_DAYS')
            start_date = current_date - timedelta(days=int(days))
            timerange = f"{start_date.strftime('%Y%m%d')}-"

            # Read required variables
            freqtrade_path = os.getenv('FREQTRADE_PATH')
            exchange = os.getenv('EXCHANGE')
            timeframe = os.getenv('TIMEFRAME')
            pairs_str = os.getenv('PAIRS')
            pair_data_exchange = os.getenv('PAIR_DATA_EXCHANGE')
            hyperfunction = os.getenv('HYPERFUNCTION')

            # Validate required variables
            required_vars = {
                'FREQTRADE_PATH': freqtrade_path,
                'EXCHANGE': exchange,
                'PAIR_DATA_EXCHANGE': pair_data_exchange,
                'TIMEFRAME': timeframe,
                'TIMERANGE': timerange,
                'PAIRS': pairs_str,
                'HYPERFUNCTION': hyperfunction
            }

            missing_vars = [var for var, value in required_vars.items() if not value]
            if missing_vars:
                self.logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                return False

            # Parse pairs
            pairs = [pair.strip() for pair in pairs_str.split(',') if pair.strip()]
            if not pairs:
                self.logger.error("No trading pairs specified")
                return False

            # Validate FreqTrade path
            freqtrade_path = Path(freqtrade_path)
            if not freqtrade_path.exists():
                self.logger.error(f"FreqTrade path does not exist: {freqtrade_path}")
                return False

            # Create configuration object
            self.config = OptimizationConfig(
                freqtrade_path=str(freqtrade_path),
                exchange=exchange,
                timeframe=timeframe,
                timerange=timerange,
                pairs=pairs,
                pair_data_exchange=pair_data_exchange,
                hyperfunction=hyperfunction
            )

            # Initialize executor
            self.executor = FreqTradeExecutor(self.config, self.logger)

            self.logger.info("Configuration loaded successfully")
            self.logger.info(f"FreqTrade path: {self.config.freqtrade_path}")
            self.logger.info(f"Exchange: {self.config.exchange}")
            self.logger.info(f"Timeframe: {self.config.timeframe}")
            self.logger.info(f"Timerange: {self.config.timerange}")
            self.logger.info(f"Pairs: {', '.join(self.config.pairs)}")
            self.logger.info(f"Hyperopt function: {self.config.hyperfunction}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False

    def download_data(self) -> bool:
        """Download trading data for all specified pairs."""
        try:
            self.logger.info("Starting data download...")

            result = self.executor.download_data(
                exchange=self.config.pair_data_exchange,
                pairs=self.config.pairs,
                timeframes=[self.config.timeframe],
                timerange=self.config.timerange
            )

            if result.success:
                self.logger.info("Data download completed successfully")
                return True
            else:
                self.logger.error(f"Data download failed: {result.error_message}")
                # Try to continue anyway - data might already exist
                self.logger.warning("Continuing with existing data...")
                return True

        except Exception as e:
            self.logger.error(f"Error during data download: {e}")
            return False

    def find_strategies(self) -> List[str]:
        """Find all Python strategy files in the strategies directory."""
        try:
            strategies_dir = Path(self.config.freqtrade_path) / "user_data" / "strategies"

            if not strategies_dir.exists():
                self.logger.error(f"Strategies directory not found: {strategies_dir}")
                return []

            strategy_files = list(strategies_dir.glob("*.py"))
            strategies = []

            for strategy_file in strategy_files:
                # Skip __init__.py and other special files
                if strategy_file.name.startswith("__"):
                    continue

                strategy_name = strategy_file.stem
                strategies.append(strategy_name)

            self.logger.info(f"Found {len(strategies)} strategies: {', '.join(strategies)}")
            return strategies

        except Exception as e:
            self.logger.error(f"Error finding strategies: {e}")
            return []

    def optimize_strategy(self, strategy_name: str) -> bool:
        """Run complete optimization workflow for a single strategy (3 runs)."""
        try:
            self.logger.info(f"Processing strategy: {strategy_name}")

            successful_runs = 0

            # Run optimization 3 times
            for run_number in range(1, 4):
                self.logger.info(f"Starting hyperopt for {strategy_name} (Run {run_number}/3)...")

                result = self.executor.run_hyperopt(
                    strategy_name=strategy_name,
                    run_number=run_number
                )

                if result.success:
                    successful_runs += 1
                    profit_pct = self._extract_profit_from_output(result.stdout)
                    self.logger.info(f"✓ Hyperopt completed for {strategy_name} (Run {run_number}) - "
                                     f"Profit: {profit_pct:.2f}% - DB record {result.optimization_id}")
                else:
                    self.logger.error(f"✗ Hyperopt failed for {strategy_name} (Run {run_number}): "
                                      f"{result.error_message}")

            return successful_runs > 0

        except Exception as e:
            self.logger.error(f"Error optimizing strategy {strategy_name}: {e}")
            return False

    def _extract_profit_from_output(self, output: str) -> float:
        """Extract profit percentage from command output."""
        try:
            import re
            match = re.search(r"Total profit %\s*│\s*([\d.-]+)%", output)
            if match:
                return float(match.group(1))
        except:
            pass
        return 0.0

    def print_enhanced_summary(self) -> None:
        """Print enhanced summary with database insights."""
        self.logger.info("=" * 60)
        self.logger.info("OPTIMIZATION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total strategies processed: {self.strategies_processed}")
        self.logger.info(f"Successful optimizations: {self.strategies_successful}")
        self.logger.info(f"Failed optimizations: {self.strategies_failed}")

        # Get top performers from database
        try:
            if self.executor:
                best_strategies = self.executor.db_manager.get_best_strategies(limit=5)
                if best_strategies:
                    self.logger.info("\nTOP 5 PERFORMERS THIS SESSION:")
                    self.logger.info("-" * 40)
                    for i, strategy in enumerate(best_strategies, 1):
                        self.logger.info(f"{i}. {strategy['strategy_name']} - {strategy['total_profit_pct']:+.2f}% "
                                         f"({strategy['total_trades']} trades, {strategy['win_rate']:.1f}% win rate)")
        except Exception as e:
            self.logger.warning(f"Could not retrieve top performers: {e}")

        self.logger.info("=" * 60)
        if self.executor and self.executor.session_id:
            self.logger.info(f"Session ID: {self.executor.session_id}")
        self.logger.info("Use the database query tools to analyze results in detail.")
        self.logger.info("=" * 60)

    def run(self) -> bool:
        """Run the complete optimization workflow with database tracking."""
        try:
            session_start_time = datetime.now()
            self.logger.info("Starting FreqTrade optimization process...")

            # Load configuration
            if not self.load_configuration():
                return False

            # Start database session
            session_id = self.executor.start_session()

            # Download data
            if not self.download_data():
                # This is not a fatal error, as data might exist
                pass

            # Find strategies
            strategies = self.find_strategies()
            if not strategies:
                self.logger.error("No strategies found. Cannot proceed.")
                return False

            # Process each strategy
            total_strategies = len(strategies)
            for i, strategy_name in enumerate(strategies):
                self.logger.info(f"--- Starting Strategy {i + 1}/{total_strategies}: {strategy_name} ---")
                self.strategies_processed += 1

                if self.optimize_strategy(strategy_name):
                    self.strategies_successful += 1
                    self.logger.info(f"✓ {strategy_name} optimization completed successfully")
                else:
                    self.strategies_failed += 1
                    self.logger.error(f"✗ {strategy_name} optimization failed")

            # Update session summary
            session_duration = int((datetime.now() - session_start_time).total_seconds())
            self.executor.db_manager.update_session_summary(
                session_id,
                total_strategies,
                self.strategies_successful,
                self.strategies_failed,
                session_duration
            )

            # Print enhanced summary with database insights
            self.print_enhanced_summary()

            return self.strategies_successful > 0

        except KeyboardInterrupt:
            self.logger.warning("Process interrupted by user")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during optimization workflow: {e}")
            return False

def main():
    """Main entry point of the CLI application."""
    print("FreqTrade Hyperparameter Optimization Automation")
    print("=" * 50)

    optimizer = FreqTradeOptimizer()
    exit_code = 1  # Default to failure

    try:
        if optimizer.run():
            print("\n✓ Optimization workflow completed successfully!")
            exit_code = 0
        else:
            print("\n✗ Optimization workflow completed with errors.")

    except Exception as e:
        print(f"\nFatal error: {e}")
    finally:
        sys.exit(exit_code)

if __name__ == "__main__":
    main()