# FreqTrade Hyperparameter Optimization Automation

A comprehensive Python application that automates the hyperparameter optimization process for multiple FreqTrade strategies with advanced database storage, reality gap analysis, and a modern GUI dashboard.

## 🚀 Features

### Core Functionality
- ✅ **Automated Environment Setup**: Reads configuration from `.env` file and activates FreqTrade virtual environment
- ✅ **Data Management**: Downloads trading data for all specified pairs automatically
- ✅ **Multi-Strategy Processing**: Iterates through all strategy files in the strategies folder
- ✅ **Triple Optimization**: Runs hyperparameter optimization 3 times for each strategy for better results
- ✅ **Validation Backtesting**: Automated backtesting of optimized strategies to detect overfitting

### Database & Analytics
- ✅ **Simplified Database**: Efficient two-table SQLite structure for hyperopt and backtest results
- ✅ **Reality Gap Analysis**: Compare optimization vs backtest performance to detect overfitting
- ✅ **Advanced Metrics**: Sharpe, Calmar, Sortino ratios, profit factor, expectancy tracking
- ✅ **Session Tracking**: Groups optimization runs and tracks overall performance
- ✅ **Performance Timeline**: Track strategy evolution across multiple optimization sessions

### User Interfaces
- ✅ **Modern GUI Dashboard**: Tkinter-based interface with tabbed organization
- ✅ **CLI Tools**: Comprehensive command-line analyzers and runners
- ✅ **Results Export**: Export best configurations with profit percentage naming
- ✅ **Interactive Analysis**: Query, compare, and analyze results with built-in tools

### Technical Features
- ✅ **Robust Error Handling**: Gracefully handles errors and provides detailed logging
- ✅ **Cross-Platform Support**: Works on both Windows and Unix/Linux systems
- ✅ **Progress Tracking**: Real-time progress indicators and comprehensive logging
- ✅ **Migration Support**: Migrate from older database schemas

## 📦 Installation

### 1. Clone or Download
```bash
git clone <repository_url>
cd freqtrade-optimizer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.template` to `.env` and configure your settings:

```bash
# FreqTrade Configuration
FREQTRADE_PATH=/path/to/your/freqtrade
EXCHANGE=binance
PAIR_DATA_EXCHANGE=binance
TIMEFRAME=5m
HISTORICAL_DATA_IN_DAYS=365

# Trading pairs (comma-separated, no spaces around commas)
PAIRS=BTC/USDT,ETH/USDT,ADA/USDT,DOT/USDT,LINK/USDT

# Hyperopt configuration
HYPERFUNCTION=SharpeHyperOptLoss
```

### 4. Prepare FreqTrade
Ensure your FreqTrade installation is ready:
- FreqTrade should be installed with a virtual environment (`.venv`)
- Strategies should be in `user_data/strategies/` directory
- The `config_template.json` should be in your project root

## 🎯 Quick Start

### GUI Dashboard (Recommended)
```bash
python app/main_gui.py
```

The GUI provides:
- **Results Analysis**: View and analyze hyperopt and backtest results
- **Data Management**: Browse and manage downloaded market data
- **Config Editor**: Edit FreqTrade configurations with syntax highlighting
- **Execution**: Run optimizations and backtests with real-time output
- **Logs**: Monitor application logs with filtering and auto-refresh

### Command Line Interface
```bash
# Run full optimization workflow
python app/main.py

# Analyze results
python app/modules/result_analyzer.py best-hyperopt --limit 10

# Run validation backtests
python app/modules/backtest_runner.py batch --limit 5
```

## 📊 Analysis Tools

### CLI Result Analyzer
Comprehensive analysis of optimization and backtest results:

```bash
# Show top performing hyperopt strategies
python app/modules/result_analyzer.py best-hyperopt --limit 10 --min-trades 20

# Show best backtest results
python app/modules/result_analyzer.py best-backtest --limit 10

# Reality gap analysis (detect overfitting)
python app/modules/result_analyzer.py gap --strategy RSIStrategy

# Compare optimization vs backtest for specific strategy
python app/modules/result_analyzer.py vs RSIStrategy

# Show performance timeline
python app/modules/result_analyzer.py timeline RSIStrategy

# Database statistics
python app/modules/result_analyzer.py stats

# Export best configurations
python app/modules/result_analyzer.py export hyperopt --limit 5

# Generate comprehensive strategy report
python app/modules/result_analyzer.py report RSIStrategy
```

### Backtest Runner
Dedicated tool for running validation backtests:

```bash
# Run backtest from specific hyperopt result
python app/modules/backtest_runner.py from-hyperopt 123

# Batch backtest top strategies
python app/modules/backtest_runner.py batch --limit 5

# Show untested hyperopt strategies
python app/modules/backtest_runner.py list-untested

# Show backtest opportunities
python app/modules/backtest_runner.py opportunities
```

## 📁 Project Structure

```
freqtrade-optimizer/
├── app/
│   ├── main.py                 # CLI entry point
│   ├── main_gui.py            # GUI entry point
│   └── modules/
│       ├── freqtrade_optimizer.py      # Core optimization logic
│       ├── freqtrade_executor.py       # Command execution
│       ├── results_database_manager.py # Database operations
│       ├── result_analyzer.py          # CLI analysis tool
│       ├── backtest_runner.py          # Backtest validation tool
│       ├── optimization_config.py      # Configuration management
│       ├── strategy_config_manager.py  # Strategy configs
│       └── dashboard/                  # GUI components
│           ├── dashboard.py            # Main dashboard
│           ├── results_analysis_tab.py # Results analysis
│           ├── data_management_tab.py  # Data management
│           ├── config_editor_tab.py    # Config editor
│           ├── execution_tab.py        # Execution interface
│           └── logs_tab.py             # Log viewer
├── optimization_results/       # Generated results (auto-created)
│   ├── configs/               # Strategy configurations
│   ├── hyperopt_results/      # Detailed hyperopt outputs
│   └── backtest_results/      # Validation backtest outputs
├── logs/                      # Application logs (auto-created)
├── resources/                 # Templates and resources
│   └── config_template.json   # FreqTrade config template
├── .env                       # Your configuration
├── freqtrade_results.db      # SQLite database (auto-created)
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 💾 Database Structure

The system uses a simplified two-table SQLite database:

### `hyperopt_results`
Stores hyperparameter optimization results with:
- Strategy metadata (name, timeframe, pairs)
- Performance metrics (profit, trades, win rate, drawdown)
- Advanced analytics (Sharpe, Calmar, Sortino ratios)
- Configuration and raw results as JSON
- Session tracking information

### `backtest_results`
Stores validation backtest results with:
- All performance metrics from hyperopt table
- Additional backtest-specific data (trade duration, best/worst trades)
- Optional link to originating hyperopt run (`hyperopt_id`)
- Reality gap calculation support

## 📈 Reality Gap Analysis

One of the key features is detecting overfitting through reality gap analysis:

```bash
# Show strategies with highest overfitting risk
python app/modules/result_analyzer.py gap --limit 20

# Analyze specific strategy's performance gap
python app/modules/result_analyzer.py vs RSIStrategy
```

**Reality Gap** = Hyperopt Profit % - Backtest Profit %

- **Positive Gap**: Potential overfitting (optimization performed better than backtest)
- **Negative Gap**: Underoptimization or market changes
- **Small Gap (±2%)**: Acceptable performance consistency

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required Settings
FREQTRADE_PATH=/home/user/freqtrade
EXCHANGE=binance
PAIR_DATA_EXCHANGE=binance
TIMEFRAME=5m
HISTORICAL_DATA_IN_DAYS=365
PAIRS=BTC/USDT,ETH/USDT,ADA/USDT,DOT/USDT,LINK/USDT
HYPERFUNCTION=SharpeHyperOptLoss
```

### FreqTrade Config Template
The system uses `resources/config_template.json` as a base for all strategy configurations. Key settings:

```json
{
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": 100,
  "timeframe": "5m",
  "dry_run": true,
  "exchange": {
    "name": "binance",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"]
  }
}
```

## 📊 Example Output

### Optimization Session
```
[2024-12-16 10:30:00] Starting FreqTrade optimization process...
[2024-12-16 10:30:01] Configuration loaded successfully
[2024-12-16 10:30:01] FreqTrade path: /home/user/freqtrade
[2024-12-16 10:30:01] Exchange: binance | Timeframe: 5m | Pairs: 5
[2024-12-16 10:30:02] Started session: OptSession_20241216_103000
[2024-12-16 10:30:05] Data download completed successfully
[2024-12-16 10:30:06] Found 5 strategies: RSIStrategy, MACDStrategy, EMAStrategy...

Processing RSIStrategy:
[2024-12-16 10:45:22] ✓ Run 1/3 completed - Profit: +23.45% - DB record 87
[2024-12-16 11:00:15] ✓ Run 2/3 completed - Profit: +21.87% - DB record 88
[2024-12-16 11:15:45] ✓ Run 3/3 completed - Profit: +25.12% - DB record 89

============================================================
OPTIMIZATION SUMMARY
============================================================
Total strategies processed: 5
Successful optimizations: 4
Failed optimizations: 1

TOP 5 PERFORMERS THIS SESSION:
1. RSIStrategy - +25.12% (45 trades, 67.8% win rate)
2. MACDStrategy - +18.67% (52 trades, 63.5% win rate)
3. EMAStrategy - +12.34% (38 trades, 60.5% win rate)
4. BBStrategy - +8.91% (41 trades, 58.3% win rate)

🎯 VALIDATION BACKTESTS
Running validation backtests for top 3 strategies...
✓ RSIStrategy backtest: +22.34% (reality gap: -2.78%)
✓ MACDStrategy backtest: +16.23% (reality gap: -2.44%)
✓ EMAStrategy backtest: +11.89% (reality gap: -0.45%)

Use analysis tools to explore results in detail.
============================================================
```

### CLI Analysis Examples

#### Top Strategies
```bash
$ python app/modules/result_analyzer.py best-hyperopt --limit 5

🏆 TOP 5 HYPEROPT STRATEGIES
┌─────────────┬──────────────┬─────────┬──────────┬─────────────┬──────────────┬───────────┬────────────┐
│ Strategy    │ Total Profit │ Trades  │ Win Rate │ Avg Profit  │ Max Drawdown │ Sharpe    │ Date       │
├─────────────┼──────────────┼─────────┼──────────┼─────────────┼──────────────┼───────────┼────────────┤
│ RSIStrategy │ +25.12%      │ 45      │ 67.8%    │ +0.56%      │ -8.45%       │ 1.34      │ 2024-12-16 │
│ MACDStrat   │ +23.89%      │ 38      │ 71.1%    │ +0.63%      │ -6.23%       │ 1.56      │ 2024-12-16 │
│ EMAStrategy │ +18.67%      │ 52      │ 63.5%    │ +0.36%      │ -9.12%       │ 1.12      │ 2024-12-16 │
│ BBStrategy  │ +15.34%      │ 41      │ 58.3%    │ +0.37%      │ -11.67%      │ 0.98      │ 2024-12-15 │
│ StochStrat  │ +12.45%      │ 33      │ 60.6%    │ +0.38%      │ -7.89%       │ 1.08      │ 2024-12-15 │
└─────────────┴──────────────┴─────────┴──────────┴─────────────┴──────────────┴───────────┴────────────┘
```

#### Reality Gap Analysis
```bash
$ python app/modules/result_analyzer.py gap --limit 5

📊 REALITY GAP ANALYSIS
┌─────────────┬─────────────┬─────────────┬──────────┬───────────────┬─────────────┐
│ Strategy    │ Opt Profit  │ BT Profit   │ Gap      │ Assessment    │ Status      │
├─────────────┼─────────────┼─────────────┼──────────┼───────────────┼─────────────┤
│ RSIStrategy │ +25.12%     │ +22.34%     │ -2.78%   │ Acceptable    │ ✓ Tested    │
│ MACDStrat   │ +23.89%     │ +16.23%     │ -7.66%   │ Overfitting   │ ✓ Tested    │
│ EMAStrategy │ +18.67%     │ +11.89%     │ -6.78%   │ Overfitting   │ ✓ Tested    │
│ BBStrategy  │ +15.34%     │ N/A         │ N/A      │ Not Tested    │ ✗ Pending   │
│ StochStrat  │ +12.45%     │ N/A         │ N/A      │ Not Tested    │ ✗ Pending   │
└─────────────┴─────────────┴─────────────┴──────────┴───────────────┴─────────────┘

📈 SUMMARY: Average gap: -5.74% | High risk strategies: 2/3
```

## 🔍 Advanced Usage

### Custom SQL Queries
Access the SQLite database directly for custom analysis:

```sql
-- Find strategies with consistent performance across runs
SELECT 
    strategy_name,
    COUNT(*) as total_runs,
    AVG(total_profit_pct) as avg_profit,
    STDEV(total_profit_pct) as profit_volatility,
    MIN(total_profit_pct) as worst_run,
    MAX(total_profit_pct) as best_run
FROM hyperopt_results 
WHERE status = 'completed' AND total_trades >= 20
GROUP BY strategy_name
HAVING total_runs >= 3
ORDER BY profit_volatility ASC, avg_profit DESC;
```

### Batch Operations
```bash
# Export configurations for top 10 strategies
python app/modules/result_analyzer.py export hyperopt --limit 10 --output production_configs

# Run backtests for all untested strategies
python app/modules/backtest_runner.py batch --limit 20
```

### GUI Advanced Features
- **Real-time Execution**: Monitor optimization progress with live output
- **Configuration Editor**: Edit JSON configs with syntax highlighting and validation
- **Data Browser**: Explore downloaded market data with filtering
- **Log Viewer**: Monitor application logs with auto-refresh and filtering

## 🛠️ Troubleshooting

### Common Issues

1. **"FreqTrade path does not exist"**
   - Check your `FREQTRADE_PATH` in `.env`
   - Ensure the path is absolute and points to FreqTrade installation

2. **"No strategies found"**
   - Verify strategies are in `{FREQTRADE_PATH}/user_data/strategies/`
   - Ensure files are `.py` files and don't start with `__`

3. **"Data download failed"**
   - Check internet connection and exchange availability
   - Verify trading pairs are valid for the selected exchange

4. **"Database connection failed"**
   - Check write permissions in project directory
   - Ensure sufficient disk space

5. **"Hyperopt failed"**
   - Verify FreqTrade virtual environment setup
   - Check strategy file syntax
   - Review logs in `logs/` directory

### Getting Help

1. **Check Logs**: Application logs in `logs/` directory provide detailed error information
2. **Database Stats**: Run `python app/modules/result_analyzer.py stats` to check database health
3. **Validate Environment**: Ensure FreqTrade installation is working independently

## 🔄 Migration

### From Older Versions
```bash
# Migrate from old database schema
python app/modules/result_analyzer.py migrate

# Clean up old tables after migration
python app/modules/result_analyzer.py cleanup-old-tables --confirm
```

## 📋 Requirements

- **Python**: 3.8+
- **FreqTrade**: Latest version with virtual environment setup
- **Disk Space**: ~1GB for database and result files (varies by usage)
- **Memory**: 4GB+ recommended for multiple concurrent optimizations
- **Platform**: Windows, macOS, Linux

## 🎯 Best Practices

1. **Start Small**: Begin with 2-3 strategies and shorter timeframes
2. **Monitor Reality Gap**: Regular backtest validation prevents overfitting
3. **Use Session Tracking**: Organize optimization runs logically
4. **Export Configurations**: Save best-performing configs for production
5. **Regular Backups**: Backup `freqtrade_results.db` and `optimization_results/`

## 📄 License

This project is open source. Please ensure you comply with FreqTrade's license terms when using this tool.

## 🤝 Contributing

Contributions are welcome! Please ensure any changes maintain compatibility with the existing database structure and CLI interfaces.

---

**Happy Trading!** 🚀📈

For more detailed information about the database structure, see [Database.md](app/Database.md)