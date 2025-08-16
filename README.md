# FreqTrade Hyperparameter Optimization Automation

A comprehensive Python application that automates the hyperparameter optimization process for multiple FreqTrade strategies with advanced database storage and analysis capabilities.

## Features

- ✅ **Automated Environment Setup**: Reads configuration from `.env` file and activates FreqTrade virtual environment
- ✅ **Data Management**: Downloads trading data for all specified pairs automatically
- ✅ **Multi-Strategy Processing**: Iterates through all strategy files in the strategies folder
- ✅ **Triple Optimization**: Runs hyperparameter optimization 3 times for each strategy for better results
- ✅ **Database Storage**: Stores optimization results in SQLite database for fast querying and analysis
- ✅ **Hybrid File Storage**: Combines database metadata with detailed JSON file storage
- ✅ **Advanced Analytics**: Query, compare, and analyze optimization results with built-in tools
- ✅ **Smart Results Export**: Exports best results with profit percentage naming
- ✅ **Session Tracking**: Groups optimization runs and tracks overall performance
- ✅ **Robust Error Handling**: Gracefully handles errors and provides detailed logging
- ✅ **Cross-Platform Support**: Works on both Windows and Unix/Linux systems
- ✅ **Progress Tracking**: Real-time progress indicators and comprehensive logging
- ✅ **Summary Reports**: Detailed summary of successful and failed optimizations

## Installation

1. **Clone or download the application files**
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your environment configuration**:
   - Copy `.env.template` to `.env`
   - Fill in your specific FreqTrade configuration

4. **Ensure your FreqTrade installation is ready**:
   - FreqTrade should be installed with a virtual environment (`.venv`)
   - Strategies should be in `user_data/strategies/` directory
   - The `config_template.json` should be in your project root

## Configuration

### Environment Variables (.env file)

```bash
# Path to your FreqTrade installation directory
FREQTRADE_PATH=/path/to/your/freqtrade

# Exchange configuration
EXCHANGE=binance
PAIR_DATA_EXCHANGE=binance

# Trading timeframe
TIMEFRAME=5m

# Historical data in days (will calculate timerange automatically)
HISTORICAL_DATA_IN_DAYS=365

# Trading pairs (comma-separated, no spaces around commas)
PAIRS=BTC/USDT,ETH/USDT,ADA/USDT,DOT/USDT,LINK/USDT

# Hyperopt loss function
HYPERFUNCTION=SharpeHyperOptLoss
```

### Requirements File

```txt
python-dotenv
tabulate
```

### Directory Structure

```
your-project/
├── freqtrade_optimizer.py           # Main application
├── optimization_config.py           # Configuration data class
├── strategy_config_manager.py       # Strategy config management
├── results_database_manager.py      # Database management
├── results_analyzer.py              # Query and analysis tool
├── .env                             # Your configuration
├── config_template.json             # FreqTrade config template
├── requirements.txt                 # Python dependencies
├── freqtrade_results.db            # SQLite database (auto-created)
├── config_files/                   # Generated strategy configs (auto-created)
├── optimization_results/            # Database-managed result files
│   ├── configs/                    # Strategy configurations
│   └── hyperopt_results/           # Detailed hyperopt outputs
└── logs/                           # Application logs (auto-created)
```

## Usage

### Basic Usage

```bash
# Run optimization (same as before)
python freqtrade_optimizer.py
```

### Database Analysis Commands

```bash
# Show top 10 performing strategies
python results_analyzer.py best --limit 10

# Show best strategies for specific timeframe
python results_analyzer.py best --timeframe 5m --limit 5

# Show only strategies with minimum trades
python results_analyzer.py best --min-trades 20 --limit 10

# Compare multiple strategies
python results_analyzer.py compare RSIStrategy MACDStrategy EMAStrategy

# Analyze performance by timeframe
python results_analyzer.py timeframes

# Show recent optimization sessions
python results_analyzer.py sessions --limit 5

# Show detailed configuration for specific optimization
python results_analyzer.py config 123

# Export best configurations to files
python results_analyzer.py export --limit 5 --output best_configs
```

### Example Output

```
[2024-01-15 10:30:00] Starting FreqTrade optimization process...
[2024-01-15 10:30:01] Configuration loaded successfully
[2024-01-15 10:30:01] FreqTrade path: /home/user/freqtrade
[2024-01-15 10:30:01] Exchange: binance
[2024-01-15 10:30:01] Timeframe: 5m
[2024-01-15 10:30:01] Pairs: BTC/USDT, ETH/USDT, ADA/USDT
[2024-01-15 10:30:02] Started optimization session 15
[2024-01-15 10:30:02] Starting data download...
[2024-01-15 10:30:05] Data download completed successfully
[2024-01-15 10:30:06] Found 5 strategies: RSIStrategy, MACDStrategy, BBStrategy, EMAStrategy, StochStrategy
[2024-01-15 10:30:07] Processing strategy: RSIStrategy
[2024-01-15 10:30:08] Starting hyperopt for RSIStrategy (Run 1/3)...
[2024-01-15 10:45:22] Hyperopt completed successfully for RSIStrategy (Run 1) - Profit: 23.45% - Saved as DB record 87
[2024-01-15 10:45:23] Starting hyperopt for RSIStrategy (Run 2/3)...
[2024-01-15 11:00:15] Hyperopt completed successfully for RSIStrategy (Run 2) - Profit: 21.87% - Saved as DB record 88
[2024-01-15 11:00:16] Starting hyperopt for RSIStrategy (Run 3/3)...
[2024-01-15 11:15:45] Hyperopt completed successfully for RSIStrategy (Run 3) - Profit: 25.12% - Saved as DB record 89
[2024-01-15 11:15:46] ✓ RSIStrategy optimization completed successfully
...
============================================================
OPTIMIZATION SUMMARY
============================================================
Total strategies processed: 5
Successful optimizations: 4
Failed optimizations: 1

TOP 5 PERFORMERS THIS SESSION:
----------------------------------------
1. RSIStrategy - +25.12% (45 trades, 67.8% win rate)
2. MACDStrategy - +18.67% (52 trades, 63.5% win rate)
3. EMAStrategy - +12.34% (38 trades, 60.5% win rate)
4. BBStrategy - +8.91% (41 trades, 58.3% win rate)
============================================================
Session ID: 15
Use the database query tools to analyze results in detail.
============================================================
```

## Database Analysis Examples

### Query Top Performers

```bash
$ python results_analyzer.py best --limit 5

🏆 TOP 5 STRATEGIES
================================================================================
┌─────────────┬──────────────┬─────────┬──────────┬─────────────┬──────────────┬───────────┬────────────┬─────┐
│ Strategy    │ Total Profit │ Trades  │ Win Rate │ Avg Profit  │ Max Drawdown │ Timeframe │ Date       │ Run │
├─────────────┼──────────────┼─────────┼──────────┼─────────────┼──────────────┼───────────┼────────────┼─────┤
│ RSIStrategy │ +25.12%      │ 45      │ 67.8%    │ +0.56%      │ -8.45%       │ 5m        │ 2024-01-15 │ 3   │
│ MACDStrat   │ +23.89%      │ 38      │ 71.1%    │ +0.63%      │ -6.23%       │ 15m       │ 2024-01-14 │ 2   │
│ EMAStrategy │ +18.67%      │ 52      │ 63.5%    │ +0.36%      │ -9.12%       │ 5m        │ 2024-01-15 │ 1   │
│ BBStrategy  │ +15.34%      │ 41      │ 58.3%    │ +0.37%      │ -11.67%      │ 1h        │ 2024-01-13 │ 3   │
│ StochStrat  │ +12.45%      │ 33      │ 60.6%    │ +0.38%      │ -7.89%       │ 15m       │ 2024-01-14 │ 1   │
└─────────────┴──────────────┴─────────┴──────────┴─────────────┴──────────────┴───────────┴────────────┴─────┘
```

### Compare Strategies

```bash
$ python results_analyzer.py compare RSIStrategy MACDStrategy EMAStrategy

📊 STRATEGY COMPARISON
================================================================================
┌─────────────┬──────┬─────────────┬─────────┬─────────┬─────────────┬──────────────┬─────────────┐
│ Strategy    │ Runs │ Avg Profit  │ Best    │ Worst   │ Avg Trades  │ Avg Win Rate │ Avg Drawdown│
├─────────────┼──────┼─────────────┼─────────┼─────────┼─────────────┼──────────────┼─────────────┤
│ RSIStrategy │ 9    │ +19.23%     │ +25.12% │ +11.45% │ 43          │ 65.2%        │ -9.12%      │
│ MACDStrat   │ 6    │ +17.89%     │ +23.89% │ +8.23%  │ 39          │ 68.1%        │ -7.45%      │
│ EMAStrategy │ 6    │ +14.56%     │ +18.67% │ +6.78%  │ 48          │ 61.3%        │ -10.23%     │
└─────────────┴──────┴─────────────┴─────────┴─────────┴─────────────┴──────────────┴─────────────┘
```

### Timeframe Analysis

```bash
$ python results_analyzer.py timeframes

⏰ TIMEFRAME ANALYSIS
================================================================================
┌───────────┬────────────┬─────────────┬─────────────┬─────────────┬─────────────┬──────────────┐
│ Timeframe │ Total Opts │ Strategies  │ Avg Profit  │ Best Profit │ Avg Trades  │ Avg Win Rate │
├───────────┼────────────┼─────────────┼─────────────┼─────────────┼─────────────┼──────────────┤
│ 5m        │ 24         │ 8           │ +16.23%     │ +25.12%     │ 45          │ 64.2%        │
│ 15m       │ 18         │ 6           │ +14.67%     │ +23.89%     │ 38          │ 66.8%        │
│ 1h        │ 12         │ 4           │ +11.45%     │ +19.34%     │ 28          │ 62.1%        │
│ 4h        │ 6          │ 2           │ +8.23%      │ +12.67%     │ 18          │ 58.9%        │
└───────────┴────────────┴─────────────┴─────────────┴─────────────┴─────────────┴──────────────┘
```

## Advanced SQL Queries

You can directly query the SQLite database for custom analysis:

### Find Best Strategy per Timeframe

```sql
SELECT 
    timeframe,
    strategy_name,
    total_profit_pct,
    total_trades,
    win_rate
FROM strategy_optimizations s1
WHERE total_profit_pct = (
    SELECT MAX(total_profit_pct) 
    FROM strategy_optimizations s2 
    WHERE s2.timeframe = s1.timeframe
    AND s2.total_trades >= 10
)
ORDER BY timeframe, total_profit_pct DESC;
```

### Strategy Performance Over Time

```sql
SELECT 
    strategy_name,
    DATE(optimization_timestamp) as date,
    AVG(total_profit_pct) as avg_profit,
    COUNT(*) as runs,
    MAX(total_profit_pct) as best_profit
FROM strategy_optimizations 
WHERE strategy_name = 'RSIStrategy'
GROUP BY strategy_name, DATE(optimization_timestamp)
ORDER BY date DESC;
```

### Find Consistent Performers

```sql
SELECT 
    strategy_name,
    COUNT(*) as total_runs,
    AVG(total_profit_pct) as avg_profit,
    MIN(total_profit_pct) as worst_profit,
    MAX(total_profit_pct) as best_profit,
    (MAX(total_profit_pct) - MIN(total_profit_pct)) as profit_range,
    AVG(win_rate) as avg_win_rate
FROM strategy_optimizations 
WHERE total_trades >= 10
GROUP BY strategy_name
HAVING total_runs >= 3
ORDER BY avg_profit DESC, profit_range ASC;
```

### High-Frequency Trading Analysis

```sql
SELECT 
    strategy_name,
    timeframe,
    AVG(total_trades) as avg_trades_per_run,
    AVG(total_profit_pct) as avg_profit,
    AVG(win_rate) as avg_win_rate,
    COUNT(*) as optimization_runs
FROM strategy_optimizations 
WHERE timeframe IN ('1m', '5m', '15m')
AND total_trades >= 50
GROUP BY strategy_name, timeframe
ORDER BY avg_profit DESC;
```

### Risk-Adjusted Performance

```sql
SELECT 
    strategy_name,
    AVG(total_profit_pct) as avg_profit,
    AVG(max_drawdown_pct) as avg_drawdown,
    AVG(sharpe_ratio) as avg_sharpe,
    (AVG(total_profit_pct) / ABS(AVG(max_drawdown_pct))) as profit_to_drawdown_ratio
FROM strategy_optimizations 
WHERE total_trades >= 20
AND max_drawdown_pct < 0
GROUP BY strategy_name
ORDER BY profit_to_drawdown_ratio DESC;
```

### Session Performance Tracking

```sql
SELECT 
    os.id as session_id,
    os.session_timestamp,
    os.successful_strategies,
    os.total_strategies,
    ROUND(os.successful_strategies * 100.0 / os.total_strategies, 1) as success_rate,
    os.session_duration_seconds / 60 as duration_minutes,
    AVG(so.total_profit_pct) as avg_session_profit
FROM optimization_sessions os
LEFT JOIN session_strategies ss ON os.id = ss.session_id
LEFT JOIN strategy_optimizations so ON ss.optimization_id = so.id
GROUP BY os.id, os.session_timestamp, os.successful_strategies, os.total_strategies, os.session_duration_seconds
ORDER BY os.session_timestamp DESC
LIMIT 10;
```

### Best Configurations for Specific Pairs

```sql
SELECT 
    strategy_name,
    total_profit_pct,
    total_trades,
    win_rate,
    pair_whitelist,
    config_file_path
FROM strategy_optimizations 
WHERE pair_whitelist LIKE '%BTC/USDT%'
AND total_trades >= 15
ORDER BY total_profit_pct DESC
LIMIT 10;
```

## Features Explained

### Database Integration
- **SQLite Database**: Stores searchable metadata for fast queries
- **JSON Files**: Preserves complete configurations and detailed results
- **Session Tracking**: Groups optimization runs and tracks overall performance
- **Hybrid Storage**: Best of both worlds - fast queries and complete data

### Multi-Run Optimization
Each strategy is optimized 3 times to account for randomness in hyperparameter optimization. All results are stored in the database for analysis.

### Smart File Organization
- Database stores searchable metadata (profit, trades, timeframes, etc.)
- JSON files contain complete configurations and detailed hyperopt results
- Automatic file organization in timestamped directories

### Advanced Analytics
- Compare strategies across multiple dimensions
- Track performance trends over time
- Analyze optimal timeframes and configurations
- Export best configurations for production use

### Comprehensive Logging
- Console output for real-time monitoring
- Detailed log files in the `logs/` directory
- Database logging for all operations
- Error tracking and debugging information

## Configuration Options

### Hyperopt Parameters
The application uses the following default hyperopt settings:
- **Epochs**: 200 (configurable in `OptimizationConfig`)
- **Spaces**: buy, sell, roi, stoploss
- **Timeout**: 1 hour per optimization run
- **Loss Function**: Configurable via `HYPERFUNCTION` env var

### Supported Loss Functions
- `SharpeHyperOptLoss` - Sharpe ratio optimization
- `SortinoHyperOptLoss` - Sortino ratio optimization
- `CalmarHyperOptLoss` - Calmar ratio optimization
- `MaxDrawDownHyperOptLoss` - Minimize drawdown
- `ProfitDrawDownHyperOptLoss` - Profit vs drawdown balance

## Database Schema

### Main Tables

1. **strategy_optimizations**: Individual optimization results
   - Strategy metadata (name, timeframe, pairs)
   - Performance metrics (profit, trades, win rate, drawdown)
   - File paths to detailed configs and results
   - Optimization settings and duration

2. **optimization_sessions**: Groups of optimization runs
   - Session metadata and summary statistics
   - Configuration used for the entire session

3. **session_strategies**: Links strategies to sessions

### Key Fields for Analysis

- `total_profit_pct`: Profit percentage (e.g., 5.25 for 5.25%)
- `total_trades`: Number of trades executed
- `win_rate`: Percentage of winning trades
- `max_drawdown_pct`: Maximum drawdown percentage
- `sharpe_ratio`: Risk-adjusted return metric
- `timeframe`: Trading timeframe (5m, 15m, 1h, etc.)
- `strategy_name`: Name of the strategy
- `optimization_timestamp`: When the optimization was run

## Troubleshooting

### Common Issues

1. **"FreqTrade path does not exist"**
   - Check your `FREQTRADE_PATH` in `.env`
   - Ensure the path is absolute, not relative

2. **"No strategies found"**
   - Verify strategies are in `{FREQTRADE_PATH}/user_data/strategies/`
   - Check that strategy files are `.py` files
   - Ensure files don't start with `__` (like `__init__.py`)

3. **"Data download failed"**
   - Check internet connection
   - Verify exchange name is correct
   - Ensure trading pairs are valid for the exchange

4. **"Database connection failed"**
   - Check write permissions in project directory
   - Ensure SQLite is available (included with Python)
   - Verify disk space for database file

5. **"Hyperopt failed"**
   - Check FreqTrade virtual environment is properly set up
   - Verify strategy file syntax is correct
   - Ensure sufficient disk space for optimization data

### Environment Setup

**For Linux/macOS**:
```bash
# Ensure FreqTrade venv exists
cd /path/to/freqtrade
python -m venv .venv
source .venv/bin/activate
pip install freqtrade
```

**For Windows**:
```cmd
# Ensure FreqTrade venv exists
cd C:\path\to\freqtrade
python -m venv .venv
.venv\Scripts\activate
pip install freqtrade
```

## Advanced Usage

### Custom Analysis Scripts

```python
import sqlite3
from app.modules.results_database_manager import ResultsDatabaseManager

# Initialize database manager
db_manager = ResultsDatabaseManager()

# Get best strategies
best_strategies = db_manager.get_best_strategies(limit=10)

# Custom query example
with sqlite3.connect('old/freqtrade_results.db') as conn:
   cursor = conn.execute("""
        SELECT strategy_name, AVG(total_profit_pct) as avg_profit
        FROM strategy_optimizations 
        WHERE total_trades >= 20
        GROUP BY strategy_name
        ORDER BY avg_profit DESC
    """)
   for row in cursor.fetchall():
      print(f"{row[0]}: {row[1]:.2f}% average profit")
```

### Batch Processing

```bash
# Run multiple optimization sessions with different timeframes
for timeframe in 5m 15m 1h; do
    echo "TIMEFRAME=$timeframe" > .env.temp
    cat .env >> .env.temp
    mv .env.temp .env
    python freqtrade_optimizer.py
done
```

### Integration with CI/CD

The application returns appropriate exit codes:
- `0` - Success (at least one strategy optimized)
- `1` - Failure (no strategies successfully optimized)

## Performance Considerations

- **Memory Usage**: Each optimization can use 1-2 GB RAM
- **CPU Usage**: Highly CPU intensive, benefits from multiple cores
- **Disk Space**: Database and JSON files can accumulate over time
- **Network**: Initial data download requires stable internet
- **Database Performance**: Indexes are automatically created for fast queries

## Backup and Maintenance

### Database Backup
```bash
# Backup database
cp freqtrade_results.db freqtrade_results_backup_$(date +%Y%m%d).db

# Backup result files
tar -czf optimization_results_backup_$(date +%Y%m%d).tar.gz optimization_results/
```

### Maintenance Queries
```sql
-- Clean up old results (older than 6 months)
DELETE FROM strategy_optimizations 
WHERE optimization_timestamp < datetime('now', '-6 months');

-- Vacuum database to reclaim space
VACUUM;

-- Check database integrity
PRAGMA integrity_check;
```

## Security Notes

- Never commit `.env` files to version control
- Keep API keys and secrets out of config templates
- Use sandbox mode for testing
- Regularly backup database and result files
- Consider encryption for sensitive trading data

## Migration from File-Only System

If you have existing result files, you can create a migration script:

```python
# migration_example.py
import json
from pathlib import Path
from app.modules.results_database_manager import ResultsDatabaseManager, OptimizationResult

db_manager = ResultsDatabaseManager()

# Process existing result files
results_dir = Path("old_results")
for result_file in results_dir.glob("*.json"):
   with open(result_file, 'r') as f:
      data = json.load(f)

   # Extract data and create OptimizationResult
   # ... (custom parsing logic based on your old file format)

   # Save to database
   db_manager.save_optimization_result(result)
```

## Support

For FreqTrade-specific issues, consult:
- [FreqTrade Documentation](https://www.freqtrade.io/)
- [FreqTrade GitHub](https://github.com/freqtrade/freqtrade)

For application-specific issues:
- Check the generated log files in `logs/`
- Verify configuration in `.env`
- Ensure all dependencies are installed
- Use the database query tools for result analysis