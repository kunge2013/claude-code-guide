"""
Main GUI window for the SQL Query Tool.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Optional, List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.connection import ConnectionManager
from src.database.queries import QueryManager
from src.gui.config_dialog import ConfigDialog


class ResultsTable(ttk.Frame):
    """A frame displaying query results in a table format."""

    def __init__(self, parent):
        super().__init__(parent)
        self.tree = None
        self.scrollbar_v = None
        self.scrollbar_h = None
        self._create_widgets()

    def _create_widgets(self):
        """Create table widgets."""
        # Vertical scrollbar
        self.scrollbar_v = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self.scrollbar_h = ttk.Scrollbar(self, orient=tk.HORIZONTAL)

        # Treeview
        self.tree = ttk.Treeview(
            self,
            yscrollcommand=self.scrollbar_v.set,
            xscrollcommand=self.scrollbar_h.set
        )
        self.scrollbar_v.config(command=self.tree.yview)
        self.scrollbar_h.config(command=self.tree.xview)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        self.scrollbar_v.grid(row=0, column=1, sticky=tk.NS)
        self.scrollbar_h.grid(row=1, column=0, sticky=tk.EW)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def display_results(self, data: List[Dict[str, Any]], title: str) -> None:
        """
        Display query results in the table.

        Args:
            data: List of dictionaries containing the results
            title: Title for the results
        """
        # Clear existing data
        self.tree.delete(*self.tree.get_children())
        self._update_columns(list(data[0].keys()) if data else [])

        # Insert data
        for row in data:
            values = [str(row.get(col, '')) for col in self._get_columns()]
            self.tree.insert('', tk.END, values=values)

        # Set title (window title or label)
        self.master.title(f"{title} - {len(data)} row(s)")

    def _get_columns(self) -> List[str]:
        """Get current column names."""
        return self.tree.cget('columns')

    def _update_columns(self, columns: List[str]) -> None:
        """Update table columns."""
        # Clear existing columns
        self.tree['columns'] = []
        for col in self.tree['columns']:
            self.tree.heading(col, text='')
            self.tree.column(col, width=100)

        if not columns:
            self.tree['columns'] = ['No Results']
            self.tree.heading('No Results', text='No Results')
            self.tree.column('No Results', width=500)
            return

        # Set new columns
        self.tree['columns'] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.W)

    def clear(self):
        """Clear the table."""
        self.tree.delete(*self.tree.get_children())
        self._update_columns([])


class MainWindow:
    """Main application window."""

    def __init__(self):
        """Initialize the main window."""
        self.root = tk.Tk()
        self.root.title("SQL Query Tool - MySQL")
        self.root.geometry("1200x700")

        # Database connection
        self.connection_manager = ConnectionManager()
        self.query_manager = QueryManager(self.connection_manager)

        # Current results
        self.current_results = {}

        self._create_widgets()
        self._setup_menu()

    def _create_widgets(self) -> None:
        """Create GUI widgets."""
        # Top frame - Input and buttons
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X, side=tk.TOP)

        # Input frame
        input_frame = ttk.Frame(top_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # Label
        ttk.Label(input_frame, text="PROD_INST_ID:").pack(side=tk.LEFT, padx=(0, 5))

        # Entry field
        self.prod_inst_id_var = tk.StringVar()
        self.prod_inst_id_entry = ttk.Entry(
            input_frame,
            textvariable=self.prod_inst_id_var,
            width=30
        )
        self.prod_inst_id_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.prod_inst_id_entry.bind('<Return>', lambda e: self._run_all_queries())

        # Query buttons
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="Instance Info",
            command=self._query_instance_info
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Change Log",
            command=self._query_change_log
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Change Record",
            command=self._query_change_record
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Run All Queries",
            command=self._run_all_queries
        ).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Button(
            button_frame,
            text="Configuration",
            command=self._open_config_dialog
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Clear Results",
            command=self._clear_results
        ).pack(side=tk.LEFT, padx=5)

        # Notebook for tabbed results
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Create tabs
        self.result_tables = {}
        tab_names = [
            ('Instance Info', 'instance_info'),
            ('Change Log', 'change_log'),
            ('Change Record', 'change_record')
        ]

        for tab_name, key in tab_names:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_name)
            table = ResultsTable(frame)
            table.pack(fill=tk.BOTH, expand=True)
            self.result_tables[key] = table

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _setup_menu(self) -> None:
        """Setup application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Configuration", command=self._open_config_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Query menu
        query_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Query", menu=query_menu)
        query_menu.add_command(label="Instance Info", command=self._query_instance_info)
        query_menu.add_command(label="Change Log", command=self._query_change_log)
        query_menu.add_command(label="Change Record", command=self._query_change_record)
        query_menu.add_separator()
        query_menu.add_command(label="Run All Queries", command=self._run_all_queries)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _get_prod_inst_id(self) -> Optional[str]:
        """Get and validate PROD_INST_ID from input field."""
        prod_inst_id = self.prod_inst_id_var.get().strip()
        if not prod_inst_id:
            messagebox.showwarning("Input Required", "Please enter a PROD_INST_ID")
            self.prod_inst_id_entry.focus()
            return None
        return prod_inst_id

    def _execute_query(self, query_func, result_key: str, tab_name: str) -> None:
        """
        Execute a query and display results.

        Args:
            query_func: Query function to execute
            result_key: Key for storing results
            tab_name: Name of the tab for title
        """
        prod_inst_id = self._get_prod_inst_id()
        if not prod_inst_id:
            return

        self._set_status(f"Querying {tab_name}...")
        self.root.update()

        try:
            results = query_func(prod_inst_id)
            self.current_results[result_key] = results
            self.result_tables[result_key].display_results(results, tab_name)
            self.notebook.select(result_key)
            self._set_status(f"Query completed: {len(results)} row(s) returned")
        except Exception as e:
            messagebox.showerror("Query Error", f"Failed to execute query:\n{str(e)}")
            self._set_status("Query failed")

    def _query_instance_info(self) -> None:
        """Execute Instance Info query."""
        self._execute_query(
            self.query_manager.get_instance_info,
            'instance_info',
            'Instance Info'
        )

    def _query_change_log(self) -> None:
        """Execute Change Log query."""
        self._execute_query(
            self.query_manager.get_change_log,
            'change_log',
            'Change Log'
        )

    def _query_change_record(self) -> None:
        """Execute Change Record query."""
        self._execute_query(
            self.query_manager.get_change_record,
            'change_record',
            'Change Record'
        )

    def _run_all_queries(self) -> None:
        """Execute all three queries."""
        prod_inst_id = self._get_prod_inst_id()
        if not prod_inst_id:
            return

        self._set_status("Running all queries...")
        self.root.update()

        try:
            results = self.query_manager.get_all_queries(prod_inst_id)
            self.current_results = results

            # Display results in each tab
            self.result_tables['instance_info'].display_results(
                results['instance_info'], 'Instance Info'
            )
            self.result_tables['change_log'].display_results(
                results['change_log'], 'Change Log'
            )
            self.result_tables['change_record'].display_results(
                results['change_record'], 'Change Record'
            )

            # Select first tab
            self.notebook.select(0)

            total_rows = sum(len(r) for r in results.values())
            self._set_status(f"All queries completed: {total_rows} total row(s)")
        except Exception as e:
            messagebox.showerror("Query Error", f"Failed to execute queries:\n{str(e)}")
            self._set_status("Queries failed")

    def _clear_results(self) -> None:
        """Clear all results tables."""
        for table in self.result_tables.values():
            table.clear()
        self.current_results.clear()
        self.root.title("SQL Query Tool - MySQL")
        self._set_status("Results cleared")

    def _open_config_dialog(self) -> None:
        """Open configuration dialog."""
        ConfigDialog(
            self.root,
            self.connection_manager.config,
            self._on_config_save
        )

    def _on_config_save(self, config: dict) -> None:
        """Handle configuration save."""
        self.connection_manager.update_config(**config)
        self._set_status("Configuration saved")

    def _set_status(self, message: str) -> None:
        """Set status bar message."""
        self.status_var.set(message)

    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            "SQL Query Tool v1.0\n\n"
            "A simple tool to query MySQL database\n"
            "using PROD_INST_ID as input.\n\n"
            "Features:\n"
            "• Instance Information\n"
            "• Change Log\n"
            "• Change Record"
        )

    def run(self) -> None:
        """Start the application main loop."""
        # Check if database is configured
        if not self.connection_manager.config.get('database'):
            messagebox.showwarning(
                "Configuration Required",
                "Please configure your database connection first."
            )
            self._open_config_dialog()

        self.root.mainloop()
