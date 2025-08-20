# FreqTrade Results Database - Simplified Schema

## Overview

The FreqTrade optimization system uses a simplified two-table database structure designed for efficient storage and analysis of hyperparameter optimization and backtesting results. This streamlined approach focuses on the essential data needed for performance analysis and reality gap detection.

## Database Schema

### Core Tables

#### 1. `hyperopt_results`
Main table storing hyperparameter optimization results:

```sql
CREATE TABLE hyperopt_results (
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

    -- Trade Statistics
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
);
```

#### 2. `backtest_results`
Table storing backtest validation results:

```sql
CREATE TABLE backtest_results (
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
);
```

### Indexes

The database includes performance indexes for common query patterns:

```sql
-- Hyperopt indexes
CREATE INDEX idx_hyperopt_strategy_profit ON hyperopt_results(strategy_name, total_profit_pct);
CREATE INDEX idx_hyperopt_timeframe_profit ON hyperopt_results(timeframe, total_profit_pct);
CREATE INDEX idx_hyperopt_timestamp ON hyperopt_results(timestamp);
CREATE INDEX idx_hyperopt_status ON hyperopt_results(status);

-- Backtest indexes
CREATE INDEX idx_backtest_strategy_profit ON backtest_results(strategy_name, total_profit_pct);
CREATE INDEX idx_backtest_timeframe_profit ON backtest_results(timeframe, total_profit_pct);
CREATE INDEX idx_backtest_timestamp ON backtest_results(timestamp);
CREATE INDEX idx_backtest_hyperopt ON backtest_results(hyperopt_id);
CREATE INDEX idx_backtest_status ON backtest_results(status);
```

## Key Features

### 1. **Simplified Architecture**
- Only two main tables instead of complex multi-table schemas
- Embedded JSON for configuration and detailed results
- Direct foreign key relationship between backtests and hyperopt runs

### 2. **Reality Gap Analysis**
The database structure enables easy comparison between optimization and backtest results:

```sql
SELECT 
    h.strategy_name,
    h.total_profit_pct as hyperopt_profit,
    b.total_profit_pct as backtest_profit,
    (h.total_profit_pct - b.total_profit_pct) as reality_gap
FROM hyperopt_results h
LEFT JOIN backtest_results b ON h.id = b.hyperopt_id
WHERE h.status = 'completed'
ORDER BY ABS(h.total_profit_pct - COALESCE(b.total_profit_pct, 0)) DESC;
```

### 3. **Session Tracking**
Session information is stored as JSON in the `session_info` field:

```json
{
    "session_name": "OptSession_20241216_143022",
    "start_time": "2024-12-16T14:30:22",
    "exchange": "binance",
    "timeframe": "5m",
    "timerange": "20231216-",
    "hyperopt_function": "SharpeHyperOptLoss",
    "epochs": 200,
    "strategies_processed": 5,
    "strategies_successful": 4,
    "duration_seconds": 3600
}
```

### 4. **Comprehensive Metrics**
Both tables store essential performance metrics:
- **Profit Metrics**: Total profit %, absolute profit, average profit
- **Risk Metrics**: Maximum drawdown, Sharpe ratio, Calmar ratio, Sortino ratio
- **Trade Statistics**: Win rate, total trades, best/worst trades
- **Advanced Analytics**: Profit factor, expectancy

## Data Classes

### HyperoptResult
```python
@dataclass
class HyperoptResult(TradingResult):
    # Hyperopt specific
    hyperopt_function: str
    epochs: int
    spaces: List[str]
    
    # Metadata
    hyperopt_json_data: Dict[str, Any]
    optimization_duration: int
    run_number: int = 1
```

### BacktestResult
```python
@dataclass
class BacktestResult(TradingResult):
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
```

## Usage Examples

### Finding Best Performing Strategies

```sql
-- Top 10 hyperopt strategies
SELECT strategy_name, total_profit_pct, total_trades, win_rate, sharpe_ratio
FROM hyperopt_results 
WHERE status = 'completed' AND total_trades >= 10
ORDER BY total_profit_pct DESC 
LIMIT 10;
```

### Reality Gap Analysis

```sql
-- Strategies with highest overfitting risk
SELECT 
    h.strategy_name,
    h.total_profit_pct as opt_profit,
    b.total_profit_pct as bt_profit,
    (h.total_profit_pct - b.total_profit_pct) as gap,
    CASE 
        WHEN (h.total_profit_pct - b.total_profit_pct) > 5 THEN 'High Overfitting Risk'
        WHEN (h.total_profit_pct - b.total_profit_pct) < -2 THEN 'Underoptimized'
        ELSE 'Acceptable'
    END as assessment
FROM hyperopt_results h
JOIN backtest_results b ON h.id = b.hyperopt_id
WHERE h.status = 'completed' AND b.status = 'completed'
ORDER BY gap DESC;
```

### Performance Timeline

```sql
-- Strategy performance over time
SELECT 
    'hyperopt' as type, 
    id, 
    timestamp, 
    total_profit_pct, 
    total_trades,
    run_number as details
FROM hyperopt_results 
WHERE strategy_name = 'RSIStrategy'

UNION ALL

SELECT 
    'backtest' as type,
    id,
    timestamp,
    total_profit_pct,
    total_trades,
    CAST(hyperopt_id as TEXT) as details
FROM backtest_results 
WHERE strategy_name = 'RSIStrategy'

ORDER BY timestamp DESC;
```

### Session Analysis

```sql
-- Session performance summary
SELECT 
    json_extract(session_info, '$.session_name') as session,
    json_extract(session_info, '$.start_time') as start_time,
    COUNT(*) as total_runs,
    AVG(total_profit_pct) as avg_profit,
    MAX(total_profit_pct) as best_profit,
    json_extract(session_info, '$.duration_seconds') as duration
FROM hyperopt_results 
WHERE session_info IS NOT NULL
GROUP BY json_extract(session_info, '$.session_name')
ORDER BY start_time DESC;
```

## File Organization

The database works in conjunction with a structured file system:

```
optimization_results/
├── configs/                    # Strategy configurations
│   ├── 20241216_143022_RSIStrategy_run1_config.json
│   └── 20241216_143022_RSIStrategy_backtest_config.json
├── hyperopt_results/          # Detailed hyperopt outputs
│   └── 20241216_143022_RSIStrategy_run1_hyperopt.json
└── backtest_results/          # Detailed backtest outputs
    └── 20241216_143022_RSIStrategy_backtest_results.json
```

## Analysis Tools

### CLI Analyzer
The system includes a comprehensive CLI analyzer:

```bash
# Show best performing strategies
python result_analyzer.py best-hyperopt --limit 10

# Reality gap analysis
python result_analyzer.py gap --strategy RSIStrategy

# Strategy comparison
python result_analyzer.py vs RSIStrategy

# Database statistics
python result_analyzer.py stats

# Export best configurations
python result_analyzer.py export hyperopt --limit 5
```

### Backtest Runner
Dedicated tool for running validation backtests:

```bash
# Run backtest from hyperopt result
python backtest_runner.py from-hyperopt 123

# Batch backtest best strategies
python backtest_runner.py batch --limit 5

# Show untested strategies
python backtest_runner.py list-untested
```

## Migration Support

The database manager includes migration support from older schema versions:

```python
# Migrate from old complex schema
db_manager.migrate_from_old_schema()

# Cleanup old tables after migration
db_manager.cleanup_old_tables(confirm=True)
```

## Performance Considerations

### Optimization Tips
- **Indexes**: Carefully designed indexes for common query patterns
- **JSON Storage**: Configuration and detailed results stored as JSON for flexibility
- **Batch Operations**: Efficient bulk insert operations for multiple optimizations
- **Foreign Keys**: Proper relationships with foreign key constraints

### Storage Efficiency
- **Minimal Tables**: Only two main tables reduce complexity
- **Embedded Data**: JSON fields eliminate need for separate detail tables
- **Optional Fields**: NULL-able fields for optional data reduce storage
- **File References**: Large binary data stored as files, referenced by path

## Best Practices

### 1. **Data Integrity**
- Always use transactions for multi-table operations
- Validate JSON data before storage
- Handle missing or null values gracefully

### 2. **Performance**
- Use parameterized queries to prevent SQL injection
- Leverage indexes for filtering and sorting
- Consider pagination for large result sets

### 3. **Analysis**
- Compare optimization vs backtest results regularly
- Monitor reality gap trends over time
- Use session information for workflow tracking

### 4. **Maintenance**
- Regularly backup the database file
- Monitor database size and performance
- Archive old results when appropriate

This simplified database structure provides a robust foundation for FreqTrade optimization analysis while maintaining performance and ease of use.