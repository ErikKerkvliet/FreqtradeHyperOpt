#!/usr/bin/env python3
"""
Backtest Analysis Tab
Displays and manages backtest results.
"""

import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path

from .abstract_tab import AbstractTab


class BacktestAnalysisTab(AbstractTab):
    """
    A dedicated tab for analyzing backtest results and reality gap.
    """

    def __init__(self, parent, db_manager, logger):
        """Initialize the Backtest Analysis tab."""
        super().__init__(parent, db_manager, logger)
        self.frame = ttk.Frame(self.parent)

        # Tab-specific variables
        self.strategy_var = tk.StringVar()
        self.timeframe_var = tk.StringVar()

        # Widgets
        self.strategy_combo = None
        self.timeframe_combo = None
        self.results_tree = None
        self.config_text = None
        self.backtest_text = None
        self.metrics_labels = {}

    def create_tab(self) -> ttk.Frame:
        """Create the backtest analysis tab interface."""
        left_panel = ttk.Frame(self.frame)
        left_panel.pack(side='left', fill='y', padx=(0, 10), pady=10)
        right_panel = ttk.Frame(self.frame)
        right_panel.pack(side='right', fill='both', expand=True, pady=10)

        self._create_filters_section(left_panel)
        self._create_results_section(left_panel)
        self._create_details_section(right_panel)

        return self.frame

    def _create_filters_section(self, parent):
        """Create the filters for backtest results."""
        filters_frame = self.create_labeled_frame(parent, "Filters")
        filters_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(filters_frame, text="Strategy:").pack(anchor='w')
        self.strategy_combo = ttk.Combobox(filters_frame, textvariable=self.strategy_var, width=25, state="readonly")
        self.strategy_combo.pack(fill='x', pady=(0, 10))
        self.strategy_combo.bind('<<ComboboxSelected>>', lambda e: self.load_backtest_results())

        ttk.Label(filters_frame, text="Timeframe:").pack(anchor='w')
        self.timeframe_combo = ttk.Combobox(filters_frame, textvariable=self.timeframe_var, width=25, state="readonly")
        self.timeframe_combo.pack(fill='x', pady=(0, 10))
        self.timeframe_combo.bind('<<ComboboxSelected>>', lambda e: self.load_backtest_results())

        ttk.Button(filters_frame, text="Refresh Data", command=self.refresh_data).pack(fill='x')

    def _create_results_section(self, parent):
        """Create the treeview list for backtest results."""
        results_frame = self.create_labeled_frame(parent, "Backtest Results")
        results_frame.pack(fill='both', expand=True)

        columns = ('ID', 'Strategy', 'BT Profit %', 'Opt Profit %', 'Gap %', 'Trades', 'Date')
        self.results_tree = self.create_treeview(results_frame, columns)

        column_config = {
            'ID': {'text': 'ID', 'width': 40},
            'Strategy': {'text': 'Strategy', 'width': 120},
            'BT Profit %': {'text': 'BT Profit', 'width': 70},
            'Opt Profit %': {'text': 'Opt Profit', 'width': 70},
            'Gap %': {'text': 'Gap', 'width': 60},
            'Trades': {'text': 'Trades', 'width': 60},
            'Date': {'text': 'Date', 'width': 90}
        }
        self.setup_treeview_columns(self.results_tree, column_config)
        self.bind_treeview_selection(self.results_tree, self._on_result_select)

        # FIX: Simplified and corrected layout for Treeview and Scrollbar
        v_scroll = ttk.Scrollbar(results_frame, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side='right', fill='y')
        self.results_tree.pack(side='left', fill='both', expand=True)

    def _create_details_section(self, parent):
        """Create the right-side panel for showing result details."""
        details_frame = self.create_labeled_frame(parent, "Backtest Details")
        details_frame.pack(fill='both', expand=True)

        details_notebook = ttk.Notebook(details_frame)
        details_notebook.pack(fill='both', expand=True)

        metrics_frame = ttk.Frame(details_notebook)
        config_frame = ttk.Frame(details_notebook)
        backtest_frame = ttk.Frame(details_notebook)

        details_notebook.add(metrics_frame, text="Metrics")
        details_notebook.add(config_frame, text="Configuration")
        details_notebook.add(backtest_frame, text="Backtest Log")

        self.config_text = self.create_scrolled_text(config_frame, wrap=tk.WORD)
        self.config_text.pack(fill='both', expand=True)
        self.backtest_text = self.create_scrolled_text(backtest_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.backtest_text.pack(fill='both', expand=True)

        self._create_metrics_display(metrics_frame)

    def _create_metrics_display(self, parent):
        """Create the grid of performance metrics."""
        metrics_container = ttk.Frame(parent, padding=10)
        metrics_container.pack(fill='both', expand=True)

        metrics_info = [
            ('Total Profit %', 'total_profit_pct'), ('Sharpe Ratio', 'sharpe_ratio'),
            ('Avg. Trade Duration', 'avg_trade_duration'), ('Sortino Ratio', 'sortino_ratio'),
            ('Total Trades', 'total_trades'), ('Calmar Ratio', 'calmar_ratio'),
            ('Win Rate %', 'win_rate'), ('Expectancy', 'expectancy'),
            ('Max Drawdown %', 'max_drawdown_pct'), ('Profit Factor', 'profit_factor'),
            ('Best Trade %', 'best_trade_pct'), ('Worst Trade %', 'worst_trade_pct'),
        ]

        self.metrics_labels = {}
        for i, (label, key) in enumerate(metrics_info):
            ttk.Label(metrics_container, text=f"{label}:").grid(row=i % 6, column=(i // 6) * 2, sticky='w',
                                                                padx=(0, 10), pady=2)
            value_label = ttk.Label(metrics_container, text="N/A", font=('TkDefaultFont', 9, 'bold'))
            value_label.grid(row=i % 6, column=(i // 6) * 2 + 1, sticky='w', padx=(0, 20), pady=2)
            self.metrics_labels[key] = value_label

    def _on_result_select(self, event=None):
        """Callback when a result is selected in the treeview."""
        selected_item = self.get_selected_treeview_item(self.results_tree)
        if selected_item:
            self.load_result_details(selected_item['values'][0])

    def load_strategies_filter(self):
        """Load strategy names for the filter dropdown."""
        query = "SELECT DISTINCT strategy_name FROM backtest_results ORDER BY strategy_name"
        results = self.execute_database_query(query)
        options = ["All Strategies"] + [row['strategy_name'] for row in results] if results else []
        self.populate_combobox(self.strategy_combo, options, "All Strategies")

    def load_timeframes(self):
        """Load timeframes for the filter dropdown."""
        query = "SELECT DISTINCT timeframe FROM backtest_results WHERE timeframe IS NOT NULL ORDER BY timeframe"
        results = self.execute_database_query(query)
        options = ["All Timeframes"] + [row['timeframe'] for row in results] if results else []
        self.populate_combobox(self.timeframe_combo, options, "All Timeframes")

    def load_backtest_results(self):
        """Load and display backtest results based on current filters."""
        query = """
            SELECT b.id, b.strategy_name, b.total_profit_pct AS bt_profit, b.total_trades, b.timestamp,
                   h.total_profit_pct AS opt_profit
            FROM backtest_results b
            LEFT JOIN hyperopt_results h ON b.hyperopt_id = h.id
            WHERE b.status = 'completed'
        """
        params = []

        if self.strategy_var.get() != "All Strategies":
            query += " AND b.strategy_name = ?"
            params.append(self.strategy_var.get())
        if self.timeframe_var.get() != "All Timeframes":
            query += " AND b.timeframe = ?"
            params.append(self.timeframe_var.get())

        query += " ORDER BY b.total_profit_pct DESC LIMIT 100"
        results = self.execute_database_query(query, tuple(params))

        self.clear_treeview(self.results_tree)
        if results:
            for row in results:
                gap = (row['bt_profit'] or 0) - (row['opt_profit'] or 0)
                self.results_tree.insert('', 'end', values=(
                    row['id'], row['strategy_name'],
                    self.format_percentage(row['bt_profit']),
                    self.format_percentage(row['opt_profit']) if row['opt_profit'] is not None else "N/A",
                    self.format_percentage(gap) if row['opt_profit'] is not None else "N/A",
                    row['total_trades'] or "N/A",
                    row['timestamp'][:10] if row['timestamp'] else "N/A"
                ))

    def load_result_details(self, backtest_id: int):
        """Load the details for a specific backtest result."""
        query = "SELECT * FROM backtest_results WHERE id = ?"
        results = self.execute_database_query(query, (backtest_id,))
        if not results: return
        result = results[0]

        # Update metrics
        for key, label in self.metrics_labels.items():
            value = result[key] if key in result.keys() else None
            if isinstance(value, float) and ('_pct' in key or 'rate' in key):
                formatted = self.format_percentage(value)
            elif isinstance(value, float):
                formatted = self.format_number(value)
            else:
                formatted = value or "N/A"
            label.config(text=str(formatted))

        # Load config file content
        self.config_text.delete(1.0, tk.END)
        config_path = result['config_file_path']
        if config_path and Path(config_path).exists():
            config_data = self.load_json_file(config_path)
            self.config_text.insert(1.0, json.dumps(config_data, indent=2) if config_data else "Failed to load config.")
        else:
            self.config_text.insert(1.0, "Configuration file not found.")

        # Load backtest log
        self.backtest_text.delete(1.0, tk.END)
        if result['backtest_json']:
            try:
                backtest_data = json.loads(result['backtest_json'])
                raw_output = backtest_data.get('raw_output', json.dumps(backtest_data, indent=2))
                self.backtest_text.insert(1.0, raw_output)
            except (json.JSONDecodeError, TypeError):
                self.backtest_text.insert(1.0, result['backtest_json'])
        else:
            self.backtest_text.insert(1.0, "Backtest log not found.")

    def refresh_data(self):
        """Refresh all data displays in this tab."""
        self.load_strategies_filter()
        self.load_timeframes()
        self.load_backtest_results()