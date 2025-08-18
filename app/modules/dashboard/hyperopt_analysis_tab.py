#!/usr/bin/env python3
"""
Hyperopt Analysis Tab
Displays and manages hyperparameter optimization results.
"""

import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path

from .abstract_tab import AbstractTab


class HyperoptAnalysisTab(AbstractTab):
    """
    A dedicated tab for analyzing hyperparameter optimization results.
    """

    def __init__(self, parent, db_manager, logger):
        """Initialize the Hyperopt Analysis tab."""
        super().__init__(parent, db_manager, logger)
        self.frame = ttk.Frame(self.parent)

        # Tab-specific variables
        self.session_var = tk.StringVar()
        self.strategy_var = tk.StringVar()
        self.timeframe_var = tk.StringVar()

        # Widgets
        self.session_combo = None
        self.strategy_combo = None
        self.timeframe_combo = None
        self.results_tree = None
        self.config_text = None
        self.hyperopt_text = None
        self.metrics_labels = {}

    def create_tab(self) -> ttk.Frame:
        """Create the hyperopt analysis tab interface."""
        # Main layout: Left for lists, Right for details
        left_panel = ttk.Frame(self.frame)
        left_panel.pack(side='left', fill='y', padx=(0, 10), pady=10)
        right_panel = ttk.Frame(self.frame)
        right_panel.pack(side='right', fill='both', expand=True, pady=10)

        # Build UI sections
        self._create_filters_section(left_panel)
        self._create_results_section(left_panel)
        self._create_details_section(right_panel)

        return self.frame

    def _create_filters_section(self, parent):
        """Create the filters for hyperopt results."""
        filters_frame = self.create_labeled_frame(parent, "Filters")
        filters_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(filters_frame, text="Session:").pack(anchor='w')
        self.session_combo = ttk.Combobox(filters_frame, textvariable=self.session_var, width=25, state="readonly")
        self.session_combo.pack(fill='x', pady=(0, 10))
        self.session_combo.bind('<<ComboboxSelected>>', lambda e: self.load_optimization_results())

        ttk.Label(filters_frame, text="Strategy:").pack(anchor='w')
        self.strategy_combo = ttk.Combobox(filters_frame, textvariable=self.strategy_var, width=25, state="readonly")
        self.strategy_combo.pack(fill='x', pady=(0, 10))
        self.strategy_combo.bind('<<ComboboxSelected>>', lambda e: self.load_optimization_results())

        ttk.Label(filters_frame, text="Timeframe:").pack(anchor='w')
        self.timeframe_combo = ttk.Combobox(filters_frame, textvariable=self.timeframe_var, width=25, state="readonly")
        self.timeframe_combo.pack(fill='x', pady=(0, 10))
        self.timeframe_combo.bind('<<ComboboxSelected>>', lambda e: self.load_optimization_results())

        ttk.Button(filters_frame, text="Refresh Data", command=self.refresh_data).pack(fill='x')

    def _create_results_section(self, parent):
        """Create the treeview list for hyperopt results."""
        results_frame = self.create_labeled_frame(parent, "Optimization Results")
        results_frame.pack(fill='both', expand=True)

        columns = ('ID', 'Strategy', 'Profit %', 'Trades', 'Win Rate', 'Date')
        self.results_tree = self.create_treeview(results_frame, columns)

        column_config = {
            'ID': {'text': 'ID', 'width': 40},
            'Strategy': {'text': 'Strategy', 'width': 130},
            'Profit %': {'text': 'Profit %', 'width': 70},
            'Trades': {'text': 'Trades', 'width': 60},
            'Win Rate': {'text': 'Win Rate', 'width': 70},
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
        details_frame = self.create_labeled_frame(parent, "Optimization Details")
        details_frame.pack(fill='both', expand=True)

        details_notebook = ttk.Notebook(details_frame)
        details_notebook.pack(fill='both', expand=True)

        metrics_frame = ttk.Frame(details_notebook)
        config_frame = ttk.Frame(details_notebook)
        hyperopt_frame = ttk.Frame(details_notebook)

        details_notebook.add(metrics_frame, text="Metrics")
        details_notebook.add(config_frame, text="Configuration")
        details_notebook.add(hyperopt_frame, text="Hyperopt Log")

        self.config_text = self.create_scrolled_text(config_frame, wrap=tk.WORD)
        self.config_text.pack(fill='both', expand=True)
        self.hyperopt_text = self.create_scrolled_text(hyperopt_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.hyperopt_text.pack(fill='both', expand=True)

        self._create_metrics_display(metrics_frame)

    def _create_metrics_display(self, parent):
        """Create the grid of performance metrics."""
        metrics_container = ttk.Frame(parent, padding=10)
        metrics_container.pack(fill='both', expand=True)

        metrics_info = [
            ('Total Profit %', 'total_profit_pct'), ('Sharpe Ratio', 'sharpe_ratio'),
            ('Total Profit Abs', 'total_profit_abs'), ('Sortino Ratio', 'sortino_ratio'),
            ('Total Trades', 'total_trades'), ('Calmar Ratio', 'calmar_ratio'),
            ('Win Rate %', 'win_rate'), ('Expectancy', 'expectancy'),
            ('Avg Profit %', 'avg_profit_pct'), ('Profit Factor', 'profit_factor'),
            ('Max Drawdown %', 'max_drawdown_pct'), ('Duration', 'optimization_duration_seconds')
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

    def load_sessions(self):
        """Load hyperopt sessions for the filter dropdown."""
        query = """
            SELECT DISTINCT json_extract(session_info, '$.session_name') as session_name,
            COUNT(*) as run_count, MIN(timestamp) as start_time
            FROM hyperopt_results WHERE session_info IS NOT NULL
            GROUP BY session_name ORDER BY start_time DESC
        """
        results = self.execute_database_query(query)
        session_options = ["All Sessions"]
        if results:
            session_options.extend([f"{row['session_name']} ({row['run_count']} runs)" for row in results])
        self.populate_combobox(self.session_combo, session_options, "All Sessions")

    def load_strategies_filter(self):
        """Load strategy names for the filter dropdown."""
        query = "SELECT DISTINCT strategy_name FROM hyperopt_results ORDER BY strategy_name"
        results = self.execute_database_query(query)
        options = ["All Strategies"] + [row['strategy_name'] for row in results] if results else []
        self.populate_combobox(self.strategy_combo, options, "All Strategies")

    def load_timeframes(self):
        """Load timeframes for the filter dropdown."""
        query = "SELECT DISTINCT timeframe FROM hyperopt_results WHERE timeframe IS NOT NULL ORDER BY timeframe"
        results = self.execute_database_query(query)
        options = ["All Timeframes"] + [row['timeframe'] for row in results] if results else []
        self.populate_combobox(self.timeframe_combo, options, "All Timeframes")

    def load_optimization_results(self):
        """Load and display hyperopt results based on current filters."""
        query = "SELECT id, strategy_name, total_profit_pct, total_trades, win_rate, timestamp FROM hyperopt_results WHERE status = 'completed'"
        params = []

        if self.strategy_var.get() != "All Strategies":
            query += " AND strategy_name = ?"
            params.append(self.strategy_var.get())
        if self.timeframe_var.get() != "All Timeframes":
            query += " AND timeframe = ?"
            params.append(self.timeframe_var.get())
        if self.session_var.get() != "All Sessions":
            session_name = self.session_var.get().split(' (')[0]
            query += " AND json_extract(session_info, '$.session_name') = ?"
            params.append(session_name)

        query += " ORDER BY total_profit_pct DESC LIMIT 100"
        results = self.execute_database_query(query, tuple(params))

        self.clear_treeview(self.results_tree)
        if results:
            for row in results:
                self.results_tree.insert('', 'end', values=(
                    row['id'], row['strategy_name'],
                    self.format_percentage(row['total_profit_pct']),
                    row['total_trades'] or "N/A",
                    self.format_percentage(row['win_rate']),
                    row['timestamp'][:10] if row['timestamp'] else "N/A"
                ))

    def load_result_details(self, optimization_id: int):
        """Load the details for a specific hyperopt result."""
        query = "SELECT * FROM hyperopt_results WHERE id = ?"
        results = self.execute_database_query(query, (optimization_id,))
        if not results: return
        result = results[0]

        # Update metrics
        for key, label in self.metrics_labels.items():
            value = result[key] if key in result.keys() else None
            if key.endswith('_pct'):
                formatted = self.format_percentage(value)
            elif key.endswith('_seconds'):
                formatted = f"{value // 60}m {value % 60}s" if value else "N/A"
            else:
                formatted = self.format_number(value) if isinstance(value, float) else (value or "N/A")
            label.config(text=str(formatted))

        # Load config file content
        self.config_text.delete(1.0, tk.END)
        config_path = result['config_file_path']
        if config_path and Path(config_path).exists():
            config_data = self.load_json_file(config_path)
            self.config_text.insert(1.0, json.dumps(config_data, indent=2) if config_data else "Failed to load config.")
        else:
            self.config_text.insert(1.0, "Configuration file not found.")

        # Load hyperopt log
        self.hyperopt_text.delete(1.0, tk.END)
        if result['hyperopt_json']:
            try:
                hyperopt_data = json.loads(result['hyperopt_json'])
                raw_output = hyperopt_data.get('raw_output', json.dumps(hyperopt_data, indent=2))
                self.hyperopt_text.insert(1.0, raw_output)
            except (json.JSONDecodeError, TypeError):
                self.hyperopt_text.insert(1.0, result['hyperopt_json'])  # Show raw text if not valid JSON
        else:
            self.hyperopt_text.insert(1.0, "Hyperopt log not found.")

    def refresh_data(self):
        """Refresh all data displays in this tab."""
        self.load_sessions()
        self.load_strategies_filter()
        self.load_timeframes()
        self.load_optimization_results()