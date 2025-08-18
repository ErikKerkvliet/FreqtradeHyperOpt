#!/usr/bin/env python3
"""
Abstract Tab Base Class
Contains shared functionality for all dashboard tabs.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any
from pathlib import Path

from ..results_database_manager import DatabaseManager


class AbstractTab(ABC):
    """
    Abstract base class for all dashboard tabs.
    Contains shared functionality and defines the interface that all tabs must implement.
    """

    def __init__(self, parent, db_manager: DatabaseManager, logger: logging.Logger):
        """
        Initialize the abstract tab.

        Args:
            parent: Parent tkinter widget
            db_manager: Database manager instance
            logger: Logger instance
        """
        self.parent = parent
        self.db_manager = db_manager
        self.logger = logger
        self.frame = None

        # Shared callbacks that can be set by the main dashboard
        self.callbacks: Dict[str, Callable] = {}

    @abstractmethod
    def create_tab(self) -> ttk.Frame:
        """
        Create and return the tab's main frame with all widgets.
        Must be implemented by each concrete tab class.

        Returns:
            ttk.Frame: The main frame for this tab
        """
        pass

    @abstractmethod
    def refresh_data(self):
        """
        Refresh the data displayed in this tab.
        Must be implemented by each concrete tab class.
        """
        pass

    def set_callback(self, name: str, callback: Callable):
        """
        Set a callback function that can be called by this tab.

        Args:
            name: Name of the callback
            callback: The callback function
        """
        self.callbacks[name] = callback

    def call_callback(self, name: str, *args, **kwargs):
        """
        Call a registered callback function.

        Args:
            name: Name of the callback to call
            *args: Positional arguments to pass to the callback
            **kwargs: Keyword arguments to pass to the callback
        """
        if name in self.callbacks:
            try:
                return self.callbacks[name](*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error calling callback '{name}': {e}")
        else:
            self.logger.warning(f"Callback '{name}' not found")

    def show_error(self, title: str, message: str):
        """
        Show an error message dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        messagebox.showerror(title, message)

    def show_info(self, title: str, message: str):
        """
        Show an information message dialog.

        Args:
            title: Dialog title
            message: Information message
        """
        messagebox.showinfo(title, message)

    def show_warning(self, title: str, message: str):
        """
        Show a warning message dialog.

        Args:
            title: Dialog title
            message: Warning message
        """
        messagebox.showwarning(title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """
        Show a yes/no confirmation dialog.

        Args:
            title: Dialog title
            message: Question message

        Returns:
            bool: True if user clicked Yes, False otherwise
        """
        return messagebox.askyesno(title, message)

    def browse_file(self, title: str = "Select File", filetypes: list = None, initialdir: str = None) -> Optional[str]:
        """
        Open a file browser dialog.

        Args:
            title: Dialog title
            filetypes: List of file type tuples, e.g., [("JSON files", "*.json")]
            initialdir: Initial directory to open

        Returns:
            Optional[str]: Selected file path or None if cancelled
        """
        if filetypes is None:
            filetypes = [("All files", "*.*")]

        return filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=initialdir
        )

    def browse_save_file(self, title: str = "Save File", filetypes: list = None,
                         initialdir: str = None, defaultextension: str = None) -> Optional[str]:
        """
        Open a save file dialog.

        Args:
            title: Dialog title
            filetypes: List of file type tuples
            initialdir: Initial directory to open
            defaultextension: Default file extension

        Returns:
            Optional[str]: Selected file path or None if cancelled
        """
        if filetypes is None:
            filetypes = [("All files", "*.*")]

        return filedialog.asksaveasfilename(
            title=title,
            filetypes=filetypes,
            initialdir=initialdir,
            defaultextension=defaultextension
        )

    def create_labeled_frame(self, parent, text: str, padding: int = 10) -> ttk.LabelFrame:
        """
        Create a labeled frame with padding.

        Args:
            parent: Parent widget
            text: Label text
            padding: Padding amount

        Returns:
            ttk.LabelFrame: The created labeled frame
        """
        return ttk.LabelFrame(parent, text=text, padding=padding)

    def create_button_frame(self, parent) -> ttk.Frame:
        """
        Create a frame for holding buttons.

        Args:
            parent: Parent widget

        Returns:
            ttk.Frame: The button frame
        """
        return ttk.Frame(parent)

    def create_scrolled_text(self, parent, wrap=tk.WORD, font=None) -> tk.Text:
        """
        Create a scrolled text widget.

        Args:
            parent: Parent widget
            wrap: Text wrapping mode
            font: Font tuple

        Returns:
            tk.Text: The scrolled text widget
        """
        import tkinter.scrolledtext as scrolledtext
        return scrolledtext.ScrolledText(parent, wrap=wrap, font=font)

    def create_treeview(self, parent, columns: tuple, show: str = 'headings',
                        selectmode: str = 'browse') -> ttk.Treeview:
        """
        Create a treeview widget.

        Args:
            parent: Parent widget
            columns: Column names tuple
            show: What to show ('tree', 'headings', or 'tree headings')
            selectmode: Selection mode

        Returns:
            ttk.Treeview: The created treeview
        """
        return ttk.Treeview(parent, columns=columns, show=show, selectmode=selectmode)

    def setup_treeview_columns(self, tree: ttk.Treeview, column_config: Dict[str, Dict[str, Any]]):
        """
        Setup treeview columns with headings and widths.

        Args:
            tree: Treeview widget
            column_config: Dict with column name as key and config dict as value
                          Example: {'Name': {'text': 'Name', 'width': 100}}
        """
        for col_name, config in column_config.items():
            tree.heading(col_name, text=config.get('text', col_name))
            tree.column(col_name, width=config.get('width', 100))

    def add_scrollbars_to_widget(self, parent, widget, orient: str = 'both') -> Dict[str, ttk.Scrollbar]:
        """
        Add scrollbars to a widget.

        Args:
            parent: Parent frame
            widget: Widget to add scrollbars to
            orient: Scrollbar orientation ('vertical', 'horizontal', or 'both')

        Returns:
            Dict[str, ttk.Scrollbar]: Dictionary of created scrollbars
        """
        scrollbars = {}

        if orient in ['vertical', 'both']:
            v_scrollbar = ttk.Scrollbar(parent, orient='vertical', command=widget.yview)
            widget.configure(yscrollcommand=v_scrollbar.set)
            scrollbars['vertical'] = v_scrollbar

        if orient in ['horizontal', 'both']:
            h_scrollbar = ttk.Scrollbar(parent, orient='horizontal', command=widget.xview)
            widget.configure(xscrollcommand=h_scrollbar.set)
            scrollbars['horizontal'] = h_scrollbar

        return scrollbars

    def pack_with_scrollbars(self, widget, scrollbars: Dict[str, ttk.Scrollbar],
                             fill: str = 'both', expand: bool = True):
        """
        Pack a widget with its scrollbars using grid layout.

        Args:
            widget: The main widget
            scrollbars: Dictionary of scrollbars
            fill: Fill mode for the widget
            expand: Whether widget should expand
        """
        # Create a frame to hold widget and scrollbars
        container = ttk.Frame(widget.master)
        container.pack(fill=fill, expand=expand)

        # Configure grid weights
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Place the main widget
        widget.grid(row=0, column=0, sticky='nsew')

        # Place scrollbars
        if 'vertical' in scrollbars:
            scrollbars['vertical'].grid(row=0, column=1, sticky='ns')

        if 'horizontal' in scrollbars:
            scrollbars['horizontal'].grid(row=1, column=0, sticky='ew')

    def load_json_file(self, file_path: str) -> Optional[Dict]:
        """
        Load and parse a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Optional[Dict]: Parsed JSON data or None if failed
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load JSON file {file_path}: {e}")
            self.show_error("Error", f"Failed to load file: {e}")
            return None

    def save_json_file(self, file_path: str, data: Dict) -> bool:
        """
        Save data to a JSON file.

        Args:
            file_path: Path to save the file
            data: Data to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save JSON file {file_path}: {e}")
            self.show_error("Error", f"Failed to save file: {e}")
            return False

    def execute_database_query(self, query: str, params: tuple = None) -> Optional[list]:
        """
        Execute a database query and return results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Optional[list]: Query results or None if failed
        """
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params or ())
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            self.show_error("Database Error", f"Query failed: {e}")
            return None

    def format_percentage(self, value: float, decimals: int = 2) -> str:
        """
        Format a number as a percentage.

        Args:
            value: The value to format
            decimals: Number of decimal places

        Returns:
            str: Formatted percentage string
        """
        if value is None:
            return "N/A"
        return f"{value:+.{decimals}f}%"

    def format_number(self, value: float, decimals: int = 2) -> str:
        """
        Format a number with specified decimal places.

        Args:
            value: The value to format
            decimals: Number of decimal places

        Returns:
            str: Formatted number string
        """
        if value is None:
            return "N/A"
        return f"{value:.{decimals}f}"

    def format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            str: Formatted file size
        """
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def truncate_text(self, text: str, max_length: int = 50) -> str:
        """
        Truncate text to a maximum length with ellipsis.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            str: Truncated text
        """
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def validate_json_text(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Validate JSON text.

        Args:
            text: JSON text to validate

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            json.loads(text)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)

    def bind_treeview_selection(self, tree: ttk.Treeview, callback: Callable):
        """
        Bind a selection event to a treeview.

        Args:
            tree: Treeview widget
            callback: Callback function to call on selection
        """
        tree.bind('<<TreeviewSelect>>', callback)

    def get_selected_treeview_item(self, tree: ttk.Treeview) -> Optional[Dict]:
        """
        Get the selected item from a treeview.

        Args:
            tree: Treeview widget

        Returns:
            Optional[Dict]: Selected item data or None
        """
        selection = tree.selection()
        if not selection:
            return None

        item = tree.item(selection[0])
        return {
            'id': selection[0],
            'values': item['values'],
            'tags': item['tags']
        }

    def clear_treeview(self, tree: ttk.Treeview):
        """
        Clear all items from a treeview.

        Args:
            tree: Treeview widget to clear
        """
        for item in tree.get_children():
            tree.delete(item)

    def populate_combobox(self, combobox: ttk.Combobox, values: list, default_value: str = None):
        """
        Populate a combobox with values.

        Args:
            combobox: Combobox widget
            values: List of values
            default_value: Default value to set
        """
        combobox['values'] = values
        if default_value and default_value in values:
            combobox.set(default_value)
        elif values:
            combobox.set(values[0])

    def create_status_label(self, parent, initial_text: str = "Ready") -> ttk.Label:
        """
        Create a status label.

        Args:
            parent: Parent widget
            initial_text: Initial status text

        Returns:
            ttk.Label: The status label
        """
        return ttk.Label(parent, text=initial_text, foreground='gray')

    def update_status(self, status_label: ttk.Label, text: str, color: str = 'gray'):
        """
        Update a status label.

        Args:
            status_label: Status label widget
            text: New status text
            color: Text color
        """
        status_label.config(text=text, foreground=color)

    def disable_widget(self, widget):
        """
        Disable a widget.

        Args:
            widget: Widget to disable
        """
        try:
            widget.config(state='disabled')
        except tk.TclError:
            pass  # Some widgets don't support state

    def enable_widget(self, widget):
        """
        Enable a widget.

        Args:
            widget: Widget to enable
        """
        try:
            widget.config(state='normal')
        except tk.TclError:
            pass  # Some widgets don't support state