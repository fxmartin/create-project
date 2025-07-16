# ABOUTME: Main application entry point
# ABOUTME: Initializes and starts the PyQt application

import sys
from pathlib import Path

from .utils import init_logging, get_default_logger


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
    
    if logger:
        logger.info("Project structure initialized successfully!")
    else:
        print("Project structure initialized successfully!")

    # Validate project structure
    project_root = Path(__file__).parent.parent
    if logger:
        logger.debug(f"Project root: {project_root}")
    else:
        print(f"Project root: {project_root}")

    # Check if main directories exist
    required_dirs = [
        "create_project/core",
        "create_project/gui",
        "create_project/utils",
        "create_project/templates",
        "create_project/resources",
        "create_project/config",
        "tests",
        "docs"
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            missing_dirs.append(dir_path)

    if missing_dirs:
        error_msg = f"Missing directories: {', '.join(missing_dirs)}"
        if logger:
            logger.error(error_msg)
        else:
            print(f"Error: {error_msg}")
        return 1

    if logger:
        logger.info("All required directories present!")
        logger.info("Ready for development!")
    else:
        print("All required directories present!")
        print("Ready for development!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
