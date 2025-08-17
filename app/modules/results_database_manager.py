#!/usr/bin/env python3
"""
Enhanced Database Manager for FreqTrade Results
Restructured to separate hyperopt runs and backtest runs into dedicated tables.
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


class ResultsDatabaseManager:
    """
    Enhanced database manager with separate tables for hyperopt and backtest results.
    Maintains relationships between optimization and validation runs.
    """

    def __init__(self, db_path: str = "freqtrade_results.db"):
        """
        Initialize the enhanced database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database with the new enhanced schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")

                # Create hyperopt results table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS hyperopt_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_name VARCHAR(100) NOT NULL,
                        hyperopt_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

                        -- Configuration
                        max_open_trades INTEGER,
                        timeframe VARCHAR(10) NOT NULL,
                        stake_amount DECIMAL(10, 8),
                        stake_currency VARCHAR(10),
                        timerange VARCHAR(50),
                        pair_whitelist TEXT,
                        exchange_name VARCHAR(50),

                        -- Hyperopt Settings
                        hyperopt_function VARCHAR(100),
                        epochs INTEGER,
                        spaces TEXT,  -- JSON array of spaces

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

                        -- File References
                        config_file_path VARCHAR(255),
                        hyperopt_result_file_path VARCHAR(255),

                        -- Meta Information
                        optimization_duration_seconds INTEGER,
                        run_number INTEGER DEFAULT 1,
                        session_id INTEGER,
                        status VARCHAR(20) DEFAULT 'completed',

                        FOREIGN KEY (session_id) REFERENCES optimization_sessions(id)
                    )
                """)

                # Create backtest results table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_name VARCHAR(100) NOT NULL,
                        backtest_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

                        -- Configuration
                        max_open_trades INTEGER,
                        timeframe VARCHAR(10) NOT NULL,
                        stake_amount DECIMAL(10, 8),
                        stake_currency VARCHAR(10),
                        timerange VARCHAR(50),
                        pair_whitelist TEXT,
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

                        -- File References
                        config_file_path VARCHAR(255),
                        backtest_result_file_path VARCHAR(255),

                        -- Meta Information
                        backtest_duration_seconds INTEGER,
                        status VARCHAR(20) DEFAULT 'completed',
                        hyperopt_id INTEGER,  -- Link to hyperopt run that generated this config
                        session_id INTEGER,   -- Link to backtest session

                        FOREIGN KEY (hyperopt_id) REFERENCES hyperopt_runs(id),
                        FOREIGN KEY (session_id) REFERENCES backtest_sessions(id)
                    )
                """)

                # Create detailed trade records table (optional for detailed analysis)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        backtest_id INTEGER NOT NULL,
                        pair VARCHAR(20) NOT NULL,

                        open_timestamp DATETIME,
                        close_timestamp DATETIME,
                        open_rate DECIMAL(15, 8),
                        close_rate DECIMAL(15, 8),
                        amount DECIMAL(15, 8),

                        profit_pct DECIMAL(10, 4),
                        profit_abs DECIMAL(15, 8),
                        trade_duration INTEGER,  -- in minutes

                        exit_reason VARCHAR(50),
                        is_open BOOLEAN DEFAULT FALSE,

                        FOREIGN KEY (backtest_id) REFERENCES backtest_runs(id) ON DELETE CASCADE
                    )
                """)

                # Sessions table for hyperopt
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS optimization_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        total_strategies INTEGER,
                        successful_strategies INTEGER,
                        failed_strategies INTEGER,
                        session_duration_seconds INTEGER,

                        exchange_name VARCHAR(50),
                        timeframe VARCHAR(10),
                        timerange VARCHAR(50),
                        hyperopt_function VARCHAR(100),
                        epochs INTEGER
                    )
                """)

                # Sessions table for backtests
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        total_strategies INTEGER,
                        successful_backtests INTEGER,
                        failed_backtests INTEGER,
                        session_duration_seconds INTEGER,

                        exchange_name VARCHAR(50),
                        timeframe VARCHAR(10),
                        timerange VARCHAR(50),

                        optimization_session_id INTEGER,  -- Link to related optimization session
                        FOREIGN KEY (optimization_session_id) REFERENCES optimization_sessions(id)
                    )
                """)

                # Create indexes for better performance
                indexes = [
                    # Hyperopt indexes
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_strategy_profit ON hyperopt_runs(strategy_name, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_timeframe_profit ON hyperopt_runs(timeframe, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_timestamp ON hyperopt_runs(hyperopt_timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_session ON hyperopt_runs(session_id)",

                    # Backtest indexes
                    "CREATE INDEX IF NOT EXISTS idx_backtest_strategy_profit ON backtest_runs(strategy_name, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_timeframe_profit ON backtest_runs(timeframe, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_timestamp ON backtest_runs(backtest_timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_hyperopt ON backtest_runs(hyperopt_id)",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_session ON backtest_runs(session_id)",

                    # Trade indexes
                    "CREATE INDEX IF NOT EXISTS idx_trades_backtest ON backtest_trades(backtest_id)",
                    "CREATE INDEX IF NOT EXISTS idx_trades_pair ON backtest_trades(pair)",
                    "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON backtest_trades(open_timestamp)",
                ]

                for index_sql in indexes:
                    conn.execute(index_sql)

                conn.commit()
                self.logger.info(f"Enhanced database initialized: {self.db_path}")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    def start_optimization_session(self, **session_config) -> int:
        """Start a new hyperopt optimization session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO optimization_sessions 
                    (exchange_name, timeframe, timerange, hyperopt_function, epochs)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_config.get('exchange_name'),
                    session_config.get('timeframe'),
                    session_config.get('timerange'),
                    session_config.get('hyperopt_function'),
                    session_config.get('epochs')
                ))
                session_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"Started optimization session {session_id}")
                return session_id

        except Exception as e:
            self.logger.error(f"Failed to start optimization session: {e}")
            raise

    def start_backtest_session(self, optimization_session_id: Optional[int] = None, **session_config) -> int:
        """Start a new backtest session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO backtest_sessions 
                    (exchange_name, timeframe, timerange, optimization_session_id)
                    VALUES (?, ?, ?, ?)
                """, (
                    session_config.get('exchange_name'),
                    session_config.get('timeframe'),
                    session_config.get('timerange'),
                    optimization_session_id
                ))
                session_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"Started backtest session {session_id}")
                return session_id

        except Exception as e:
            self.logger.error(f"Failed to start backtest session: {e}")
            raise

    def save_hyperopt_result(self, result: HyperoptResult, session_id: Optional[int] = None) -> int:
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
                    INSERT INTO hyperopt_runs (
                        strategy_name, max_open_trades, timeframe, stake_amount, stake_currency,
                        timerange, pair_whitelist, exchange_name, hyperopt_function, epochs, spaces,
                        total_profit_pct, total_profit_abs, total_trades, win_rate, avg_profit_pct,
                        max_drawdown_pct, sharpe_ratio, calmar_ratio, sortino_ratio, profit_factor,
                        expectancy, config_file_path, hyperopt_result_file_path,
                        optimization_duration_seconds, run_number, session_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.strategy_name, result.max_open_trades, result.timeframe,
                    result.stake_amount, result.stake_currency, result.timerange,
                    json.dumps(result.pair_whitelist), result.exchange_name,
                    result.hyperopt_function, result.epochs, json.dumps(result.spaces),
                    result.total_profit_pct, result.total_profit_abs, result.total_trades,
                    result.win_rate, result.avg_profit_pct, result.max_drawdown_pct,
                    result.sharpe_ratio, result.calmar_ratio, result.sortino_ratio,
                    result.profit_factor, result.expectancy, str(config_path), str(hyperopt_path),
                    result.optimization_duration, result.run_number, session_id
                ))

                hyperopt_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"Saved hyperopt result {hyperopt_id} for {result.strategy_name}")
                return hyperopt_id

        except Exception as e:
            self.logger.error(f"Failed to save hyperopt result: {e}")
            raise

    def save_backtest_result(self, result: BacktestResult, session_id: Optional[int] = None) -> int:
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
                    INSERT INTO backtest_runs (
                        strategy_name, max_open_trades, timeframe, stake_amount, stake_currency,
                        timerange, pair_whitelist, exchange_name, total_profit_pct, total_profit_abs,
                        total_trades, win_rate, avg_profit_pct, max_drawdown_pct, max_drawdown_abs,
                        sharpe_ratio, calmar_ratio, sortino_ratio, profit_factor, expectancy,
                        winning_trades, losing_trades, draw_trades, best_trade_pct, worst_trade_pct,
                        avg_trade_duration, config_file_path, backtest_result_file_path,
                        backtest_duration_seconds, hyperopt_id, session_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    str(config_path), str(backtest_path), result.backtest_duration,
                    result.hyperopt_id, session_id
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
                SELECT * FROM hyperopt_runs 
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
                SELECT * FROM backtest_runs 
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
                    h.hyperopt_timestamp,

                    b.id as backtest_id,
                    b.total_profit_pct as backtest_profit,
                    b.total_trades as backtest_trades,
                    b.win_rate as backtest_win_rate,
                    b.max_drawdown_pct as backtest_drawdown,
                    b.sharpe_ratio as backtest_sharpe,
                    b.backtest_timestamp,

                    (h.total_profit_pct - b.total_profit_pct) as reality_gap_pct

                FROM hyperopt_runs h
                LEFT JOIN backtest_runs b ON h.id = b.hyperopt_id
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

    def save_backtest_trades(self, backtest_id: int, trades: List[Dict]) -> None:
        """Save individual trade records for detailed analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for trade in trades:
                    conn.execute("""
                        INSERT INTO backtest_trades (
                            backtest_id, pair, open_timestamp, close_timestamp,
                            open_rate, close_rate, amount, profit_pct, profit_abs,
                            trade_duration, exit_reason, is_open
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        backtest_id, trade['pair'], trade['open_timestamp'], trade['close_timestamp'],
                        trade['open_rate'], trade['close_rate'], trade['amount'],
                        trade['profit_pct'], trade['profit_abs'], trade['trade_duration'],
                        trade['exit_reason'], trade.get('is_open', False)
                    ))

                conn.commit()
                self.logger.info(f"Saved {len(trades)} trade records for backtest {backtest_id}")

        except Exception as e:
            self.logger.error(f"Failed to save backtest trades: {e}")

    def get_backtest_trade_analysis(self, backtest_id: int) -> Dict[str, Any]:
        """Get detailed trade analysis for a backtest."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get trade statistics
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        AVG(profit_pct) as avg_profit_pct,
                        SUM(profit_abs) as total_profit_abs,
                        AVG(trade_duration) as avg_duration_minutes,
                        MIN(profit_pct) as worst_trade_pct,
                        MAX(profit_pct) as best_trade_pct
                    FROM backtest_trades
                    WHERE backtest_id = ?
                """, (backtest_id,))

                trade_stats = dict(cursor.fetchone())

                # Get trades by pair
                cursor = conn.execute("""
                    SELECT 
                        pair,
                        COUNT(*) as trade_count,
                        AVG(profit_pct) as avg_profit_pct,
                        SUM(profit_abs) as total_profit
                    FROM backtest_trades
                    WHERE backtest_id = ?
                    GROUP BY pair
                    ORDER BY total_profit DESC
                """, (backtest_id,))

                trades_by_pair = [dict(row) for row in cursor.fetchall()]

                # Get exit reasons
                cursor = conn.execute("""
                    SELECT 
                        exit_reason,
                        COUNT(*) as count,
                        AVG(profit_pct) as avg_profit_pct
                    FROM backtest_trades
                    WHERE backtest_id = ?
                    GROUP BY exit_reason
                    ORDER BY count DESC
                """, (backtest_id,))

                exit_reasons = [dict(row) for row in cursor.fetchall()]

                return {
                    'trade_stats': trade_stats,
                    'trades_by_pair': trades_by_pair,
                    'exit_reasons': exit_reasons
                }

        except Exception as e:
            self.logger.error(f"Failed to get backtest trade analysis: {e}")
            return {}

    def update_optimization_session_summary(self, session_id: int, total_strategies: int,
                                            successful_strategies: int, failed_strategies: int,
                                            session_duration: int) -> None:
        """Update optimization session summary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE optimization_sessions 
                    SET total_strategies = ?, successful_strategies = ?, 
                        failed_strategies = ?, session_duration_seconds = ?
                    WHERE id = ?
                """, (total_strategies, successful_strategies, failed_strategies,
                      session_duration, session_id))
                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to update optimization session summary: {e}")

    def update_backtest_session_summary(self, session_id: int, total_strategies: int,
                                        successful_backtests: int, failed_backtests: int,
                                        session_duration: int) -> None:
        """Update backtest session summary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE backtest_sessions 
                    SET total_strategies = ?, successful_backtests = ?, 
                        failed_backtests = ?, session_duration_seconds = ?
                    WHERE id = ?
                """, (total_strategies, successful_backtests, failed_backtests,
                      session_duration, session_id))
                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to update backtest session summary: {e}")

    def migrate_from_old_schema(self) -> bool:
        """
        Migrate data from the old schema to the new enhanced schema.
        This method helps transition existing data to the new structure.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if old table exists
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='strategy_optimizations'
                """)

                if not cursor.fetchone():
                    self.logger.info("No old schema found, skipping migration")
                    return True

                self.logger.info("Migrating data from old schema...")

                # Migrate optimization data to hyperopt_runs
                cursor = conn.execute("""
                    INSERT INTO hyperopt_runs (
                        strategy_name, hyperopt_timestamp, max_open_trades, timeframe,
                        stake_amount, stake_currency, timerange, pair_whitelist, exchange_name,
                        hyperopt_function, epochs, total_profit_pct, total_profit_abs,
                        total_trades, win_rate, avg_profit_pct, max_drawdown_pct,
                        sharpe_ratio, config_file_path, hyperopt_result_file_path,
                        optimization_duration_seconds, run_number, session_id, status
                    )
                    SELECT 
                        strategy_name, optimization_timestamp, max_open_trades, timeframe,
                        stake_amount, stake_currency, timerange, pair_whitelist, exchange_name,
                        hyperopt_function, epochs, total_profit_pct, total_profit_abs,
                        total_trades, win_rate, avg_profit_pct, max_drawdown_pct,
                        COALESCE(sharpe_ratio, 0), config_file_path, hyperopt_result_file_path,
                        optimization_duration_seconds, COALESCE(run_number, 1), 
                        (SELECT session_id FROM session_strategies WHERE optimization_id = strategy_optimizations.id LIMIT 1),
                        COALESCE(status, 'completed')
                    FROM strategy_optimizations
                """)

                migrated_count = cursor.rowcount
                self.logger.info(f"Migrated {migrated_count} optimization records")

                # Migrate hyperopt JSON results if they exist
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='hyperopt_json_results'
                """)

                if cursor.fetchone():
                    # Update hyperopt_runs with JSON data references
                    conn.execute("""
                        UPDATE hyperopt_runs 
                        SET hyperopt_result_file_path = COALESCE(hyperopt_result_file_path, 
                            'migrated_from_json_table_id_' || 
                            (SELECT id FROM hyperopt_json_results WHERE optimization_id = hyperopt_runs.id LIMIT 1)
                        )
                        WHERE hyperopt_result_file_path IS NULL
                    """)

                conn.commit()
                self.logger.info("Migration completed successfully")
                return True

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False

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