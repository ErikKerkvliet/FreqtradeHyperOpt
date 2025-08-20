#!/usr/bin/env python3
"""
FreqTrade Dashboard GUI - Main Orchestrator
This file contains the main FreqTradeDashboard class that assembles all the tabs
and manages the overall application state.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv

# Import your existing modules
from ..results_database_manager import DatabaseManager
from ..optimization_config import OptimizationConfig
from ..freqtrade_executor import FreqTradeExecutor

# Import the new modular tabs
from .results_analysis_tab import ResultsAnalysisTab
from .data_management_tab import DataManagementTab
from .config_editor_tab import ConfigEditorTab
from .execution_tab import ExecutionTab
from .logs_tab import LogsTab


class FreqTradeDashboard:
    """Main dashboard application class that orchestrates all the UI tabs."""

    def __init__(self, root: tk.Tk):
        """Initialize the main dashboard application."""
        self.root = root
        self.root.title("FreqTrade Optimization Dashboard")
        self.root.geometry("1200x800")

        self.logger: Optional[logging.Logger] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.executor: Optional[FreqTradeExecutor] = None

        # Configuration variables
        self.freqtrade_path = ""
        self.config = None

        # Initialize core components
        self.setup_logging()
        self.db_manager = DatabaseManager()
        self.load_basic_config()

        # Create main interface
        self.create_widgets()

        # Initialize executor after GUI is built - pass the shared db_manager
        self.initialize_executor()

        # Setup communication between tabs
        self.setup_callbacks()

        # Load initial data into all tabs
        self.refresh_all_data()

    def setup_logging(self):
        """
        Setup comprehensive logging to both console and a file for the GUI.
        This ensures log files are created for the LogsTab to display.
        """
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"freqtrade_dashboard_{timestamp}.log"

        # Configure logging with both a file and stream handler
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("FreqTrade Dashboard GUI Initialized")

    def load_basic_config(self):
        """Load basic configuration from .env file."""
        load_dotenv()
        self.freqtrade_path = os.getenv('FREQTRADE_PATH', '')

        try:
            days = int(os.getenv('HISTORICAL_DATA_IN_DAYS', '365'))
            start_date = datetime.now() - timedelta(days=days)
            timerange = f"{start_date.strftime('%Y%m%d')}-"

            self.config = OptimizationConfig(
                freqtrade_path=self.freqtrade_path,
                exchange=os.getenv('EXCHANGE', 'binance'),
                timeframe=os.getenv('TIMEFRAME', '5m'),
                timerange=timerange,
                pairs=os.getenv('PAIRS', 'BTC/USDT,ETH/USDT').split(','),
                pair_data_exchange=os.getenv('PAIR_DATA_EXCHANGE', os.getenv('EXCHANGE', 'binance')),
                hyperfunction=os.getenv('HYPERFUNCTION', 'SharpeHyperOptLoss')
            )
        except Exception as e:
            self.logger.error(f"Failed to create full OptimizationConfig: {e}")
            self.config = None

    def initialize_executor(self):
        """Initialize the FreqTrade executor."""
        if self.config and Path(self.config.freqtrade_path).exists():
            try:
                # Pass the shared db_manager to avoid duplicate initialization
                self.executor = FreqTradeExecutor(self.config, self.logger, self.db_manager)
            except Exception as e:
                self.logger.error(f"Failed to initialize executor: {e}")
                messagebox.showerror("Executor Error", f"Failed to initialize FreqTrade executor: {e}")
                self.executor = None
        else:
            self.logger.warning("FreqTrade path not configured or does not exist. Executor not initialized.")

    def create_widgets(self):
        """Create the main GUI widgets and assemble the tabs."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Instantiate each tab
        self.results_tab = ResultsAnalysisTab(self.notebook, self.db_manager, self.logger)
        self.data_tab = DataManagementTab(self.notebook, self.db_manager, self.logger)
        self.config_tab = ConfigEditorTab(self.notebook, self.db_manager, self.logger)
        self.execution_tab = ExecutionTab(self.notebook, self.db_manager, self.logger)
        self.logs_tab = LogsTab(self.notebook, self.db_manager, self.logger)

        # Create and add each tab to the notebook
        self.notebook.add(self.results_tab.create_tab(), text="Results Analysis")
        self.notebook.add(self.data_tab.create_tab(), text="Data Management")
        self.notebook.add(self.config_tab.create_tab(), text="Config Editor")
        self.notebook.add(self.execution_tab.create_tab(), text="Execution")
        self.notebook.add(self.logs_tab.create_tab(), text="Logs")

    def setup_callbacks(self):
        """Setup callbacks to enable communication between tabs and the main app."""
        # Register callbacks that tabs can call on the main dashboard
        tab_callbacks = {
            'get_executor': lambda: self.executor,
            'get_freqtrade_path': lambda: self.freqtrade_path,
            'refresh_results_data': self.results_tab.refresh_data,
            'show_download_dialog': self.show_download_data_dialog,  # Updated to accept config_data parameter
        }

        # Set these callbacks for each tab
        for tab in [self.results_tab, self.data_tab, self.config_tab, self.execution_tab, self.logs_tab]:
            for name, func in tab_callbacks.items():
                tab.set_callback(name, func)

        # Set callbacks from the main app to the tabs (e.g., for executor output)
        if self.executor:
            self.executor.set_callbacks(
                progress_callback=self.execution_tab.update_progress,
                output_callback=self.execution_tab.append_output,
                completion_callback=self.execution_tab._on_execution_complete
            )
    def refresh_all_data(self):
        """Refresh the data in all tabs."""
        for tab in [self.results_tab, self.data_tab, self.config_tab, self.execution_tab, self.logs_tab]:
            try:
                tab.refresh_data()
            except Exception as e:
                self.logger.error(f"Error refreshing tab {tab.__class__.__name__}: {e}")

    def show_download_data_dialog(self, config_data: dict = None):
        """Open a dialog to download new market data with optional pre-filled config data."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Download Data")
        window_height = "367" if config_data else "343"
        dialog.geometry(f"450x{window_height}")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Pre-fill from config_data if available, otherwise use defaults
        default_exchange = "binance"
        default_pairs = "BTC/USDT,ETH/USDT"
        default_timeframes = ['5m', '1h']

        if config_data:
            default_exchange = config_data.get('exchange', default_exchange)
            if config_data.get('pairs'):
                default_pairs = ",".join(config_data['pairs'])
            if config_data.get('timeframe'):
                # If config has a specific timeframe, pre-select it and similar ones
                config_tf = config_data['timeframe']
                if config_tf in ['1m', '5m', '15m', '30m']:
                    default_timeframes = ['1m', '5m', '15m']
                elif config_tf in ['1h', '4h']:
                    default_timeframes = ['1h', '4h']
                elif config_tf == '1d':
                    default_timeframes = ['1d']
                else:
                    default_timeframes = [config_tf] if config_tf in ['1m', '5m', '15m', '30m', '1h', '4h', '1d'] else [
                        '5m', '1h']

        # Exchange
        ttk.Label(main_frame, text="Exchange:").pack(anchor='w')
        exchange_var = tk.StringVar(value=default_exchange)
        exchange_combo = ttk.Combobox(main_frame, textvariable=exchange_var)
        exchange_combo['values'] = ['binance', 'kraken', 'coinbase', 'bittrex', 'okx']
        exchange_combo.pack(fill='x', pady=(0, 10))

        # Pairs
        ttk.Label(main_frame, text="Trading Pairs (comma-separated):").pack(anchor='w')
        pairs_var = tk.StringVar(value=default_pairs)
        pairs_entry = ttk.Entry(main_frame, textvariable=pairs_var)
        pairs_entry.pack(fill='x', pady=(0, 10))

        # Add helpful text if config was used
        if config_data:
            help_label = ttk.Label(main_frame, text="✓ Pre-filled from selected config file",
                                   foreground='green', font=('TkDefaultFont', 8))
            help_label.pack(anchor='w', pady=(0, 5))

        # Timeframes
        ttk.Label(main_frame, text="Timeframes:").pack(anchor='w')
        timeframes_frame = ttk.Frame(main_frame)
        timeframes_frame.pack(fill='x', pady=(0, 10))
        timeframe_vars = {}
        timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

        for i, tf in enumerate(timeframes):
            var = tk.BooleanVar(value=(tf in default_timeframes))
            timeframe_vars[tf] = var
            ttk.Checkbutton(timeframes_frame, text=tf, variable=var).grid(row=i // 4, column=i % 4, sticky='w',
                                                                          padx=(0, 10))

        # Days of history
        ttk.Label(main_frame, text="Days of history:").pack(anchor='w')
        days_var = tk.StringVar(value="30")
        ttk.Entry(main_frame, textvariable=days_var).pack(fill='x', pady=(0, 20))

        def start_download():
            selected_timeframes = [tf for tf, var in timeframe_vars.items() if var.get()]
            pairs = [p.strip() for p in pairs_var.get().split(',') if p.strip()]

            if not self.executor:
                messagebox.showerror("Error", "Executor is not initialized.")
                return
            if not selected_timeframes:
                messagebox.showerror("Error", "Please select at least one timeframe.")
                return
            if not pairs:
                messagebox.showerror("Error", "Please enter at least one trading pair.")
                return

            try:
                days = int(days_var.get())
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number of days.")
                return

            dialog.destroy()

            # Switch to execution tab and run download
            self.notebook.select(3)
            import threading
            threading.Thread(
                target=self.executor.download_data,
                args=(exchange_var.get(), pairs, selected_timeframes),
                kwargs={'days': days},
                daemon=True
            ).start()

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Download", command=start_download, style='Accent.TButton').pack(side='right')

    def cleanup(self):
        """
        FIX: Add a safe cleanup method to be called before the application closes.
        This will ensure background threads are stopped gracefully.
        """
        self.logger.info("Performing cleanup before application exit...")
        self.logs_tab.cleanup()
        if self.executor:
            self.executor.stop_execution()