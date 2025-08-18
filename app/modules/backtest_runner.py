#!/usr/bin/env python3
"""
Simplified Backtest Runner for FreqTrade
CLI tool for running backtests on hyperopt results using the simplified database.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from freqtrade_executor import FreqTradeExecutor
from optimization_config import OptimizationConfig
from results_database_manager import DatabaseManager
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta


class SimplifiedBacktestRunner:
    """
    Simplified backtest runner that works with the two-table database structure.
    """

    def __init__(self):
        """Initialize the backtest runner."""
        self.logger = self._setup_logger()
        self.db_manager = DatabaseManager()
        self.executor: Optional[FreqTradeExecutor] = None
        self.config: Optional[OptimizationConfig] = None

        # Load configuration
        self._load_config()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the backtest runner."""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s'
        )
        return logging.getLogger(__name__)

    def _load_config(self) -> bool:
        """Load configuration from environment variables."""
        try:
            load_dotenv()

            # Calculate timerange
            current_date = datetime.now()
            days = int(os.getenv('HISTORICAL_DATA_IN_DAYS', '365'))
            start_date = current_date - timedelta(days=days)
            timerange = f"{start_date.strftime('%Y%m%d')}-"

            # Read configuration
            freqtrade_path = os.getenv('FREQTRADE_PATH')
            exchange = os.getenv('EXCHANGE')
            timeframe = os.getenv('TIMEFRAME')
            pairs_str = os.getenv('PAIRS')
            pair_data_exchange = os.getenv('PAIR_DATA_EXCHANGE')
            hyperfunction = os.getenv('HYPERFUNCTION')

            if not freqtrade_path:
                self.logger.error("FREQTRADE_PATH not set in environment")
                return False

            # Parse pairs
            pairs = [pair.strip() for pair in pairs_str.split(',') if pair.strip()] if pairs_str else []

            # Create configuration
            self.config = OptimizationConfig(
                freqtrade_path=freqtrade_path,
                exchange=exchange or 'binance',
                timeframe=timeframe or '5m',
                timerange=timerange,
                pairs=pairs,
                pair_data_exchange=pair_data_exchange or exchange or 'binance',
                hyperfunction=hyperfunction or 'SharpeHyperOptLoss'
            )

            # Initialize executor
            self.executor = FreqTradeExecutor(self.config, self.logger)

            return True

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False

    def run_single_backtest(self, strategy_name: str, config_file: str, timerange: str = None) -> bool:
        """
        Run a single backtest.

        Args:
            strategy_name: Name of the strategy
            config_file: Path to config file
            timerange: Optional timerange override

        Returns:
            True if successful
        """
        try:
            if not self.executor:
                self.logger.error("Executor not initialized")
                return False

            self.logger.info(f"Running backtest for {strategy_name}")

            # Start backtest session
            session_name = f"BacktestSession_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.executor.start_session(session_name)

            result = self.executor.run_backtest(
                strategy_name=strategy_name,
                config_file=config_file,
                timerange=timerange
            )

            if result.success:
                self.logger.info(f"✓ Backtest completed successfully - DB record {result.backtest_id}")
                return True
            else:
                self.logger.error(f"✗ Backtest failed: {result.error_message}")
                return False

        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            return False

    def run_backtest_from_hyperopt(self, hyperopt_id: int) -> bool:
        """
        Run backtest using configuration from a hyperopt result.

        Args:
            hyperopt_id: ID of the hyperopt result

        Returns:
            True if successful
        """
        try:
            if not self.executor:
                self.logger.error("Executor not initialized")
                return False

            self.logger.info(f"Running backtest from hyperopt ID {hyperopt_id}")

            # Start backtest session
            session_name = f"BacktestFromHyperopt_{hyperopt_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.executor.start_session(session_name)

            result = self.executor.run_strategy_backtest_from_hyperopt(hyperopt_id)

            if result.success:
                self.logger.info(f"✓ Backtest completed successfully - DB record {result.backtest_id}")
                return True
            else:
                self.logger.error(f"✗ Backtest failed: {result.error_message}")
                return False

        except Exception as e:
            self.logger.error(f"Error running backtest from hyperopt: {e}")
            return False

    def batch_backtest_best_hyperopt(self, limit: int = 5, timeframe: str = None) -> None:
        """
        Run backtests for the best hyperopt strategies.

        Args:
            limit: Number of top strategies to backtest
            timeframe: Optional timeframe filter
        """
        try:
            if not self.executor:
                self.logger.error("Executor not initialized")
                return

            self.logger.info(f"Starting batch backtest for top {limit} hyperopt strategies")

            # Start batch session
            session_name = f"BatchBacktest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.executor.start_session(session_name)

            results = self.executor.batch_backtest_from_best_hyperopt(limit=limit, timeframe=timeframe)

            if results:
                successful = sum(1 for r in results if r.success)
                self.logger.info(f"Batch backtest completed: {successful}/{len(results)} successful")

                # Show summary
                print(f"\n📊 BATCH BACKTEST SUMMARY")
                print("=" * 50)
                for i, result in enumerate(results, 1):
                    status = "✓" if result.success else "✗"
                    if hasattr(result, 'backtest_id') and result.backtest_id:
                        print(f"{i}. {status} Backtest completed - DB record {result.backtest_id}")
                    else:
                        print(f"{i}. {status} Backtest failed: {result.error_message}")
            else:
                self.logger.warning("No strategies found for batch backtesting")

        except Exception as e:
            self.logger.error(f"Error during batch backtest: {e}")

    def list_untested_hyperopt_results(self, limit: int = 10) -> None:
        """List hyperopt results that haven't been backtested yet."""
        try:
            print(f"\n⏳ TOP {limit} UNTESTED HYPEROPT STRATEGIES")
            print("=" * 80)

            # Get untested strategies from database
            best_strategies = self.db_manager.get_best_hyperopt_strategies(limit=100)  # Get more to filter

            # Filter for untested ones
            untested = []
            for strategy in best_strategies:
                # Check if this hyperopt has been backtested
                comparison_data = self.db_manager.get_optimization_vs_backtest_comparison(strategy['strategy_name'])
                is_tested = any(row['hyperopt_id'] == strategy['id'] and row['backtest_id'] for row in comparison_data)

                if not is_tested:
                    untested.append(strategy)

                if len(untested) >= limit:
                    break

            if not untested:
                print("All hyperopt strategies have been backtested!")
                return

            for i, strategy in enumerate(untested, 1):
                print(f"{i:2d}. ID {strategy['id']:3d} | {strategy['strategy_name']:20s} | "
                      f"{strategy['total_profit_pct']:+6.2f}% | {strategy['total_trades']:3d} trades | "
                      f"{strategy['timestamp'][:10]}")

            print(f"\n💡 To backtest a strategy, use:")
            print(f"python backtest_runner.py from-hyperopt <ID>")

        except Exception as e:
            self.logger.error(f"Error listing untested strategies: {e}")

    def show_backtest_opportunities(self) -> None:
        """Show opportunities for backtesting."""
        try:
            print(f"\n🔍 BACKTEST OPPORTUNITIES")
            print("=" * 60)

            # Get statistics
            stats = self.db_manager.get_stats_summary()

            if stats:
                hyperopt_count = stats.get('hyperopt', {}).get('total_hyperopt', 0)
                backtest_count = stats.get('backtest', {}).get('total_backtest', 0)
                linked_count = stats.get('backtest', {}).get('linked_to_hyperopt', 0)

                print(f"📊 Database Statistics:")
                print(f"• Total hyperopt runs: {hyperopt_count}")
                print(f"• Total backtest runs: {backtest_count}")
                print(f"• Linked backtests: {linked_count}")
                print(f"• Untested hyperopt runs: {hyperopt_count - linked_count}")

                if hyperopt_count > linked_count:
                    print(f"\n💡 Recommended Actions:")
                    print(f"1. Run batch backtest: python backtest_runner.py batch --limit 5")
                    print(f"2. Test specific strategy: python backtest_runner.py from-hyperopt <ID>")
                    print(f"3. List untested: python backtest_runner.py list-untested")
                else:
                    print(f"\n✓ All hyperopt strategies have been backtested!")

        except Exception as e:
            self.logger.error(f"Error showing backtest opportunities: {e}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Simplified FreqTrade Backtest Runner")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Single backtest command
    single_parser = subparsers.add_parser("single", help="Run single backtest")
    single_parser.add_argument("strategy", help="Strategy name")
    single_parser.add_argument("config", help="Config file path")
    single_parser.add_argument("--timerange", help="Timerange override")

    # Backtest from hyperopt command
    from_hyperopt_parser = subparsers.add_parser("from-hyperopt", help="Run backtest from hyperopt result")
    from_hyperopt_parser.add_argument("hyperopt_id", type=int, help="Hyperopt ID")

    # Batch backtest command
    batch_parser = subparsers.add_parser("batch", help="Batch backtest best hyperopt strategies")
    batch_parser.add_argument("--limit", type=int, default=5, help="Number of strategies to backtest")
    batch_parser.add_argument("--timeframe", help="Filter by timeframe")

    # List untested command
    list_parser = subparsers.add_parser("list-untested", help="List untested hyperopt strategies")
    list_parser.add_argument("--limit", type=int, default=10, help="Number of results to show")

    # Show opportunities command
    subparsers.add_parser("opportunities", help="Show backtest opportunities")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    runner = SimplifiedBacktestRunner()

    try:
        if args.command == "single":
            success = runner.run_single_backtest(args.strategy, args.config, args.timerange)
            sys.exit(0 if success else 1)

        elif args.command == "from-hyperopt":
            success = runner.run_backtest_from_hyperopt(args.hyperopt_id)
            sys.exit(0 if success else 1)

        elif args.command == "batch":
            runner.batch_backtest_best_hyperopt(args.limit, args.timeframe)

        elif args.command == "list-untested":
            runner.list_untested_hyperopt_results(args.limit)

        elif args.command == "opportunities":
            runner.show_backtest_opportunities()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()