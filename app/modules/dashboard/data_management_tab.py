#!/usr/bin/env python3
"""
Data Management Tab
Handles the data management functionality of the dashboard.
"""

import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from .abstract_tab import AbstractTab


class DataManagementTab(AbstractTab):
    """
    Tab for managing FreqTrade data files.
    """

    def __init__(self, parent, db_manager, logger):
        """Initialize the Data Management tab."""
        super().__init__(parent, db_manager, logger)

        # Tab-specific variables
        self.data_status_var = tk.StringVar(value="Ready")

        # Widgets that will be created
        self.data_notebook = None
        self.exchange_frames = {}
        self.exchange_trees = {}

    def create_tab(self) -> ttk.Frame:
        """Create the data management tab."""
        self.frame = ttk.Frame(self.parent)

        # FIX: Remove this line. The callback is not available yet, and the path is
        # only needed when refresh_data() is called anyway.
        # self.freqtrade_path = self.call_callback('get_freqtrade_path')

        self._create_toolbar()
        self._create_data_notebook()

        return self.frame

    def _create_toolbar(self):
        """Create the toolbar for data management."""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill='x', padx=10, pady=5)

        ttk.Button(toolbar, text="Refresh Data", command=self.refresh_data).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar, text="Download Data", command=self._download_new_data).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar, text="Delete Selected", command=self._delete_selected_data).pack(side='left', padx=(0, 20))

        # Status label
        status_label = self.create_status_label(toolbar, "Ready")
        status_label.pack(side='left')
        status_label.config(textvariable=self.data_status_var)

    def _create_data_notebook(self):
        """Create the notebook for exchange data tabs."""
        self.data_notebook = ttk.Notebook(self.frame)
        self.data_notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Initialize with common exchanges
        exchanges = ["binance", "kraken", "coinbase", "other"]
        for exchange in exchanges:
            self._create_exchange_tab(exchange)

    def _create_exchange_tab(self, exchange_name: str):
        """Create a tab for a specific exchange."""
        # Create frame for exchange
        exchange_frame = ttk.Frame(self.data_notebook)
        self.data_notebook.add(exchange_frame, text=exchange_name.capitalize())
        self.exchange_frames[exchange_name] = exchange_frame

        # Create filter frame
        filter_frame = self._create_filter_section(exchange_frame, exchange_name)
        filter_frame.pack(fill='x', padx=10, pady=5)

        # Create data table
        table_frame = self._create_data_table(exchange_frame, exchange_name)
        table_frame.pack(fill='both', expand=True, padx=10, pady=(5, 10))

        # Add summary label
        summary_frame = ttk.Frame(exchange_frame)
        summary_frame.pack(fill='x', padx=10, pady=(0, 5))

        summary_var = tk.StringVar(value="Ready")
        summary_label = ttk.Label(summary_frame, textvariable=summary_var, foreground='gray')
        summary_label.pack(side='left')

        # Store reference to summary var in the tree
        tree = self.exchange_trees[exchange_name]
        tree.summary_var = summary_var

    def _create_filter_section(self, parent, exchange_name: str) -> ttk.Frame:
        """Create the filter section for an exchange."""
        filter_frame = self.create_labeled_frame(parent, "Filters", padding=5)

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
        ttk.Button(filter_row1, text="Clear All",
                   command=lambda: self._clear_filters(exchange_name)).pack(side='right', padx=(10, 0))

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
                   command=lambda: self._apply_quick_filter(exchange_name, 'hourly')).pack(side='left', padx=(0, 2))
        ttk.Button(quick_filter_frame, text="BTC Pairs", width=8,
                   command=lambda: self._apply_quick_filter(exchange_name, 'btc_pairs')).pack(side='left', padx=(0, 2))
        ttk.Button(quick_filter_frame, text="USDT Pairs", width=9,
                   command=lambda: self._apply_quick_filter(exchange_name, 'usdt_pairs')).pack(side='left', padx=(0, 2))

        # Store filter variables in the tree (will be created next)
        filter_vars = {
            'search_var': search_var,
            'timeframe_var': timeframe_var,
            'base_currency_var': base_currency_var,
            'quote_currency_var': quote_currency_var
        }

        # Bind filter events (will be bound after tree creation)
        self._pending_filter_bindings = {
            exchange_name: {
                'search_entry': search_entry,
                'timeframe_combo': timeframe_combo,
                'base_currency_combo': base_currency_combo,
                'quote_currency_combo': quote_currency_combo,
                'filter_vars': filter_vars
            }
        }

        return filter_frame

    def _create_data_table(self, parent, exchange_name: str) -> ttk.Frame:
        """Create the data table for an exchange."""
        table_frame = ttk.Frame(parent)

        # Define columns
        columns = (
        'Pair', 'Base', 'Quote', 'Timeframe', 'Start Date', 'End Date', 'Records', 'File Size', 'Last Modified')
        tree = self.create_treeview(table_frame, columns, selectmode='extended')

        # Configure columns
        column_config = {
            'Pair': {'text': 'Trading Pair', 'width': 100},
            'Base': {'text': 'Base', 'width': 50},
            'Quote': {'text': 'Quote', 'width': 50},
            'Timeframe': {'text': 'Timeframe', 'width': 70},
            'Start Date': {'text': 'Start Date', 'width': 90},
            'End Date': {'text': 'End Date', 'width': 90},
            'Records': {'text': 'Records', 'width': 70},
            'File Size': {'text': 'File Size', 'width': 70},
            'Last Modified': {'text': 'Last Modified', 'width': 110}
        }
        self.setup_treeview_columns(tree, column_config)

        # Add scrollbars
        scrollbars = self.add_scrollbars_to_widget(table_frame, tree)

        # Configure grid layout
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        tree.grid(row=0, column=0, sticky='nsew')
        if 'vertical' in scrollbars:
            scrollbars['vertical'].grid(row=0, column=1, sticky='ns')
        if 'horizontal' in scrollbars:
            scrollbars['horizontal'].grid(row=1, column=0, sticky='ew')

        # Store tree reference and initialize data storage
        self.exchange_trees[exchange_name] = tree
        tree._all_data = []  # Store all data for filtering

        # Bind filter events now that tree is created
        if hasattr(self, '_pending_filter_bindings') and exchange_name in self._pending_filter_bindings:
            bindings = self._pending_filter_bindings[exchange_name]
            filter_vars = bindings['filter_vars']

            # Store filter variables in tree
            for var_name, var in filter_vars.items():
                setattr(tree, var_name, var)

            # Bind events
            bindings['search_entry'].bind('<KeyRelease>', lambda e: self._apply_filters(exchange_name))
            bindings['timeframe_combo'].bind('<<ComboboxSelected>>', lambda e: self._apply_filters(exchange_name))
            bindings['base_currency_combo'].bind('<<ComboboxSelected>>', lambda e: self._apply_filters(exchange_name))
            bindings['quote_currency_combo'].bind('<<ComboboxSelected>>', lambda e: self._apply_filters(exchange_name))

        return table_frame

    def refresh_data(self):
        """Refresh the data information for all exchanges."""
        # FIX: Get the freqtrade_path from the callback every time.
        freqtrade_path = self.call_callback('get_freqtrade_path')
        if not freqtrade_path:
            self.data_status_var.set("FreqTrade path not configured")
            return

        try:
            self.data_status_var.set("Scanning data files...")

            # Get data directory
            data_base_dir = Path(freqtrade_path) / "user_data" / "data"

            if not data_base_dir.exists():
                self.data_status_var.set("Data directory not found")
                return

            # Scan each exchange directory
            for exchange_name, tree in self.exchange_trees.items():
                self._load_exchange_data(exchange_name, tree, data_base_dir)

            self.data_status_var.set("Data scan completed")

        except Exception as e:
            self.logger.error(f"Error refreshing data info: {e}")
            self.data_status_var.set("Error scanning data")
            self.show_error("Error", f"Failed to refresh data: {e}")

    def _load_exchange_data(self, exchange_name: str, tree, data_base_dir: Path):
        """Load data files for a specific exchange."""
        # Clear existing items and stored data
        self.clear_treeview(tree)
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
                        base_currency, quote_currency = self._parse_pair(pair)
                        if '/' not in pair and base_currency != "Unknown":
                            pair = f"{base_currency}/{quote_currency}"

                        # Get file info
                        file_stat = json_file.stat()
                        file_size = self.format_file_size(file_stat.st_size)
                        last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M')

                        # Try to get data range and record count
                        start_date, end_date, record_count = self._analyze_data_file(json_file)

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

    def _parse_pair(self, pair: str) -> tuple[str, str]:
        """Parse a trading pair to extract base and quote currencies."""
        if '/' in pair:
            return pair.split('/', 1)

        # Handle pairs without separator
        base_currency = "Unknown"
        quote_currency = "Unknown"

        # Try to guess common separations
        for quote in ['USDT', 'BTC', 'ETH', 'BNB', 'USD', 'EUR', 'BUSD']:
            if pair.endswith(quote):
                base_currency = pair[:-len(quote)]
                quote_currency = quote
                break

        return base_currency, quote_currency

    def _analyze_data_file(self, file_path: Path) -> tuple[str, str, str]:
        """Analyze a data file to get date range and record count."""
        try:
            data = self.load_json_file(str(file_path))

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

    def _display_filtered_data(self, tree):
        """Display filtered data in the treeview."""
        # Clear current display
        self.clear_treeview(tree)

        # Add visible items
        for data_item in tree._all_data:
            if data_item['visible']:
                tree.insert('', 'end', values=data_item['values'], tags=(data_item['file_path'],))

    def _apply_filters(self, exchange_name: str):
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

    def _apply_quick_filter(self, exchange_name: str, filter_type: str):
        """Apply predefined quick filters."""
        tree = self.exchange_trees[exchange_name]

        if filter_type == 'hourly':
            # Show only hourly and higher timeframes
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
            self._apply_filters(exchange_name)

        elif filter_type == 'usdt_pairs':
            # Show only USDT quote pairs
            tree.timeframe_var.set('All')
            tree.base_currency_var.set('All')
            tree.quote_currency_var.set('USDT')
            tree.search_var.set('')
            self._apply_filters(exchange_name)

    def _clear_filters(self, exchange_name: str):
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

    def _download_new_data(self):
        """Open dialog to download new data."""
        self.call_callback('show_download_dialog')

    def _delete_selected_data(self):
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
            self.show_warning("Warning", "Please select data files to delete!")
            return

        # Confirm deletion
        if not self.ask_yes_no("Confirm Deletion",
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
            self.show_info("Success", f"Deleted {deleted_count} file(s) successfully!")
            self.data_status_var.set(f"Deleted {deleted_count} files")
            # Update summary after deletion
            if hasattr(tree, 'summary_var'):
                remaining_count = len(tree.get_children())
                tree.summary_var.set(f"Showing {remaining_count} data files")
        else:
            self.show_error("Error", "No files were deleted!")