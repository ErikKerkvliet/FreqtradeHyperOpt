#!/usr/bin/env python3
"""
Database manager for FreqTrade optimization results.
Handles storage and retrieval of optimization data with hybrid file/database approach.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re


@dataclass
class OptimizationResult:
    """Data class for optimization results."""
    strategy_name: str
    total_profit_pct: float
    total_profit_abs: float
    total_trades: int
    win_rate: float
    avg_profit_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    config_data: Dict[str, Any]
    hyperopt_results: Dict[str, Any]
    optimization_duration: int
    run_number: int = 1


class ResultsDatabaseManager:
    """
    Manages the database for FreqTrade optimization results.
    Implements hybrid storage: metadata in SQLite, full configs in JSON files.
    """

    def __init__(self, db_path: str = "freqtrade_results.db", results_dir: str = "results"):
        """
        Initialize the database manager.

        Args:
            db_path: Path to SQLite database file
            results_dir: Directory for storing JSON result files
        """
        self.db_path = db_path
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

        (self.results_dir / "hyperopt").mkdir(exist_ok=True)
        (self.results_dir / "backtest").mkdir(exist_ok=True)

        self.configs_dir = Path("configs")
        self.configs_dir.mkdir(exist_ok=True)

        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")

                # Create tables (will be ignored if they exist)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_optimizations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_name VARCHAR(100) NOT NULL,
                        optimization_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

                        max_open_trades INTEGER,
                        timeframe VARCHAR(10),
                        stake_amount DECIMAL(10, 8),
                        stake_currency VARCHAR(10),

                        pair_whitelist TEXT,
                        pair_blacklist TEXT,
                        exchange_name VARCHAR(50),

                        hyperopt_function VARCHAR(100),
                        epochs INTEGER,
                        timerange VARCHAR(50),

                        total_profit_pct DECIMAL(10, 4),
                        total_profit_abs DECIMAL(15, 8),
                        total_trades INTEGER,
                        win_rate DECIMAL(5, 2),
                        avg_profit_pct DECIMAL(10, 4),
                        max_drawdown_pct DECIMAL(10, 4),
                        sharpe_ratio DECIMAL(10, 4),

                        config_file_path VARCHAR(255),
                        hyperopt_result_file_path VARCHAR(255),

                        optimization_duration_seconds INTEGER,
                        run_number INTEGER DEFAULT 1,
                        status VARCHAR(20) DEFAULT 'completed'
                    )
                """)

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

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_strategies (
                        session_id INTEGER,
                        optimization_id INTEGER,
                        FOREIGN KEY (session_id) REFERENCES optimization_sessions(id),
                        FOREIGN KEY (optimization_id) REFERENCES strategy_optimizations(id)
                    )
                """)

                # NEW TABLE: Store hyperopt JSON results
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS hyperopt_json_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        optimization_id INTEGER NOT NULL,
                        session_id INTEGER,
                        hyperopt_json_data TEXT NOT NULL,
                        created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (optimization_id) REFERENCES strategy_optimizations(id) ON DELETE CASCADE,
                        FOREIGN KEY (session_id) REFERENCES optimization_sessions(id) ON DELETE CASCADE
                    )
                """)

                # Create indexes if they don't exist
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_strategy_profit ON strategy_optimizations(strategy_name, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_timeframe_profit ON strategy_optimizations(timeframe, total_profit_pct)",
                    "CREATE INDEX IF NOT EXISTS idx_timestamp ON strategy_optimizations(optimization_timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_status ON strategy_optimizations(status)",
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_optimization ON hyperopt_json_results(optimization_id)",
                    "CREATE INDEX IF NOT EXISTS idx_hyperopt_session ON hyperopt_json_results(session_id)"
                ]

                for index_sql in indexes:
                    conn.execute(index_sql)

                conn.commit()
                self.logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    def start_session(self, **session_config) -> int:
        """
        Start a new optimization session.

        Args:
            **session_config: Session configuration parameters

        Returns:
            Session ID
        """
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
            self.logger.error(f"Failed to start session: {e}")
            raise

    def save_hyperopt_json_result(self, optimization_id: int, session_id: int, hyperopt_json_data: str) -> int:
        """
        Save the raw hyperopt JSON result to the database.

        Args:
            optimization_id: ID of the optimization record
            session_id: ID of the session
            hyperopt_json_data: Raw JSON string from hyperopt-show command

        Returns:
            ID of the inserted hyperopt JSON record
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO hyperopt_json_results (optimization_id, session_id, hyperopt_json_data)
                    VALUES (?, ?, ?)
                """, (optimization_id, session_id, hyperopt_json_data))

                json_result_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"Saved hyperopt JSON result {json_result_id} for optimization {optimization_id}")
                return json_result_id

        except Exception as e:
            self.logger.error(f"Failed to save hyperopt JSON result: {e}")
            raise

    def get_hyperopt_json_result(self, optimization_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve the hyperopt JSON result for a specific optimization.

        Args:
            optimization_id: ID of the optimization record

        Returns:
            Parsed JSON data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT hyperopt_json_data FROM hyperopt_json_results 
                    WHERE optimization_id = ?
                    ORDER BY created_timestamp DESC
                    LIMIT 1
                """, (optimization_id,))

                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                return None

        except Exception as e:
            self.logger.error(f"Failed to get hyperopt JSON result: {e}")
            return None

    def get_session_hyperopt_results(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Get all hyperopt JSON results for a specific session.

        Args:
            session_id: ID of the session

        Returns:
            List of hyperopt JSON results with metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT hjr.id, hjr.optimization_id, hjr.hyperopt_json_data, hjr.created_timestamp,
                           so.strategy_name, so.total_profit_pct, so.total_trades
                    FROM hyperopt_json_results hjr
                    JOIN strategy_optimizations so ON hjr.optimization_id = so.id
                    WHERE hjr.session_id = ?
                    ORDER BY so.total_profit_pct DESC
                """, (session_id,))

                results = []
                for row in cursor.fetchall():
                    result_dict = dict(row)
                    result_dict['hyperopt_json_data'] = json.loads(result_dict['hyperopt_json_data'])
                    results.append(result_dict)

                return results

        except Exception as e:
            self.logger.error(f"Failed to get session hyperopt results: {e}")
            return []

    def save_optimization_result(self, result: OptimizationResult, session_id: Optional[int] = None) -> int:
        """
        Save optimization result to database and files.

        Args:
            result: OptimizationResult object
            session_id: Optional session ID to link this result to

        Returns:
            Optimization record ID
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save config file
            config_filename = f"{timestamp}_{result.strategy_name}_run{result.run_number}_config.json"
            config_path = self.configs_dir / config_filename
            with open(config_path, 'w') as f:
                json.dump(result.config_data, f, indent=2)

            # Extract config data for database
            config = result.config_data
            pair_whitelist = json.dumps(config.get('exchange', {}).get('pair_whitelist', []))
            pair_blacklist = json.dumps(config.get('exchange', {}).get('pair_blacklist', []))

            # Insert into database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO strategy_optimizations (
                        strategy_name, max_open_trades, timeframe, stake_amount, stake_currency,
                        pair_whitelist, pair_blacklist, exchange_name, hyperopt_function,
                        epochs, timerange, total_profit_pct, total_profit_abs, total_trades,
                        win_rate, avg_profit_pct, max_drawdown_pct, sharpe_ratio,
                        config_file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.strategy_name,
                    config.get('max_open_trades'),
                    config.get('timeframe'),
                    config.get('stake_amount'),
                    config.get('stake_currency'),
                    pair_whitelist,
                    pair_blacklist,
                    config.get('exchange', {}).get('name'),
                    result.hyperopt_results.get('hyperopt_function'),
                    result.hyperopt_results.get('epochs'),
                    result.hyperopt_results.get('timerange'),
                    result.total_profit_pct,
                    result.total_profit_abs,
                    result.total_trades,
                    result.win_rate,
                    result.avg_profit_pct,
                    result.max_drawdown_pct,
                    result.sharpe_ratio,
                    str(config_path)
                ))

                optimization_id = cursor.lastrowid

                # Link to session if provided
                if session_id:
                    conn.execute("""
                        INSERT INTO session_strategies (session_id, optimization_id)
                        VALUES (?, ?)
                    """, (session_id, optimization_id))

                conn.commit()

                self.logger.info(f"Saved optimization result {optimization_id} for {result.strategy_name}")
                return optimization_id

        except Exception as e:
            self.logger.error(f"Failed to save optimization result: {e}")
            raise

    def get_best_strategies(self, limit: int = 10, timeframe: Optional[str] = None) -> List[Dict]:
        """
        Get the best performing strategies.

        Args:
            limit: Number of results to return
            timeframe: Optional timeframe filter

        Returns:
            List of strategy optimization records
        """
        try:
            query = """
                SELECT * FROM strategy_optimizations 
                WHERE status = 'completed'
            """
            params = []

            if timeframe:
                query += " AND timeframe = ?"
                params.append(timeframe)

            query += " ORDER BY total_profit_pct DESC LIMIT ?"
            params.append(limit)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]

                return results

        except Exception as e:
            self.logger.error(f"Failed to get best strategies: {e}")
            return []

    def get_strategy_history(self, strategy_name: str) -> List[Dict]:
        """
        Get optimization history for a specific strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            List of optimization records for the strategy
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM strategy_optimizations 
                    WHERE strategy_name = ?
                    ORDER BY optimization_timestamp DESC
                """, (strategy_name,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            self.logger.error(f"Failed to get strategy history: {e}")
            return []

    def get_config_comparison(self, optimization_ids: List[int]) -> List[Dict]:
        """
        Compare configurations between multiple optimizations.

        Args:
            optimization_ids: List of optimization IDs to compare

        Returns:
            List of comparison data with loaded config files
        """
        try:
            placeholders = ','.join(['?'] * len(optimization_ids))

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(f"""
                    SELECT id, strategy_name, total_profit_pct, config_file_path, hyperopt_result_file_path
                    FROM strategy_optimizations 
                    WHERE id IN ({placeholders})
                    ORDER BY total_profit_pct DESC
                """, optimization_ids)

                results = []
                for row in cursor.fetchall():
                    record = dict(row)

                    # Load config file
                    try:
                        with open(record['config_file_path'], 'r') as f:
                            record['config_data'] = json.load(f)
                    except Exception as e:
                        self.logger.warning(f"Could not load config file {record['config_file_path']}: {e}")
                        record['config_data'] = {}

                    results.append(record)

                return results

        except Exception as e:
            self.logger.error(f"Failed to get config comparison: {e}")
            return []

    def update_session_summary(self, session_id: int, total_strategies: int,
                               successful_strategies: int, failed_strategies: int,
                               session_duration: int) -> None:
        """
        Update session summary with final statistics.

        Args:
            session_id: Session ID
            total_strategies: Total number of strategies processed
            successful_strategies: Number of successful optimizations
            failed_strategies: Number of failed optimizations
            session_duration: Total session duration in seconds
        """
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

                self.logger.info(f"Updated session {session_id} summary")

        except Exception as e:
            self.logger.error(f"Failed to update session summary: {e}")

    def parse_hyperopt_results(self, hyperopt_output: str) -> Dict[str, Any]:
        """
        Parse hyperopt output to extract key metrics.

        Args:
            hyperopt_output: Raw hyperopt output string

        Returns:
            Dictionary with parsed metrics
        """
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
                total = wins + int(win_rate_match.group(2)) + int(win_rate_match.group(3))
                results['win_rate'] = (wins / total * 100) if total > 0 else 0

            # Extract average profit
            avg_profit_match = re.search(r"Avg profit %\s*│\s*([\d.-]+)%", hyperopt_output)
            if avg_profit_match:
                results['avg_profit_pct'] = float(avg_profit_match.group(1))

            # Extract max drawdown
            drawdown_match = re.search(r"Max Drawdown\s*│\s*([\d.-]+)%", hyperopt_output)
            if drawdown_match:
                results['max_drawdown_pct'] = float(drawdown_match.group(1))

            # Try to extract Sharpe ratio (if available)
            sharpe_match = re.search(r"Sharpe\s*│\s*([\d.-]+)", hyperopt_output)
            if sharpe_match:
                results['sharpe_ratio'] = float(sharpe_match.group(1))
            else:
                results['sharpe_ratio'] = 0.0

        except Exception as e:
            self.logger.warning(f"Error parsing hyperopt results: {e}")

        return results