# ABOUTME: Main application entry point
# ABOUTME: Initializes and starts the PyQt application

import sys

from .utils import get_default_logger, init_logging


def main():
    """Main entry point for the application."""
    # Initialize logging system first
    try:
        init_logging()
        logger = get_default_logger()
        logger.info("Python Project Creator starting...")
        logger.info("Logging system initialized successfully")
    except Exception as e:
        print(f"Error initializing logging: {e}")
        print("Python Project Creator starting...")
        logger = None

    # Launch GUI application
    from .gui import main as gui_main

    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
