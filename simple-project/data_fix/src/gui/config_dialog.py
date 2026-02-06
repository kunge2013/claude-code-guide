"""
Configuration dialog for database settings.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional


class ConfigDialog:
    """Dialog for configuring database connection settings."""

    def __init__(self, parent, config: dict, on_save: Callable[[dict], None]):
        """
        Initialize the configuration dialog.

        Args:
            parent: Parent window
            config: Current configuration dictionary
            on_save: Callback function when configuration is saved
        """
        self.config = config.copy()
        self.on_save = on_save
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Database Configuration")
        self.dialog.geometry("450x350")
        self.dialog.resizable(False, False)

        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self._load_current_config()

        # Center dialog on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Database Connection Settings",
            font=('', 12, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Form fields
        self.fields = {}
        labels = [
            ('host', 'Host:'),
            ('port', 'Port:'),
            ('user', 'User:'),
            ('password', 'Password:'),
            ('database', 'Database:')
        ]

        for i, (key, label) in enumerate(labels):
            ttk.Label(main_frame, text=label).grid(
                row=i + 1, column=0, sticky=tk.W, pady=5
            )
            entry = ttk.Entry(main_frame, width=30)
            if key == 'password':
                entry.config(show='*')
            entry.grid(row=i + 1, column=1, columnspan=2, sticky=tk.EW, pady=5)
            self.fields[key] = entry

        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=len(labels) + 1, column=0, columnspan=3, pady=(20, 0))

        # Test Connection button
        self.test_btn = ttk.Button(
            button_frame,
            text="Test Connection",
            command=self._test_connection
        )
        self.test_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="Save",
            command=self._save
        )
        save_btn.pack(side=tk.LEFT, padx=5)

        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="",
            foreground='green'
        )
        self.status_label.grid(row=len(labels) + 2, column=0, columnspan=3, pady=(10, 0))

    def _load_current_config(self) -> None:
        """Load current configuration into form fields."""
        for key, entry in self.fields.items():
            value = self.config.get(key, '')
            entry.delete(0, tk.END)
            entry.insert(0, str(value))

    def _test_connection(self) -> None:
        """Test the database connection with current settings."""
        from ..database.connection import ConnectionManager

        # Get current form values
        test_config = {
            key: entry.get()
            for key, entry in self.fields.items()
        }

        # Convert port to integer
        try:
            test_config['port'] = int(test_config['port'])
        except ValueError:
            self._show_status("Port must be a number", 'red')
            return

        self._show_status("Testing connection...", 'blue')
        self.test_btn.config(state=tk.DISABLED)
        self.dialog.update()

        try:
            conn_mgr = ConnectionManager()
            conn_mgr.config = {
                **conn_mgr.config,
                **test_config,
                'charset': 'utf8mb4'
            }
            if conn_mgr.test_connection():
                self._show_status("Connection successful!", 'green')
            else:
                self._show_status("Connection failed. Check your settings.", 'red')
        except Exception as e:
            self._show_status(f"Connection failed: {str(e)}", 'red')
        finally:
            self.test_btn.config(state=tk.NORMAL)

    def _show_status(self, message: str, color: str) -> None:
        """Show status message."""
        self.status_label.config(text=message, foreground=color)

    def _save(self) -> None:
        """Save the configuration."""
        # Get form values
        config = {
            key: entry.get()
            for key, entry in self.fields.items()
        }

        # Convert port to integer
        try:
            config['port'] = int(config['port'])
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        # Validate required fields
        if not all([config['host'], config['user'], config['database']]):
            messagebox.showerror("Error", "Host, User, and Database are required")
            return

        self.result = config
        self.on_save(config)
        self.dialog.destroy()

    def _cancel(self) -> None:
        """Cancel the dialog."""
        self.dialog.destroy()
