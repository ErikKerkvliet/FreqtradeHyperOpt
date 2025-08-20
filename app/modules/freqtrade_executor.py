#!/usr/bin/env python3
"""
FreqTrade Command Executor - Updated for Simplified Two-Table Database
Unified class for executing FreqTrade commands (hyperopt, backtest, download-data)
with direct database integration using the simplified schema.
"""

import os
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass

from .optimization_config import OptimizationConfig
from .strategy_config_manager import StrategyConfigManager
from .results_database_manager import DatabaseManager, HyperoptResult, BacktestResult


@dataclass
class ExecutionResult:
    """Result of a command execution."""
    success: bool
    return_code: int
    stdout: str
    stderr: str
    duration: int
    hyperopt_id: Optional[int] = None
    backtest_id: Optional[int] = None
    error_message: Optional[str] = None


class FreqTradeExecutor:
    """
    Unified command executor for FreqTrade operations.
    Handles hyperopt, backtest, and data download commands with simplified database integration.
    """

    def __init__(self, config: OptimizationConfig = None, logger: logging.Logger = None, db_manager: DatabaseManager = None):
        """
        Initialize the executor.

        Args:
            config: OptimizationConfig object
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or self._setup_default_logger()
        self.db_manager = db_manager
        self.strategy_config_manager = None

        if self.config:
            self.strategy_config_manager = StrategyConfigManager(self.config, self.logger)

        # Execution state
        self.current_process: Optional[subprocess.Popen] = None
        self.current_session_info: Dict[str, Any] = {}
        self.is_running = False

        # Session info for tracking
        self.session_start_time = datetime.now()

        # Callbacks for GUI integration
        self.progress_callback: Optional[Callable[[str], None]] = None
        self.output_callback: Optional[Callable[[str], None]] = None
        self.completion_callback: Optional[Callable[[ExecutionResult], None]] = None

    @staticmethod
    def _setup_default_logger() -> logging.Logger:
        """Setup default logger if none provided."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def set_callbacks(self, progress_callback: Callable[[str], None] = None,
                      output_callback: Callable[[str], None] = None,
                      completion_callback: Callable[[ExecutionResult], None] = None):
        """Set callbacks for GUI integration."""
        self.progress_callback = progress_callback
        self.output_callback = output_callback
        self.completion_callback = completion_callback

    def start_session(self, session_name: str = None) -> Dict[str, Any]:
        """Start a new session for tracking related operations."""
        self.session_start_time = datetime.now()

        session_info = {
            'session_name': session_name or f"Session_{self.session_start_time.strftime('%Y%m%d_%H%M%S')}",
            'start_time': self.session_start_time.isoformat(),
            'exchange': self.config.exchange if self.config else 'unknown',
            'timeframe': self.config.timeframe if self.config else 'unknown',
            'timerange': self.config.timerange if self.config else 'unknown',
            'hyperopt_function': self.config.hyperfunction if self.config else 'unknown',
            'epochs': self.config.epochs if self.config else 0,
            'strategies_processed': 0,
            'strategies_successful': 0,
            'strategies_failed': 0
        }

        self.current_session_info = session_info
        self.logger.info(f"Started session: {session_info['session_name']}")
        return session_info

    def update_session_stats(self, success: bool = None):
        """Update session statistics."""
        if success is not None:
            self.current_session_info['strategies_processed'] = self.current_session_info.get('strategies_processed',
                                                                                              0) + 1
            if success:
                self.current_session_info['strategies_successful'] = self.current_session_info.get(
                    'strategies_successful', 0) + 1
            else:
                self.current_session_info['strategies_failed'] = self.current_session_info.get('strategies_failed',
                                                                                               0) + 1

        # Update duration
        if self.session_start_time:
            duration = (datetime.now() - self.session_start_time).total_seconds()
            self.current_session_info['duration_seconds'] = int(duration)

    def execute_command(self, command: List[str], timeout: int = 3600) -> ExecutionResult:
        """
        Execute a FreqTrade command with proper environment setup.

        Args:
            command: Command to execute as list of strings
            timeout: Command timeout in seconds

        Returns:
            ExecutionResult object
        """
        start_time = time.time()
        result = None

        try:
            if not self.config or not self.config.freqtrade_path:
                return ExecutionResult(
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr="FreqTrade path not configured",
                    duration=0,
                    error_message="FreqTrade path not configured"
                )

            self.is_running = True
            self._notify_progress(f"Running")
            self._notify_output(f"Command: {' '.join(command)}\n")

            # Setup environment
            env = os.environ.copy()
            cwd = self.config.freqtrade_path

            # Build command with virtual environment activation
            if os.name == 'nt':  # Windows
                venv_activate = Path(self.config.freqtrade_path) / '.venv' / 'Scripts' / 'activate.bat'
                if venv_activate.exists():
                    full_command = f'call "{venv_activate}" && ' + ' '.join(command)
                else:
                    full_command = ' '.join(command)
                    self._notify_output("Warning: Virtual environment not found\n")
            else:  # Unix/Linux
                venv_activate = Path(self.config.freqtrade_path) / '.venv' / 'bin' / 'activate'
                if venv_activate.exists():
                    full_command = f'bash -c "source {venv_activate} && {" ".join(command)}"'
                else:
                    full_command = ' '.join(command)
                    self._notify_output("Warning: Virtual environment not found\n")

            # Execute command
            self.current_process = subprocess.Popen(
                full_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=env
            )

            # Read output in real-time
            stdout_lines = []
            stderr_lines = []

            while True:
                # Check if process is still running
                if self.current_process.poll() is not None:
                    # Process finished, read remaining output
                    remaining_stdout, remaining_stderr = self.current_process.communicate()
                    if remaining_stdout:
                        stdout_lines.append(remaining_stdout)
                        self._notify_output(remaining_stdout)
                    if remaining_stderr:
                        stderr_lines.append(remaining_stderr)
                        self._notify_output(remaining_stderr)
                    break

                # Read available output
                try:
                    import select
                    ready, _, _ = select.select([self.current_process.stdout, self.current_process.stderr], [], [], 0.1)

                    for stream in ready:
                        line = stream.readline()
                        if line:
                            if stream == self.current_process.stdout:
                                stdout_lines.append(line)
                            else:
                                stderr_lines.append(line)
                            self._notify_output(line)

                except ImportError:
                    # Fallback for Windows (no select module)
                    try:
                        stdout, stderr = self.current_process.communicate(timeout=0.1)
                        if stdout:
                            stdout_lines.append(stdout)
                            self._notify_output(stdout)
                        if stderr:
                            stderr_lines.append(stderr)
                            self._notify_output(stderr)
                        break
                    except subprocess.TimeoutExpired:
                        continue

            # Get results
            return_code = self.current_process.returncode
            stdout = ''.join(stdout_lines)
            stderr = ''.join(stderr_lines)
            duration = int(time.time() - start_time)

            result = ExecutionResult(
                success=(return_code == 0),
                return_code=return_code,
                stdout=stdout,
                stderr=stderr,
                duration=duration
            )

            if return_code == 0:
                self._notify_progress("Command completed successfully")
            else:
                result.error_message = f"Command failed with {return_code}"
                self._notify_progress(f"Command failed with {return_code}")

            return result

        except subprocess.TimeoutExpired:
            if self.current_process:
                self.current_process.terminate()

            duration = int(time.time() - start_time)
            result = ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr="Command timed out",
                duration=duration,
                error_message=f"Command timed out after {timeout} seconds"
            )

            self._notify_progress("Command timed out")
            return result

        except Exception as e:
            duration = int(time.time() - start_time)
            error_msg = f"Execution error: {e}"

            result = ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=duration,
                error_message=error_msg
            )

            self.logger.error(error_msg)
            self._notify_progress("Execution error")
            return result

        finally:
            self.is_running = False
            self.current_process = None
            if self.completion_callback and result:
                self.completion_callback(result)

    def run_hyperopt(self, strategy_name: str, config_file: str = None,
                     timerange: str = None, epochs: int = None,
                     spaces: List[str] = None, hyperopt_loss: str = None,
                     run_number: int = 1) -> ExecutionResult:
        """
        Run hyperparameter optimization for a strategy.

        Args:
            strategy_name: Name of the strategy
            config_file: Path to config file (optional, will create if not provided)
            timerange: Timerange for optimization
            epochs: Number of epochs
            spaces: Hyperopt spaces to optimize
            hyperopt_loss: Loss function to use
            run_number: Run number for this optimization

        Returns:
            ExecutionResult with hyperopt_id if successful
        """
        try:
            self.logger.info(f"Starting hyperopt for {strategy_name} (Run {run_number})")

            # Use provided values or defaults from config
            if not timerange and self.config:
                timerange = self.config.timerange
            if not epochs and self.config:
                epochs = self.config.epochs
            if not spaces:
                spaces = ['buy', 'sell', 'roi', 'stoploss']
            if not hyperopt_loss and self.config:
                hyperopt_loss = self.config.hyperfunction

            # Create strategy config if not provided
            if not config_file:
                if not self.strategy_config_manager:
                    raise ValueError("Strategy config manager not available")

                if not self.strategy_config_manager.create_config(strategy_name):
                    raise ValueError(f"Failed to create config for strategy {strategy_name}")

                config_file = f"configs/{strategy_name}.json"

            # Remove stale lock file
            if self.config:
                lock_file_path = Path(self.config.freqtrade_path) / "user_data" / "hyperopt.lock"
                if lock_file_path.exists():
                    self.logger.warning(f"Removed stale lock file: {lock_file_path}")
                    lock_file_path.unlink()

            # Build command
            command = [
                          "freqtrade", "hyperopt",
                          "--config", config_file,
                          "--strategy", strategy_name,
                          "--timerange", timerange,
                          "--epochs", str(epochs),
                          "--spaces"] + spaces + [
                          "--hyperopt-loss", hyperopt_loss
                      ]

            # Execute hyperopt
            result = self.execute_command(command, timeout=self.config.timeout if self.config else 3600)

            if not result.success:
                self.update_session_stats(success=False)
                return result

            # Get hyperopt results
            show_result = self._get_hyperopt_results()
            if not show_result.success:
                result.error_message = "Failed to retrieve hyperopt results"
                self.update_session_stats(success=False)
                return result

            # Parse and save results to database
            hyperopt_id = self._save_hyperopt_results_to_db(
                strategy_name, show_result.stdout, config_file,
                result.duration, run_number
            )

            if hyperopt_id:
                result.hyperopt_id = hyperopt_id
                self.logger.info(f"Hyperopt completed for {strategy_name} - DB record {hyperopt_id}")
                self.update_session_stats(success=True)
            else:
                result.error_message = "Failed to save results to database"
                self.update_session_stats(success=False)

            return result

        except Exception as e:
            error_msg = f"Error during hyperopt for {strategy_name}: {e}"
            self.logger.error(error_msg)
            self.update_session_stats(success=False)
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=0,
                error_message=error_msg
            )

    def run_backtest(self, strategy_name: str, config_file: str,
                     timerange: str = None, hyperopt_id: Optional[int] = None) -> ExecutionResult:
        """
        Run backtest for a strategy.

        Args:
            strategy_name: Name of the strategy
            config_file: Path to config file
            timerange: Timerange for backtest
            hyperopt_id: Optional link to hyperopt run that generated this config

        Returns:
            ExecutionResult object
        """
        try:
            self.logger.info(f"Starting backtest for {strategy_name}")

            if not timerange and self.config:
                timerange = self.config.timerange

            # Build command
            command = [
                "freqtrade", "backtesting",
                "--config", config_file,
                "--strategy", strategy_name,
                "--timerange", timerange
            ]

            # Execute backtest
            result = self.execute_command(command)

            if result.success:
                # Parse and save backtest results
                backtest_id = self._save_backtest_results_to_db(
                    strategy_name, result.stdout, config_file,
                    result.duration, hyperopt_id
                )

                if backtest_id:
                    result.backtest_id = backtest_id
                    self.logger.info(f"Backtest completed for {strategy_name} - DB record {backtest_id}")
                    self.update_session_stats(success=True)
                else:
                    result.error_message = "Failed to save backtest results to database"
                    self.update_session_stats(success=False)
            else:
                self.logger.error(f"Backtest failed for {strategy_name}")
                self.update_session_stats(success=False)

            return result

        except Exception as e:
            error_msg = f"Error during backtest for {strategy_name}: {e}"
            self.logger.error(error_msg)
            self.update_session_stats(success=False)
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=0,
                error_message=error_msg
            )

    def run_strategy_backtest_from_hyperopt(self, hyperopt_id: int) -> ExecutionResult:
        """
        Run backtest for a strategy using the configuration from a hyperopt result.

        Args:
            hyperopt_id: ID of the hyperopt result to use

        Returns:
            ExecutionResult object
        """
        try:
            # Get hyperopt result from database
            hyperopt_results = self.db_manager.get_best_hyperopt_strategies(limit=1000)  # Get all to find by ID
            hyperopt_result = None

            for result in hyperopt_results:
                if result['id'] == hyperopt_id:
                    hyperopt_result = result
                    break

            if not hyperopt_result:
                error_msg = f"Hyperopt result with ID {hyperopt_id} not found"
                self.logger.error(error_msg)
                return ExecutionResult(
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr=error_msg,
                    duration=0,
                    error_message=error_msg
                )

            strategy_name = hyperopt_result['strategy_name']
            config_file = hyperopt_result['config_file_path']

            if not config_file or not Path(config_file).exists():
                error_msg = f"Config file not found for hyperopt ID {hyperopt_id}: {config_file}"
                self.logger.error(error_msg)
                return ExecutionResult(
                    success=False,
                    return_code=-1,
                    stdout="",
                    stderr=error_msg,
                    duration=0,
                    error_message=error_msg
                )

            self.logger.info(f"Running backtest for {strategy_name} using hyperopt config {hyperopt_id}")

            return self.run_backtest(
                strategy_name=strategy_name,
                config_file=config_file,
                hyperopt_id=hyperopt_id
            )

        except Exception as e:
            error_msg = f"Error running backtest from hyperopt {hyperopt_id}: {e}"
            self.logger.error(error_msg)
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=0,
                error_message=error_msg
            )

    def batch_backtest_from_best_hyperopt(self, limit: int = 5, timeframe: Optional[str] = None) -> List[
        ExecutionResult]:
        """
        Run backtests for the best performing hyperopt strategies.

        Args:
            limit: Number of top strategies to backtest
            timeframe: Optional timeframe filter

        Returns:
            List of ExecutionResult objects
        """
        try:
            # Get best hyperopt strategies
            best_strategies = self.db_manager.get_best_hyperopt_strategies(limit=limit, timeframe=timeframe)

            if not best_strategies:
                self.logger.warning("No hyperopt strategies found for batch backtesting")
                return []

            results = []
            self.logger.info(f"Starting batch backtest for {len(best_strategies)} strategies")

            for i, strategy in enumerate(best_strategies, 1):
                self.logger.info(
                    f"Backtesting {i}/{len(best_strategies)}: {strategy['strategy_name']} (ID {strategy['id']})")

                result = self.run_strategy_backtest_from_hyperopt(strategy['id'])
                results.append(result)

                if result.success:
                    self.logger.info(f"✓ Backtest completed for {strategy['strategy_name']}")
                else:
                    self.logger.error(f"✗ Backtest failed for {strategy['strategy_name']}: {result.error_message}")

            successful = sum(1 for r in results if r.success)
            self.logger.info(f"Batch backtest completed: {successful}/{len(results)} successful")

            return results

        except Exception as e:
            error_msg = f"Error during batch backtesting: {e}"
            self.logger.error(error_msg)
            return []

    def download_data(self, exchange: str, pairs: List[str], timeframes: List[str],
                      timerange: str = None, days: int = None) -> ExecutionResult:
        """
        Download market data.

        Args:
            exchange: Exchange name
            pairs: List of trading pairs
            timeframes: List of timeframes
            timerange: Timerange for download
            days: Number of days to download (alternative to timerange)

        Returns:
            ExecutionResult object
        """
        try:
            self.logger.info(f"Starting data download for {len(pairs)} pairs on {exchange}")

            # Calculate timerange if days provided
            if days and not timerange:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                timerange = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"

            # Download data for each timeframe
            all_results = []

            for timeframe in timeframes:
                self._notify_progress(f"Downloading {timeframe} data...")

                # Build command
                command = [
                              "freqtrade", "download-data",
                              "--exchange", exchange,
                              "--timeframe", timeframe,
                              "--timerange", timerange,
                              "-p"] + pairs

                # Execute download
                result = self.execute_command(command, timeout=600)
                all_results.append(result)

                if not result.success:
                    self.logger.error(f"Download failed for timeframe {timeframe}")
                    return result
                else:
                    self.logger.info(f"Download completed for timeframe {timeframe}")

            # Return combined result
            total_duration = sum(r.duration for r in all_results)
            combined_stdout = '\n'.join(r.stdout for r in all_results)

            return ExecutionResult(
                success=True,
                return_code=0,
                stdout=combined_stdout,
                stderr="",
                duration=total_duration
            )

        except Exception as e:
            error_msg = f"Error during data download: {e}"
            self.logger.error(error_msg)
            return ExecutionResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                duration=0,
                error_message=error_msg
            )

    def stop_execution(self) -> bool:
        """Stop the current execution."""
        if self.current_process and self.is_running:
            try:
                self.current_process.terminate()
                self.logger.info("Execution stopped by user")
                self._notify_progress("Execution stopped")
                return True
            except Exception as e:
                self.logger.error(f"Failed to stop execution: {e}")
                return False
        return False

    def get_session_summary(self) -> Dict[str, Any]:
        """Get current session summary."""
        self.update_session_stats()  # Update duration
        return self.current_session_info.copy()

    def _get_hyperopt_results(self) -> ExecutionResult:
        """Get hyperopt results using hyperopt-show command."""
        command = ["freqtrade", "hyperopt-show", "-n", "1", "--print-json"]
        return self.execute_command(command, timeout=60)

    def _save_hyperopt_results_to_db(self, strategy_name: str, hyperopt_output: str,
                                     config_file: str, optimization_duration: int,
                                     run_number: int) -> Optional[int]:
        """Save hyperopt results to simplified database."""
        try:
            # Parse metrics from hyperopt output
            parsed_metrics = self.db_manager.parse_hyperopt_results(hyperopt_output)

            # Load config data
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            # Extract JSON results
            try:
                json_start_index = hyperopt_output.find('[')
                if json_start_index != -1:
                    clean_json_str = hyperopt_output[json_start_index:]
                    hyperopt_json_results = json.loads(clean_json_str)
                else:
                    hyperopt_json_results = {"raw_output": hyperopt_output}
            except json.JSONDecodeError:
                hyperopt_json_results = {"raw_output": hyperopt_output}

            # Add metadata
            hyperopt_json_results.update({
                "hyperopt_function": self.config.hyperfunction if self.config else "Unknown",
                "epochs": self.config.epochs if self.config else 0,
                "timerange": self.config.timerange if self.config else "Unknown",
                "optimization_timestamp": datetime.now().isoformat(),
                "optimization_duration_seconds": optimization_duration
            })

            # Create HyperoptResult
            result = HyperoptResult(
                strategy_name=strategy_name,
                total_profit_pct=parsed_metrics.get('total_profit_pct', 0.0),
                total_profit_abs=parsed_metrics.get('total_profit_abs', 0.0),
                total_trades=parsed_metrics.get('total_trades', 0),
                win_rate=parsed_metrics.get('win_rate', 0.0),
                avg_profit_pct=parsed_metrics.get('avg_profit_pct', 0.0),
                max_drawdown_pct=parsed_metrics.get('max_drawdown_pct', 0.0),
                sharpe_ratio=parsed_metrics.get('sharpe_ratio', 0.0),
                calmar_ratio=parsed_metrics.get('calmar_ratio', 0.0),
                sortino_ratio=parsed_metrics.get('sortino_ratio', 0.0),
                profit_factor=parsed_metrics.get('profit_factor', 0.0),
                expectancy=parsed_metrics.get('expectancy', 0.0),

                # Configuration details
                max_open_trades=config_data.get('max_open_trades', 1),
                timeframe=config_data.get('timeframe', self.config.timeframe if self.config else '5m'),
                stake_amount=config_data.get('stake_amount', 100.0),
                stake_currency=config_data.get('stake_currency', 'USDT'),
                timerange=self.config.timerange if self.config else 'Unknown',
                pair_whitelist=config_data.get('exchange', {}).get('pair_whitelist', []),
                exchange_name=config_data.get('exchange', {}).get('name',
                                                                  self.config.exchange if self.config else 'unknown'),

                # Hyperopt specific
                hyperopt_function=self.config.hyperfunction if self.config else 'Unknown',
                epochs=self.config.epochs if self.config else 0,
                spaces=['buy', 'sell', 'roi', 'stoploss'],  # Default spaces

                # Metadata
                config_data=config_data,
                hyperopt_json_data=hyperopt_json_results,
                optimization_duration=optimization_duration,
                run_number=run_number
            )

            # Save to database with session info
            hyperopt_id = self.db_manager.save_hyperopt_result(result, self.current_session_info)
            return hyperopt_id

        except Exception as e:
            self.logger.error(f"Failed to save hyperopt results to database: {e}")
            return None

    def _save_backtest_results_to_db(self, strategy_name: str, backtest_output: str,
                                     config_file: str, backtest_duration: int,
                                     hyperopt_id: Optional[int] = None) -> Optional[int]:
        """Save backtest results to simplified database."""
        try:
            # Parse metrics from backtest output
            parsed_metrics = self.db_manager.parse_backtest_results(backtest_output)

            # Load config data
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            # Create BacktestResult
            result = BacktestResult(
                strategy_name=strategy_name,
                total_profit_pct=parsed_metrics.get('total_profit_pct', 0.0),
                total_profit_abs=parsed_metrics.get('total_profit_abs', 0.0),
                total_trades=parsed_metrics.get('total_trades', 0),
                win_rate=parsed_metrics.get('win_rate', 0.0),
                avg_profit_pct=parsed_metrics.get('avg_profit_pct', 0.0),
                max_drawdown_pct=parsed_metrics.get('max_drawdown_pct', 0.0),
                max_drawdown_abs=parsed_metrics.get('max_drawdown_abs', 0.0),

                # Advanced metrics
                sharpe_ratio=parsed_metrics.get('sharpe_ratio', 0.0),
                calmar_ratio=parsed_metrics.get('calmar_ratio', 0.0),
                sortino_ratio=parsed_metrics.get('sortino_ratio', 0.0),
                profit_factor=parsed_metrics.get('profit_factor', 0.0),
                expectancy=parsed_metrics.get('expectancy', 0.0),

                # Trade statistics
                winning_trades=parsed_metrics.get('winning_trades', 0),
                losing_trades=parsed_metrics.get('losing_trades', 0),
                draw_trades=parsed_metrics.get('draw_trades', 0),
                best_trade_pct=parsed_metrics.get('best_trade_pct', 0.0),
                worst_trade_pct=parsed_metrics.get('worst_trade_pct', 0.0),
                avg_trade_duration=parsed_metrics.get('avg_trade_duration', 'Unknown'),

                # Configuration
                max_open_trades=config_data.get('max_open_trades', 1),
                timeframe=config_data.get('timeframe', self.config.timeframe if self.config else '5m'),
                stake_amount=config_data.get('stake_amount', 100.0),
                stake_currency=config_data.get('stake_currency', 'USDT'),
                timerange=self.config.timerange if self.config else 'Unknown',
                pair_whitelist=config_data.get('exchange', {}).get('pair_whitelist', []),
                exchange_name=config_data.get('exchange', {}).get('name',
                                                                  self.config.exchange if self.config else 'unknown'),

                # File references and metadata
                config_data=config_data,
                backtest_results={"raw_output": backtest_output},
                backtest_duration=backtest_duration,
                hyperopt_id=hyperopt_id
            )

            # Save to database with session info
            backtest_id = self.db_manager.save_backtest_result(result, self.current_session_info)
            return backtest_id

        except Exception as e:
            self.logger.error(f"Failed to save backtest results to database: {e}")
            return None

    def _notify_progress(self, message: str):
        """Notify progress callback if available."""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            self.logger.info(message)

    def _notify_output(self, output: str):
        """Notify output callback if available."""
        if self.output_callback:
            self.output_callback(output)
        else:
            # Don't log every line to avoid spam
            pass