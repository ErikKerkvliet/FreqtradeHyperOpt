#!/usr/bin/env python3
"""
Execution Tab
Handles the execution functionality of the dashboard.
"""

import tkinter as tk
from tkinter import ttk
import threading
from pathlib import Path

from .abstract_tab import AbstractTab


class ExecutionTab(AbstractTab):
    """
    Tab for executing FreqTrade commands (hyperopt, backtest, etc.).
    """

    def __init__(self, parent, db_manager, logger):
        """Initialize the Execution tab."""
        super().__init__(parent, db_manager, logger)

        # Tab-specific variables
        self.exec_strategy_var = tk.StringVar()
        self.exec_config_var = tk.StringVar()
        self.exec_timerange_var = tk.StringVar(value="20240101-20241201")
        self.exec_epochs_var = tk.StringVar(value="100")
        self.exec_hyperfunction_var = tk.StringVar(value="SharpeHyperOptLoss")
        self.progress_var = tk.StringVar(value="Ready")

        # Hyperopt spaces
        self.spaces_vars = {}

        # Widgets
        self.exec_strategy_combo = None
        self.exec_config_entry = None
        self.progress_bar = None
        self.output_text = None

        # Execution state
        self.execution_thread = None

    def create_tab(self) -> ttk.Frame:
        """Create the execution tab."""
        self.frame = ttk.Frame(self.parent)

        # Configure grid layout for the main frame
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=0, minsize=350)  # Fixed width for left panel
        self.frame.grid_columnconfigure(1, weight=1)  # Expandable right panel

        # Create left panel for parameters (FIXED WIDTH)
        left_exec_panel = ttk.Frame(self.frame)
        left_exec_panel.grid(row=0, column=0, sticky='nsew', padx=(10, 5), pady=10)

        # Create right panel for output (EXPANDABLE)
        right_exec_panel = ttk.Frame(self.frame)
        right_exec_panel.grid(row=0, column=1, sticky='nsew', padx=(5, 10), pady=10)
        right_exec_panel.grid_rowconfigure(0, weight=1)
        right_exec_panel.grid_columnconfigure(0, weight=1)

        self._create_parameters_section(left_exec_panel)
        self._create_execution_buttons(left_exec_panel)
        self._create_progress_section(left_exec_panel)
        self._create_output_section(right_exec_panel)

        # Load initial data
        self._load_strategies()

        return self.frame

    def _create_parameters_section(self, parent):
        """Create the execution parameters section."""
        params_frame = self.create_labeled_frame(parent, "Execution Parameters")
        params_frame.pack(fill='x', pady=(0, 10))

        # Strategy selection
        ttk.Label(params_frame, text="Strategy:").pack(anchor='w')
        self.exec_strategy_combo = ttk.Combobox(params_frame, textvariable=self.exec_strategy_var, width=25)
        self.exec_strategy_combo.pack(fill='x', pady=(0, 10))

        # Config file selection
        ttk.Label(params_frame, text="Config File:").pack(anchor='w')
        config_file_frame = ttk.Frame(params_frame)
        config_file_frame.pack(fill='x', pady=(0, 10))

        self.exec_config_entry = ttk.Entry(config_file_frame, textvariable=self.exec_config_var, width=20)
        self.exec_config_entry.pack(side='left', fill='x', expand=True)
        ttk.Button(config_file_frame, text="Browse", command=self._browse_config_file).pack(side='right', padx=(5, 0))

        # Timerange
        ttk.Label(params_frame, text="Timerange:").pack(anchor='w')
        ttk.Entry(params_frame, textvariable=self.exec_timerange_var, width=25).pack(fill='x', pady=(0, 10))

        # Epochs (for hyperopt)
        ttk.Label(params_frame, text="Epochs:").pack(anchor='w')
        ttk.Entry(params_frame, textvariable=self.exec_epochs_var, width=25).pack(fill='x', pady=(0, 10))

        # Hyperopt Loss Function
        ttk.Label(params_frame, text="Hyperopt Loss Function:").pack(anchor='w')
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

        spaces = ['buy', 'sell', 'roi', 'stoploss']
        for i, space in enumerate(spaces):
            var = tk.BooleanVar(value=True)
            self.spaces_vars[space] = var
            ttk.Checkbutton(spaces_frame, text=space.title(), variable=var).grid(
                row=i // 2, column=i % 2, sticky='w'
            )

    def _create_execution_buttons(self, parent):
        """Create the execution buttons section."""
        buttons_frame = self.create_labeled_frame(parent, "Execution")
        buttons_frame.pack(fill='x')

        ttk.Button(buttons_frame, text="Run Hyperopt", command=self._run_hyperopt,
                   style='Accent.TButton').pack(fill='x', pady=(0, 5))
        ttk.Button(buttons_frame, text="Run Backtest", command=self._run_backtest).pack(fill='x', pady=(0, 5))
        ttk.Button(buttons_frame, text="Download Data", command=self._download_data).pack(fill='x', pady=(0, 5))
        ttk.Button(buttons_frame, text="Stop Execution", command=self._stop_execution).pack(fill='x')

    def _create_progress_section(self, parent):
        """Create the progress section."""
        progress_frame = self.create_labeled_frame(parent, "Progress")
        progress_frame.pack(fill='x', pady=(10, 0))

        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var, wraplength=300)
        progress_label.pack(anchor='w')

        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=(5, 0))

    def _create_output_section(self, parent):
        """Create the output section."""
        output_frame = self.create_labeled_frame(parent, "Execution Output")
        output_frame.grid(row=0, column=0, sticky='nsew')
        output_frame.grid_rowconfigure(0, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)

        self.output_text = self.create_scrolled_text(output_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.output_text.grid(row=0, column=0, sticky='nsew')

    def _load_strategies(self):
        """Load strategies for execution combo box."""
        try:
            freqtrade_path = self.call_callback('get_freqtrade_path')
            if not freqtrade_path:
                return

            strategies_dir = Path(freqtrade_path) / "user_data" / "strategies"
            if strategies_dir.exists():
                strategies = []
                for file in strategies_dir.glob("*.py"):
                    if not file.name.startswith("__"):
                        strategies.append(file.stem)

                self.populate_combobox(self.exec_strategy_combo, sorted(strategies))

        except Exception as e:
            self.logger.error(f"Error loading strategies: {e}")

    def _browse_config_file(self):
        """Browse for configuration file for execution."""
        initial_path = Path("../../configs")
        file_path = self.browse_file(
            title="Select Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(initial_path) if initial_path.exists() else None
        )

        if file_path:
            self.exec_config_var.set(file_path)

    def _run_hyperopt(self):
        """Run hyperopt optimization."""
        if not self._validate_execution_params():
            return

        strategy = self.exec_strategy_var.get()
        config_file = self.exec_config_var.get()
        timerange = self.exec_timerange_var.get()
        epochs = self.exec_epochs_var.get()
        hyperfunction = self.exec_hyperfunction_var.get()

        # Get selected spaces
        selected_spaces = [space for space, var in self.spaces_vars.items() if var.get()]
        if not selected_spaces:
            self.show_error("Error", "Please select at least one hyperopt space!")
            return

        try:
            epochs_int = int(epochs)
        except ValueError:
            self.show_error("Error", "Please enter a valid number of epochs!")
            return

        # Clear output and start execution
        self.output_text.delete(1.0, tk.END)
        self.progress_bar.start()

        def run_in_thread():
            try:
                executor = self.call_callback('get_executor')
                if not executor:
                    self._execution_error("Executor not available")
                    return

                result = executor.run_hyperopt(
                    strategy_name=strategy,
                    config_file=config_file,
                    timerange=timerange,
                    epochs=epochs_int,
                    spaces=selected_spaces,
                    hyperopt_loss=hyperfunction
                )

                # Update GUI in main thread
                self.frame.after(0, lambda: self._on_execution_complete(result))

            except Exception as e:
                error_msg = f"Error running hyperopt: {e}"
                self.frame.after(0, lambda: self._execution_error(error_msg))

        self.execution_thread = threading.Thread(target=run_in_thread)
        self.execution_thread.daemon = True
        self.execution_thread.start()

    def _run_backtest(self):
        """Run backtest."""
        if not self._validate_execution_params():
            return

        strategy = self.exec_strategy_var.get()
        config_file = self.exec_config_var.get()
        timerange = self.exec_timerange_var.get()

        # Clear output and start execution
        self.output_text.delete(1.0, tk.END)
        self.progress_bar.start()

        def run_in_thread():
            try:
                executor = self.call_callback('get_executor')
                if not executor:
                    self._execution_error("Executor not available")
                    return

                result = executor.run_backtest(
                    strategy_name=strategy,
                    config_file=config_file,
                    timerange=timerange
                )

                # Update GUI in main thread
                self.frame.after(0, lambda: self._on_execution_complete(result))

            except Exception as e:
                error_msg = f"Error running backtest: {e}"
                self.frame.after(0, lambda: self._execution_error(error_msg))

        self.execution_thread = threading.Thread(target=run_in_thread)
        self.execution_thread.daemon = True
        self.execution_thread.start()

    def _download_data(self):
        """Download market data."""
        self.call_callback('show_download_dialog')

    def _stop_execution(self):
        """Stop the current execution."""
        executor = self.call_callback('get_executor')
        if executor and executor.is_running:
            if executor.stop_execution():
                self.progress_var.set("Execution stopped")
                self.progress_bar.stop()
                self._append_output("\nExecution stopped by user.\n")
            else:
                self.show_error("Error", "Failed to stop execution!")
        else:
            self.show_info("Info", "No process is currently running.")

    def _validate_execution_params(self) -> bool:
        """Validate execution parameters."""
        strategy = self.exec_strategy_var.get()
        config_file = self.exec_config_var.get()

        if not strategy:
            self.show_error("Error", "Please select a strategy!")
            return False

        if not config_file:
            self.show_error("Error", "Please select a configuration file!")
            return False

        if config_file and not Path(config_file).exists():
            self.show_error("Error", f"Configuration file not found: {config_file}")
            return False

        return True

    def _on_execution_complete(self, result):
        """Handle execution completion."""
        self.progress_bar.stop()

        if result.success:
            message = "Command completed successfully!"
            full_message = "command completed successfully!"
            if hasattr(result, 'hyperopt_id') and result.hyperopt_id:
                full_message += f"\n (Hyperopt DB record: {result.hyperopt_id})"
            elif hasattr(result, 'backtest_id') and result.backtest_id:
                full_message += f"\n (Backtest DB record: {result.backtest_id})"

            self.progress_var.set(message)
            self._append_output(f"\n✓ {full_message}\n")

            # Refresh data in other tabs
            self.call_callback('refresh_results_data')
        else:
            message = "Unknown error"
            self.progress_var.set(f"Error")
            self._append_output(f"\n✗ Error: {message}\n")

    def _execution_error(self, message: str):
        """Handle execution error."""
        self.progress_var.set("Error")
        self.progress_bar.stop()
        self._append_output(f"\n✗ {message}\n")
        self.show_error("Execution Error", message)

    def _append_output(self, text: str):
        """Append text to output display."""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

    def update_progress(self, message: str):
        """Update progress display (called from executor callback)."""
        self.progress_var.set(message)

    def append_output(self, text: str):
        """Append text to output display (called from executor callback)."""
        self._append_output(text)

    def set_strategy(self, strategy_name: str):
        """Set the strategy for execution."""
        self.exec_strategy_var.set(strategy_name)

    def set_config_file(self, config_file: str):
        """Set the config file for execution."""
        self.exec_config_var.set(config_file)

    def refresh_data(self):
        """Refresh strategies list."""
        self._load_strategies()