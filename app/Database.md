# FreqTrade Backtest Database Integration

## Overview

This enhancement adds comprehensive database storage and analysis capabilities for FreqTrade backtest results, complementing the existing optimization result storage. The system now tracks both hyperparameter optimization and backtest performance in a unified database structure.

## New Database Tables

### 1. `strategy_backtests`
Main table storing backtest results and metadata:

```sql
CREATE TABLE strategy_backtests (
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
    pair_blacklist TEXT,
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
    optimization_id INTEGER,  -- Link to optimization result
    session_id INTEGER,       -- Link to backtest session
    
    FOREIGN KEY (optimization_id) REFERENCES strategy_optimizations(id),
    FOREIGN KEY (session_id) REFERENCES backtest_sessions(id)
);
```

### 2. `backtest_sessions`
Groups related backtest runs:

```sql
CREATE TABLE backtest_sessions (
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
);
```

### 3. `backtest_trades`
Detailed individual trade records:

```sql
CREATE TABLE backtest_trades (
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
    trade_duration INTEGER,
    
    exit_reason VARCHAR(50),
    is_open BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (backtest_id) REFERENCES strategy_backtests(id) ON DELETE CASCADE
);
```

## Enhanced Features

### 1. BacktestResult Data Class

```python
@dataclass
class BacktestResult:
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
    config_data: Dict[str, Any]
    backtest_results: Dict[str, Any]
    backtest_duration: int
    timeframe: str
    timerange: str
    stake_currency: str
    stake_amount: float
    max_open_trades: int
```

### 2. Enhanced FreqTrade Executor

The `FreqTradeExecutor` now supports:

- **Backtest Execution**: `run_backtest()` method with database integration
- **Batch Backtesting**: `batch_backtest_from_session()` for testing all optimizations from a session
- **Configuration Linking**: `run_strategy_backtest_from_optimization()` to test optimized parameters
- **Session Management**: Separate backtest sessions with links to optimization sessions

### 3. Enhanced Results Analyzer

New analysis capabilities:

```bash
# Show best backtest results
python enhanced_result_analyzer.py best --type backtest --limit 10

# Compare optimization vs backtest results
python enhanced_result_analyzer.py vs RSIStrategy

# Analyze reality gap (overfitting detection)
python enhanced_result_analyzer.py gap --strategy RSIStrategy

# Show detailed trade analysis
python enhanced_result_analyzer.py trades 123

# Show backtest sessions
python enhanced_result_analyzer.py sessions --type backtest
```

### 4. Backtest Runner CLI

New standalone CLI for running backtests:

```bash
# Run single backtest
python backtest_runner.py single RSIStrategy config.json --timerange 20240101-20240201

# Run backtest from optimization result
python backtest_runner.py from-opt 123

# Batch backtest all strategies from optimization session
python backtest_runner.py batch 15 --limit 5

# List available optimizations for backtesting
python backtest_runner.py list-opts

# List available sessions for batch backtesting
python backtest_runner.py list-sessions
```

## Key Benefits

### 1. **Reality Gap Analysis**
- Compare optimization results with backtest performance
- Detect overfitting and unrealistic expectations
- Track the difference between in-sample and out-of-sample performance

### 2. **Comprehensive Trade Analysis**
- Store individual trade details for deep analysis
- Analyze performance by trading pair
- Understand exit reasons and trade duration patterns

### 3. **Session Linking**
- Link backtest sessions to optimization sessions
- Track the full workflow from optimization to validation
- Maintain audit trail of parameter evolution

### 4. **Advanced Metrics**
- Store Sharpe, Calmar, and Sortino ratios
- Track profit factor and expectancy
- Monitor drawdown patterns and trade distribution

### 5. **Batch Operations**
- Automatically backtest all optimized strategies
- Compare multiple strategies systematically
- Generate comprehensive performance reports

## Usage Examples

### Example 1: Basic Backtest with Database Storage

```python
from modules.freqtrade_executor import FreqTradeExecutor
from modules.optimization_config import OptimizationConfig

# Initialize executor
config = OptimizationConfig(...)
executor = FreqTradeExecutor(config)

# Start backtest session
session_id = executor.start_backtest_session()

# Run backtest
result = executor.run_backtest(
    strategy_name="RSIStrategy",
    config_file="config.json",
    timerange="20240101-20240201"
)

if result.success:
    print(f"Backtest completed! Database ID: {result.backtest_id}")
```

### Example 2: Batch Backtest from Optimization Session

```python
# Run backtests for top 5 strategies from optimization session 15
results = executor.batch_backtest_from_session(session_id=15, limit=5)

successful = sum(1 for r in results if r.success)
print(f"Completed {successful}/{len(results)} backtests successfully")
```

### Example 3: Reality Gap Analysis

```python
from modules.enhanced_result_analyzer import EnhancedResultsAnalyzer

analyzer = EnhancedResultsAnalyzer()

# Analyze reality gap for specific strategy
analyzer.show_reality_gap_analysis("RSIStrategy")

# Compare optimization vs backtest for all strategies
analyzer.show_optimization_vs_backtest_comparison("RSIStrategy")
```

### Example 4: Trade-Level Analysis

```python
# Get detailed trade analysis for a backtest
trade_analysis = db_manager.get_backtest_trade_analysis(backtest_id=123)

print(f"Total trades: {trade_analysis['trade_stats']['total_trades']}")
print(f"Best performing pair: {trade_analysis['trades_by_pair'][0]['pair']}")
print(f"Most common exit reason: {trade_analysis['exit_reasons'][0]['exit_reason']}")
```

## Database Queries

### Find Strategies with Consistent Performance

```sql
SELECT 
    so.strategy_name,
    AVG(so.total_profit_pct) as avg_opt_profit,
    AVG(sb.total_profit_pct) as avg_bt_profit,
    (AVG(so.total_profit_pct) - AVG(sb.total_profit_pct)) as reality_gap,
    COUNT(sb.id) as backtest_count
FROM strategy_optimizations so
JOIN strategy_backtests sb ON sb.optimization_id = so.id
WHERE so.status = 'completed' AND sb.status = 'completed'
GROUP BY so.strategy_name
HAVING backtest_count >= 3
ORDER BY reality_gap ASC;
```

### Top Performing Backtests by Sharpe Ratio

```sql
SELECT 
    strategy_name,
    total_profit_pct,
    sharpe_ratio,
    calmar_ratio,
    total_trades,
    timeframe
FROM strategy_backtests
WHERE status = 'completed' 
  AND total_trades >= 20
  AND sharpe_ratio IS NOT NULL
ORDER BY sharpe_ratio DESC
LIMIT 10;
```

### Trade Analysis by Pair

```sql
SELECT 
    bt.pair,
    COUNT(btr.id) as trade_count,
    AVG(btr.profit_pct) as avg_profit_pct,
    SUM(btr.profit_abs) as total_profit,
    AVG(btr.trade_duration) as avg_duration_minutes
FROM strategy_backtests bt
JOIN backtest_trades btr ON bt.id = btr.backtest_id
WHERE bt.strategy_name = 'RSIStrategy'
GROUP BY bt.pair
ORDER BY total_profit DESC;
```

## File Organization

The enhanced system maintains the hybrid storage approach:

```
optimization_results/
├── configs/                    # Strategy configurations
│   ├── 20241216_123456_RSIStrategy_backtest_config.json
│   └── 20241216_123456_RSIStrategy_run1_config.json
├── hyperopt_results/          # Optimization results
│   └── 20241216_123456_RSIStrategy_run1_hyperopt.json
└── backtest_results/          # New: Backtest results
    └── 20241216_123456_RSIStrategy_backtest_results.json
```

## Migration Considerations

### Existing Users
- The new tables are created automatically on first run
- Existing optimization data remains unchanged
- New indexes improve query performance

### Performance Impact
- Additional storage for backtest results and trades
- Minimal impact on optimization workflows
- Optional trade detail storage (can be disabled)

## Best Practices

### 1. **Systematic Validation**
```python
# Always backtest your best optimizations
best_optimizations = db_manager.get_best_strategies(limit=10)
for opt in best_optimizations:
    executor.run_strategy_backtest_from_optimization(opt['id'])
```

### 2. **Reality Gap Monitoring**
```python
# Regularly check for overfitting
analyzer.show_reality_gap_analysis()

# Alert on high gaps
if avg_reality_gap > 5.0:
    print("⚠️ High reality gap detected - review optimization parameters")
```

### 3. **Trade Analysis**
```python
# Analyze trade patterns
for backtest in recent_backtests:
    trade_analysis = db_manager.get_backtest_trade_analysis(backtest['id'])
    if trade_analysis['trade_stats']['avg_duration_minutes'] > 1440:  # > 24 hours
        print(f"Long holding periods detected in {backtest['strategy_name']}")
```

### 4. **Session Organization**
```python
# Link backtest sessions to optimization sessions
opt_session_id = executor.start_session()
# ... run optimizations ...

bt_session_id = executor.start_backtest_session(
    optimization_session_id=opt_session_id
)
# ... run backtests ...
```

## Future Enhancements

### Planned Features
1. **Walk-Forward Analysis**: Time-series validation with rolling windows
2. **Monte Carlo Simulation**: Statistical robustness testing
3. **Portfolio Backtesting**: Multi-strategy portfolio analysis
4. **Risk Metrics**: VaR, CVaR, and other risk measurements
5. **Benchmark Comparison**: Compare against buy-and-hold strategies

### Integration Opportunities
1. **GUI Dashboard**: Visual backtest analysis in the existing dashboard
2. **Automated Alerts**: Notifications for significant performance gaps
3. **Report Generation**: Automated PDF reports with charts and analysis
4. **API Endpoints**: REST API for external analysis tools

This backtest database integration provides a comprehensive foundation for systematic strategy validation and performance analysis, helping traders make more informed decisions based on realistic backtesting data.