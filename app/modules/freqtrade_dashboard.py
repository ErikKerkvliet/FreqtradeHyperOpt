#!/usr/bin/env python3
"""
FreqTrade Dashboard GUI
A comprehensive tkinter-based dashboard for managing FreqTrade optimization results,
configuration editing, and running hyperopt/backtest commands.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import sqlite3
import json
import subprocess
import threading
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

# Import your existing modules
from .results_database_manager import ResultsDatabaseManager
from .optimization_config import OptimizationConfig
from .freqtrade_executor import FreqTradeExecutor
from dotenv import load_dotenv


class FreqTradeDashboard:
    """Main dashboard application class."""

    def __init__(self, root):
        self.root = root
        self.root.title("FreqTrade Optimization Dashboard")
        self.root.geometry("1200x800")

        self.logger = None

        # Setup logging first
        self.setup_logging()

        # Initialize database manager
        self.db_manager = ResultsDatabaseManager()
        self.executor: Optional[FreqTradeExecutor] = None

        # Load basic configuration (without executor)
        self.load_basic_config()

        # Create main interface
        self.create_widgets()

        # Now initialize executor after all methods are available
        self.initialize_executor()

        # Load initial data
        self.refresh_data()

    def setup_logging(self):
        """Setup logging for the GUI."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_basic_config(self):
        """Load basic configuration from .env file."""
        load_dotenv()
        self.freqtrade_path = os.getenv('FREQTRADE_PATH', '')
        self.exchange = os.getenv('EXCHANGE', 'binance')
        self.timeframe = os.getenv('TIMEFRAME', '5m')
        self.pairs = os.getenv('PAIRS', 'BTC/USDT,ETH/USDT').split(',')
        self.hyperfunction = os.getenv('HYPERFUNCTION', 'SharpeHyperOptLoss')

    def initialize_executor(self):
        """Initialize executor after all GUI methods are available."""
        if self.freqtrade_path and Path(self.freqtrade_path).exists():
            try:
                from datetime import datetime, timedelta
                days = int(os.getenv('HISTORICAL_DATA_IN_DAYS', '365'))
                start_date = datetime.now() - timedelta(days=days)
                timerange = f"{start_date.strftime('%Y%m%d')}-"

                config = OptimizationConfig(
                    freqtrade_path=self.freqtrade_path,
                    exchange=self.exchange,
                    timeframe=self.timeframe,
                    timerange=timerange,
                    pairs=self.pairs,
                    pair_data_exchange=os.getenv('PAIR_DATA_EXCHANGE', self.exchange),
                    hyperfunction=self.hyperfunction
                )

                self.executor = FreqTradeExecutor(config, self.logger)

                # Set GUI callbacks
                self.executor.set_callbacks(
                    progress_callback=self.update_progress,
                    output_callback=self.append_output,
                    completion_callback=self.on_execution_complete
                )

            except Exception as e:
                self.logger.error(f"Failed to initialize executor: {e}")
                self.executor = None

    def update_progress(self, message: str):
        """Update progress display (called from executor)."""
        if hasattr(self, 'progress_var'):
            self.progress_var.set(message)

    def append_output(self, text: str):
        """Append text to output display (called from executor)."""
        if hasattr(self, 'output_text'):
            self.output_text.insert(tk.END, text)
            self.output_text.see(tk.END)

    def on_execution_complete(self, result):
        """Handle execution completion (called from executor)."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.stop()

        if result.success:
            message = "Command completed successfully!"
            if hasattr(result, 'optimization_id') and result.optimization_id:
                message += f" (DB record: {result.optimization_id})"
            if hasattr(self, 'progress_var'):
                self.progress_var.set(message)
            self.append_output(f"\n✓ {message}\n")

            # Refresh data to show new results
            self.refresh_data()
            if hasattr(self, 'refresh_data_info'):
                self.refresh_data_info()
        else:
            message = f"Command failed: {result.error_message or 'Unknown error'}"
            if hasattr(self, 'progress_var'):
                self.progress_var.set(message)
            self.append_output(f"\n✗ {message}\n")

    def on_session_change(self, event=None):
        """Handle session selection change."""
        self.load_optimization_results()

    def create_widgets(self):
        """Create the main GUI widgets."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create tabs
        self.create_results_tab()
        self.create_data_tab()
        self.create_config_tab()
        self.create_execution_tab()
        self.create_logs_tab()

    def create_results_tab(self):
        """Create the results analysis tab."""
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="Results Analysis")

        # Create left panel for filters
        left_panel = ttk.Frame(self.results_frame)
        left_panel.pack(side='left', fill='y', padx=(0, 10))

        # Filters section
        filters_frame = ttk.LabelFrame(left_panel, text="Filters", padding=10)
        filters_frame.pack(fill='x', pady=(0, 10))

        # Session filter
        ttk.Label(filters_frame, text="Session:").pack(anchor='w')
        self.session_var = tk.StringVar()
        self.session_combo = ttk.Combobox(filters_frame, textvariable=self.session_var, width=20)
        self.session_combo.pack(fill='x', pady=(0, 10))
        self.session_combo.bind('<<ComboboxSelected>>', self.on_session_change)

        # Strategy filter
        ttk.Label(filters_frame, text="Strategy:").pack(anchor='w')
        self.strategy_var = tk.StringVar()
        self.strategy_combo = ttk.Combobox(filters_frame, textvariable=self.strategy_var, width=20)
        self.strategy_combo.pack(fill='x', pady=(0, 10))

        # Timeframe filter
        ttk.Label(filters_frame, text="Timeframe:").pack(anchor='w')
        self.timeframe_var = tk.StringVar()
        self.timeframe_combo = ttk.Combobox(filters_frame, textvariable=self.timeframe_var, width=20)
        self.timeframe_combo.pack(fill='x', pady=(0, 10))

        # Refresh button
        ttk.Button(filters_frame, text="Refresh Data", command=self.refresh_data).pack(fill='x')

        # Results section
        results_list_frame = ttk.LabelFrame(left_panel, text="Optimization Results", padding=10)
        results_list_frame.pack(fill='both', expand=True)

        # Results treeview
        columns = ('ID', 'Strategy', 'Profit %', 'Trades', 'Win Rate', 'Date')
        self.results_tree = ttk.Treeview(results_list_frame, columns=columns, show='headings', height=15)

        # Configure columns
        self.results_tree.heading('ID', text='ID')
        self.results_tree.heading('Strategy', text='Strategy')
        self.results_tree.heading('Profit %', text='Profit %')
        self.results_tree.heading('Trades', text='Trades')
        self.results_tree.heading('Win Rate', text='Win Rate')
        self.results_tree.heading('Date', text='Date')

        self.results_tree.column('ID', width=50)
        self.results_tree.column('Strategy', width=120)
        self.results_tree.column('Profit %', width=80)
        self.results_tree.column('Trades', width=60)
        self.results_tree.column('Win Rate', width=80)
        self.results_tree.column('Date', width=100)

        # Add scrollbar to treeview
        results_scrollbar = ttk.Scrollbar(results_list_frame, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)

        self.results_tree.pack(side='left', fill='both', expand=True)
        results_scrollbar.pack(side='right', fill='y')

        # Bind selection event
        self.results_tree.bind('<<TreeviewSelect>>', self.on_result_select)

        # Create right panel for details
        right_panel = ttk.Frame(self.results_frame)
        right_panel.pack(side='right', fill='both', expand=True)

        # Details section
        details_frame = ttk.LabelFrame(right_panel, text="Optimization Details", padding=10)
        details_frame.pack(fill='both', expand=True)

        # Create notebook for details
        self.details_notebook = ttk.Notebook(details_frame)
        self.details_notebook.pack(fill='both', expand=True)

        # Configuration tab
        self.config_details_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.config_details_frame, text="Configuration")

        self.config_text = scrolledtext.ScrolledText(self.config_details_frame, wrap=tk.WORD)
        self.config_text.pack(fill='both', expand=True)

        # Hyperopt JSON tab
        self.hyperopt_details_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.hyperopt_details_frame, text="Hyperopt JSON")

        self.hyperopt_text = scrolledtext.ScrolledText(self.hyperopt_details_frame, wrap=tk.WORD)
        self.hyperopt_text.pack(fill='both', expand=True)

        # Metrics tab
        self.metrics_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.metrics_frame, text="Metrics")

        self.create_metrics_display()

    def create_metrics_display(self):
        """Create the metrics display in the metrics tab."""
        # Create a frame for metrics
        metrics_container = ttk.Frame(self.metrics_frame, padding=10)
        metrics_container.pack(fill='both', expand=True)

        # Metrics labels
        self.metrics_labels = {}
        metrics_info = [
            ('Total Profit %', 'total_profit_pct'),
            ('Total Profit Abs', 'total_profit_abs'),
            ('Total Trades', 'total_trades'),
            ('Win Rate %', 'win_rate'),
            ('Avg Profit %', 'avg_profit_pct'),
            ('Max Drawdown %', 'max_drawdown_pct'),
            ('Sharpe Ratio', 'sharpe_ratio'),
            ('Optimization Duration', 'optimization_duration_seconds'),
            ('Run Number', 'run_number'),
            ('Timeframe', 'timeframe'),
            ('Exchange', 'exchange_name')
        ]

        for i, (label, key) in enumerate(metrics_info):
            row = i // 2
            col = i % 2

            ttk.Label(metrics_container, text=f"{label}:").grid(row=row, column=col * 2, sticky='w', padx=(0, 10),
                                                                pady=5)
            value_label = ttk.Label(metrics_container, text="N/A", font=('TkDefaultFont', 9, 'bold'))
            value_label.grid(row=row, column=col * 2 + 1, sticky='w', padx=(0, 20), pady=5)
            self.metrics_labels[key] = value_label


    def create_data_tab(self):
        """Create the data management tab with exchange subtabs."""
        self.data_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.data_frame, text="Data Management")

        # Create toolbar for data management
        data_toolbar = ttk.Frame(self.data_frame)
        data_toolbar.pack(fill='x', padx=10, pady=5)

        ttk.Button(data_toolbar, text="Refresh Data", command=self.refresh_data_info).pack(side='left', padx=(0, 5))
        ttk.Button(data_toolbar, text="Download Data", command=self.download_new_data).pack(side='left', padx=(0, 5))
        ttk.Button(data_toolbar, text="Delete Selected", command=self.delete_selected_data).pack(side='left', padx=(0, 20))

        # Status label
        self.data_status_var = tk.StringVar(value="Ready")
        ttk.Label(data_toolbar, textvariable=self.data_status_var, foreground='gray').pack(side='left')

        # Create notebook for exchange subtabs
        self.data_notebook = ttk.Notebook(self.data_frame)
        self.data_notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Dictionary to store exchange frames and trees
        self.exchange_frames = {}
        self.exchange_trees = {}

        # Initialize with common exchanges
        self.create_exchange_tab("binance")
        self.create_exchange_tab("kraken")
        self.create_exchange_tab("coinbase")
        self.create_exchange_tab("other")

        # Load initial data
        self.refresh_data_info()


    def create_exchange_tab(self, exchange_name):
        """Create a tab for a specific exchange."""
        # Create frame for exchange
        exchange_frame = ttk.Frame(self.data_notebook)
        self.data_notebook.add(exchange_frame, text=exchange_name.capitalize())
        self.exchange_frames[exchange_name] = exchange_frame

        # Create filter frame
        filter_frame = ttk.LabelFrame(exchange_frame, text="Filters", padding=5)
        filter_frame.pack(fill='x', padx=10, pady=5)

        # Create two rows for filters
        filter_row1 = ttk.Frame(filter_frame)
        filter_row1.pack(fill='x', pady=(0, 5))

        filter_row2 = ttk.Frame(filter_frame)
        filter_row2.pack(fill='x')

        # Row 1: Search and Timeframe filters
        ttk.Label(filter_row1, text="Search:").pack(side='left', padx=(0, 5))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_row1, textvariable=search_var, width=15)
        search_entry.pack(side='left', padx=(0, 15))

        ttk.Label(filter_row1, text="Timeframe:").pack(side='left', padx=(0, 5))
        timeframe_var = tk.StringVar()
        timeframe_combo = ttk.Combobox(filter_row1, textvariable=timeframe_var, width=8)
        timeframe_combo['values'] = ['All', '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        timeframe_combo.set('All')
        timeframe_combo.pack(side='left', padx=(0, 15))

        # Clear filters button
        ttk.Button(filter_row1, text="Clear All", command=lambda: self.clear_filters(exchange_name)).pack(side='right',
                                                                                                          padx=(10, 0))

        # Row 2: Base/Quote currency filters and quick filters
        ttk.Label(filter_row2, text="Base Currency:").pack(side='left', padx=(0, 5))
        base_currency_var = tk.StringVar()
        base_currency_combo = ttk.Combobox(filter_row2, textvariable=base_currency_var, width=8)
        base_currency_combo['values'] = ['All', 'BTC', 'ETH', 'BNB', 'ADA', 'DOT', 'LINK', 'SOL', 'XRP', 'LTC', 'AVAX']
        base_currency_combo.set('All')
        base_currency_combo.pack(side='left', padx=(0, 15))

        ttk.Label(filter_row2, text="Quote Currency:").pack(side='left', padx=(0, 5))
        quote_currency_var = tk.StringVar()
        quote_currency_combo = ttk.Combobox(filter_row2, textvariable=quote_currency_var, width=8)
        quote_currency_combo['values'] = ['All', 'USDT', 'BTC', 'ETH', 'BNB', 'USD', 'EUR', 'BUSD']
        quote_currency_combo.set('All')
        quote_currency_combo.pack(side='left', padx=(0, 15))

        # Quick filter buttons
        quick_filter_frame = ttk.Frame(filter_row2)
        quick_filter_frame.pack(side='right', padx=(10, 0))

        ttk.Button(quick_filter_frame, text="Hour+", width=6,
                   command=lambda: self.apply_quick_filter(exchange_name, 'hourly')).pack(side='left', padx=(0, 2))
        ttk.Button(quick_filter_frame, text="BTC Pairs", width=8,
                   command=lambda: self.apply_quick_filter(exchange_name, 'btc_pairs')).pack(side='left', padx=(0, 2))
        ttk.Button(quick_filter_frame, text="USDT Pairs", width=9,
                   command=lambda: self.apply_quick_filter(exchange_name, 'usdt_pairs')).pack(side='left', padx=(0, 2))

        # Bind filter events
        search_entry.bind('<KeyRelease>', lambda e: self.apply_filters(exchange_name))
        timeframe_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters(exchange_name))
        base_currency_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters(exchange_name))
        quote_currency_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters(exchange_name))

        # Create data table
        table_frame = ttk.Frame(exchange_frame)
        table_frame.pack(fill='both', expand=True, padx=10, pady=(5, 10))

        # Define columns
        columns = ('Pair', 'Base', 'Quote', 'Timeframe', 'Start Date', 'End Date', 'Records', 'File Size', 'Last Modified')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='extended')

        tree._all_data = []  # Store all data for filtering

        # Configure column headings and widths
        tree.heading('Pair', text='Trading Pair')
        tree.heading('Base', text='Base')
        tree.heading('Quote', text='Quote')
        tree.heading('Timeframe', text='Timeframe')
        tree.heading('Start Date', text='Start Date')
        tree.heading('End Date', text='End Date')
        tree.heading('Records', text='Records')
        tree.heading('File Size', text='File Size')
        tree.heading('Last Modified', text='Last Modified')

        tree.column('Pair', width=100)
        tree.column('Base', width=50)
        tree.column('Quote', width=50)
        tree.column('Timeframe', width=70)
        tree.column('Start Date', width=90)
        tree.column('End Date', width=90)
        tree.column('Records', width=70)
        tree.column('File Size', width=70)
        tree.column('Last Modified', width=110)

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack tree and scrollbars
        tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        # Configure grid weights
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Store tree reference and filter variables
        self.exchange_trees[exchange_name] = tree
        tree.search_var = search_var
        tree.timeframe_var = timeframe_var
        tree.base_currency_var = base_currency_var
        tree.quote_currency_var = quote_currency_var

        # Add data summary label
        summary_frame = ttk.Frame(exchange_frame)
        summary_frame.pack(fill='x', padx=10, pady=(0, 5))

        summary_var = tk.StringVar(value="Ready")
        ttk.Label(summary_frame, textvariable=summary_var, foreground='gray').pack(side='left')
        tree.summary_var = summary_var


    def refresh_data_info(self):
        """Refresh the data information for all exchanges."""
        if not self.freqtrade_path:
            self.data_status_var.set("FreqTrade path not configured")
            return

        try:
            self.data_status_var.set("Scanning data files...")

            # Get data directory
            data_base_dir = Path(self.freqtrade_path) / "user_data" / "data"

            if not data_base_dir.exists():
                self.data_status_var.set("Data directory not found")
                return

            # Scan each exchange directory
            for exchange_name, tree in self.exchange_trees.items():
                self.load_exchange_data(exchange_name, tree, data_base_dir)

            self.data_status_var.set("Data scan completed")

        except Exception as e:
            self.logger.error(f"Error refreshing data info: {e}")
            self.data_status_var.set("Error scanning data")
            messagebox.showerror("Error", f"Failed to refresh data: {e}")

    def load_exchange_data(self, exchange_name, tree, data_base_dir):
        """Load data files for a specific exchange."""
        # Clear existing items and stored data
        for item in tree.get_children():
            tree.delete(item)
        tree._all_data = []

        exchange_dirs = []

        if exchange_name == "other":
            # For "other" tab, scan all directories except known exchanges
            known_exchanges = ["binance", "kraken", "coinbase"]
            for item in data_base_dir.iterdir():
                if item.is_dir() and item.name not in known_exchanges:
                    exchange_dirs.append(item)
        else:
            # For specific exchange
            exchange_dir = data_base_dir / exchange_name
            if exchange_dir.exists():
                exchange_dirs.append(exchange_dir)

        total_files = 0
        loaded_files = 0

        for exchange_dir in exchange_dirs:
            try:
                # Scan for JSON files (FreqTrade data format)
                json_files = list(exchange_dir.rglob("*.json"))
                total_files += len(json_files)

                for json_file in json_files:
                    try:
                        # Parse filename to extract pair and timeframe
                        file_stem = json_file.stem

                        # Handle different naming conventions
                        if '-' in file_stem:
                            parts = file_stem.rsplit('-', 1)
                            if len(parts) == 2:
                                pair, timeframe = parts
                                pair = pair.replace('_', '/')
                            else:
                                pair = file_stem
                                timeframe = "unknown"
                        else:
                            pair = file_stem.replace('_', '/')
                            timeframe = "unknown"

                        # Extract base and quote currencies from pair
                        if '/' in pair:
                            base_currency, quote_currency = pair.split('/', 1)
                        else:
                            # Handle pairs without separator
                            base_currency = "Unknown"
                            quote_currency = "Unknown"
                            # Try to guess common separations
                            for quote in ['USDT', 'BTC', 'ETH', 'BNB', 'USD', 'EUR', 'BUSD']:
                                if pair.endswith(quote):
                                    base_currency = pair[:-len(quote)]
                                    quote_currency = quote
                                    pair = f"{base_currency}/{quote_currency}"
                                    break

                        # Get file info
                        file_stat = json_file.stat()
                        file_size = self.format_file_size(file_stat.st_size)
                        last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M')

                        # Try to get data range and record count
                        start_date, end_date, record_count = self.analyze_data_file(json_file)

                        values = (
                            pair,
                            base_currency,
                            quote_currency,
                            timeframe,
                            start_date,
                            end_date,
                            record_count,
                            file_size,
                            last_modified
                        )
                        tags = (str(json_file),)

                        # Store data for filtering
                        tree._all_data.append({
                            'values': values,
                            'file_path': str(json_file),
                            'visible': True
                        })

                        loaded_files += 1

                    except Exception as e:
                        self.logger.warning(f"Error processing file {json_file}: {e}")
                        continue

            except Exception as e:
                self.logger.error(f"Error scanning exchange directory {exchange_dir}: {e}")
                continue

        self._display_filtered_data(tree)

        # Update summary
        if hasattr(tree, 'summary_var'):
            tree.summary_var.set(f"Loaded {loaded_files} of {total_files} data files")


    def analyze_data_file(self, file_path):
        """Analyze a data file to get date range and record count."""
        try:
            import json

            with open(file_path, 'r') as f:
                data = json.load(f)

            if not data:
                return "No data", "No data", "0"

            # Data is typically in OHLCV format: [timestamp, open, high, low, close, volume]
            record_count = len(data)

            if record_count > 0:
                # Get first and last timestamps
                first_timestamp = data[0][0] if data[0] else None
                last_timestamp = data[-1][0] if data[-1] else None

                if first_timestamp and last_timestamp:
                    start_date = datetime.fromtimestamp(first_timestamp / 1000).strftime('%Y-%m-%d')
                    end_date = datetime.fromtimestamp(last_timestamp / 1000).strftime('%Y-%m-%d')
                    return start_date, end_date, str(record_count)

            return "Unknown", "Unknown", str(record_count)

        except Exception as e:
            self.logger.warning(f"Error analyzing data file {file_path}: {e}")
            return "Error", "Error", "Error"


    def format_file_size(self, size_bytes):
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def _display_filtered_data(self, tree):
        """Display filtered data in the treeview."""
        # Clear current display
        for item in tree.get_children():
            tree.delete(item)

        # Add visible items
        for data_item in tree._all_data:
            if data_item['visible']:
                tree.insert('', 'end', values=data_item['values'], tags=(data_item['file_path'],))

    def apply_filters(self, exchange_name):
        """Apply all filters to the exchange data display."""
        tree = self.exchange_trees[exchange_name]

        # Get filter values
        search_text = tree.search_var.get().upper()
        timeframe_filter = tree.timeframe_var.get()
        base_currency_filter = tree.base_currency_var.get()
        quote_currency_filter = tree.quote_currency_var.get()

        visible_count = 0
        total_count = len(tree._all_data)

        # Apply filters to stored data
        for data_item in tree._all_data:
            values = data_item['values']
            if not values or len(values) < 9:
                data_item['visible'] = False
                continue

            pair, base_currency, quote_currency, timeframe, start_date, end_date, records, file_size, last_modified = values

            # Apply filters
            show_item = True

            if search_text and search_text not in pair.upper():
                show_item = False
            if timeframe_filter != "All" and timeframe != timeframe_filter:
                show_item = False
            if base_currency_filter != "All" and base_currency != base_currency_filter:
                show_item = False
            if quote_currency_filter != "All" and quote_currency != quote_currency_filter:
                show_item = False

            data_item['visible'] = show_item
            if show_item:
                visible_count += 1

        # Update display
        self._display_filtered_data(tree)

        # Update summary
        if hasattr(tree, 'summary_var'):
            if visible_count == total_count:
                tree.summary_var.set(f"Showing all {total_count} data files")
            else:
                tree.summary_var.set(f"Showing {visible_count} of {total_count} data files")

    def apply_quick_filter(self, exchange_name, filter_type):
        """Apply predefined quick filters."""
        tree = self.exchange_trees[exchange_name]

        if filter_type == 'hourly':
            # Show only hourly and higher timeframes (1h, 4h, 1d, 1w)
            tree.timeframe_var.set('All')
            tree.base_currency_var.set('All')
            tree.quote_currency_var.set('All')
            tree.search_var.set('')

            # Custom filter for hourly+
            hourly_timeframes = ['1h', '4h', '1d', '1w', '12h', '6h', '8h']

            visible_count = 0
            for data_item in tree._all_data:
                values = data_item['values']
                if values and len(values) >= 4:
                    timeframe = values[3]
                    if timeframe in hourly_timeframes:
                        data_item['visible'] = True
                        visible_count += 1
                    else:
                        data_item['visible'] = False
                else:
                    data_item['visible'] = False

            self._display_filtered_data(tree)

            if hasattr(tree, 'summary_var'):
                tree.summary_var.set(f"Showing {visible_count} hourly+ timeframe files")

        elif filter_type == 'btc_pairs':
            # Show only BTC quote pairs
            tree.timeframe_var.set('All')
            tree.base_currency_var.set('All')
            tree.quote_currency_var.set('BTC')
            tree.search_var.set('')
            self.apply_filters(exchange_name)

        elif filter_type == 'usdt_pairs':
            # Show only USDT quote pairs
            tree.timeframe_var.set('All')
            tree.base_currency_var.set('All')
            tree.quote_currency_var.set('USDT')
            tree.search_var.set('')
            self.apply_filters(exchange_name)

    def clear_filters(self, exchange_name):
        """Clear all filters for an exchange."""
        tree = self.exchange_trees[exchange_name]

        # Reset all filter variables
        tree.search_var.set('')
        tree.timeframe_var.set('All')
        tree.base_currency_var.set('All')
        tree.quote_currency_var.set('All')

        # Show all items
        for data_item in tree._all_data:
            data_item['visible'] = True

        self._display_filtered_data(tree)

        # Update summary
        if hasattr(tree, 'summary_var'):
            total_count = len(tree._all_data)
            tree.summary_var.set(f"Showing all {total_count} data files")

    def download_new_data(self):
        """Open dialog to download new data."""
        # Create a simple dialog for downloading data
        dialog = tk.Toplevel(self.root)
        dialog.title("Download Data")
        dialog.geometry("450x343")
        dialog.resizable(False, False)

        # Make dialog modal
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))

        # Create main frame with padding
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Exchange
        ttk.Label(main_frame, text="Exchange:").pack(anchor='w')
        exchange_var = tk.StringVar(value="binance")
        exchange_combo = ttk.Combobox(main_frame, textvariable=exchange_var)
        exchange_combo['values'] = ['binance', 'kraken', 'coinbase', 'bittrex', 'okx']
        exchange_combo.pack(fill='x', pady=(0, 10))

        # Pairs
        ttk.Label(main_frame, text="Trading Pairs (comma-separated):").pack(anchor='w')
        pairs_var = tk.StringVar(value="BTC/USDT,ETH/USDT")
        pairs_entry = ttk.Entry(main_frame, textvariable=pairs_var)
        pairs_entry.pack(fill='x', pady=(0, 10))

        # Timeframes
        ttk.Label(main_frame, text="Timeframes:").pack(anchor='w')
        timeframes_frame = ttk.Frame(main_frame)
        timeframes_frame.pack(fill='x', pady=(0, 10))

        timeframe_vars = {}
        timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        for i, tf in enumerate(timeframes):
            var = tk.BooleanVar(value=(tf in ['5m', '1h']))
            timeframe_vars[tf] = var
            ttk.Checkbutton(timeframes_frame, text=tf, variable=var).grid(row=i // 4, column=i % 4, sticky='w',
                                                                          padx=(0, 10))

        # Timerange
        ttk.Label(main_frame, text="Days of history:").pack(anchor='w')
        days_var = tk.StringVar(value="30")
        days_entry = ttk.Entry(main_frame, textvariable=days_var)
        days_entry.pack(fill='x', pady=(0, 20))

        # Define start_download function
        def start_download():
            # Get selected timeframes
            selected_timeframes = [tf for tf, var in timeframe_vars.items() if var.get()]
            if not selected_timeframes:
                messagebox.showerror("Error", "Please select at least one timeframe!")
                return

            # Build download command
            pairs = [p.strip() for p in pairs_var.get().split(',') if p.strip()]
            if not pairs:
                messagebox.showerror("Error", "Please enter at least one trading pair!")
                return

            try:
                days = int(days_var.get())
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                timerange = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number of days!")
                return

            dialog.destroy()

            # Execute download command
            for timeframe in selected_timeframes:
                command = [
                              "freqtrade", "download-data",
                              "--exchange", exchange_var.get(),
                              "--timeframe", timeframe,
                              "--timerange", timerange,
                              "-p"] + pairs

                # Switch to execution tab and run command
                self.notebook.select(3)  # Execution tab
                self.execute_command(command, f"Data Download ({timeframe})")
                break  # Only run first command, user can run others manually

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')

        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Download", command=start_download).pack(side='right')

    def delete_selected_data(self):
        """Delete selected data files."""
        # Get current exchange tab
        current_tab = self.data_notebook.index(self.data_notebook.select())
        exchange_names = list(self.exchange_trees.keys())

        if current_tab >= len(exchange_names):
            return

        exchange_name = exchange_names[current_tab]
        tree = self.exchange_trees[exchange_name]

        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select data files to delete!")
            return

        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion",
                                   f"Are you sure you want to delete {len(selected_items)} data file(s)?"):
            return

        deleted_count = 0
        for item in selected_items:
            try:
                # Get file path from tags
                tags = tree.item(item)['tags']
                if tags:
                    file_path = Path(tags[0])
                    if file_path.exists():
                        file_path.unlink()
                        tree.delete(item)
                        deleted_count += 1
            except Exception as e:
                self.logger.error(f"Error deleting file: {e}")

        if deleted_count > 0:
            messagebox.showinfo("Success", f"Deleted {deleted_count} file(s) successfully!")
            self.data_status_var.set(f"Deleted {deleted_count} files")
            # Update summary after deletion
            if hasattr(tree, 'summary_var'):
                remaining_count = len(tree.get_children())
                tree.summary_var.set(f"Showing {remaining_count} data files")
        else:
            messagebox.showerror("Error", "No files were deleted!")


    def create_config_tab(self):
        """Create the configuration editing tab."""
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="Config Editor")

        # Create toolbar
        toolbar_frame = ttk.Frame(self.config_frame)
        toolbar_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(toolbar_frame, text="Load Config", command=self.load_config_file).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_frame, text="Save Config", command=self.save_config_file).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_frame, text="New Config", command=self.new_config_file).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_frame, text="Validate JSON", command=self.validate_config_json).pack(side='left', padx=(0, 20))

        # Current file label
        self.current_file_label = ttk.Label(toolbar_frame, text="No file loaded", foreground='gray')
        self.current_file_label.pack(side='left')

        # Create text editor
        editor_frame = ttk.Frame(self.config_frame)
        editor_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.config_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.NONE, font=('Consolas', 10))
        self.config_editor.pack(fill='both', expand=True)

        # Add line numbers (simple implementation)
        self.config_editor.bind('<KeyRelease>', self.update_line_numbers)
        self.config_editor.bind('<Button-1>', self.update_line_numbers)

        self.current_config_file = None


    def create_execution_tab(self):
        """Create the execution tab for running hyperopt and backtest."""
        self.execution_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.execution_frame, text="Execution")

        # Create left panel for parameters
        left_exec_panel = ttk.Frame(self.execution_frame)
        left_exec_panel.pack(side='left', fill='y', padx=(10, 5), pady=10)

        # Parameters section
        params_frame = ttk.LabelFrame(left_exec_panel, text="Execution Parameters", padding=10)
        params_frame.pack(fill='x', pady=(0, 10))

        # Strategy selection
        ttk.Label(params_frame, text="Strategy:").pack(anchor='w')
        self.exec_strategy_var = tk.StringVar()
        self.exec_strategy_combo = ttk.Combobox(params_frame, textvariable=self.exec_strategy_var, width=25)
        self.exec_strategy_combo.pack(fill='x', pady=(0, 10))

        # Config file selection
        ttk.Label(params_frame, text="Config File:").pack(anchor='w')
        config_file_frame = ttk.Frame(params_frame)
        config_file_frame.pack(fill='x', pady=(0, 10))

        self.exec_config_var = tk.StringVar()
        ttk.Entry(config_file_frame, textvariable=self.exec_config_var, width=20).pack(side='left', fill='x', expand=True)
        ttk.Button(config_file_frame, text="Browse", command=self.browse_config_file).pack(side='right', padx=(5, 0))

        # Timerange
        ttk.Label(params_frame, text="Timerange:").pack(anchor='w')
        self.exec_timerange_var = tk.StringVar(value="20240101-20241201")
        ttk.Entry(params_frame, textvariable=self.exec_timerange_var, width=25).pack(fill='x', pady=(0, 10))

        # Epochs (for hyperopt)
        ttk.Label(params_frame, text="Epochs:").pack(anchor='w')
        self.exec_epochs_var = tk.StringVar(value="100")
        ttk.Entry(params_frame, textvariable=self.exec_epochs_var, width=25).pack(fill='x', pady=(0, 10))

        # Hyperopt Loss Function
        ttk.Label(params_frame, text="Hyperopt Loss Function:").pack(anchor='w')
        self.exec_hyperfunction_var = tk.StringVar(value=self.hyperfunction)
        hyperfunction_combo = ttk.Combobox(params_frame, textvariable=self.exec_hyperfunction_var, width=25)
        hyperfunction_combo['values'] = [
            'SharpeHyperOptLoss',
            'SortinoHyperOptLoss',
            'CalmarHyperOptLoss',
            'MaxDrawDownHyperOptLoss',
            'ProfitDrawDownHyperOptLoss',
            'OnlyProfitHyperOptLoss',
            'ShortTradeDurHyperOptLoss'
        ]
        hyperfunction_combo.pack(fill='x', pady=(0, 10))

        # Hyperopt spaces
        ttk.Label(params_frame, text="Hyperopt Spaces:").pack(anchor='w')
        spaces_frame = ttk.Frame(params_frame)
        spaces_frame.pack(fill='x', pady=(0, 10))

        self.spaces_vars = {}
        spaces = ['buy', 'sell', 'roi', 'stoploss']
        for i, space in enumerate(spaces):
            var = tk.BooleanVar(value=True)
            self.spaces_vars[space] = var
            ttk.Checkbutton(spaces_frame, text=space.title(), variable=var).grid(row=i // 2, column=i % 2, sticky='w')

        # Execution buttons
        buttons_frame = ttk.LabelFrame(left_exec_panel, text="Execution", padding=10)
        buttons_frame.pack(fill='x')

        ttk.Button(buttons_frame, text="Run Hyperopt", command=self.run_hyperopt, style='Accent.TButton').pack(fill='x',
                                                                                                               pady=(0, 5))
        ttk.Button(buttons_frame, text="Run Backtest", command=self.run_backtest).pack(fill='x', pady=(0, 5))
        ttk.Button(buttons_frame, text="Stop Execution", command=self.stop_execution).pack(fill='x')

        # Progress section
        progress_frame = ttk.LabelFrame(left_exec_panel, text="Progress", padding=10)
        progress_frame.pack(fill='x', pady=(10, 0))

        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(anchor='w')

        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=(5, 0))

        # Create right panel for output
        right_exec_panel = ttk.Frame(self.execution_frame)
        right_exec_panel.pack(side='right', fill='both', expand=True, padx=(5, 10), pady=10)

        # Output section
        output_frame = ttk.LabelFrame(right_exec_panel, text="Execution Output", padding=10)
        output_frame.pack(fill='both', expand=True)

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.output_text.pack(fill='both', expand=True)

        # Initialize execution state
        self.execution_thread = None

        # Load strategies
        self.load_strategies()


    def create_logs_tab(self):
        """Create the logs tab."""
        self.logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_frame, text="Logs")

        # Logs toolbar
        logs_toolbar = ttk.Frame(self.logs_frame)
        logs_toolbar.pack(fill='x', padx=10, pady=5)

        ttk.Button(logs_toolbar, text="Refresh Logs", command=self.refresh_logs).pack(side='left', padx=(0, 5))
        ttk.Button(logs_toolbar, text="Clear Logs", command=self.clear_logs).pack(side='left', padx=(0, 5))
        ttk.Button(logs_toolbar, text="Save Logs", command=self.save_logs).pack(side='left')

        # Logs display
        logs_display_frame = ttk.Frame(self.logs_frame)
        logs_display_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.logs_text = scrolledtext.ScrolledText(logs_display_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.logs_text.pack(fill='both', expand=True)


    def refresh_data(self):
        """Refresh all data displays."""
        self.load_sessions()
        self.load_strategies_filter()
        self.load_timeframes()
        self.load_optimization_results()


    def load_sessions(self):
        """Load sessions into the combo box."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.execute("""
                        SELECT id, session_timestamp, successful_strategies, total_strategies
                        FROM optimization_sessions 
                        ORDER BY session_timestamp DESC
                    """)
                sessions = cursor.fetchall()

            session_options = ["All Sessions"]
            for session in sessions:
                session_id, timestamp, success, total = session
                session_options.append(f"Session {session_id} - {timestamp[:16]} ({success}/{total})")

            self.session_combo['values'] = session_options
            if session_options:
                self.session_combo.set(session_options[0])

        except Exception as e:
            self.logger.error(f"Error loading sessions: {e}")
            messagebox.showerror("Error", f"Failed to load sessions: {e}")

    def load_strategies_filter(self):
        """Load strategies for filter combo box."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.execute("""
                        SELECT DISTINCT strategy_name FROM strategy_optimizations 
                        ORDER BY strategy_name
                    """)
                strategies = [row[0] for row in cursor.fetchall()]

            strategy_options = ["All Strategies"] + strategies
            self.strategy_combo['values'] = strategy_options
            if strategy_options:
                self.strategy_combo.set(strategy_options[0])

        except Exception as e:
            self.logger.error(f"Error loading strategies: {e}")


    def load_timeframes(self):
        """Load timeframes for filter combo box."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.execute("""
                        SELECT DISTINCT timeframe FROM strategy_optimizations 
                        WHERE timeframe IS NOT NULL
                        ORDER BY timeframe
                    """)
                timeframes = [row[0] for row in cursor.fetchall()]

            timeframe_options = ["All Timeframes"] + timeframes
            self.timeframe_combo['values'] = timeframe_options
            if timeframe_options:
                self.timeframe_combo.set(timeframe_options[0])

        except Exception as e:
            self.logger.error(f"Error loading timeframes: {e}")


    def load_strategies(self):
        """Load strategies for execution combo box."""
        try:
            if not self.freqtrade_path:
                return

            strategies_dir = Path(self.freqtrade_path) / "user_data" / "strategies"
            if strategies_dir.exists():
                strategies = []
                for file in strategies_dir.glob("*.py"):
                    if not file.name.startswith("__"):
                        strategies.append(file.stem)

                self.exec_strategy_combo['values'] = sorted(strategies)
                if strategies:
                    self.exec_strategy_combo.set(strategies[0])
        except Exception as e:
            self.logger.error(f"Error loading strategies: {e}")

    def load_optimization_results(self):
        """Load optimization results based on current filters."""
        try:
            # Build query based on filters
            query = """
                SELECT id, strategy_name, total_profit_pct, total_trades, win_rate, 
                       optimization_timestamp, timeframe
                FROM strategy_optimizations 
                WHERE status = 'completed'
            """
            params = []

            # Apply session filter
            session_text = self.session_var.get()
            if session_text and session_text != "All Sessions":
                session_id = int(session_text.split()[1])
                query += " AND id IN (SELECT optimization_id FROM session_strategies WHERE session_id = ?)"
                params.append(session_id)

            # Apply strategy filter
            strategy_text = self.strategy_var.get()
            if strategy_text and strategy_text != "All Strategies":
                query += " AND strategy_name = ?"
                params.append(strategy_text)

            # Apply timeframe filter
            timeframe_text = self.timeframe_var.get()
            if timeframe_text and timeframe_text != "All Timeframes":
                query += " AND timeframe = ?"
                params.append(timeframe_text)

            query += " ORDER BY total_profit_pct DESC LIMIT 100"

            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.execute(query, params)
                results = cursor.fetchall()

            # Clear existing items
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)

            # Insert new items
            for result in results:
                opt_id, strategy, profit, trades, win_rate, timestamp, timeframe = result
                self.results_tree.insert('', 'end', values=(
                    opt_id,
                    strategy,
                    f"{profit:.2f}%" if profit else "N/A",
                    trades or "N/A",
                    f"{win_rate:.1f}%" if win_rate else "N/A",
                    timestamp[:10] if timestamp else "N/A"
                ))

        except Exception as e:
            self.logger.error(f"Error loading optimization results: {e}")
            messagebox.showerror("Error", f"Failed to load results: {e}")

    def on_result_select(self, event=None):
        """Handle result selection in the treeview."""
        selection = self.results_tree.selection()
        if not selection:
            return

        item = self.results_tree.item(selection[0])
        opt_id = item['values'][0]

        self.load_result_details(opt_id)


    def load_result_details(self, optimization_id):
        """Load detailed information for a selected optimization."""
        try:
            # Load optimization details
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                        SELECT * FROM strategy_optimizations WHERE id = ?
                    """, (optimization_id,))
                result = cursor.fetchone()

            if not result:
                return

            # Update metrics display
            metrics_mapping = {
                'total_profit_pct': lambda x: f"{x:.2f}%" if x else "N/A",
                'total_profit_abs': lambda x: f"{x:.8f}" if x else "N/A",
                'total_trades': lambda x: str(x) if x else "N/A",
                'win_rate': lambda x: f"{x:.1f}%" if x else "N/A",
                'avg_profit_pct': lambda x: f"{x:.2f}%" if x else "N/A",
                'max_drawdown_pct': lambda x: f"{x:.2f}%" if x else "N/A",
                'sharpe_ratio': lambda x: f"{x:.2f}" if x else "N/A",
                'optimization_duration_seconds': lambda x: f"{x // 60}m {x % 60}s" if x else "N/A",
                'run_number': lambda x: str(x) if x else "N/A",
                'timeframe': lambda x: str(x) if x else "N/A",
                'exchange_name': lambda x: str(x) if x else "N/A"
            }

            for key, formatter in metrics_mapping.items():
                if key in self.metrics_labels:
                    value = result[key] if key in result.keys() else None
                    self.metrics_labels[key].config(text=formatter(value))

            # Load configuration
            config_file_path = result['config_file_path']
            if config_file_path and Path(config_file_path).exists():
                with open(config_file_path, 'r') as f:
                    config_data = json.load(f)
                self.config_text.delete(1.0, tk.END)
                self.config_text.insert(1.0, json.dumps(config_data, indent=2))
            else:
                self.config_text.delete(1.0, tk.END)
                self.config_text.insert(1.0, "Configuration file not found")

            # Load hyperopt JSON
            hyperopt_data = self.db_manager.get_hyperopt_json_result(optimization_id)
            if hyperopt_data:
                self.hyperopt_text.delete(1.0, tk.END)
                self.hyperopt_text.insert(1.0, json.dumps(hyperopt_data, indent=2))
            else:
                self.hyperopt_text.delete(1.0, tk.END)
                self.hyperopt_text.insert(1.0, "Hyperopt JSON data not found")

        except Exception as e:
            self.logger.error(f"Error loading result details: {e}")
            messagebox.showerror("Error", f"Failed to load result details: {e}")


    # Config Editor Methods
    def load_config_file(self):
        """Load a configuration file into the editor."""
        file_path = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                self.config_editor.delete(1.0, tk.END)
                self.config_editor.insert(1.0, content)
                self.current_config_file = file_path
                self.current_file_label.config(text=f"File: {Path(file_path).name}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")


    def save_config_file(self):
        """Save the current configuration."""
        if not self.current_config_file:
            self.save_config_as()
            return

        try:
            content = self.config_editor.get(1.0, tk.END)
            with open(self.current_config_file, 'w') as f:
                f.write(content)

            messagebox.showinfo("Success", "Configuration saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")


    def save_config_as(self):
        """Save configuration as a new file."""
        file_path = filedialog.asksaveasfilename(
            title="Save Configuration As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            try:
                content = self.config_editor.get(1.0, tk.END)
                with open(file_path, 'w') as f:
                    f.write(content)

                self.current_config_file = file_path
                self.current_file_label.config(text=f"File: {Path(file_path).name}")
                messagebox.showinfo("Success", "Configuration saved successfully!")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")


    def new_config_file(self):
        """Create a new configuration file."""
        template = {
            "max_open_trades": 3,
            "stake_currency": "USDT",
            "stake_amount": 100,
            "tradable_balance_ratio": 0.99,
            "fiat_display_currency": "USD",
            "timeframe": "5m",
            "dry_run": True,
            "dry_run_wallet": 1000,
            "cancel_open_orders_on_exit": False,
            "exchange": {
                "name": "binance",
                "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
                "pair_blacklist": []
            },
            "pairlists": [{"method": "StaticPairList"}]
        }

        self.config_editor.delete(1.0, tk.END)
        self.config_editor.insert(1.0, json.dumps(template, indent=2))
        self.current_config_file = None
        self.current_file_label.config(text="New file (unsaved)")


    def validate_config_json(self):
        """Validate the JSON in the config editor."""
        try:
            content = self.config_editor.get(1.0, tk.END)
            json.loads(content)
            messagebox.showinfo("Validation", "JSON is valid!")
        except json.JSONDecodeError as e:
            messagebox.showerror("Validation Error", f"Invalid JSON: {e}")


    def update_line_numbers(self, event=None):
        """Update line numbers (simple implementation)."""
        # This is a placeholder for line number functionality
        pass


    # Execution Methods
    def browse_config_file(self):
        """Browse for configuration file for execution."""

        initial_path = Path(self.freqtrade_path) / "user_data" / "config"
        file_path = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=self.freqtrade_path
        )

        if file_path:
            self.exec_config_var.set(file_path)


    def run_hyperopt(self):
        self.notebook.select(3)
        """Run hyperopt optimization using the executor."""
        if self.executor and self.executor.is_running:
            messagebox.showwarning("Warning", "Another process is already running!")
            return

        if not self.executor:
            messagebox.showerror("Error", "Executor not initialized! Check your FreqTrade path configuration.")
            return

        strategy = self.exec_strategy_var.get()
        config_file = self.exec_config_var.get()
        timerange = self.exec_timerange_var.get()
        epochs = self.exec_epochs_var.get()

        if not strategy:
            messagebox.showerror("Error", "Please select a strategy!")
            return

        if not config_file:
            messagebox.showerror("Error", "Please select a configuration file!")
            return

        # Build spaces parameter
        selected_spaces = [space for space, var in self.spaces_vars.items() if var.get()]
        if not selected_spaces:
            messagebox.showerror("Error", "Please select at least one hyperopt space!")
            return

        try:
            epochs_int = int(epochs)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of epochs!")
            return

        selected_hyperfunction = self.exec_hyperfunction_var.get()

        # Clear output and start execution
        self.output_text.delete(1.0, tk.END)
        self.progress_bar.start()

        def run_in_thread():
            try:
                result = self.executor.run_hyperopt(
                    strategy_name=strategy,
                    config_file=config_file,
                    timerange=timerange,
                    epochs=epochs_int,
                    spaces=selected_spaces,
                    hyperopt_loss=selected_hyperfunction  # CHANGE: Use selected function
                )

                # Update GUI in main thread
                self.root.after(0, lambda: self.on_execution_complete(result))

            except Exception as e:
                error_msg = f"Error running hyperopt: {e}"
                self.root.after(0, lambda: self.execution_error(error_msg))

        self.execution_thread = threading.Thread(target=run_in_thread)
        self.execution_thread.daemon = True
        self.execution_thread.start()


    def run_backtest(self):
        """Run backtest using the executor."""
        if self.executor and self.executor.is_running:
            messagebox.showwarning("Warning", "Another process is already running!")
            return

        if not self.executor:
            messagebox.showerror("Error", "Executor not initialized! Check your FreqTrade path configuration.")
            return

        strategy = self.exec_strategy_var.get()
        config_file = self.exec_config_var.get()
        timerange = self.exec_timerange_var.get()

        if not strategy:
            messagebox.showerror("Error", "Please select a strategy!")
            return

        if not config_file:
            messagebox.showerror("Error", "Please select a configuration file!")
            return

        # Clear output and start execution
        self.output_text.delete(1.0, tk.END)
        self.progress_bar.start()

        def run_in_thread():
            try:
                result = self.executor.run_backtest(
                    strategy_name=strategy,
                    config_file=config_file,
                    timerange=timerange
                )

                # Update GUI in main thread
                self.root.after(0, lambda: self.on_execution_complete(result))

            except Exception as e:
                error_msg = f"Error running backtest: {e}"
                self.root.after(0, lambda: self.execution_error(error_msg))

        self.execution_thread = threading.Thread(target=run_in_thread)
        self.execution_thread.daemon = True
        self.execution_thread.start()

    def execute_command(self, command, operation_name):
        """Execute a FreqTrade command in a separate thread."""

        def run_command():
            try:
                self.progress_var.set(f"Running {operation_name}...")
                self.progress_bar.start()
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, f"Starting {operation_name}...\n")
                self.output_text.insert(tk.END, f"Command: {' '.join(command)}\n\n")

                # Change to FreqTrade directory
                env = os.environ.copy()
                if self.freqtrade_path:
                    cwd = self.freqtrade_path
                    # Activate virtual environment
                    if os.name == 'nt':  # Windows
                        venv_activate = Path(self.freqtrade_path) / '.venv' / 'Scripts' / 'activate.bat'
                        full_command = f'call "{venv_activate}" && ' + ' '.join(command)
                        self.current_process = subprocess.Popen(
                            full_command,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            cwd=cwd,
                            env=env
                        )
                    else:  # Unix/Linux
                        venv_activate = Path(self.freqtrade_path) / '.venv' / 'bin' / 'activate'
                        # Use bash explicitly and check if venv exists
                        if venv_activate.exists():
                            full_command = f'bash -c "source {venv_activate} && {" ".join(command)}"'
                        else:
                            # Try without virtual environment
                            full_command = ' '.join(command)
                            self.root.after(0, lambda: self.append_output(
                                "Warning: Virtual environment not found, running without venv\n"))

                        self.current_process = subprocess.Popen(
                            full_command,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            cwd=cwd,
                            env=env
                        )
                else:
                    # Run without virtual environment
                    self.current_process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )

                # Read output line by line
                while True:
                    output = self.current_process.stdout.readline()
                    if output == '' and self.current_process.poll() is not None:
                        break
                    if output:
                        self.root.after(0, lambda text=output: self.append_output(text))

                # Get return code
                return_code = self.current_process.poll()

                if return_code == 0:
                    self.root.after(0, lambda: self.execution_completed(f"{operation_name} completed successfully!"))
                else:
                    self.root.after(0, lambda: self.execution_completed(
                        f"{operation_name} failed with return code {return_code}"))

            except Exception as e:
                self.root.after(0, lambda: self.execution_error(f"Error running {operation_name}: {e}"))
            finally:
                self.current_process = None

        # Start execution in a separate thread
        self.execution_thread = threading.Thread(target=run_command)
        self.execution_thread.daemon = True
        self.execution_thread.start()


    def execution_completed(self, message):
        """Handle execution completion (called from main thread)."""
        self.progress_var.set(message)
        self.progress_bar.stop()
        self.output_text.insert(tk.END, f"\n{message}\n")
        self.output_text.see(tk.END)

        # Refresh data to show new results
        self.refresh_data()


    def execution_error(self, message):
        """Handle execution error (called from main thread)."""
        self.progress_var.set("Error")
        self.progress_bar.stop()
        self.output_text.insert(tk.END, f"\n{message}\n")
        self.output_text.see(tk.END)
        messagebox.showerror("Execution Error", message)

    def stop_execution(self):
        """Stop the current execution."""
        if self.executor and self.executor.is_running:
            if self.executor.stop_execution():
                self.progress_var.set("Execution stopped")
                self.progress_bar.stop()
                self.append_output("\nExecution stopped by user.\n")
            else:
                messagebox.showerror("Error", "Failed to stop execution!")
        else:
            messagebox.showinfo("Info", "No process is currently running.")

    # Logs Methods
    def refresh_logs(self):
        """Refresh the logs display."""
        try:
            logs_dir = Path("logs")
            if logs_dir.exists():
                # Get the most recent log file
                log_files = list(logs_dir.glob("freqtrade_optimizer_*.log"))
                if log_files:
                    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
                    with open(latest_log, 'r') as f:
                        content = f.read()

                    self.logs_text.delete(1.0, tk.END)
                    self.logs_text.insert(1.0, content)
                    self.logs_text.see(tk.END)
                else:
                    self.logs_text.delete(1.0, tk.END)
                    self.logs_text.insert(1.0, "No log files found.")
            else:
                self.logs_text.delete(1.0, tk.END)
                self.logs_text.insert(1.0, "Logs directory not found.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load logs: {e}")


    def clear_logs(self):
        """Clear the logs display."""
        self.logs_text.delete(1.0, tk.END)


    def save_logs(self):
        """Save logs to a file."""
        content = self.logs_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("Warning", "No logs to save!")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Logs",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                messagebox.showinfo("Success", "Logs saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {e}")


def main():
    """Main function to run the dashboard."""
    root = tk.Tk()

    # Configure ttk styles
    style = ttk.Style()
    style.theme_use('clam')  # Use a modern theme

    # Configure custom styles
    style.configure('Accent.TButton', foreground='white', background='#0078d4')
    style.map('Accent.TButton', background=[('active', '#106ebe')])

    # Create and run the dashboard
    app = FreqTradeDashboard(root)

    # Handle window closing
    def on_closing():
        if app.executor and app.executor.is_running:
            if messagebox.askokcancel("Quit", "A process is running. Do you want to stop it and quit?"):
                app.executor.stop_execution()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the GUI
    root.mainloop()


if __name__ == "__main__":
    main()