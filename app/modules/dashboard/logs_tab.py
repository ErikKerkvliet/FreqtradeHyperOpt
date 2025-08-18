#!/usr/bin/env python3
"""
Logs Tab
Handles the logs viewing functionality of the dashboard.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime
import threading
import time

from .abstract_tab import AbstractTab


class LogsTab(AbstractTab):
    """
    Tab for viewing and managing application logs.
    """

    def __init__(self, parent, db_manager, logger):
        """Initialize the Logs tab."""
        super().__init__(parent, db_manager, logger)

        # Tab-specific variables
        self.logs_text = None
        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.refresh_interval_var = tk.StringVar(value="5")
        self.log_level_var = tk.StringVar(value="All")
        self.current_log_file = None
        self.auto_refresh_thread = None
        self.stop_auto_refresh = False

        # Available log files
        self.log_files = []

    def create_tab(self) -> ttk.Frame:
        """Create the logs tab."""
        self.frame = ttk.Frame(self.parent)

        self._create_toolbar()
        self._create_log_display()
        self._create_status_bar()

        return self.frame

    def _create_toolbar(self):
        """Create the toolbar for logs management."""
        toolbar_frame = ttk.Frame(self.frame)
        toolbar_frame.pack(fill='x', padx=10, pady=5)

        # Left side - File operations
        left_frame = ttk.Frame(toolbar_frame)
        left_frame.pack(side='left', fill='x', expand=True)

        ttk.Button(left_frame, text="Refresh Logs", command=self.refresh_data).pack(side='left', padx=(0, 5))
        ttk.Button(left_frame, text="Clear Display", command=self._clear_logs).pack(side='left', padx=(0, 5))
        ttk.Button(left_frame, text="Save Logs", command=self._save_logs).pack(side='left', padx=(0, 15))

        # Log file selection
        ttk.Label(left_frame, text="Log File:").pack(side='left', padx=(0, 5))
        self.log_file_combo = ttk.Combobox(left_frame, width=30, state="readonly")
        self.log_file_combo.pack(side='left', padx=(0, 15))
        self.log_file_combo.bind('<<ComboboxSelected>>', self._on_log_file_change)

        # Log level filter
        ttk.Label(left_frame, text="Level:").pack(side='left', padx=(0, 5))
        log_level_combo = ttk.Combobox(left_frame, textvariable=self.log_level_var, width=10, state="readonly")
        log_level_combo['values'] = ['All', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        log_level_combo.pack(side='left', padx=(0, 5))
        log_level_combo.bind('<<ComboboxSelected>>', self._apply_log_filter)

        # Right side - Auto-refresh controls
        right_frame = ttk.Frame(toolbar_frame)
        right_frame.pack(side='right')

        ttk.Checkbutton(right_frame, text="Auto-refresh", variable=self.auto_refresh_var,
                        command=self._toggle_auto_refresh).pack(side='left', padx=(0, 5))

        ttk.Label(right_frame, text="Interval (s):").pack(side='left', padx=(0, 5))
        interval_combo = ttk.Combobox(right_frame, textvariable=self.refresh_interval_var, width=5, state="readonly")
        interval_combo['values'] = ['1', '2', '5', '10', '30']
        interval_combo.pack(side='left')

    def _create_log_display(self):
        """Create the main log display area."""
        display_frame = ttk.Frame(self.frame)
        display_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Create scrolled text widget for logs
        self.logs_text = self.create_scrolled_text(display_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.logs_text.pack(fill='both', expand=True)

        # Configure text tags for different log levels
        self.logs_text.tag_config('DEBUG', foreground='gray')
        self.logs_text.tag_config('INFO', foreground='black')
        self.logs_text.tag_config('WARNING', foreground='orange')
        self.logs_text.tag_config('ERROR', foreground='red')
        self.logs_text.tag_config('CRITICAL', foreground='red', background='yellow')

        # Make text read-only
        self.logs_text.config(state='disabled')

    def _create_status_bar(self):
        """Create the status bar."""
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill='x', padx=10, pady=(0, 5))

        self.status_label = self.create_status_label(status_frame, "Ready")
        self.status_label.pack(side='left')

        # Lines count label
        self.lines_label = ttk.Label(status_frame, text="Lines: 0", foreground='gray')
        self.lines_label.pack(side='right')

    def refresh_data(self):
        """Refresh the logs display."""
        try:
            self._discover_log_files()
            self._load_current_log()
            self._update_status("Logs refreshed")
        except Exception as e:
            self.logger.error(f"Error refreshing logs: {e}")
            self._update_status("Error refreshing logs", "red")

    def _discover_log_files(self):
        """Discover available log files."""
        try:
            logs_dir = Path("logs")
            if not logs_dir.exists():
                self.log_files = []
                self.populate_combobox(self.log_file_combo, ["No log files found"])
                return

            # Find all log files
            log_files = []
            for pattern in ["*.log", "*.txt"]:
                log_files.extend(logs_dir.glob(pattern))

            # Sort by modification time (newest first)
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            self.log_files = log_files

            # Update combo box
            if log_files:
                file_names = [f.name for f in log_files]
                self.populate_combobox(self.log_file_combo, file_names)

                # Select the most recent file if none selected
                if not self.current_log_file and file_names:
                    self.log_file_combo.set(file_names[0])
                    self.current_log_file = log_files[0]
            else:
                self.populate_combobox(self.log_file_combo, ["No log files found"])
                self.current_log_file = None

        except Exception as e:
            self.logger.error(f"Error discovering log files: {e}")
            self.log_files = []

    def _on_log_file_change(self, event=None):
        """Handle log file selection change."""
        selected_name = self.log_file_combo.get()

        if selected_name == "No log files found":
            self.current_log_file = None
            return

        # Find the corresponding file
        for log_file in self.log_files:
            if log_file.name == selected_name:
                self.current_log_file = log_file
                break

        self._load_current_log()

    def _load_current_log(self):
        """Load the currently selected log file."""
        if not self.current_log_file or not self.current_log_file.exists():
            self._clear_logs()
            self._update_status("No log file selected")
            return

        try:
            self._update_status("Loading log file...")

            # Read the log file
            with open(self.current_log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Update display
            self._display_log_content(content)

            # Update status
            file_size = self.format_file_size(self.current_log_file.stat().st_size)
            modified_time = datetime.fromtimestamp(self.current_log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            self._update_status(f"Loaded: {self.current_log_file.name} ({file_size}) - Modified: {modified_time}")

        except Exception as e:
            self.logger.error(f"Error loading log file {self.current_log_file}: {e}")
            self._update_status(f"Error loading log file: {e}", "red")
            self.show_error("Error", f"Failed to load log file: {e}")

    def _display_log_content(self, content: str):
        """Display log content with syntax highlighting."""
        # Enable text widget for editing
        self.logs_text.config(state='normal')

        # Clear current content
        self.logs_text.delete(1.0, tk.END)

        # Split content into lines
        lines = content.split('\n')

        # Process each line and apply appropriate formatting
        for line in lines:
            if not line.strip():
                self.logs_text.insert(tk.END, '\n')
                continue

            # Determine log level
            log_level = self._detect_log_level(line)

            # Apply filter
            if self.log_level_var.get() != "All" and log_level != self.log_level_var.get():
                continue

            # Insert line with appropriate tag
            self.logs_text.insert(tk.END, line + '\n', log_level)

        # Disable text widget
        self.logs_text.config(state='disabled')

        # Scroll to bottom
        self.logs_text.see(tk.END)

        # Update line count
        line_count = len(self.logs_text.get(1.0, tk.END).split('\n')) - 1
        self.lines_label.config(text=f"Lines: {line_count}")

    def _detect_log_level(self, line: str) -> str:
        """Detect the log level of a line."""
        line_upper = line.upper()

        if 'CRITICAL' in line_upper:
            return 'CRITICAL'
        elif 'ERROR' in line_upper:
            return 'ERROR'
        elif 'WARNING' in line_upper or 'WARN' in line_upper:
            return 'WARNING'
        elif 'DEBUG' in line_upper:
            return 'DEBUG'
        elif 'INFO' in line_upper:
            return 'INFO'
        else:
            return 'INFO'  # Default to INFO

    def _apply_log_filter(self, event=None):
        """Apply log level filter to current display."""
        if self.current_log_file:
            self._load_current_log()

    def _clear_logs(self):
        """Clear the logs display."""
        self.logs_text.config(state='normal')
        self.logs_text.delete(1.0, tk.END)
        self.logs_text.config(state='disabled')
        self.lines_label.config(text="Lines: 0")

    def _save_logs(self):
        """Save current logs to a file."""
        content = self.logs_text.get(1.0, tk.END)
        if not content.strip():
            self.show_warning("Warning", "No logs to save!")
            return

        file_path = self.browse_save_file(
            title="Save Logs",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            defaultextension=".log"
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                self.show_info("Success", "Logs saved successfully!")
                self._update_status(f"Logs saved to: {Path(file_path).name}")
            except Exception as e:
                self.logger.error(f"Error saving logs: {e}")
                self.show_error("Error", f"Failed to save logs: {e}")

    def _toggle_auto_refresh(self):
        """Toggle auto-refresh functionality."""
        if self.auto_refresh_var.get():
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()
            # Update status here, in direct response to the user action
            self._update_status("Auto-refresh stopped")

    def _start_auto_refresh(self):
        """Start auto-refresh in a background thread."""
        if self.auto_refresh_thread and self.auto_refresh_thread.is_alive():
            return

        self.stop_auto_refresh = False
        self.auto_refresh_thread = threading.Thread(target=self._auto_refresh_worker, daemon=True)
        self.auto_refresh_thread.start()
        self._update_status("Auto-refresh started")

    def _stop_auto_refresh(self):
        """
        FIX: Safely stop the auto-refresh thread without updating the UI.
        The UI update is now handled in _toggle_auto_refresh.
        """
        self.stop_auto_refresh = True

    def _auto_refresh_worker(self):
        """Worker thread for auto-refresh."""
        while not self.stop_auto_refresh and self.auto_refresh_var.get():
            try:
                # Get refresh interval
                interval = int(self.refresh_interval_var.get())

                # Wait for the specified interval
                for _ in range(interval * 10):  # Check every 0.1 seconds
                    if self.stop_auto_refresh or not self.auto_refresh_var.get():
                        return
                    time.sleep(0.1)

                # Refresh logs in the main thread
                if not self.stop_auto_refresh and self.auto_refresh_var.get():
                    self.frame.after(0, self._load_current_log)

            except Exception as e:
                self.logger.error(f"Error in auto-refresh worker: {e}")
                break

    def _update_status(self, message: str, color: str = 'gray'):
        """Update the status label."""
        # Check if the label widget still exists before trying to configure it
        if self.status_label and self.status_label.winfo_exists():
            self.status_label.config(text=message, foreground=color)

    # FIX: Remove the unreliable __del__ method
    # def __del__(self):
    #     """Cleanup when tab is destroyed."""
    #     self._stop_auto_refresh()

    def cleanup(self):
        """
        FIX: Add a safe cleanup method to be called by the main application
        before the window is destroyed.
        """
        self._stop_auto_refresh()