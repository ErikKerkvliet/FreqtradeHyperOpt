#!/usr/bin/env python3
"""
Config Editor Tab
Handles the configuration editing functionality of the dashboard.
"""

import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path

from .abstract_tab import AbstractTab


class ConfigEditorTab(AbstractTab):
    """
    Tab for editing FreqTrade configuration files.
    """

    def __init__(self, parent, db_manager, logger):
        """Initialize the Config Editor tab."""
        super().__init__(parent, db_manager, logger)

        # Tab-specific variables
        self.current_config_file = None
        self.config_editor = None
        self.config_modified = False

        # Widgets
        self.current_file_label = None
        self.modified_label = None
        self.context_menu = None

    def create_tab(self) -> ttk.Frame:
        """Create the config editor tab."""
        self.frame = ttk.Frame(self.parent)

        self._create_toolbar()
        self._create_editor()

        return self.frame

    def _create_toolbar(self):
        """Create the toolbar for config editor."""
        toolbar_frame = ttk.Frame(self.frame)
        toolbar_frame.pack(fill='x', padx=10, pady=5)

        # File operations
        ttk.Button(toolbar_frame, text="Load Config", command=self._load_config_file).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_frame, text="Save Config", command=self._save_config_file).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_frame, text="Save As...", command=self._save_config_as).pack(side='left', padx=(0, 5))
        ttk.Button(toolbar_frame, text="New Config", command=self._new_config_file).pack(side='left', padx=(0, 5))

        # Separator
        ttk.Separator(toolbar_frame, orient='vertical').pack(side='left', fill='y', padx=(10, 10))

        # Validation and formatting
        ttk.Button(toolbar_frame, text="Validate JSON", command=self._validate_config_json).pack(side='left',
                                                                                                 padx=(0, 5))
        ttk.Button(toolbar_frame, text="Format JSON", command=self._format_json).pack(side='left', padx=(0, 5))

        # Separator
        ttk.Separator(toolbar_frame, orient='vertical').pack(side='left', fill='y', padx=(10, 10))

        # Template operations
        ttk.Button(toolbar_frame, text="Load Template", command=self._load_template).pack(side='left', padx=(0, 20))

        # Current file label
        self.current_file_label = ttk.Label(toolbar_frame, text="No file loaded", foreground='gray')
        self.current_file_label.pack(side='left')

        # Modified indicator
        self.modified_label = ttk.Label(toolbar_frame, text="", foreground='red')
        self.modified_label.pack(side='right')

    def _create_editor(self):
        """Create the text editor with context menu and keyboard shortcuts."""
        editor_frame = ttk.Frame(self.frame)
        editor_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # FIX: Enable the undo/redo stack on the text widget
        self.config_editor = self.create_scrolled_text(
            editor_frame,
            wrap=tk.NONE,
            font=('Consolas', 10)
        )
        self.config_editor.config(undo=True)
        self.config_editor.pack(fill='both', expand=True)

        # Create the right-click context menu
        self.context_menu = tk.Menu(self.config_editor, tearoff=0)
        # FIX: Add Undo and Redo to the context menu
        self.context_menu.add_command(label="Undo", accelerator="Ctrl+Z",
                                      command=lambda: self.config_editor.event_generate("<<Undo>>"))
        self.context_menu.add_command(label="Redo", accelerator="Ctrl+Shift+Z",
                                      command=lambda: self.config_editor.event_generate("<<Redo>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Cut", accelerator="Ctrl+X",
                                      command=lambda: self.config_editor.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="Copy", accelerator="Ctrl+C",
                                      command=lambda: self.config_editor.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Paste", accelerator="Ctrl+V",
                                      command=lambda: self.config_editor.event_generate("<<Paste>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self._select_all)

        # Bind modification events
        self.config_editor.bind('<KeyRelease>', self._on_text_modified)
        self.config_editor.bind('<Button-1>', self._on_text_modified)

        # Bind context menu and keyboard shortcuts
        self.config_editor.bind("<Button-3>", self._show_context_menu)
        self.config_editor.bind("<Control-a>", self._select_all)
        self.config_editor.bind("<Control-A>", self._select_all)

        # FIX: Bind Undo and Redo keyboard shortcuts
        self.config_editor.bind("<Control-z>", lambda e: self.config_editor.event_generate("<<Undo>>"))
        self.config_editor.bind("<Control-Z>", lambda e: self.config_editor.event_generate("<<Undo>>"))
        self.config_editor.bind("<Control-Shift-z>", lambda e: self.config_editor.event_generate("<<Redo>>"))
        self.config_editor.bind("<Control-Shift-Z>", lambda e: self.config_editor.event_generate("<<Redo>>"))

        # File operation shortcuts
        self.config_editor.bind('<Control-s>', lambda e: self._save_config_file())
        self.config_editor.bind('<Control-o>', lambda e: self._load_config_file())
        self.config_editor.bind('<Control-n>', lambda e: self._new_config_file())

    def _show_context_menu(self, event):
        """Display the context menu at the cursor's position."""
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _select_all(self, event=None):
        """Select all text in the editor."""
        self.config_editor.tag_add('sel', '1.0', 'end-1c')
        return "break"

    def _on_text_modified(self, event=None):
        """Handle text modification events."""
        # The undo/redo stack generates a modification event, so we ignore it
        # if the event type is a virtual event (like <<Undo>> or <<Redo>>)
        if event and event.type == tk.EventType.VirtualEvent:
            return

        if not self.config_modified:
            self.config_modified = True
            self._update_title()

    def _update_title(self):
        """Update the title to show modification status."""
        if self.current_config_file:
            filename = Path(self.current_config_file).name
            if self.config_modified:
                self.current_file_label.config(text=f"File: {filename} *")
                self.modified_label.config(text="(Modified)")
            else:
                self.current_file_label.config(text=f"File: {filename}")
                self.modified_label.config(text="")
        else:
            if self.config_modified:
                self.current_file_label.config(text="New file (unsaved) *")
                self.modified_label.config(text="(Modified)")
            else:
                self.current_file_label.config(text="New file (unsaved)")
                self.modified_label.config(text="")

    def _load_config_file(self):
        """Load a configuration file into the editor."""
        if self.config_modified:
            response = tk.messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them first?"
            )
            if response is True:
                if not self._save_config_file():
                    return
            elif response is None:
                return

        file_path = self.browse_file(
            title="Select Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir="configs"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                self.config_editor.delete(1.0, tk.END)
                self.config_editor.insert(1.0, content)
                self.current_config_file = file_path
                self.config_modified = False
                self._update_title()
                self.config_editor.edit_reset()  # Clear the undo stack
                self.logger.info(f"Loaded config file: {file_path}")

            except Exception as e:
                self.show_error("Error", f"Failed to load file: {e}")

    def _save_config_file(self) -> bool:
        """Save the current configuration."""
        if not self.current_config_file:
            return self._save_config_as()

        try:
            content = self.config_editor.get(1.0, tk.END)

            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                if not self.ask_yes_no("Invalid JSON", f"The JSON is invalid: {e}\n\nDo you want to save anyway?"):
                    return False

            with open(self.current_config_file, 'w') as f:
                f.write(content)

            self.config_modified = False
            self._update_title()
            self.show_info("Success", "Configuration saved successfully!")
            self.logger.info(f"Saved config file: {self.current_config_file}")
            return True

        except Exception as e:
            self.show_error("Error", f"Failed to save file: {e}")
            return False

    def _save_config_as(self) -> bool:
        """Save configuration as a new file."""
        file_path = self.browse_save_file(
            title="Save Configuration As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir="configs"
        )

        if file_path:
            try:
                content = self.config_editor.get(1.0, tk.END)

                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    if not self.ask_yes_no("Invalid JSON", f"The JSON is invalid: {e}\n\nDo you want to save anyway?"):
                        return False

                with open(file_path, 'w') as f:
                    f.write(content)

                self.current_config_file = file_path
                self.config_modified = False
                self._update_title()
                self.show_info("Success", "Configuration saved successfully!")
                self.logger.info(f"Saved config file as: {file_path}")
                return True

            except Exception as e:
                self.show_error("Error", f"Failed to save file: {e}")
                return False
        return False

    def _new_config_file(self):
        """Create a new configuration file."""
        if self.config_modified:
            response = tk.messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them first?"
            )
            if response is True:
                if not self._save_config_file():
                    return
            elif response is None:
                return

        template = {
            "max_open_trades": 3, "stake_currency": "USDT", "stake_amount": 100,
            "tradable_balance_ratio": 0.99, "fiat_display_currency": "USD",
            "timeframe": "5m", "dry_run": True, "dry_run_wallet": 1000,
            "cancel_open_orders_on_exit": False,
            "exchange": {"name": "binance", "pair_whitelist": ["BTC/USDT", "ETH/USDT"], "pair_blacklist": []},
            "pairlists": [{"method": "StaticPairList"}]
        }

        self.config_editor.delete(1.0, tk.END)
        self.config_editor.insert(1.0, json.dumps(template, indent=2))
        self.current_config_file = None
        self.config_modified = False
        self._update_title()
        self.config_editor.edit_reset()
        self.logger.info("Created new config file from template")

    def _validate_config_json(self):
        """Validate the JSON in the config editor."""
        try:
            content = self.config_editor.get(1.0, tk.END)
            is_valid, error_message = self.validate_json_text(content)
            if is_valid:
                self.show_info("Validation", "JSON is valid!")
            else:
                self.show_error("Validation Error", f"Invalid JSON: {error_message}")
        except Exception as e:
            self.show_error("Error", f"Validation failed: {e}")

    def _format_json(self):
        """Format the JSON in the editor."""
        try:
            content = self.config_editor.get(1.0, tk.END)
            is_valid, error_message = self.validate_json_text(content)
            if is_valid:
                parsed_json = json.loads(content)
                formatted_json = json.dumps(parsed_json, indent=2, sort_keys=False)
                cursor_pos = self.config_editor.index(tk.INSERT)
                self.config_editor.delete(1.0, tk.END)
                self.config_editor.insert(1.0, formatted_json)
                try:
                    self.config_editor.mark_set(tk.INSERT, cursor_pos)
                except tk.TclError:
                    pass
                self._on_text_modified()
                self.show_info("Success", "JSON formatted successfully!")
            else:
                self.show_error("Format Error", f"Cannot format invalid JSON: {error_message}")
        except Exception as e:
            self.show_error("Error", f"Formatting failed: {e}")

    def _load_template(self):
        """Load a configuration template."""
        if self.config_modified:
            response = tk.messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them first?"
            )
            if response is True:
                if not self._save_config_file():
                    return
            elif response is None:
                return

        template_path = self.browse_file(
            title="Select Template File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir="resources"
        )
        if template_path:
            try:
                template_data = self.load_json_file(template_path)
                if template_data:
                    self.config_editor.delete(1.0, tk.END)
                    self.config_editor.insert(1.0, json.dumps(template_data, indent=2))
                    self.current_config_file = None
                    self.config_modified = False
                    self._update_title()
                    self.config_editor.edit_reset()
                    self.logger.info(f"Loaded template: {template_path}")
            except Exception as e:
                self.show_error("Error", f"Failed to load template: {e}")

    def get_current_config_text(self) -> str:
        """Get the current configuration text."""
        return self.config_editor.get(1.0, tk.END)

    def set_config_text(self, content: str):
        """Set the configuration text."""
        self.config_editor.delete(1.0, tk.END)
        self.config_editor.insert(1.0, content)
        self.config_modified = False
        self._update_title()
        self.config_editor.edit_reset()

    def is_modified(self) -> bool:
        """Check if the configuration has been modified."""
        return self.config_modified

    def get_current_file_path(self) -> str:
        """Get the current file path."""
        return self.current_config_file

    def refresh_data(self):
        """Refresh data (not applicable for config editor)."""
        pass

    def insert_config_snippet(self, snippet: dict, description: str = ""):
        """Insert a configuration snippet at the cursor position."""
        try:
            snippet_text = json.dumps(snippet, indent=2)
            cursor_pos = self.config_editor.index(tk.INSERT)
            self.config_editor.insert(cursor_pos, snippet_text)
            self._on_text_modified()
            if description:
                self.show_info("Snippet Inserted", f"Inserted {description}")
        except Exception as e:
            self.show_error("Error", f"Failed to insert snippet: {e}")

    def find_text(self, search_text: str, case_sensitive: bool = False):
        """Find text in the editor."""
        try:
            start_pos = self.config_editor.index(tk.INSERT)
            pos = self.config_editor.search(search_text, start_pos, tk.END, nocase=not case_sensitive)
            if pos:
                end_pos = f"{pos}+{len(search_text)}c"
                self.config_editor.mark_set(tk.INSERT, pos)
                self.config_editor.selection_clear()
                self.config_editor.selection_set(pos, end_pos)
                self.config_editor.see(pos)
                return True
            else:
                self.show_info("Search", f"Text '{search_text}' not found")
                return False
        except Exception as e:
            self.show_error("Error", f"Search failed: {e}")
            return False

    def replace_text(self, search_text: str, replace_text: str, replace_all: bool = False):
        """Replace text in the editor."""
        try:
            if replace_all:
                content = self.config_editor.get(1.0, tk.END)
                new_content, count = content.replace(search_text, replace_text), content.count(search_text)
                if count > 0:
                    self.config_editor.delete(1.0, tk.END)
                    self.config_editor.insert(1.0, new_content)
                    self._on_text_modified()
                    self.show_info("Replace", f"Replaced {count} occurrence(s)")
                else:
                    self.show_info("Replace", "No occurrences found")
                return count
            else:
                try:
                    if self.config_editor.get(tk.SEL_FIRST, tk.SEL_LAST) == search_text:
                        self.config_editor.delete(tk.SEL_FIRST, tk.SEL_LAST)
                        self.config_editor.insert(tk.INSERT, replace_text)
                        self._on_text_modified()
                        return 1
                except tk.TclError:
                    pass
                return 1 if self.find_text(search_text) else 0
        except Exception as e:
            self.show_error("Error", f"Replace failed: {e}")
            return 0