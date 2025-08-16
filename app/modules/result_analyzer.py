#!/usr/bin/env python3
"""
FreqTrade Results Analyzer
Command-line utility for querying and analyzing optimization results.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import List, Optional
from tabulate import tabulate
from .results_database_manager import ResultsDatabaseManager


class ResultsAnalyzer:
    """
    Utility class for analyzing FreqTrade optimization results.
    """

    def __init__(self, db_path: str = "freqtrade_results.db"):
        self.db_manager = ResultsDatabaseManager(db_path)

    def show_best_strategies(self, limit: int = 10, timeframe: Optional[str] = None,
                             min_trades: int = 10) -> None:
        """Show the best performing strategies."""
        print(f"\n🏆 TOP {limit} STRATEGIES")
        print("=" * 80)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = """
                    SELECT strategy_name, total_profit_pct, total_trades, win_rate, 
                           avg_profit_pct, max_drawdown_pct, timeframe, 
                           optimization_timestamp, run_number
                    FROM strategy_optimizations 
                    WHERE status = 'completed' AND total_trades >= ?
                """
                params = [min_trades]

                if timeframe:
                    query += " AND timeframe = ?"
                    params.append(timeframe)

                query += " ORDER BY total_profit_pct DESC LIMIT ?"
                params.append(limit)

                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                results = cursor.fetchall()

                if not results:
                    print("No results found matching criteria.")
                    return

                table_data = []
                for row in results:
                    table_data.append([
                        row['strategy_name'],
                        f"{row['total_profit_pct']:+.2f}%",
                        row['total_trades'],
                        f"{row['win_rate']:.1f}%",
                        f"{row['avg_profit_pct']:+.2f}%",
                        f"{row['max_drawdown_pct']:-.2f}%",
                        row['timeframe'],
                        row['optimization_timestamp'][:10],  # Date only
                        row['run_number']
                    ])

                headers = ['Strategy', 'Total Profit', 'Trades', 'Win Rate',
                           'Avg Profit', 'Max Drawdown', 'Timeframe', 'Date', 'Run']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

        except Exception as e:
            print(f"Error retrieving best strategies: {e}")

    def show_strategy_comparison(self, strategy_names: List[str]) -> None:
        """Compare multiple strategies."""
        print(f"\n📊 STRATEGY COMPARISON")
        print("=" * 80)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                placeholders = ','.join(['?'] * len(strategy_names))
                query = f"""
                    SELECT strategy_name, 
                           COUNT(*) as total_runs,
                           AVG(total_profit_pct) as avg_profit,
                           MAX(total_profit_pct) as best_profit,
                           MIN(total_profit_pct) as worst_profit,
                           AVG(total_trades) as avg_trades,
                           AVG(win_rate) as avg_win_rate,
                           AVG(max_drawdown_pct) as avg_drawdown
                    FROM strategy_optimizations 
                    WHERE strategy_name IN ({placeholders}) AND status = 'completed'
                    GROUP BY strategy_name
                    ORDER BY avg_profit DESC
                """

                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, strategy_names)
                results = cursor.fetchall()

                if not results:
                    print("No results found for specified strategies.")
                    return

                table_data = []
                for row in results:
                    table_data.append([
                        row['strategy_name'],
                        row['total_runs'],
                        f"{row['avg_profit']:+.2f}%",
                        f"{row['best_profit']:+.2f}%",
                        f"{row['worst_profit']:+.2f}%",
                        f"{row['avg_trades']:.0f}",
                        f"{row['avg_win_rate']:.1f}%",
                        f"{row['avg_drawdown']:-.2f}%"
                    ])

                headers = ['Strategy', 'Runs', 'Avg Profit', 'Best', 'Worst',
                           'Avg Trades', 'Avg Win Rate', 'Avg Drawdown']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

        except Exception as e:
            print(f"Error comparing strategies: {e}")

    def show_timeframe_analysis(self) -> None:
        """Analyze performance by timeframe."""
        print(f"\n⏰ TIMEFRAME ANALYSIS")
        print("=" * 80)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = """
                    SELECT timeframe,
                           COUNT(*) as total_optimizations,
                           COUNT(DISTINCT strategy_name) as unique_strategies,
                           AVG(total_profit_pct) as avg_profit,
                           MAX(total_profit_pct) as best_profit,
                           AVG(total_trades) as avg_trades,
                           AVG(win_rate) as avg_win_rate
                    FROM strategy_optimizations 
                    WHERE status = 'completed'
                    GROUP BY timeframe
                    ORDER BY avg_profit DESC
                """

                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query)
                results = cursor.fetchall()

                if not results:
                    print("No results found.")
                    return

                table_data = []
                for row in results:
                    table_data.append([
                        row['timeframe'],
                        row['total_optimizations'],
                        row['unique_strategies'],
                        f"{row['avg_profit']:+.2f}%",
                        f"{row['best_profit']:+.2f}%",
                        f"{row['avg_trades']:.0f}",
                        f"{row['avg_win_rate']:.1f}%"
                    ])

                headers = ['Timeframe', 'Total Opts', 'Strategies', 'Avg Profit',
                           'Best Profit', 'Avg Trades', 'Avg Win Rate']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

        except Exception as e:
            print(f"Error analyzing timeframes: {e}")

    def show_config_details(self, optimization_id: int) -> None:
        """Show detailed configuration for a specific optimization."""
        print(f"\n⚙️  CONFIGURATION DETAILS - ID {optimization_id}")
        print("=" * 80)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM strategy_optimizations WHERE id = ?
                """, (optimization_id,))

                result = cursor.fetchone()
                if not result:
                    print(f"No optimization found with ID {optimization_id}")
                    return

                # Display basic info
                print(f"Strategy: {result['strategy_name']}")
                print(f"Profit: {result['total_profit_pct']:+.2f}%")
                print(f"Trades: {result['total_trades']}")
                print(f"Win Rate: {result['win_rate']:.1f}%")
                print(f"Timeframe: {result['timeframe']}")
                print(f"Date: {result['optimization_timestamp']}")
                print()

                # Load and display config file
                if result['config_file_path'] and Path(result['config_file_path']).exists():
                    with open(result['config_file_path'], 'r') as f:
                        config = json.load(f)

                    print("📄 Configuration:")
                    print(json.dumps(config, indent=2))
                else:
                    print("⚠️  Config file not found")

        except Exception as e:
            print(f"Error retrieving config details: {e}")

    def show_hyperopt_json(self, optimization_id: int) -> None:
        """Show the raw hyperopt JSON result for a specific optimization."""
        print(f"\n📊 HYPEROPT JSON RESULT - ID {optimization_id}")
        print("=" * 80)

        try:
            hyperopt_data = self.db_manager.get_hyperopt_json_result(optimization_id)

            if hyperopt_data:
                print(json.dumps(hyperopt_data, indent=2))
            else:
                print(f"No hyperopt JSON result found for optimization ID {optimization_id}")

        except Exception as e:
            print(f"Error retrieving hyperopt JSON result: {e}")

    def show_session_hyperopt_results(self, session_id: int) -> None:
        """Show all hyperopt results for a specific session."""
        print(f"\n📊 SESSION {session_id} HYPEROPT RESULTS")
        print("=" * 80)

        try:
            results = self.db_manager.get_session_hyperopt_results(session_id)

            if not results:
                print(f"No hyperopt results found for session {session_id}")
                return

            for result in results:
                print(f"\n--- {result['strategy_name']} (Profit: {result['total_profit_pct']:+.2f}%) ---")
                print(f"Optimization ID: {result['optimization_id']}")
                print(f"Trades: {result['total_trades']}")
                print(f"Created: {result['created_timestamp']}")
                print("\nHyperopt JSON Data:")
                print(json.dumps(result['hyperopt_json_data'], indent=2))
                print("-" * 60)

        except Exception as e:
            print(f"Error retrieving session hyperopt results: {e}")

    def show_sessions(self, limit: int = 10) -> None:
        """Show recent optimization sessions."""
        print(f"\n📅 RECENT SESSIONS")
        print("=" * 80)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT id, session_timestamp, total_strategies, successful_strategies,
                           failed_strategies, session_duration_seconds, timeframe, epochs
                    FROM optimization_sessions 
                    ORDER BY session_timestamp DESC
                    LIMIT ?
                """, (limit,))

                results = cursor.fetchall()

                if not results:
                    print("No sessions found.")
                    return

                table_data = []
                for row in results:
                    duration_min = row['session_duration_seconds'] // 60 if row['session_duration_seconds'] else 0
                    success_rate = (row['successful_strategies'] / row['total_strategies'] * 100) if row[
                        'total_strategies'] else 0

                    table_data.append([
                        row['id'],
                        row['session_timestamp'][:16],  # Remove seconds
                        row['total_strategies'] or 0,
                        row['successful_strategies'] or 0,
                        row['failed_strategies'] or 0,
                        f"{success_rate:.0f}%",
                        f"{duration_min}min",
                        row['timeframe'],
                        row['epochs']
                    ])

                headers = ['ID', 'Timestamp', 'Total', 'Success', 'Failed',
                           'Success Rate', 'Duration', 'Timeframe', 'Epochs']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

        except Exception as e:
            print(f"Error retrieving sessions: {e}")

    def export_best_configs(self, output_dir: str = "best_configs", limit: int = 5) -> None:
        """Export configuration files for the best performing strategies."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"\n💾 EXPORTING TOP {limit} CONFIGURATIONS")
        print("=" * 80)

        try:
            best_strategies = self.db_manager.get_best_strategies(limit=limit)

            for i, strategy in enumerate(best_strategies, 1):
                config_file = strategy['config_file_path']
                if config_file and Path(config_file).exists():
                    # Copy config file with descriptive name
                    dest_name = f"{i:02d}_{strategy['strategy_name']}_profit{strategy['total_profit_pct']:+.2f}%.json"
                    dest_path = output_path / dest_name

                    with open(config_file, 'r') as src, open(dest_path, 'w') as dst:
                        config = json.load(src)
                        json.dump(config, dst, indent=2)

                    print(f"✓ Exported: {dest_name}")
                else:
                    print(f"✗ Config not found for {strategy['strategy_name']}")

            print(f"\nConfigurations exported to: {output_path}")

        except Exception as e:
            print(f"Error exporting configs: {e}")

    def export_hyperopt_results(self, session_id: int, output_dir: str = "hyperopt_exports") -> None:
        """Export all hyperopt JSON results for a session."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"\n💾 EXPORTING HYPEROPT RESULTS FOR SESSION {session_id}")
        print("=" * 80)

        try:
            results = self.db_manager.get_session_hyperopt_results(session_id)

            if not results:
                print(f"No hyperopt results found for session {session_id}")
                return

            for result in results:
                # Create filename with strategy name and profit
                filename = f"session{session_id}_{result['strategy_name']}_opt{result['optimization_id']}_profit{result['total_profit_pct']:+.2f}%.json"
                file_path = output_path / filename

                # Save the hyperopt JSON data
                with open(file_path, 'w') as f:
                    json.dump(result['hyperopt_json_data'], f, indent=2)

                print(f"✓ Exported: {filename}")

            print(f"\nHyperopt results exported to: {output_path}")

        except Exception as e:
            print(f"Error exporting hyperopt results: {e}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="FreqTrade Results Analyzer")
    parser.add_argument("--db", default="freqtrade_results.db", help="Database file path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Best strategies command
    best_parser = subparsers.add_parser("best", help="Show best performing strategies")
    best_parser.add_argument("--limit", type=int, default=10, help="Number of results to show")
    best_parser.add_argument("--timeframe", help="Filter by timeframe")
    best_parser.add_argument("--min-trades", type=int, default=10, help="Minimum number of trades")

    # Compare strategies command
    compare_parser = subparsers.add_parser("compare", help="Compare multiple strategies")
    compare_parser.add_argument("strategies", nargs="+", help="Strategy names to compare")

    # Timeframe analysis command
    subparsers.add_parser("timeframes", help="Analyze performance by timeframe")

    # Show config command
    config_parser = subparsers.add_parser("config", help="Show configuration details")
    config_parser.add_argument("id", type=int, help="Optimization ID")

    # Show hyperopt JSON command
    hyperopt_parser = subparsers.add_parser("hyperopt", help="Show hyperopt JSON result")
    hyperopt_parser.add_argument("id", type=int, help="Optimization ID")

    # Show session hyperopt results command
    session_hyperopt_parser = subparsers.add_parser("session-hyperopt", help="Show all hyperopt results for a session")
    session_hyperopt_parser.add_argument("session_id", type=int, help="Session ID")

    # Sessions command
    sessions_parser = subparsers.add_parser("sessions", help="Show recent sessions")
    sessions_parser.add_argument("--limit", type=int, default=10, help="Number of sessions to show")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export best configurations")
    export_parser.add_argument("--output", default="best_configs", help="Output directory")
    export_parser.add_argument("--limit", type=int, default=5, help="Number of configs to export")

    # Export hyperopt results command
    export_hyperopt_parser = subparsers.add_parser("export-hyperopt", help="Export hyperopt results for a session")
    export_hyperopt_parser.add_argument("session_id", type=int, help="Session ID")
    export_hyperopt_parser.add_argument("--output", default="hyperopt_exports", help="Output directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    analyzer = ResultsAnalyzer(args.db)

    try:
        if args.command == "best":
            analyzer.show_best_strategies(args.limit, args.timeframe, args.min_trades)
        elif args.command == "compare":
            analyzer.show_strategy_comparison(args.strategies)
        elif args.command == "timeframes":
            analyzer.show_timeframe_analysis()
        elif args.command == "config":
            analyzer.show_config_details(args.id)
        elif args.command == "hyperopt":
            analyzer.show_hyperopt_json(args.id)
        elif args.command == "session-hyperopt":
            analyzer.show_session_hyperopt_results(args.session_id)
        elif args.command == "sessions":
            analyzer.show_sessions(args.limit)
        elif args.command == "export":
            analyzer.export_best_configs(args.output, args.limit)
        elif args.command == "export-hyperopt":
            analyzer.export_hyperopt_results(args.session_id, args.output)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()