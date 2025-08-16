#!/usr/bin/env python3
"""
FreqTrade Hyperparameter Optimization Automation
A comprehensive tool for automating FreqTrade strategy optimization across multiple strategies
with advanced database storage and analysis capabilities.
"""

import os
import sys
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
from optimization_config import OptimizationConfig
from strategy_config_manager import StrategyConfigManager
from results_database_manager import ResultsDatabaseManager, OptimizationResult

import re
import signal
from dotenv import load_dotenv


class FreqTradeOptimizer:
    """
    Main class for automating FreqTrade hyperparameter optimization with database storage.

    This class handles the complete optimization workflow:
    - Environment setup and configuration
    - Data downloading
    - Strategy processing
    - Hyperparameter optimization
    - Results export and database management
    """

    def __init__(self):
        """Initialize the optimizer with logging, configuration, and database setup."""
        self.logger = None
        self.setup_logging()
        self.config: Optional[OptimizationConfig] = None
        self.strategies_processed = 0
        self.strategies_successful = 0
        self.strategies_failed = 0
        self.results_summary = []

        # Initialize database manager
        self.db_manager = ResultsDatabaseManager()
        self.session_id: Optional[int] = None
        self.session_start_time: Optional[datetime] = None

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
        self.print_enhanced_summary()
        sys.exit(0)

    def load_configuration(self) -> bool:
        """
        Load configuration from .env file and validate all required parameters.

        Returns:
            bool: True if configuration loaded successfully, False otherwise.
        """
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

    def activate_venv_and_execute(self, command: str, timeout: int = 300) -> Tuple[bool, str, str]:
        """
        Execute a command within the FreqTrade virtual environment.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            venv_path = Path(self.config.freqtrade_path) / ".venv" / "bin" / "activate"

            # Construct the command to activate venv and run freqtrade command
            if os.name == 'nt':  # Windows
                venv_activate = f"{Path(self.config.freqtrade_path) / '.venv' / 'Scripts' / 'activate.bat'}"
                full_command = f"call \"{venv_activate}\" && cd \"{self.config.freqtrade_path}\" && {command}"
                shell_cmd = ["cmd", "/c", full_command]
            else:  # Unix/Linux
                venv_activate = f"source \"{venv_path}\""
                full_command = f"{venv_activate} && cd \"{self.config.freqtrade_path}\" && {command}"
                shell_cmd = ["/bin/bash", "-c", full_command]

            # Execute command
            process = subprocess.run(
                shell_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.config.freqtrade_path,
            )

            # Log stdout/stderr for better debugging
            if process.stdout:
                self.logger.info(f"Command output:\n{process.stdout}")
            if process.stderr:
                self.logger.error(f"Command error output:\n{process.stderr}")

            success = process.returncode == 0
            return success, process.stdout, process.stderr

        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout} seconds: {command}")
            return False, "", "Command timed out"
        except Exception as e:
            self.logger.error(f"Failed to execute command: {command}, Error: {e}")
            return False, "", str(e)

    def download_data(self) -> bool:
        """
        Download trading data for all specified pairs.

        Returns:
            bool: True if data download was successful, False otherwise.
        """
        try:
            self.logger.info("Starting data download...")

            pairs_str = " ".join(self.config.pairs)
            data_dir = f"user_data/data/{self.config.pair_data_exchange}"

            command = (
                f"freqtrade download-data "
                f"--exchange {self.config.pair_data_exchange} "
                f"--timeframe {self.config.timeframe} "
                f"--timerange {self.config.timerange} "
                f"-p {pairs_str} "
                f"--datadir {data_dir}"
            )

            self.logger.info(f"Downloading data for pairs: {', '.join(self.config.pairs)}")
            success, stdout, stderr = self.activate_venv_and_execute(command, timeout=600)

            if success:
                self.logger.info("Data download completed successfully")
                return True
            else:
                self.logger.error(f"Data download failed.")
                # Try to continue anyway - data might already exist
                self.logger.warning("Continuing with existing data...")
                return True

        except Exception as e:
            self.logger.error(f"Error during data download: {e}")
            return False

    def find_strategies(self) -> List[str]:
        """
        Find all Python strategy files in the strategies directory.

        Returns:
            List of strategy names (without .py extension).
        """
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

    def run_hyperopt(self, strategy_name: str, run_number: int) -> bool:
        """
        Run hyperparameter optimization for a specific strategy with database storage.

        Args:
            strategy_name: Name of the strategy to optimize
            run_number: Current run number (1-3)

        Returns:
            True if optimization and result saving were successful, False otherwise.
        """
        try:
            start_time = time.time()

            # Automatically remove stale lock file
            lock_file_path = Path(self.config.freqtrade_path) / "user_data" / "hyperopt.lock"
            if lock_file_path.exists():
                self.logger.warning(f"Found and removed stale lock file: {lock_file_path}")
                lock_file_path.unlink()

            self.logger.info(f"Starting hyperopt for {strategy_name} (Run {run_number}/3)...")

            command = (
                f"freqtrade hyperopt "
                f"--config config_files/{strategy_name}.json "
                f"--strategy {strategy_name} "
                f"--timerange {self.config.timerange} "
                f"--epochs {self.config.epochs} "
                f"--spaces buy sell roi stoploss "
                f"--hyperopt-loss {self.config.hyperfunction}"
                f"--timeframe {self.config.timeframe} "
            )

            success, stdout, stderr = self.activate_venv_and_execute(command, timeout=self.config.timeout)

            if not success:
                self.logger.error(f"Hyperopt failed for {strategy_name} (Run {run_number}).")
                return False

            # Get best results from the completed run
            show_command = "freqtrade hyperopt-show -n 1 --print-json"
            success, result_stdout, result_stderr = self.activate_venv_and_execute(show_command)

            if not success or not result_stdout:
                self.logger.error(f"Failed to get hyperopt results for {strategy_name}.")
                return False

            # Calculate optimization duration
            optimization_duration = int(time.time() - start_time)

            # Parse results using database manager
            parsed_metrics = self.db_manager.parse_hyperopt_results(result_stdout)

            # Load current strategy config
            config_path = Path("config_files") / f"{strategy_name}.json"
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # Extract hyperopt JSON results for full storage
            try:
                json_start_index = result_stdout.find('[')
                if json_start_index != -1:
                    clean_json_str = result_stdout[json_start_index:]
                    hyperopt_json_results = json.loads(clean_json_str)
                else:
                    hyperopt_json_results = {"raw_output": result_stdout}
            except json.JSONDecodeError:
                hyperopt_json_results = {"raw_output": result_stdout}

            # Add metadata to hyperopt results
            hyperopt_json_results.update({
                "hyperopt_function": self.config.hyperfunction,
                "epochs": self.config.epochs,
                "timerange": self.config.timerange,
                "optimization_timestamp": datetime.now().isoformat(),
                "optimization_duration_seconds": optimization_duration
            })

            # Create OptimizationResult object
            result = OptimizationResult(
                strategy_name=strategy_name,
                total_profit_pct=parsed_metrics.get('total_profit_pct', 0.0),
                total_profit_abs=parsed_metrics.get('total_profit_abs', 0.0),
                total_trades=parsed_metrics.get('total_trades', 0),
                win_rate=parsed_metrics.get('win_rate', 0.0),
                avg_profit_pct=parsed_metrics.get('avg_profit_pct', 0.0),
                max_drawdown_pct=parsed_metrics.get('max_drawdown_pct', 0.0),
                sharpe_ratio=parsed_metrics.get('sharpe_ratio', 0.0),
                config_data=config_data,
                hyperopt_results=hyperopt_json_results,
                optimization_duration=optimization_duration,
                run_number=run_number
            )

            # Save to database
            optimization_id = self.db_manager.save_optimization_result(result, self.session_id)

            # Also save the traditional file (for backward compatibility)
            profit_pct = parsed_metrics.get('total_profit_pct', 0.0)
            self._save_traditional_result_file(strategy_name, run_number, profit_pct)

            self.logger.info(f"Hyperopt completed successfully for {strategy_name} (Run {run_number}) - "
                             f"Profit: {profit_pct:.2f}% - Saved as DB record {optimization_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error during hyperopt for {strategy_name} (Run {run_number}): {e}")
            return False

    def _save_traditional_result_file(self, strategy_name: str, run_number: int, profit_pct: float) -> None:
        """Save result file in traditional format for backward compatibility."""
        try:
            # Create results directory if it doesn't exist
            results_dir = Path(self.config.freqtrade_path) / "user_data" / "strategies" / "results"
            results_dir.mkdir(exist_ok=True)

            # Find and move the generated hyperopt file
            source_file = Path(self.config.freqtrade_path) / "user_data" / "strategies" / f"{strategy_name}.json"
            target_file = results_dir / f"{profit_pct:+.2f}-{strategy_name}-run{run_number}.json"

            if source_file.exists():
                source_file.rename(target_file)
                self.logger.debug(f"Traditional result file saved: {target_file}")
            else:
                self.logger.warning(f"Could not find traditional hyperopt result file: {source_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save traditional result file: {e}")

    @staticmethod
    def get_total_profit_percentage(report_text: str) -> float | None:
        """
        Parses the backtesting report to find the total profit percentage.

        Args:
          report_text: A string containing the full backtesting report.

        Returns:
          The total profit percentage as a float (e.g., 1.96),
          or None if the value cannot be found.
        """
        # Regex to find "Total profit %" and capture the associated number
        match = re.search(r"│\s*Total profit %\s*│\s*([\d.]+)%", report_text)

        if match:
            try:
                # The first captured group is the number, convert it to a float
                return float(match.group(1))
            except (ValueError, IndexError):
                # Return None if conversion or capturing fails
                return None

        return None

    def optimize_strategy(self, strategy_name: str) -> bool:
        """
        Run complete optimization workflow for a single strategy (3 runs).

        Args:
            strategy_name: Name of the strategy to optimize

        Returns:
            bool: True if at least one run was successful, False otherwise.
        """
        try:
            self.logger.info(f"Processing strategy: {strategy_name}")

            strategy_config_manager = StrategyConfigManager(self.config, self.logger)

            # Create strategy config
            if not strategy_config_manager.create_config(strategy_name):
                return False

            successful_runs = 0
            # Run optimization 3 times
            for run_number in range(1, 2):
                if self.run_hyperopt(strategy_name, run_number):
                    successful_runs += 1

            return successful_runs > 0

        except Exception as e:
            self.logger.error(f"Error optimizing strategy {strategy_name}: {e}")
            return False

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
            best_strategies = self.db_manager.get_best_strategies(limit=5)
            if best_strategies:
                self.logger.info("\nTOP 5 PERFORMERS THIS SESSION:")
                self.logger.info("-" * 40)
                for i, strategy in enumerate(best_strategies, 1):
                    self.logger.info(f"{i}. {strategy['strategy_name']} - {strategy['total_profit_pct']:+.2f}% "
                                     f"({strategy['total_trades']} trades, {strategy['win_rate']:.1f}% win rate)")
        except Exception as e:
            self.logger.warning(f"Could not retrieve top performers: {e}")

        self.logger.info("=" * 60)
        if self.session_id:
            self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info("Use the database query tools to analyze results in detail.")
        self.logger.info("=" * 60)

    def run(self) -> bool:
        """
        Run the complete optimization workflow with database tracking.

        Returns:
            bool: True if the workflow completed successfully, False otherwise.
        """
        try:
            self.session_start_time = datetime.now()
            self.logger.info("Starting FreqTrade optimization process...")

            # Load configuration
            if not self.load_configuration():
                return False

            # Start database session
            self.session_id = self.db_manager.start_session(
                exchange_name=self.config.exchange,
                timeframe=self.config.timeframe,
                timerange=self.config.timerange,
                hyperopt_function=self.config.hyperfunction,
                epochs=self.config.epochs
            )

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
            if self.session_start_time:
                session_duration = int((datetime.now() - self.session_start_time).total_seconds())
                self.db_manager.update_session_summary(
                    self.session_id,
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
    """Main entry point of the application."""
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