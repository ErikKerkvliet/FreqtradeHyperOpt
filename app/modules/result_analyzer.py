#!/usr/bin/env python3
"""
Simplified FreqTrade Results Analyzer
CLI tool for analyzing the simplified two-table database structure.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional
from tabulate import tabulate
from results_database_manager import DatabaseManager


class SimplifiedResultsAnalyzer:
    """
    Analyzer for the simplified database schema with just hyperopt_results and backtest_results tables.
    """

    def __init__(self, db_path: str = "freqtrade_results.db"):
        self.db_manager = DatabaseManager(db_path)

    def show_best_hyperopt_strategies(self, limit: int = 10, timeframe: Optional[str] = None,
                                      min_trades: int = 10) -> None:
        """Show the best performing hyperopt strategies."""
        print(f"\n🏆 TOP {limit} HYPEROPT STRATEGIES")
        print("=" * 100)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = """
                    SELECT strategy_name, total_profit_pct, total_trades, win_rate, 
                           avg_profit_pct, max_drawdown_pct, sharpe_ratio, timeframe, 
                           timestamp, run_number, epochs, hyperopt_function
                    FROM hyperopt_results 
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
                    print("No hyperopt results found matching criteria.")
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
                        f"{row['sharpe_ratio']:.2f}",
                        row['timeframe'],
                        row['timestamp'][:10],
                        row['run_number'],
                        row['epochs'],
                        row['hyperopt_function'][:15] + "..." if len(row['hyperopt_function']) > 15 else row[
                            'hyperopt_function']
                    ])

                headers = ['Strategy', 'Profit', 'Trades', 'Win Rate', 'Avg Profit',
                           'Drawdown', 'Sharpe', 'Timeframe', 'Date', 'Run', 'Epochs', 'Loss Func']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

        except Exception as e:
            print(f"Error retrieving best hyperopt strategies: {e}")

    def show_best_backtest_strategies(self, limit: int = 10, timeframe: Optional[str] = None,
                                      min_trades: int = 10) -> None:
        """Show the best performing backtest strategies."""
        print(f"\n🎯 TOP {limit} BACKTEST STRATEGIES")
        print("=" * 100)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = """
                    SELECT b.strategy_name, b.total_profit_pct, b.total_trades, b.win_rate, 
                           b.avg_profit_pct, b.max_drawdown_pct, b.sharpe_ratio, b.timeframe, 
                           b.timestamp, b.avg_trade_duration,
                           h.total_profit_pct as hyperopt_profit,
                           (b.total_profit_pct - COALESCE(h.total_profit_pct, 0)) as reality_gap
                    FROM backtest_results b
                    LEFT JOIN hyperopt_results h ON b.hyperopt_id = h.id
                    WHERE b.status = 'completed' AND b.total_trades >= ?
                """
                params = [min_trades]

                if timeframe:
                    query += " AND b.timeframe = ?"
                    params.append(timeframe)

                query += " ORDER BY b.total_profit_pct DESC LIMIT ?"
                params.append(limit)

                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                results = cursor.fetchall()

                if not results:
                    print("No backtest results found matching criteria.")
                    return

                table_data = []
                for row in results:
                    hyperopt_profit = f"{row['hyperopt_profit']:+.2f}%" if row['hyperopt_profit'] else "N/A"
                    reality_gap = f"{row['reality_gap']:+.2f}%" if row['reality_gap'] else "N/A"

                    table_data.append([
                        row['strategy_name'],
                        f"{row['total_profit_pct']:+.2f}%",
                        row['total_trades'],
                        f"{row['win_rate']:.1f}%",
                        f"{row['avg_profit_pct']:+.2f}%",
                        f"{row['max_drawdown_pct']:-.2f}%",
                        f"{row['sharpe_ratio']:.2f}",
                        row['timeframe'],
                        row['timestamp'][:10],
                        row['avg_trade_duration'] or "N/A",
                        hyperopt_profit,
                        reality_gap
                    ])

                headers = ['Strategy', 'BT Profit', 'Trades', 'Win Rate', 'Avg Profit',
                           'Drawdown', 'Sharpe', 'Timeframe', 'Date', 'Avg Duration',
                           'Opt Profit', 'Gap']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

        except Exception as e:
            print(f"Error retrieving best backtest strategies: {e}")

    def show_reality_gap_analysis(self, strategy_name: Optional[str] = None, limit: int = 20) -> None:
        """Show reality gap analysis between optimization and backtest results."""
        print(f"\n📊 REALITY GAP ANALYSIS")
        if strategy_name:
            print(f"Strategy: {strategy_name}")
        print("=" * 120)

        try:
            comparison_data = self.db_manager.get_optimization_vs_backtest_comparison(strategy_name)

            if not comparison_data:
                print("No comparison data found.")
                return

            # Sort by absolute reality gap (highest gaps first)
            comparison_data.sort(key=lambda x: abs(x['reality_gap_pct'] or 0), reverse=True)
            comparison_data = comparison_data[:limit]

            table_data = []
            for row in comparison_data:
                backtest_status = "✓ Tested" if row['backtest_id'] else "✗ Not Tested"

                table_data.append([
                    row['strategy_name'],
                    f"{row['hyperopt_profit']:+.2f}%",
                    f"{row['backtest_profit']:+.2f}%" if row['backtest_profit'] else "N/A",
                    f"{row['reality_gap_pct']:+.2f}%" if row['reality_gap_pct'] else "N/A",
                    f"{row['hyperopt_trades']}",
                    f"{row['backtest_trades']}" if row['backtest_trades'] else "N/A",
                    f"{row['hyperopt_sharpe']:.2f}",
                    f"{row['backtest_sharpe']:.2f}" if row['backtest_sharpe'] else "N/A",
                    row['hyperopt_timestamp'][:10],
                    row['backtest_timestamp'][:10] if row['backtest_timestamp'] else "N/A",
                    backtest_status
                ])

            headers = ['Strategy', 'Opt Profit', 'BT Profit', 'Gap', 'Opt Trades',
                       'BT Trades', 'Opt Sharpe', 'BT Sharpe', 'Opt Date', 'BT Date', 'Status']

            print(tabulate(table_data, headers=headers, tablefmt='grid'))

            # Summary statistics
            tested_strategies = [row for row in comparison_data if row['backtest_id']]
            if tested_strategies:
                avg_gap = sum(row['reality_gap_pct'] for row in tested_strategies) / len(tested_strategies)
                max_gap = max(row['reality_gap_pct'] for row in tested_strategies)
                min_gap = min(row['reality_gap_pct'] for row in tested_strategies)

                print(f"\n📈 SUMMARY STATISTICS:")
                print(f"Strategies tested: {len(tested_strategies)}/{len(comparison_data)}")
                print(f"Average reality gap: {avg_gap:+.2f}%")
                print(f"Maximum gap (overfitting): {max_gap:+.2f}%")
                print(f"Minimum gap (underfitting): {min_gap:+.2f}%")

                high_gap_count = sum(1 for row in tested_strategies if abs(row['reality_gap_pct']) > 5.0)
                if high_gap_count > 0:
                    print(f"⚠️  Strategies with >5% gap: {high_gap_count} (potential overfitting)")

        except Exception as e:
            print(f"Error analyzing reality gap: {e}")

    def show_strategy_comparison(self, strategy_name: str) -> None:
        """Compare optimization vs backtest results for a specific strategy."""
        print(f"\n🔍 OPTIMIZATION vs BACKTEST: {strategy_name}")
        print("=" * 120)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get all optimizations and their corresponding backtests for this strategy
                cursor = conn.execute("""
                    SELECT 
                        h.id as hyperopt_id, h.run_number, h.timestamp as h_timestamp,
                        h.total_profit_pct as h_profit, h.total_trades as h_trades,
                        h.win_rate as h_win_rate, h.sharpe_ratio as h_sharpe,
                        h.epochs, h.hyperopt_function,

                        b.id as backtest_id, b.timestamp as b_timestamp,
                        b.total_profit_pct as b_profit, b.total_trades as b_trades,
                        b.win_rate as b_win_rate, b.sharpe_ratio as b_sharpe,
                        b.avg_trade_duration,

                        (h.total_profit_pct - COALESCE(b.total_profit_pct, 0)) as gap

                    FROM hyperopt_results h
                    LEFT JOIN backtest_results b ON h.id = b.hyperopt_id
                    WHERE h.strategy_name = ? AND h.status = 'completed'
                    ORDER BY h.total_profit_pct DESC
                """, (strategy_name,))

                results = cursor.fetchall()

                if not results:
                    print(f"No optimization results found for strategy: {strategy_name}")
                    return

                table_data = []
                for row in results:
                    status = "✓ Tested" if row['backtest_id'] else "✗ Pending"

                    table_data.append([
                        row['hyperopt_id'],
                        row['run_number'],
                        f"{row['h_profit']:+.2f}%",
                        f"{row['b_profit']:+.2f}%" if row['b_profit'] else "N/A",
                        f"{row['gap']:+.2f}%" if row['gap'] and row['b_profit'] else "N/A",
                        row['h_trades'],
                        row['b_trades'] or "N/A",
                        f"{row['h_sharpe']:.2f}",
                        f"{row['b_sharpe']:.2f}" if row['b_sharpe'] else "N/A",
                        row['h_timestamp'][:10],
                        row['b_timestamp'][:10] if row['b_timestamp'] else "N/A",
                        row['epochs'],
                        status
                    ])

                headers = ['H_ID', 'Run', 'H_Profit', 'B_Profit', 'Gap', 'H_Trades',
                           'B_Trades', 'H_Sharpe', 'B_Sharpe', 'H_Date', 'B_Date', 'Epochs', 'Status']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

                # Show recommendations
                tested_runs = [row for row in results if row['backtest_id']]
                untested_runs = [row for row in results if not row['backtest_id']]

                print(f"\n💡 RECOMMENDATIONS:")
                print(f"• Total optimizations: {len(results)}")
                print(f"• Tested: {len(tested_runs)}")
                print(f"• Pending backtest: {len(untested_runs)}")

                if untested_runs:
                    best_untested = untested_runs[0]  # Already sorted by profit
                    print(f"• Best untested: ID {best_untested['hyperopt_id']} ({best_untested['h_profit']:+.2f}%)")

                if tested_runs:
                    avg_gap = sum(row['gap'] for row in tested_runs) / len(tested_runs)
                    best_tested = max(tested_runs, key=lambda x: x['b_profit'] or 0)
                    print(f"• Average reality gap: {avg_gap:+.2f}%")
                    print(f"• Best backtest result: {best_tested['b_profit']:+.2f}% (ID {best_tested['hyperopt_id']})")

        except Exception as e:
            print(f"Error comparing optimization vs backtest: {e}")

    def show_strategy_timeline(self, strategy_name: str) -> None:
        """Show performance timeline for a specific strategy across optimizations and backtests."""
        print(f"\n📈 PERFORMANCE TIMELINE: {strategy_name}")
        print("=" * 120)

        try:
            timeline_data = self.db_manager.get_strategy_timeline(strategy_name)

            if not timeline_data:
                print(f"No performance data found for strategy: {strategy_name}")
                return

            table_data = []
            for row in timeline_data:
                type_icon = "🔧" if row['type'] == 'hyperopt' else "🎯"

                table_data.append([
                    f"{type_icon} {row['type'].title()}",
                    row['id'],
                    row['timestamp'][:16],
                    f"{row['total_profit_pct']:+.2f}%",
                    row['total_trades'],
                    f"{row['sharpe_ratio']:.2f}",
                    row['run_number'] or "N/A",
                    row['details'][:30] + "..." if row['details'] and len(row['details']) > 30 else row['details']
                ])

            headers = ['Type', 'ID', 'Timestamp', 'Profit', 'Trades', 'Sharpe', 'Run/Link', 'Details']

            print(tabulate(table_data, headers=headers, tablefmt='grid'))

            # Performance summary
            hyperopt_results = [row for row in timeline_data if row['type'] == 'hyperopt']
            backtest_results = [row for row in timeline_data if row['type'] == 'backtest']

            print(f"\n📊 PERFORMANCE SUMMARY:")
            print(f"• Total optimizations: {len(hyperopt_results)}")
            print(f"• Total backtests: {len(backtest_results)}")

            if hyperopt_results:
                best_opt = max(hyperopt_results, key=lambda x: x['total_profit_pct'])
                avg_opt = sum(row['total_profit_pct'] for row in hyperopt_results) / len(hyperopt_results)
                print(f"• Best optimization: {best_opt['total_profit_pct']:+.2f}% (ID {best_opt['id']})")
                print(f"• Average optimization: {avg_opt:+.2f}%")

            if backtest_results:
                best_bt = max(backtest_results, key=lambda x: x['total_profit_pct'])
                avg_bt = sum(row['total_profit_pct'] for row in backtest_results) / len(backtest_results)
                print(f"• Best backtest: {best_bt['total_profit_pct']:+.2f}% (ID {best_bt['id']})")
                print(f"• Average backtest: {avg_bt:+.2f}%")

                if hyperopt_results:
                    avg_gap = avg_opt - avg_bt
                    print(f"• Average reality gap: {avg_gap:+.2f}%")

        except Exception as e:
            print(f"Error showing performance timeline: {e}")

    def show_database_stats(self) -> None:
        """Show overall database statistics."""
        print(f"\n📊 DATABASE STATISTICS")
        print("=" * 80)

        try:
            stats = self.db_manager.get_stats_summary()

            if not stats:
                print("No statistics available.")
                return

            # Hyperopt stats
            if 'hyperopt' in stats:
                h_stats = stats['hyperopt']
                print(f"🔧 HYPEROPT RESULTS:")
                print(f"• Total runs: {h_stats.get('total_hyperopt', 0)}")
                print(f"• Unique strategies: {h_stats.get('unique_strategies_hyperopt', 0)}")
                print(f"• Average profit: {h_stats.get('avg_profit_hyperopt', 0):+.2f}%")
                print(f"• Best profit: {h_stats.get('max_profit_hyperopt', 0):+.2f}%")
                print(f"• Worst profit: {h_stats.get('min_profit_hyperopt', 0):+.2f}%")

            # Backtest stats
            if 'backtest' in stats:
                b_stats = stats['backtest']
                print(f"\n🎯 BACKTEST RESULTS:")
                print(f"• Total runs: {b_stats.get('total_backtest', 0)}")
                print(f"• Unique strategies: {b_stats.get('unique_strategies_backtest', 0)}")
                print(f"• Linked to hyperopt: {b_stats.get('linked_to_hyperopt', 0)}")
                print(f"• Average profit: {b_stats.get('avg_profit_backtest', 0):+.2f}%")
                print(f"• Best profit: {b_stats.get('max_profit_backtest', 0):+.2f}%")
                print(f"• Worst profit: {b_stats.get('min_profit_backtest', 0):+.2f}%")

            # Reality gap stats
            if 'reality_gap' in stats:
                gap_stats = stats['reality_gap']
                if gap_stats.get('compared_pairs', 0) > 0:
                    print(f"\n📈 REALITY GAP ANALYSIS:")
                    print(f"• Compared pairs: {gap_stats.get('compared_pairs', 0)}")
                    print(f"• Average gap: {gap_stats.get('avg_reality_gap', 0):+.2f}%")

        except Exception as e:
            print(f"Error retrieving database statistics: {e}")

    def export_best_configs(self, result_type: str = "hyperopt", output_dir: str = None, limit: int = 5) -> None:
        """Export configuration files for the best performing strategies."""
        if not output_dir:
            output_dir = f"best_{result_type}_configs"

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"\n💾 EXPORTING TOP {limit} {result_type.upper()} CONFIGURATIONS")
        print("=" * 80)

        try:
            if result_type == "hyperopt":
                best_strategies = self.db_manager.get_best_hyperopt_strategies(limit=limit)
            else:
                best_strategies = self.db_manager.get_best_backtest_strategies(limit=limit)

            if not best_strategies:
                print(f"No {result_type} results found.")
                return

            for i, strategy in enumerate(best_strategies, 1):
                config_file = strategy['config_file_path']
                if config_file and Path(config_file).exists():
                    dest_name = f"{i:02d}_{strategy['strategy_name']}_{result_type}_profit{strategy['total_profit_pct']:+.2f}%_id{strategy['id']}.json"
                    dest_path = output_path / dest_name

                    with open(config_file, 'r') as src, open(dest_path, 'w') as dst:
                        config = json.load(src)
                        json.dump(config, dst, indent=2)

                    print(f"✓ Exported: {dest_name}")
                else:
                    print(f"✗ Config not found for {strategy['strategy_name']} (ID {strategy['id']})")

            print(f"\n{result_type.title()} configurations exported to: {output_path}")

        except Exception as e:
            print(f"Error exporting {result_type} configs: {e}")

    def show_untested_strategies(self, limit: int = 10) -> None:
        """Show hyperopt strategies that haven't been backtested yet."""
        print(f"\n⏳ TOP {limit} UNTESTED HYPEROPT STRATEGIES")
        print("=" * 100)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row

                cursor = conn.execute("""
                    SELECT h.id, h.strategy_name, h.total_profit_pct, h.total_trades, 
                           h.win_rate, h.sharpe_ratio, h.timestamp, h.run_number
                    FROM hyperopt_results h
                    LEFT JOIN backtest_results b ON h.id = b.hyperopt_id
                    WHERE h.status = 'completed' AND b.id IS NULL
                    ORDER BY h.total_profit_pct DESC
                    LIMIT ?
                """, (limit,))

                results = cursor.fetchall()

                if not results:
                    print("All hyperopt strategies have been backtested!")
                    return

                table_data = []
                for row in results:
                    table_data.append([
                        row['id'],
                        row['strategy_name'],
                        f"{row['total_profit_pct']:+.2f}%",
                        row['total_trades'],
                        f"{row['win_rate']:.1f}%",
                        f"{row['sharpe_ratio']:.2f}",
                        row['timestamp'][:10],
                        row['run_number']
                    ])

                headers = ['ID', 'Strategy', 'Profit', 'Trades', 'Win Rate', 'Sharpe', 'Date', 'Run']
                print(tabulate(table_data, headers=headers, tablefmt='grid'))

                print(f"\n💡 RECOMMENDATION:")
                print(f"Run backtests for these strategies using:")
                print(f"python backtest_runner.py from-hyperopt <ID>")

        except Exception as e:
            print(f"Error showing untested strategies: {e}")

    def generate_strategy_report(self, strategy_name: str) -> None:
        """Generate a comprehensive report for a specific strategy."""
        print(f"\n📋 COMPREHENSIVE STRATEGY REPORT: {strategy_name}")
        print("=" * 120)

        # Show strategy comparison
        self.show_strategy_comparison(strategy_name)

        # Show performance timeline
        print("\n" + "─" * 120)
        self.show_strategy_timeline(strategy_name)

        # Show best backtest details if available
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM backtest_results 
                    WHERE strategy_name = ? AND status = 'completed'
                    ORDER BY total_profit_pct DESC LIMIT 1
                """, (strategy_name,))

                result = cursor.fetchone()
                if result:
                    print("\n" + "─" * 120)
                    print(f"🎯 BEST BACKTEST DETAILS (ID {result['id']}):")
                    print(f"• Profit: {result['total_profit_pct']:+.2f}%")
                    print(f"• Total trades: {result['total_trades']}")
                    print(f"• Win rate: {result['win_rate']:.1f}%")
                    print(f"• Max drawdown: {result['max_drawdown_pct']:-.2f}%")
                    print(f"• Sharpe ratio: {result['sharpe_ratio']:.2f}")
                    print(f"• Average trade duration: {result['avg_trade_duration']}")
                    print(f"• Best trade: {result['best_trade_pct']:+.2f}%")
                    print(f"• Worst trade: {result['worst_trade_pct']:+.2f}%")

        except Exception as e:
            print(f"Error generating comprehensive report: {e}")

    def migrate_old_database(self) -> None:
        """Migrate from old database schema to simplified schema."""
        print("\n🔄 DATABASE MIGRATION")
        print("=" * 50)

        try:
            success = self.db_manager.migrate_from_old_schema()
            if success:
                print("✓ Migration completed successfully!")

                # Show what was migrated
                stats = self.db_manager.get_stats_summary()
                if stats:
                    print(f"\nMigration results:")
                    if 'hyperopt' in stats:
                        print(f"• Hyperopt records: {stats['hyperopt'].get('total_hyperopt', 0)}")
                    if 'backtest' in stats:
                        print(f"• Backtest records: {stats['backtest'].get('total_backtest', 0)}")

                print(f"\n💡 Consider cleaning up old tables with:")
                print(f"python analyzer.py cleanup-old-tables --confirm")
            else:
                print("✗ Migration failed. Check logs for details.")

        except Exception as e:
            print(f"Migration error: {e}")

    def cleanup_old_tables(self, confirm: bool = False) -> None:
        """Remove old database tables after migration."""
        if not confirm:
            print("\n⚠️  WARNING: This will permanently delete old database tables!")
            print("Use --confirm flag if you're sure you want to proceed.")
            return

        print("\n🗑️  CLEANING UP OLD TABLES")
        print("=" * 40)

        try:
            success = self.db_manager.cleanup_old_tables(confirm=True)
            if success:
                print("✓ Old tables cleaned up successfully!")
            else:
                print("✗ Cleanup failed. Check logs for details.")
        except Exception as e:
            print(f"Cleanup error: {e}")


def main():
    """Main CLI interface for the simplified analyzer."""
    parser = argparse.ArgumentParser(description="Simplified FreqTrade Results Analyzer")
    parser.add_argument("--db", default="freqtrade_results.db", help="Database file path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Best hyperopt strategies command
    best_hyperopt_parser = subparsers.add_parser("best-hyperopt", help="Show best hyperopt strategies")
    best_hyperopt_parser.add_argument("--limit", type=int, default=10, help="Number of results to show")
    best_hyperopt_parser.add_argument("--timeframe", help="Filter by timeframe")
    best_hyperopt_parser.add_argument("--min-trades", type=int, default=10, help="Minimum number of trades")

    # Best backtest strategies command
    best_backtest_parser = subparsers.add_parser("best-backtest", help="Show best backtest strategies")
    best_backtest_parser.add_argument("--limit", type=int, default=10, help="Number of results to show")
    best_backtest_parser.add_argument("--timeframe", help="Filter by timeframe")
    best_backtest_parser.add_argument("--min-trades", type=int, default=10, help="Minimum number of trades")

    # Reality gap analysis command
    gap_parser = subparsers.add_parser("gap", help="Show reality gap analysis")
    gap_parser.add_argument("--strategy", help="Filter by strategy name")
    gap_parser.add_argument("--limit", type=int, default=20, help="Number of results to show")

    # Strategy comparison command
    vs_parser = subparsers.add_parser("vs", help="Compare optimization vs backtest for strategy")
    vs_parser.add_argument("strategy", help="Strategy name to analyze")

    # Performance timeline command
    timeline_parser = subparsers.add_parser("timeline", help="Show performance timeline for strategy")
    timeline_parser.add_argument("strategy", help="Strategy name")

    # Database stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # Untested strategies command
    untested_parser = subparsers.add_parser("untested", help="Show untested hyperopt strategies")
    untested_parser.add_argument("--limit", type=int, default=10, help="Number of results to show")

    # Export configs command
    export_parser = subparsers.add_parser("export", help="Export best configurations")
    export_parser.add_argument("type", choices=["hyperopt", "backtest"], help="Type of results to export")
    export_parser.add_argument("--output", help="Output directory")
    export_parser.add_argument("--limit", type=int, default=5, help="Number of configs to export")

    # Comprehensive report command
    report_parser = subparsers.add_parser("report", help="Generate comprehensive strategy report")
    report_parser.add_argument("strategy", help="Strategy name")

    # Migration command
    subparsers.add_parser("migrate", help="Migrate from old database schema")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup-old-tables", help="Remove old database tables")
    cleanup_parser.add_argument("--confirm", action="store_true", help="Confirm cleanup operation")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    analyzer = SimplifiedResultsAnalyzer(args.db)

    try:
        if args.command == "best-hyperopt":
            analyzer.show_best_hyperopt_strategies(args.limit, args.timeframe, args.min_trades)
        elif args.command == "best-backtest":
            analyzer.show_best_backtest_strategies(args.limit, args.timeframe, args.min_trades)
        elif args.command == "gap":
            analyzer.show_reality_gap_analysis(args.strategy, args.limit)
        elif args.command == "vs":
            analyzer.show_strategy_comparison(args.strategy)
        elif args.command == "timeline":
            analyzer.show_strategy_timeline(args.strategy)
        elif args.command == "stats":
            analyzer.show_database_stats()
        elif args.command == "untested":
            analyzer.show_untested_strategies(args.limit)
        elif args.command == "export":
            analyzer.export_best_configs(args.type, args.output, args.limit)
        elif args.command == "report":
            analyzer.generate_strategy_report(args.strategy)
        elif args.command == "migrate":
            analyzer.migrate_old_database()
        elif args.command == "cleanup-old-tables":
            analyzer.cleanup_old_tables(args.confirm)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()