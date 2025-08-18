#!/usr/bin/env python3
"""
Results Analysis Tab Container
This tab holds sub-tabs for Hyperopt and Backtest result analysis.
"""

import tkinter as tk
from tkinter import ttk

from .abstract_tab import AbstractTab
from .hyperopt_analysis_tab import HyperoptAnalysisTab
from .backtest_analysis_tab import BacktestAnalysisTab


class ResultsAnalysisTab(AbstractTab):
    """
    A container tab that organizes results analysis into sub-tabs.
    """

    def __init__(self, parent, db_manager, logger):
        """Initialize the container tab."""
        super().__init__(parent, db_manager, logger)
        self.hyperopt_tab: HyperoptAnalysisTab = None
        self.backtest_tab: BacktestAnalysisTab = None

    def create_tab(self) -> ttk.Frame:
        """Create the main frame and the sub-notebook for analysis tabs."""
        self.frame = ttk.Frame(self.parent)

        # Create a notebook to hold the sub-tabs
        notebook = ttk.Notebook(self.frame)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Create instances of the specialized tabs
        self.hyperopt_tab = HyperoptAnalysisTab(notebook, self.db_manager, self.logger)
        self.backtest_tab = BacktestAnalysisTab(notebook, self.db_manager, self.logger)

        # Add the specialized tabs to the notebook
        notebook.add(self.hyperopt_tab.create_tab(), text="Hyperopt Analysis")
        notebook.add(self.backtest_tab.create_tab(), text="Backtest Analysis")

        return self.frame

    def refresh_data(self):
        """Refresh the data in both the hyperopt and backtest sub-tabs."""
        if self.hyperopt_tab:
            self.hyperopt_tab.refresh_data()
        if self.backtest_tab:
            self.backtest_tab.refresh_data()