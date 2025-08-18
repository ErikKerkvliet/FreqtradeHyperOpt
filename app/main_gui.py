#!/usr/bin/env python3
"""
FreqTrade Dashboard GUI - Graphical User Interface
Main entry point for the tkinter-based dashboard.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the main dashboard class from the new structure
from modules.dashboard import FreqTradeDashboard


def main():
    """Main function to run the dashboard GUI."""
    try:
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
            if hasattr(app, 'current_process') and app.current_process:
                if messagebox.askokcancel("Quit", "A process is running. Do you want to stop it and quit?"):
                    try:
                        app.current_process.terminate()
                    except:
                        pass
                    root.destroy()
            else:
                root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # Start the GUI
        root.mainloop()

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all required modules are available in the modules/ directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting GUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()