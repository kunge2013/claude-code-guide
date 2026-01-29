#!/usr/bin/env python3
"""
Run the Flask web server.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from src.langchain_graph_rag.utils.logger import setup_logger
from src.langchain_graph_rag.web.app import main


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()

    # Setup logger
    setup_logger(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE', 'logs/app.log')
    )

    # Run the Flask app
    main()
