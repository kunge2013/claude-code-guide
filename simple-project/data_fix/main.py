"""
SQL Query Tool - Main Entry Point

A Python GUI application to query MySQL database with three SQL templates
based on PROD_INST_ID input.

Usage:
    python main.py
"""
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.gui.main_window import MainWindow


def main():
    """Main entry point for the application."""
    try:
        app = MainWindow()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
