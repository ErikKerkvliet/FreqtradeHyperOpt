#!/usr/bin/env python3
"""
Enhanced FreqTrade Results Analyzer
CLI tool for analyzing the new separated hyperopt and backtest results.
"""

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional
from tabulate import tabulate
from results_database_manager import ResultsDatabaseManager


class EnhancedResultsAnalyzer:
    """
    Enhanced analyzer for the new database schema with separate hyperopt and backtest tables.
    """

    def __init__(self, db_path: str = "freqtrade_results.db"):
        self.db_manager = ResultsDatabaseManager(db_path)

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
                           hyperopt_timestamp, run_number, epochs, hyperopt_function
                    FROM hyperopt_runs 
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
                        row['hyperopt_timestamp'][:10],
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
                           b.backtest_timestamp, b.avg_trade_duration,
                           h.total_profit_pct as hyperopt_profit,
                           (b.total_profit_pct - COALESCE(h.total_profit_pct, 0)) as reality_gap
                    FROM backtest_runs b
                    LEFT JOIN hyperopt_runs h ON b.hyperopt_id = h.id
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
                        row['backtest_timestamp'][:10],
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

    def show_optimization_vs_backtest_comparison(self, strategy_name: str) -> None:
        """Compare optimization vs backtest results for a specific strategy."""
        print(f"\n🔍 OPTIMIZATION vs BACKTEST: {strategy_name}")
        print("=" * 120)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get all optimizations and their corresponding backtests for this strategy
                cursor = conn.execute("""
                    SELECT 
                        h.id as hyperopt_id, h.run_number, h.hyperopt_timestamp,
                        h.total_profit_pct as h_profit, h.total_trades as h_trades,
                        h.win_rate as h_win_rate, h.sharpe_ratio as h_sharpe,
                        h.epochs, h.hyperopt_function,

                        b.id as backtest_id, b.backtest_timestamp,
                        b.total_profit_pct as b_profit, b.total_trades as b_trades,
                        b.win_rate as b_win_rate, b.sharpe_ratio as b_sharpe,
                        b.avg_trade_duration,

                        (h.total_profit_pct - COALESCE(b.total_profit_pct, 0)) as gap

                    FROM hyperopt_runs h
                    LEFT JOIN backtest_runs b ON h.id = b.hyperopt_id
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
                        row['hyperopt_timestamp'][:10],
                        row['backtest_timestamp'][:10] if row['backtest_timestamp'] else "N/A",
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

    def show_backtest_trade_details(self, backtest_id: int) -> None:
        """Show detailed trade analysis for a specific backtest."""
        print(f"\n📋 TRADE DETAILS - Backtest ID {backtest_id}")
        print("=" * 80)

        try:
            trade_analysis = self.db_manager.get_backtest_trade_analysis(backtest_id)

            if not trade_analysis:
                print(f"No trade data found for backtest ID {backtest_id}")
                return

            # Trade statistics
            stats = trade_analysis['trade_stats']
            print("📊 TRADE STATISTICS:")
            print(f"Total trades: {stats['total_trades']}")
            print(f"Average profit: {stats['avg_profit_pct']:.2f}%")
            print(f"Total profit: {stats['total_profit_abs']:.8f}")
            print(f"Average duration: {stats['avg_duration_minutes']:.1f} minutes")
            print(f"Best trade: {stats['best_trade_pct']:.2f}%")
            print(f"Worst trade: {stats['worst_trade_pct']:.2f}%")

            # Trades by pair
            if trade_analysis['trades_by_pair']:
                print(f"\n💱 PERFORMANCE BY PAIR:")
                pair_data = []
                for pair_info in trade_analysis['trades_by_pair']:
                    pair_data.append([
                        pair_info['pair'],
                        pair_info['trade_count'],
                        f"{pair_info['avg_profit_pct']:.2f}%",
                        f"{pair_info['total_profit']:.8f}"
                    ])

                print(tabulate(pair_data, headers=['Pair', 'Trades', 'Avg Profit', 'Total Profit'], tablefmt='grid'))

            # Exit reasons
            if trade_analysis['exit_reasons']:
                print(f"\n🚪 EXIT REASONS:")
                exit_data = []
                for exit_info in trade_analysis['exit_reasons']:
                    exit_data.append([
                        exit_info['exit_reason'],
                        exit_info['count'],
                        f"{exit_info['avg_profit_pct']:.2f}%"
                    ])

                print(tabulate(exit_data, headers=['Exit Reason', 'Count', 'Avg Profit'], tablefmt='grid'))

        except Exception as e:
            print(f"Error retrieving trade details: {e}")

    def show_sessions(self, session_type: str = "both", limit: int = 10) -> None:
        """Show recent optimization and/or backtest sessions."""
        if session_type in ["both", "optimization"]:
            print(f"\n📅 RECENT OPTIMIZATION SESSIONS")
            print("=" * 100)
            self._show_optimization_sessions(limit)

        if session_type in ["both", "backtest"]:
            print(f"\n📅 RECENT BACKTEST SESSIONS")
            print("=" * 100)
            self._show_backtest_sessions(limit)

    def _show_optimization_sessions(self, limit: int) -> None:
        """Show optimization sessions."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT id, session_timestamp, total_strategies, successful_strategies,
                           failed_strategies, session_duration_seconds, timeframe, epochs,
                           hyperopt_function
                    FROM optimization_sessions 
                    ORDER BY session_timestamp DESC
                    LIMIT ?
                """, (limit,))

                results = cursor.fetchall()

                if not results:
                    print("No optimization sessions found.")
                    return

                table_data = []
                for row in results:
                    duration_min = row['session_duration_seconds'] // 60 if row['session_duration_seconds'] else 0
                    success_rate = (row['successful_strategies'] / row['total_strategies'] * 100) if row[
                        'total_strategies'] else 0

                    table_data.append([
                        row['id'],
                        row['session_timestamp'][:16],
                        row['total_strategies'] or 0,
                        row['successful_strategies'] or 0,
                        row['failed_strategies'] or 0,
                        f"{success_rate:.0f}%",
                        f"{duration_min}min",
                        row['timeframe'],
                        row['epochs'],
                        row['hyperopt_function'][:20] + "..." if row['hyperopt_function'] and len(
                            row['hyperopt_function']) > 20 else row['hyperopt_function']
                    ])

                headers = ['ID', 'Timestamp', 'Total', 'Success', 'Failed',
                           'Success Rate', 'Duration', 'Timeframe', 'Epochs', 'Loss Function']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

        except Exception as e:
            print(f"Error retrieving optimization sessions: {e}")

    def _show_backtest_sessions(self, limit: int) -> None:
        """Show backtest sessions."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT bs.id, bs.session_timestamp, bs.total_strategies, 
                           bs.successful_backtests, bs.failed_backtests, 
                           bs.session_duration_seconds, bs.timeframe,
                           bs.optimization_session_id,
                           os.session_timestamp as opt_session_timestamp
                    FROM backtest_sessions bs
                    LEFT JOIN optimization_sessions os ON bs.optimization_session_id = os.id
                    ORDER BY bs.session_timestamp DESC
                    LIMIT ?
                """, (limit,))

                results = cursor.fetchall()

                if not results:
                    print("No backtest sessions found.")
                    return

                table_data = []
                for row in results:
                    duration_min = row['session_duration_seconds'] // 60 if row['session_duration_seconds'] else 0
                    success_rate = (row['successful_backtests'] / row['total_strategies'] * 100) if row[
                        'total_strategies'] else 0

                    opt_session_link = f"→ Opt #{row['optimization_session_id']}" if row[
                        'optimization_session_id'] else "Standalone"

                    table_data.append([
                        row['id'],
                        row['session_timestamp'][:16],
                        row['total_strategies'] or 0,
                        row['successful_backtests'] or 0,
                        row['failed_backtests'] or 0,
                        f"{success_rate:.0f}%",
                        f"{duration_min}min",
                        row['timeframe'],
                        opt_session_link
                    ])

                headers = ['ID', 'Timestamp', 'Total', 'Success', 'Failed',
                           'Success Rate', 'Duration', 'Timeframe', 'Linked Session']

                print(tabulate(table_data, headers=headers, tablefmt='grid'))

        except Exception as e:
            print(f"Error retrieving backtest sessions: {e}")

    def show_strategy_performance_timeline(self, strategy_name: str) -> None:
        """Show performance timeline for a specific strategy across optimizations and backtests."""
        print(f"\n📈 PERFORMANCE TIMELINE: {strategy_name}")
        print("=" * 120)

        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get combined timeline
                cursor = conn.execute("""
                    SELECT 'hyperopt' as type, id, hyperopt_timestamp as timestamp, 
                           total_profit_pct, total_trades, sharpe_ratio, run_number,
                           epochs, hyperopt_function as details
                    FROM hyperopt_runs 
                    WHERE strategy_name = ? AND status = 'completed'

                    UNION ALL

                    SELECT 'backtest' as type, id, backtest_timestamp as timestamp,
                           total_profit_pct, total_trades, sharpe_ratio, 
                           hyperopt_id as run_number, backtest_duration_seconds as epochs,
                           'Backtest validation' as details
                    FROM backtest_runs 
                    WHERE strategy_name = ? AND status = 'completed'

                    ORDER BY timestamp DESC
                """, (strategy_name, strategy_name))

                results = cursor.fetchall()

                if not results:
                    print(f"No performance data found for strategy: {strategy_name}")
                    return

                table_data = []
                for row in results:
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
                hyperopt_results = [row for row in results if row['type'] == 'hyperopt']
                backtest_results = [row for row in results if row['type'] == 'backtest']

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

    def export_best_hyperopt_configs(self, output_dir: str = "best_hyperopt_configs", limit: int = 5) -> None:
        """Export configuration files for the best performing hyperopt strategies."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"\n💾 EXPORTING TOP {limit} HYPEROPT CONFIGURATIONS")
        print("=" * 80)

        try:
            best_strategies = self.db_manager.get_best_hyperopt_strategies(limit=limit)

            for i, strategy in enumerate(best_strategies, 1):
                config_file = strategy['config_file_path']
                if config_file and Path(config_file).exists():
                    dest_name = f"{i:02d}_{strategy['strategy_name']}_hyperopt_profit{strategy['total_profit_pct']:+.2f}%_id{strategy['id']}.json"
                    dest_path = output_path / dest_name

                    with open(config_file, 'r') as src, open(dest_path, 'w') as dst:
                        config = json.load(src)
                        json.dump(config, dst, indent=2)

                    print(f"✓ Exported: {dest_name}")
                else:
                    print(f"✗ Config not found for {strategy['strategy_name']} (ID {strategy['id']})")

            print(f"\nHyperopt configurations exported to: {output_path}")

        except Exception as e:
            print(f"Error exporting hyperopt configs: {e}")

    def export_best_backtest_configs(self, output_dir: str = "best_backtest_configs", limit: int = 5) -> None:
        """Export configuration files for the best performing backtest strategies."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"\n💾 EXPORTING TOP {limit} BACKTEST CONFIGURATIONS")
        print("=" * 80)

        try:
            best_strategies = self.db_manager.get_best_backtest_strategies(limit=limit)

            for i, strategy in enumerate(best_strategies, 1):
                config_file = strategy['config_file_path']
                if config_file and Path(config_file).exists():
                    dest_name = f"{i:02d}_{strategy['strategy_name']}_backtest_profit{strategy['total_profit_pct']:+.2f}%_id{strategy['id']}.json"
                    dest_path = output_path / dest_name

                    with open(config_file, 'r') as src, open(dest_path, 'w') as dst:
                        config = json.load(src)
                        json.dump(config, dst, indent=2)

                    print(f"✓ Exported: {dest_name}")
                else:
                    print(f"✗ Config not found for {strategy['strategy_name']} (ID {strategy['id']})")

            print(f"\nBacktest configurations exported to: {output_path}")

        except Exception as e:
            print(f"Error exporting backtest configs: {e}")

    def show_comprehensive_strategy_report(self, strategy_name: str) -> None:
        """Generate a comprehensive report for a specific strategy."""
        print(f"\n📋 COMPREHENSIVE STRATEGY REPORT: {strategy_name}")
        print("=" * 120)

        # Show optimization results
        self.show_optimization_vs_backtest_comparison(strategy_name)

        # Show performance timeline
        print("\n" + "─" * 120)
        self.show_strategy_performance_timeline(strategy_name)

        # Show detailed backtest analysis for best backtest
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT id FROM backtest_runs 
                    WHERE strategy_name = ? AND status = 'completed'
                    ORDER BY total_profit_pct DESC LIMIT 1
                """, (strategy_name,))

                result = cursor.fetchone()
                if result:
                    print("\n" + "─" * 120)
                    self.show_backtest_trade_details(result['id'])

        except Exception as e:
            print(f"Error generating comprehensive report: {e}")


def main():
    """Main CLI interface for the enhanced analyzer."""
    parser = argparse.ArgumentParser(description="Enhanced FreqTrade Results Analyzer")
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

    # Trade details command
    trades_parser = subparsers.add_parser("trades", help="Show trade details for backtest")
    trades_parser.add_argument("backtest_id", type=int, help="Backtest ID")

    # Performance timeline command
    timeline_parser = subparsers.add_parser("timeline", help="Show performance timeline for strategy")
    timeline_parser.add_argument("strategy", help="Strategy name")

    # Sessions command
    sessions_parser = subparsers.add_parser("sessions", help="Show recent sessions")
    sessions_parser.add_argument("--type", choices=["optimization", "backtest", "both"],
                                 default="both", help="Type of sessions to show")
    sessions_parser.add_argument("--limit", type=int, default=10, help="Number of sessions to show")

    # Export hyperopt configs command
    export_hyperopt_parser = subparsers.add_parser("export-hyperopt", help="Export best hyperopt configurations")
    export_hyperopt_parser.add_argument("--output", default="best_hyperopt_configs", help="Output directory")
    export_hyperopt_parser.add_argument("--limit", type=int, default=5, help="Number of configs to export")

    # Export backtest configs command
    export_backtest_parser = subparsers.add_parser("export-backtest", help="Export best backtest configurations")
    export_backtest_parser.add_argument("--output", default="best_backtest_configs", help="Output directory")
    export_backtest_parser.add_argument("--limit", type=int, default=5, help="Number of configs to export")

    # Comprehensive report command
    report_parser = subparsers.add_parser("report", help="Generate comprehensive strategy report")
    report_parser.add_argument("strategy", help="Strategy name")

    # Migration command
    subparsers.add_parser("migrate", help="Migrate from old database schema")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    analyzer = EnhancedResultsAnalyzer(args.db)

    try:
        if args.command == "best-hyperopt":
            analyzer.show_best_hyperopt_strategies(args.limit, args.timeframe, args.min_trades)
        elif args.command == "best-backtest":
            analyzer.show_best_backtest_strategies(args.limit, args.timeframe, args.min_trades)
        elif args.command == "gap":
            analyzer.show_reality_gap_analysis(args.strategy, args.limit)
        elif args.command == "vs":
            analyzer.show_optimization_vs_backtest_comparison(args.strategy)
        elif args.command == "trades":
            analyzer.show_backtest_trade_details(args.backtest_id)
        elif args.command == "timeline":
            analyzer.show_strategy_performance_timeline(args.strategy)
        elif args.command == "sessions":
            analyzer.show_sessions(args.type, args.limit)
        elif args.command == "export-hyperopt":
            analyzer.export_best_hyperopt_configs(args.output, args.limit)
        elif args.command == "export-backtest":
            analyzer.export_best_backtest_configs(args.output, args.limit)
        elif args.command == "report":
            analyzer.show_comprehensive_strategy_report(args.strategy)
        elif args.command == "migrate":
            success = analyzer.db_manager.migrate_from_old_schema()
            if success:
                print("✓ Migration completed successfully!")
            else:
                print("✗ Migration failed. Check logs for details.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()