#!/usr/bin/env python3
"""
Database Manager for FreqTrade Results
Structured to separate hyperopt runs and backtest runs into dedicated tables.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC
import re


@dataclass
class TradingResult(ABC):
    """Abstract base class for trading results."""
    strategy_name: str
    total_profit_pct: float
    total_profit_abs: float
    total_trades: int
    win_rate: float
    avg_profit_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    calmar_ratio: float
    sortino_ratio: float
    profit_factor: float
    expectancy: float

    # Configuration details
    max_open_trades: int
    timeframe: str
    stake_amount: float
    stake_currency: str
    timerange: str
    pair_whitelist: List[str]
    exchange_name: str

    # Data payloads
    config_data: Dict[str, Any]

@dataclass
class HyperoptResult(TradingResult):
    """Data class for hyperopt optimization results."""
    # Hyperopt specific
    hyperopt_function: str
    epochs: int
    spaces: List[str]

    # Metadata
    hyperopt_json_data: Dict[str, Any]
    optimization_duration: int
    run_number: int = 1

@dataclass
class BacktestResult(TradingResult):
    """Data class for backtest results."""
    max_drawdown_abs: float

    # Trade statistics
    winning_trades: int
    losing_trades: int
    draw_trades: int
    best_trade_pct: float
    worst_trade_pct: float
    avg_trade_duration: str

    # File references
    backtest_results: Dict[str, Any]
    backtest_duration: int

    # Optional link to optimization
    hyperopt_id: Optional[int] = None


class DatabaseManager:
    """
    Simplified database manager with only two main tables.
    """

    def __init__(self, db_path: str = "freqtrade_results.db"):
        """
        Initialize the simplified database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database with the simplified two-table schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")

                # Create hyperopt results table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS hyperopt_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        -- Basic info
                        strategy_name VARCHAR(100) NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'completed',

                        -- Configuration
                        max_open_trades INTEGER,
                        timeframe VARCHAR(10) NOT NULL,
                        stake_amount DECIMAL(10, 8),
                        stake_currency VARCHAR(10),
                        timerange VARCHAR(50),
                        pair_whitelist TEXT,  -- JSON array
                        exchange_name VARCHAR(50),

                        -- Hyperopt Settings
                        hyperopt_function VARCHAR(100),
                        epochs INTEGER,
                        spaces TEXT,  -- JSON array of spaces
                        run_number INTEGER DEFAULT 1,

                        -- Performance Metrics
                        total_profit_pct DECIMAL(10, 4),
                        total_profit_abs DECIMAL(15, 8),
                        total_trades INTEGER,
                        win_rate DECIMAL(5, 2),
                        avg_profit_pct DECIMAL(10, 4),
                        max_drawdown_pct DECIMAL(10, 4),

                        -- Advanced Metrics
                        sharpe_ratio DECIMAL(10, 4),
                        calmar_ratio DECIMAL(10, 4),
                        sortino_ratio DECIMAL(10, 4),
                        profit_factor DECIMAL(10, 4),
                        expectancy DECIMAL(10, 6),

                        -- Trade Statistics (from hyperopt)
                        winning_trades INTEGER,
                        losing_trades INTEGER,
                        draw_trades INTEGER,

                        -- File References and Raw Data
                        config_file_path VARCHAR(255),
                        hyperopt_result_file_path VARCHAR(255),
                        config_json TEXT,  -- Full config as JSON
                        hyperopt_json TEXT,  -- Full hyperopt result as JSON
                        raw_output TEXT,  -- Raw command output

                        -- Meta Information
                        optimization_duration_seconds INTEGER,
                        session_info TEXT  -- JSON with session metadata
                    )
                """)

                # Create backtest results table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        -- Basic info
                        strategy_name VARCHAR(100) NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'completed',

                        -- Configuration
                        max_open_trades INTEGER,
                        timeframe VARCHAR(10) NOT NULL,
                        stake_amount DECIMAL(10, 8),
                        stake_currency VARCHAR(10),
                        timerange VARCHAR(50),
                        pair_whitelist TEXT,  -- JSON array
                        exchange_name VARCHAR(50),

                        -- Performance Metrics
                        total_profit_pct DECIMAL(10, 4),
                        total_profit_abs DECIMAL(15, 8),
                        total_trades INTEGER,
                        win_rate DECIMAL(5, 2),
                        avg_profit_pct DECIMAL(10, 4),
                        max_drawdown_pct DECIMAL(10, 4),
                        max_drawdown_abs DECIMAL(15, 8),

                        -- Advanced Metrics
                        sharpe_ratio DECIMAL(10, 4),
                        calmar_ratio DECIMAL(10, 4),
                        sortino_ratio DECIMAL(10, 4),
                        profit_factor DECIMAL(10, 4),
                        expectancy DECIMAL(10, 6),

                        -- Trade Statistics
                        winning_trades INTEGER,
                        losing_trades INTEGER,
                        draw_trades INTEGER,
                        best_trade_pct DECIMAL(10, 4),
                        worst_trade_pct DECIMAL(10, 4),
                        avg_trade_duration VARCHAR(50),

                        -- File References and Raw Data
                        config_file_path VARCHAR(255),
                        backtest_result_file_path VARCHAR(255),
                        config_json TEXT,  -- Full config as JSON
                        backtest_json TEXT,  -- Full backtest result as JSON
                        raw_output TEXT,  -- Raw command output
                        trades_json TEXT,  -- Individual trades as JSON (optional)

                        -- Meta Information
                        backtest_duration_seconds INTEGER,
                        hyperopt_id INTEGER,  -- Optional link to hyperopt result
                        session_info TEXT,  -- JSON with session metadata

                        FOREIGN KEY (hyperopt_id) REFERENCES hyperopt_results(id)
                    )
                """)

                # Create indexes for better performance
                indexes = [
                    # Hyperopt indexes
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_strategy_profit ON hyperopt_results(strategy_name, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_timeframe_profit ON hyperopt_results(timeframe, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_timestamp ON hyperopt_results(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_status ON hyperopt_results(status)",

                    # Backtest indexes
                    "CREATE INDEX IF NOT EXISTS idx_backtest_strategy_profit ON backtest_results(strategy_name, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_timeframe_profit ON backtest_results(timeframe, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_timestamp ON backtest_results(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_hyperopt ON backtest_results(hyperopt_id)",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_status ON backtest_results(status)",
                ]

                for index_sql in indexes:
                    conn.execute(index_sql)

                conn.commit()
                self.logger.info(f"Simplified database initialized: {self.db_path}")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    def save_hyperopt_result(self, result: HyperoptResult, session_info: Optional[Dict] = None) -> int:
        """Save hyperopt result to database."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save config and result files
            config_dir = Path("optimization_results/configs")
            hyperopt_dir = Path("optimization_results/hyperopt_results")
            config_dir.mkdir(parents=True, exist_ok=True)
            hyperopt_dir.mkdir(parents=True, exist_ok=True)

            config_filename = f"{timestamp}_{result.strategy_name}_run{result.run_number}_config.json"
            hyperopt_filename = f"{timestamp}_{result.strategy_name}_run{result.run_number}_hyperopt.json"

            config_path = config_dir / config_filename
            hyperopt_path = hyperopt_dir / hyperopt_filename

            with open(config_path, 'w') as f:
                json.dump(result.config_data, f, indent=2)

            with open(hyperopt_path, 'w') as f:
                json.dump(result.hyperopt_json_data, f, indent=2)

            # Insert into database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO hyperopt_results (
                        strategy_name, max_open_trades, timeframe, stake_amount, stake_currency,
                        timerange, pair_whitelist, exchange_name, hyperopt_function, epochs, spaces,
                        run_number, total_profit_pct, total_profit_abs, total_trades, win_rate, 
                        avg_profit_pct, max_drawdown_pct, sharpe_ratio, calmar_ratio, sortino_ratio, 
                        profit_factor, expectancy, winning_trades, losing_trades, draw_trades,
                        config_file_path, hyperopt_result_file_path, config_json, hyperopt_json,
                        optimization_duration_seconds, session_info
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.strategy_name, result.max_open_trades, result.timeframe,
                    result.stake_amount, result.stake_currency, result.timerange,
                    json.dumps(result.pair_whitelist), result.exchange_name,
                    result.hyperopt_function, result.epochs, json.dumps(result.spaces),
                    result.run_number, result.total_profit_pct, result.total_profit_abs,
                    result.total_trades, result.win_rate, result.avg_profit_pct,
                    result.max_drawdown_pct, result.sharpe_ratio, result.calmar_ratio,
                    result.sortino_ratio, result.profit_factor, result.expectancy,
                    # Extract trade stats from hyperopt data if available
                    result.hyperopt_json_data.get('winning_trades', 0),
                    result.hyperopt_json_data.get('losing_trades', 0),
                    result.hyperopt_json_data.get('draw_trades', 0),
                    str(config_path), str(hyperopt_path),
                    json.dumps(result.config_data), json.dumps(result.hyperopt_json_data),
                    result.optimization_duration, json.dumps(session_info) if session_info else None
                ))

                hyperopt_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"Saved hyperopt result {hyperopt_id} for {result.strategy_name}")
                return hyperopt_id

        except Exception as e:
            self.logger.error(f"Failed to save hyperopt result: {e}")
            raise

    def save_backtest_result(self, result: BacktestResult, session_info: Optional[Dict] = None) -> int:
        """Save backtest result to database."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save config and result files
            config_dir = Path("optimization_results/configs")
            backtest_dir = Path("optimization_results/backtest_results")
            config_dir.mkdir(parents=True, exist_ok=True)
            backtest_dir.mkdir(parents=True, exist_ok=True)

            config_filename = f"{timestamp}_{result.strategy_name}_backtest_config.json"
            backtest_filename = f"{timestamp}_{result.strategy_name}_backtest_results.json"

            config_path = config_dir / config_filename
            backtest_path = backtest_dir / backtest_filename

            with open(config_path, 'w') as f:
                json.dump(result.config_data, f, indent=2)

            with open(backtest_path, 'w') as f:
                json.dump(result.backtest_results, f, indent=2)

            # Insert into database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO backtest_results (
                        strategy_name, max_open_trades, timeframe, stake_amount, stake_currency,
                        timerange, pair_whitelist, exchange_name, total_profit_pct, total_profit_abs,
                        total_trades, win_rate, avg_profit_pct, max_drawdown_pct, max_drawdown_abs,
                        sharpe_ratio, calmar_ratio, sortino_ratio, profit_factor, expectancy,
                        winning_trades, losing_trades, draw_trades, best_trade_pct, worst_trade_pct,
                        avg_trade_duration, config_file_path, backtest_result_file_path,
                        config_json, backtest_json, backtest_duration_seconds, hyperopt_id, session_info
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.strategy_name, result.max_open_trades, result.timeframe,
                    result.stake_amount, result.stake_currency, result.timerange,
                    json.dumps(result.pair_whitelist), result.exchange_name,
                    result.total_profit_pct, result.total_profit_abs, result.total_trades,
                    result.win_rate, result.avg_profit_pct, result.max_drawdown_pct,
                    result.max_drawdown_abs, result.sharpe_ratio, result.calmar_ratio,
                    result.sortino_ratio, result.profit_factor, result.expectancy,
                    result.winning_trades, result.losing_trades, result.draw_trades,
                    result.best_trade_pct, result.worst_trade_pct, result.avg_trade_duration,
                    str(config_path), str(backtest_path),
                    json.dumps(result.config_data), json.dumps(result.backtest_results),
                    result.backtest_duration, result.hyperopt_id,
                    json.dumps(session_info) if session_info else None
                ))

                backtest_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"Saved backtest result {backtest_id} for {result.strategy_name}")
                return backtest_id

        except Exception as e:
            self.logger.error(f"Failed to save backtest result: {e}")
            raise

    def get_best_hyperopt_strategies(self, limit: int = 10, timeframe: Optional[str] = None) -> List[Dict]:
        """Get the best performing hyperopt strategies."""
        try:
            query = """
                SELECT * FROM hyperopt_results 
                WHERE status = 'completed'
            """
            params = []

            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            query += " ORDER BY total_profit_pct DESC LIMIT ?"
            params.append(limit)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]

                return results

        except Exception as e:
            self.logger.error(f"Failed to get best hyperopt strategies: {e}")
            return []

    def get_best_backtest_strategies(self, limit: int = 10, timeframe: Optional[str] = None) -> List[Dict]:
        """Get the best performing backtest strategies."""
        try:
            query = """
                SELECT * FROM backtest_results 
                WHERE status = 'completed'
            """
            params = []

            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            query += " ORDER BY total_profit_pct DESC LIMIT ?"
            params.append(limit)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]

                return results

        except Exception as e:
            self.logger.error(f"Failed to get best backtest strategies: {e}")
            return []

    def get_optimization_vs_backtest_comparison(self, strategy_name: Optional[str] = None) -> List[Dict]:
        """Compare optimization vs backtest results for reality gap analysis."""
        try:
            query = """
                SELECT 
                    h.id as hyperopt_id,
                    h.strategy_name,
                    h.total_profit_pct as hyperopt_profit,
                    h.total_trades as hyperopt_trades,
                    h.win_rate as hyperopt_win_rate,
                    h.max_drawdown_pct as hyperopt_drawdown,
                    h.sharpe_ratio as hyperopt_sharpe,
                    h.timestamp as hyperopt_timestamp,

                    b.id as backtest_id,
                    b.total_profit_pct as backtest_profit,
                    b.total_trades as backtest_trades,
                    b.win_rate as backtest_win_rate,
                    b.max_drawdown_pct as backtest_drawdown,
                    b.sharpe_ratio as backtest_sharpe,
                    b.timestamp as backtest_timestamp,

                    (h.total_profit_pct - COALESCE(b.total_profit_pct, 0)) as reality_gap_pct

                FROM hyperopt_results h
                LEFT JOIN backtest_results b ON h.id = b.hyperopt_id
                WHERE h.status = 'completed'
            """
            params = []

            if strategy_name:
                query += " AND h.strategy_name = ?"
                params.append(strategy_name)

            query += " ORDER BY ABS(h.total_profit_pct - COALESCE(b.total_profit_pct, 0)) DESC"

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]

                return results

        except Exception as e:
            self.logger.error(f"Failed to get optimization vs backtest comparison: {e}")
            return []

    def get_strategy_timeline(self, strategy_name: str) -> List[Dict]:
        """Get performance timeline for a specific strategy across optimizations and backtests."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get combined timeline
                cursor = conn.execute("""
                    SELECT 'hyperopt' as type, id, timestamp, 
                           total_profit_pct, total_trades, sharpe_ratio, run_number,
                           epochs, hyperopt_function as details
                    FROM hyperopt_results 
                    WHERE strategy_name = ? AND status = 'completed'

                    UNION ALL

                    SELECT 'backtest' as type, id, timestamp,
                           total_profit_pct, total_trades, sharpe_ratio, 
                           hyperopt_id as run_number, backtest_duration_seconds as epochs,
                           'Backtest validation' as details
                    FROM backtest_results 
                    WHERE strategy_name = ? AND status = 'completed'

                    ORDER BY timestamp DESC
                """, (strategy_name, strategy_name))

                results = [dict(row) for row in cursor.fetchall()]
                return results

        except Exception as e:
            self.logger.error(f"Failed to get strategy timeline: {e}")
            return []

    def get_hyperopt_json_result(self, hyperopt_id: int) -> Optional[Dict]:
        """Get hyperopt JSON result for a specific hyperopt run."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT hyperopt_json FROM hyperopt_results WHERE id = ?
                """, (hyperopt_id,))

                result = cursor.fetchone()
                if result and result[0]:
                    return json.loads(result[0])
                return None

        except Exception as e:
            self.logger.error(f"Failed to get hyperopt JSON result: {e}")
            return None

    def get_backtest_trades_from_json(self, backtest_id: int) -> List[Dict]:
        """Get individual trades from backtest JSON data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT trades_json FROM backtest_results WHERE id = ?
                """, (backtest_id,))

                result = cursor.fetchone()
                if result and result[0]:
                    return json.loads(result[0])
                return []

        except Exception as e:
            self.logger.error(f"Failed to get backtest trades: {e}")
            return []

    def save_backtest_trades_json(self, backtest_id: int, trades: List[Dict]) -> None:
        """Save individual trade records as JSON for detailed analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE backtest_results 
                    SET trades_json = ?
                    WHERE id = ?
                """, (json.dumps(trades), backtest_id))

                conn.commit()
                self.logger.info(f"Saved {len(trades)} trade records as JSON for backtest {backtest_id}")

        except Exception as e:
            self.logger.error(f"Failed to save backtest trades JSON: {e}")

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Hyperopt stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_hyperopt,
                        COUNT(DISTINCT strategy_name) as unique_strategies_hyperopt,
                        AVG(total_profit_pct) as avg_profit_hyperopt,
                        MAX(total_profit_pct) as max_profit_hyperopt,
                        MIN(total_profit_pct) as min_profit_hyperopt
                    FROM hyperopt_results 
                    WHERE status = 'completed'
                """)
                hyperopt_stats = dict(cursor.fetchone())

                # Backtest stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_backtest,
                        COUNT(DISTINCT strategy_name) as unique_strategies_backtest,
                        AVG(total_profit_pct) as avg_profit_backtest,
                        MAX(total_profit_pct) as max_profit_backtest,
                        MIN(total_profit_pct) as min_profit_backtest,
                        COUNT(hyperopt_id) as linked_to_hyperopt
                    FROM backtest_results 
                    WHERE status = 'completed'
                """)
                backtest_stats = dict(cursor.fetchone())

                # Reality gap stats
                cursor = conn.execute("""
                    SELECT 
                        AVG(h.total_profit_pct - b.total_profit_pct) as avg_reality_gap,
                        COUNT(*) as compared_pairs
                    FROM hyperopt_results h
                    JOIN backtest_results b ON h.id = b.hyperopt_id
                    WHERE h.status = 'completed' AND b.status = 'completed'
                """)
                gap_stats = dict(cursor.fetchone())

                return {
                    'hyperopt': hyperopt_stats,
                    'backtest': backtest_stats,
                    'reality_gap': gap_stats
                }

        except Exception as e:
            self.logger.error(f"Failed to get stats summary: {e}")
            return {}

    def parse_hyperopt_results(self, hyperopt_output: str) -> Dict[str, Any]:
        """Parse hyperopt output to extract key metrics."""
        results = {}

        try:
            # Extract profit percentage
            profit_match = re.search(r"Total profit %\s*│\s*([\d.-]+)%", hyperopt_output)
            if profit_match:
                results['total_profit_pct'] = float(profit_match.group(1))

            # Extract absolute profit
            abs_profit_match = re.search(r"Abs profit\s*│\s*([\d.-]+)", hyperopt_output)
            if abs_profit_match:
                results['total_profit_abs'] = float(abs_profit_match.group(1))

            # Extract total trades
            trades_match = re.search(r"Total trades\s*│\s*(\d+)", hyperopt_output)
            if trades_match:
                results['total_trades'] = int(trades_match.group(1))

            # Extract win rate
            win_rate_match = re.search(r"Win/Draw/Lose\s*│\s*(\d+)/(\d+)/(\d+)", hyperopt_output)
            if win_rate_match:
                wins = int(win_rate_match.group(1))
                draws = int(win_rate_match.group(2))
                losses = int(win_rate_match.group(3))
                total = wins + draws + losses
                results['win_rate'] = (wins / total * 100) if total > 0 else 0
                results['winning_trades'] = wins
                results['draw_trades'] = draws
                results['losing_trades'] = losses

            # Extract average profit
            avg_profit_match = re.search(r"Avg profit %\s*│\s*([\d.-]+)%", hyperopt_output)
            if avg_profit_match:
                results['avg_profit_pct'] = float(avg_profit_match.group(1))

            # Extract max drawdown
            drawdown_match = re.search(r"Max Drawdown\s*│\s*([\d.-]+)%", hyperopt_output)
            if drawdown_match:
                results['max_drawdown_pct'] = float(drawdown_match.group(1))

            # Extract advanced metrics if available
            sharpe_match = re.search(r"Sharpe\s*│\s*([\d.-]+)", hyperopt_output)
            if sharpe_match:
                results['sharpe_ratio'] = float(sharpe_match.group(1))

            calmar_match = re.search(r"Calmar\s*│\s*([\d.-]+)", hyperopt_output)
            if calmar_match:
                results['calmar_ratio'] = float(calmar_match.group(1))

            sortino_match = re.search(r"Sortino\s*│\s*([\d.-]+)", hyperopt_output)
            if sortino_match:
                results['sortino_ratio'] = float(sortino_match.group(1))

            profit_factor_match = re.search(r"Profit factor\s*│\s*([\d.-]+)", hyperopt_output)
            if profit_factor_match:
                results['profit_factor'] = float(profit_factor_match.group(1))

            expectancy_match = re.search(r"Expectancy\s*│\s*([\d.-]+)", hyperopt_output)
            if expectancy_match:
                results['expectancy'] = float(expectancy_match.group(1))

            # Set defaults for missing values
            results.setdefault('sharpe_ratio', 0.0)
            results.setdefault('calmar_ratio', 0.0)
            results.setdefault('sortino_ratio', 0.0)
            results.setdefault('profit_factor', 0.0)
            results.setdefault('expectancy', 0.0)

        except Exception as e:
            self.logger.warning(f"Error parsing hyperopt results: {e}")

        return results

    def parse_backtest_results(self, backtest_output: str) -> Dict[str, Any]:
        """Parse backtest output to extract key metrics."""
        results = {}

        try:
            # Extract profit percentage
            profit_match = re.search(r"Total profit %\s*│\s*([\d.-]+)%", backtest_output)
            if profit_match:
                results['total_profit_pct'] = float(profit_match.group(1))

            # Extract absolute profit
            abs_profit_match = re.search(r"Abs profit\s*│\s*([\d.-]+)", backtest_output)
            if abs_profit_match:
                results['total_profit_abs'] = float(abs_profit_match.group(1))

            # Extract total trades
            trades_match = re.search(r"Total trades\s*│\s*(\d+)", backtest_output)
            if trades_match:
                results['total_trades'] = int(trades_match.group(1))

            # Extract win/draw/lose
            win_rate_match = re.search(r"Win/Draw/Lose\s*│\s*(\d+)/(\d+)/(\d+)", backtest_output)
            if win_rate_match:
                wins = int(win_rate_match.group(1))
                draws = int(win_rate_match.group(2))
                losses = int(win_rate_match.group(3))
                total = wins + draws + losses
                results['win_rate'] = (wins / total * 100) if total > 0 else 0
                results['winning_trades'] = wins
                results['draw_trades'] = draws
                results['losing_trades'] = losses

            # Extract average profit
            avg_profit_match = re.search(r"Avg profit %\s*│\s*([\d.-]+)%", backtest_output)
            if avg_profit_match:
                results['avg_profit_pct'] = float(avg_profit_match.group(1))

            # Extract max drawdown percentage
            drawdown_pct_match = re.search(r"Max Drawdown\s*│\s*([\d.-]+)%", backtest_output)
            if drawdown_pct_match:
                results['max_drawdown_pct'] = float(drawdown_pct_match.group(1))

            # Extract max drawdown absolute
            drawdown_abs_match = re.search(r"Max Drawdown\s*│.*│\s*([\d.-]+)", backtest_output)
            if drawdown_abs_match:
                results['max_drawdown_abs'] = float(drawdown_abs_match.group(1))

            # Extract best/worst trades
            best_trade_match = re.search(r"Best trade %\s*│\s*([\d.-]+)%", backtest_output)
            if best_trade_match:
                results['best_trade_pct'] = float(best_trade_match.group(1))

            worst_trade_match = re.search(r"Worst trade %\s*│\s*([\d.-]+)%", backtest_output)
            if worst_trade_match:
                results['worst_trade_pct'] = float(worst_trade_match.group(1))

            # Extract average trade duration
            duration_match = re.search(r"Avg trade duration\s*│\s*([^│]+)", backtest_output)
            if duration_match:
                results['avg_trade_duration'] = duration_match.group(1).strip()

            # Extract advanced metrics
            sharpe_match = re.search(r"Sharpe\s*│\s*([\d.-]+)", backtest_output)
            if sharpe_match:
                results['sharpe_ratio'] = float(sharpe_match.group(1))

            calmar_match = re.search(r"Calmar\s*│\s*([\d.-]+)", backtest_output)
            if calmar_match:
                results['calmar_ratio'] = float(calmar_match.group(1))

            sortino_match = re.search(r"Sortino\s*│\s*([\d.-]+)", backtest_output)
            if sortino_match:
                results['sortino_ratio'] = float(sortino_match.group(1))

            profit_factor_match = re.search(r"Profit factor\s*│\s*([\d.-]+)", backtest_output)
            if profit_factor_match:
                results['profit_factor'] = float(profit_factor_match.group(1))

            expectancy_match = re.search(r"Expectancy\s*│\s*([\d.-]+)", backtest_output)
            if expectancy_match:
                results['expectancy'] = float(expectancy_match.group(1))

            # Set defaults for missing values
            results.setdefault('max_drawdown_abs', 0.0)
            results.setdefault('best_trade_pct', 0.0)
            results.setdefault('worst_trade_pct', 0.0)
            results.setdefault('avg_trade_duration', '0 days')
            results.setdefault('sharpe_ratio', 0.0)
            results.setdefault('calmar_ratio', 0.0)
            results.setdefault('sortino_ratio', 0.0)
            results.setdefault('profit_factor', 0.0)
            results.setdefault('expectancy', 0.0)

        except Exception as e:
            self.logger.warning(f"Error parsing backtest results: {e}")

        return results

    def migrate_from_old_schema(self) -> bool:
        """
        Migrate data from the old complex schema to the new simplified schema.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if old tables exist
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('hyperopt_runs', 'backtest_runs', 'strategy_optimizations')
                """)

                old_tables = [row[0] for row in cursor.fetchall()]

                if not old_tables:
                    self.logger.info("No old schema found, skipping migration")
                    return True

                self.logger.info(f"Migrating data from old schema tables: {old_tables}")

                # Migrate from hyperopt_runs if it exists
                if 'hyperopt_runs' in old_tables:
                    cursor = conn.execute("""
                        INSERT INTO hyperopt_results (
                            strategy_name, timestamp, max_open_trades, timeframe,
                            stake_amount, stake_currency, timerange, pair_whitelist, exchange_name,
                            hyperopt_function, epochs, spaces, run_number, total_profit_pct, 
                            total_profit_abs, total_trades, win_rate, avg_profit_pct, 
                            max_drawdown_pct, sharpe_ratio, calmar_ratio, sortino_ratio, 
                            profit_factor, expectancy, winning_trades, losing_trades, 
                            draw_trades, config_file_path, hyperopt_result_file_path,
                            optimization_duration_seconds, status
                        )
                        SELECT 
                            strategy_name, hyperopt_timestamp, max_open_trades, timeframe,
                            stake_amount, stake_currency, timerange, pair_whitelist, exchange_name,
                            hyperopt_function, epochs, spaces, run_number, total_profit_pct,
                            total_profit_abs, total_trades, win_rate, avg_profit_pct,
                            max_drawdown_pct, COALESCE(sharpe_ratio, 0), COALESCE(calmar_ratio, 0), 
                            COALESCE(sortino_ratio, 0), COALESCE(profit_factor, 0), COALESCE(expectancy, 0),
                            COALESCE(winning_trades, 0), COALESCE(losing_trades, 0), COALESCE(draw_trades, 0),
                            config_file_path, hyperopt_result_file_path,
                            optimization_duration_seconds, COALESCE(status, 'completed')
                        FROM hyperopt_runs
                    """)

                    hyperopt_migrated = cursor.rowcount
                    self.logger.info(f"Migrated {hyperopt_migrated} hyperopt records")

                # Migrate from backtest_runs if it exists
                if 'backtest_runs' in old_tables:
                    cursor = conn.execute("""
                        INSERT INTO backtest_results (
                            strategy_name, timestamp, max_open_trades, timeframe,
                            stake_amount, stake_currency, timerange, pair_whitelist, exchange_name,
                            total_profit_pct, total_profit_abs, total_trades, win_rate, 
                            avg_profit_pct, max_drawdown_pct, max_drawdown_abs,
                            sharpe_ratio, calmar_ratio, sortino_ratio, profit_factor, expectancy,
                            winning_trades, losing_trades, draw_trades, best_trade_pct, 
                            worst_trade_pct, avg_trade_duration, config_file_path, 
                            backtest_result_file_path, backtest_duration_seconds, 
                            hyperopt_id, status
                        )
                        SELECT 
                            strategy_name, backtest_timestamp, max_open_trades, timeframe,
                            stake_amount, stake_currency, timerange, pair_whitelist, exchange_name,
                            total_profit_pct, total_profit_abs, total_trades, win_rate,
                            avg_profit_pct, max_drawdown_pct, COALESCE(max_drawdown_abs, 0),
                            COALESCE(sharpe_ratio, 0), COALESCE(calmar_ratio, 0), 
                            COALESCE(sortino_ratio, 0), COALESCE(profit_factor, 0), COALESCE(expectancy, 0),
                            COALESCE(winning_trades, 0), COALESCE(losing_trades, 0), COALESCE(draw_trades, 0),
                            COALESCE(best_trade_pct, 0), COALESCE(worst_trade_pct, 0), 
                            COALESCE(avg_trade_duration, '0 days'), config_file_path,
                            backtest_result_file_path, backtest_duration_seconds,
                            hyperopt_id, COALESCE(status, 'completed')
                        FROM backtest_runs
                    """)

                    backtest_migrated = cursor.rowcount
                    self.logger.info(f"Migrated {backtest_migrated} backtest records")

                # Migrate from old strategy_optimizations table if it exists
                if 'strategy_optimizations' in old_tables and 'hyperopt_runs' not in old_tables:
                    cursor = conn.execute("""
                        INSERT INTO hyperopt_results (
                            strategy_name, timestamp, max_open_trades, timeframe,
                            stake_amount, stake_currency, timerange, pair_whitelist, exchange_name,
                            hyperopt_function, epochs, total_profit_pct, total_profit_abs,
                            total_trades, win_rate, avg_profit_pct, max_drawdown_pct,
                            sharpe_ratio, config_file_path, hyperopt_result_file_path,
                            optimization_duration_seconds, run_number, status
                        )
                        SELECT 
                            strategy_name, optimization_timestamp, max_open_trades, timeframe,
                            stake_amount, stake_currency, timerange, pair_whitelist, exchange_name,
                            hyperopt_function, epochs, total_profit_pct, total_profit_abs,
                            total_trades, win_rate, avg_profit_pct, max_drawdown_pct,
                            COALESCE(sharpe_ratio, 0), config_file_path, hyperopt_result_file_path,
                            optimization_duration_seconds, COALESCE(run_number, 1), 
                            COALESCE(status, 'completed')
                        FROM strategy_optimizations
                    """)

                    legacy_migrated = cursor.rowcount
                    self.logger.info(f"Migrated {legacy_migrated} legacy optimization records")

                conn.commit()
                self.logger.info("Migration completed successfully")
                return True

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False